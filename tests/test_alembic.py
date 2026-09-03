from pathlib import Path

from alembic import command
from alembic.config import Config

BASE_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BASE_DIR / "alembic.ini"
MIGRATIONS_DIR = BASE_DIR / "migrations"


def test_alembic_config_loads() -> None:
    config = Config(str(ALEMBIC_INI))
    script_location = config.get_main_option("script_location")
    assert script_location is not None
    assert (MIGRATIONS_DIR).resolve() == Path(script_location).resolve()


def test_alembic_url_not_hardcoded() -> None:
    config = Config(str(ALEMBIC_INI))
    assert config.get_main_option("sqlalchemy.url") == ""


def test_alembic_offline_upgrade_runs() -> None:
    """Exercise migrations/env.py (app settings + Base.metadata wiring) in
    offline mode, which does not require a live database."""
    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    command.upgrade(config, "head", sql=True)


def test_migrations_directory_exists() -> None:
    assert (MIGRATIONS_DIR / "versions").is_dir()
    assert (MIGRATIONS_DIR / "env.py").is_file()
    assert (MIGRATIONS_DIR / "script.py.mako").is_file()


def test_revision_chain_is_contiguous_single_head() -> None:
    from alembic.script import ScriptDirectory

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(config)

    heads = script.get_heads()
    assert len(heads) == 1, f"expected a single head, got {heads}"

    revision_id = heads[0]
    visited: set[str] = set()
    while revision_id is not None:
        assert revision_id not in visited, f"cycle detected at {revision_id}"
        visited.add(revision_id)
        current = script.get_revision(revision_id)
        revision_id = current.down_revision

    all_revisions = {r.revision for r in script.walk_revisions()}
    assert visited == all_revisions, "revision chain does not cover every migration"


def test_upgrade_base_to_head_then_downgrade_all() -> None:
    from alembic.script import ScriptDirectory

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(config)
    base = script.get_base()

    try:
        command.downgrade(config, base)
        tables = _current_public_tables() - {"alembic_version"}
        assert tables == set()
    finally:
        command.upgrade(config, "head")
    assert {"users", "media"} <= _current_public_tables()


def _current_public_tables() -> set[str]:
    import asyncio

    import asyncpg
    from sqlalchemy.engine import make_url

    from app.core.config import get_settings

    async def run() -> set[str]:
        url = make_url(get_settings().database_url)
        conn = await asyncpg.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            database=url.database,
        )
        try:
            rows = await conn.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            return {row["tablename"] for row in rows}
        finally:
            await conn.close()

    return asyncio.run(run())

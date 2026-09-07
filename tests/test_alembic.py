import asyncio
from pathlib import Path

import asyncpg
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

from app.core.config import get_settings

BASE_DIR = Path(__file__).resolve().parent.parent
ALEMBIC_INI = BASE_DIR / "alembic.ini"
MIGRATIONS_DIR = BASE_DIR / "migrations"


def _db_rows(sql: str, *args: object) -> list[asyncpg.Record]:
    async def run() -> list[asyncpg.Record]:
        url = make_url(get_settings().database_url)
        conn = await asyncpg.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            database=url.database,
        )
        try:
            return await conn.fetch(sql, *args)
        finally:
            await conn.close()

    return asyncio.run(run())


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


def test_migration_backfills_cms_media_links_from_legacy_urls() -> None:
    """The media-relationship migration converts existing string URL refs that
    exactly match a media row's public_url into Media foreign keys, without
    fabricating Media records for unmatched URLs."""
    from alembic.script import ScriptDirectory

    config = Config(str(ALEMBIC_INI))
    config.set_main_option("script_location", str(MIGRATIONS_DIR))
    script = ScriptDirectory.from_config(config)
    previous = "a1c3e5f7b9d2"
    assert previous in {r.revision for r in script.walk_revisions()}

    async def _seed_legacy() -> None:
        url = make_url(get_settings().database_url)
        conn = await asyncpg.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            database=url.database,
        )
        try:
            await conn.execute(
                """
                INSERT INTO media (id, original_name, storage_key, public_url, mime_type, size,
                                   created_at, updated_at)
                VALUES
                  ('00000000-0000-0000-0000-000000000001', 'cover.png', 'cover.png',
                   '/media/cover.png', 'image/png', 10, now(), now()),
                  ('00000000-0000-0000-0000-000000000002', 'video.mp4', 'video.mp4',
                   '/media/video.mp4', 'video/mp4', 10, now(), now())
                """
            )
            await conn.execute(
                """
                INSERT INTO projects (id, title, slug, status, featured, published, cover_image,
                                      demo_video_url, demo_video_type, created_at, updated_at)
                VALUES
                  ('10000000-0000-0000-0000-000000000001', 'Matched', 'matched', 'active',
                   false, true, '/media/cover.png', '/media/video.mp4', 'upload', now(), now()),
                  ('10000000-0000-0000-0000-000000000002', 'External', 'external', 'active',
                   false, true, 'https://example.com/custom.jpg',
                   'https://www.youtube.com/watch?v=xyz', 'youtube', now(), now())
                """
            )
        finally:
            await conn.close()

    try:
        command.downgrade(config, previous)
        asyncio.run(_seed_legacy())
        command.upgrade(config, "head")

        rows = _db_rows(
            """
            SELECT cover_media_id, demo_video_media_id
              FROM projects WHERE slug IN ('matched', 'external') ORDER BY slug
            """
        )
        external, matched = rows
        assert str(matched["cover_media_id"]) == "00000000-0000-0000-0000-000000000001"
        assert str(matched["demo_video_media_id"]) == "00000000-0000-0000-0000-000000000002"
        # Unmatched external URLs are NOT fabricated into Media records.
        assert external["cover_media_id"] is None
        assert external["demo_video_media_id"] is None
        assert _db_rows("SELECT count(*) AS n FROM media")[0]["n"] == 2
    finally:
        command.upgrade(config, "head")


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

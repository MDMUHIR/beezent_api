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

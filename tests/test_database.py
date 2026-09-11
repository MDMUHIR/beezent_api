from app.core.config import Settings, get_settings
from app.core.database import AsyncSessionLocal, engine, get_session
from app.models import Base, UUIDPrimaryKeyMixin


def test_settings_database_url() -> None:
    url = get_settings().database_url
    assert url.startswith("postgresql+asyncpg://")


def test_database_url_built_from_components(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setenv("DB_HOST", "db.example.com")
    monkeypatch.setenv("DB_PORT", "5433")
    monkeypatch.setenv("DB_USER", "app_user")
    monkeypatch.setenv("DB_PASSWORD", "p@ss:word")
    monkeypatch.setenv("DB_NAME", "beezents")
    settings = Settings()
    assert (
        settings.database_url
        == "postgresql+asyncpg://app_user:p%40ss%3Aword@db.example.com:5433/beezents"
    )


def test_database_url_override_takes_precedence(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://custom:custom@db:5432/custom")
    monkeypatch.setenv("DB_HOST", "ignored.example.com")
    settings = Settings()
    assert settings.database_url == "postgresql+asyncpg://custom:custom@db:5432/custom"


def test_engine_configuration() -> None:
    assert engine.url.get_backend_name() == "postgresql"
    assert engine.url.get_driver_name() == "asyncpg"


def test_session_factory_and_dependency_exist() -> None:
    assert callable(AsyncSessionLocal)
    assert callable(get_session)


def test_base_and_uuid_mixin() -> None:
    assert hasattr(Base, "metadata")
    assert "id" in UUIDPrimaryKeyMixin.__annotations__

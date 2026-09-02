from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine, get_session
from app.models import Base, UUIDPrimaryKeyMixin


def test_settings_database_url() -> None:
    url = get_settings().database_url
    assert url.startswith("postgresql+asyncpg://")


def test_engine_configuration() -> None:
    assert engine.url.get_backend_name() == "postgresql"
    assert engine.url.get_driver_name() == "asyncpg"


def test_session_factory_and_dependency_exist() -> None:
    assert callable(AsyncSessionLocal)
    assert callable(get_session)


def test_base_and_uuid_mixin() -> None:
    assert hasattr(Base, "metadata")
    assert "id" in UUIDPrimaryKeyMixin.__annotations__

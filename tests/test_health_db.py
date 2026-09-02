import asyncio

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.core.database import get_session
from app.main import app

client = TestClient(app)


async def _database_reachable() -> bool:
    probe_engine = create_async_engine(get_settings().database_url)
    try:
        async with probe_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
    finally:
        await probe_engine.dispose()


def test_db_health_when_database_available() -> None:
    if not asyncio.run(_database_reachable()):
        pytest.skip("PostgreSQL is not reachable at the configured DATABASE_URL")
    response = client.get("/api/v1/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_db_health_when_database_unavailable() -> None:
    broken_engine = create_async_engine(
        "postgresql+asyncpg://postgres:postgres@localhost:1/nope",
        connect_args={"timeout": 2},
    )
    broken_factory = async_sessionmaker(
        broken_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_session():
        async with broken_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    try:
        response = client.get("/api/v1/health/db")
        assert response.status_code == 503
        assert response.json() == {"detail": "Database unavailable"}
    finally:
        app.dependency_overrides.clear()

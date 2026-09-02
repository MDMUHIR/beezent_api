import asyncio
import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy.engine import make_url

BASE_DIR = Path(__file__).resolve().parent.parent

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/beezents_test",
)

# Point the application at the isolated test database before any app import.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _admin_dsn(url: str) -> str:
    parsed = make_url(url)
    return (
        f"postgresql://{parsed.username}:{parsed.password}"
        f"@{parsed.host}:{parsed.port or 5432}/postgres"
    )


def _test_dsn(url: str) -> str:
    parsed = make_url(url)
    return (
        f"postgresql://{parsed.username}:{parsed.password}"
        f"@{parsed.host}:{parsed.port or 5432}/{parsed.database}"
    )


async def _ensure_test_database() -> None:
    import asyncpg

    admin = await asyncpg.connect(_admin_dsn(TEST_DATABASE_URL))
    try:
        db = make_url(TEST_DATABASE_URL).database
        exists = await admin.fetchval("SELECT 1 FROM pg_database WHERE datname = $1", db)
        if not exists:
            await admin.execute(f'CREATE DATABASE "{db}"')
    finally:
        await admin.close()


async def _truncate_tables() -> None:
    import asyncpg

    conn = await asyncpg.connect(_test_dsn(TEST_DATABASE_URL))
    try:
        await conn.execute(
            "TRUNCATE TABLE users, user_sessions, projects, services, solutions, case_studies "
            "RESTART IDENTITY CASCADE"
        )
    finally:
        await conn.close()


@pytest.fixture(scope="session", autouse=True)
def prepared_database():
    """Ensure the isolated test database exists, is migrated, and is clean."""
    asyncio.run(_ensure_test_database())
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    command.upgrade(config, "head")
    asyncio.run(_truncate_tables())
    yield


@pytest.fixture(autouse=True)
def clean_tables():
    """Isolate each test with a clean users/user_sessions state."""
    asyncio.run(_truncate_tables())
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client

import asyncio
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


def run_db(coro: Any) -> Any:
    """Run an async coroutine `coro(session)` against the test database."""

    async def _runner() -> Any:
        engine = create_async_engine(get_settings().database_url)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with factory() as session:
                return await coro(session)
        finally:
            await engine.dispose()

    return asyncio.run(_runner())

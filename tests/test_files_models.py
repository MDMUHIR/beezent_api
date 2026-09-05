from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Media, User
from tests._db import run_db

BASE_DIR = Path(__file__).resolve().parent.parent


async def _table_names(session: AsyncSession) -> set[str]:
    result = await session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    return {row[0] for row in result}


def test_media_can_be_created() -> None:
    async def create(session: AsyncSession) -> None:
        media = Media(
            original_name="hero.png",
            storage_key="abc123.png",
            public_url="/media/abc123.png",
            mime_type="image/png",
            size=2048,
            width=1200,
            height=800,
            alt_text="Hero image",
            folder="projects",
        )
        session.add(media)
        await session.commit()
        await session.refresh(media)
        assert media.id is not None
        assert media.created_at is not None
        assert media.updated_at is not None
        assert media.size == 2048
        assert media.width == 1200
        assert media.height == 800
        assert media.uploaded_by is None

    run_db(create)


def test_media_optional_fields_default_null() -> None:
    async def create(session: AsyncSession) -> None:
        media = Media(
            original_name="logo.png",
            storage_key="def456.png",
            public_url="/media/def456.png",
            mime_type="image/png",
            size=512,
        )
        session.add(media)
        await session.commit()
        await session.refresh(media)
        assert media.width is None
        assert media.height is None
        assert media.alt_text is None
        assert media.folder is None

    run_db(create)


def test_media_uploaded_by_fk_set_null_on_user_delete() -> None:
    async def run(session: AsyncSession) -> None:
        user = User(email="uploader@example.com", password_hash="x", full_name="Uploader")
        session.add(user)
        await session.commit()

        media = Media(
            original_name="a.png",
            storage_key="fk1.png",
            public_url="/media/fk1.png",
            mime_type="image/png",
            size=1,
            uploaded_by=user.id,
        )
        session.add(media)
        await session.commit()

        await session.delete(user)
        await session.commit()
        await session.refresh(media)
        assert media.uploaded_by is None

    run_db(run)


def test_media_storage_key_unique() -> None:
    async def run(session: AsyncSession) -> None:
        session.add_all(
            [
                Media(
                    original_name="a.png",
                    storage_key="dup.png",
                    public_url="/media/dup.png",
                    mime_type="image/png",
                    size=1,
                ),
                Media(
                    original_name="b.png",
                    storage_key="dup.png",
                    public_url="/media/dup.png",
                    mime_type="image/png",
                    size=1,
                ),
            ]
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_media_size_check_constraint() -> None:
    async def run(session: AsyncSession) -> None:
        session.add(
            Media(
                original_name="a.png",
                storage_key="neg.png",
                public_url="/media/neg.png",
                mime_type="image/png",
                size=-1,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_media_required_fields_enforced() -> None:
    async def run(session: AsyncSession) -> None:
        session.add(
            Media(storage_key="x.png", public_url="/media/x.png", mime_type="image/png", size=1)
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_media_indexes_exist() -> None:
    async def run(session: AsyncSession) -> None:
        result = await session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'media'")
        )
        indexes = {row[0] for row in result}
        assert {"ix_media_created_at", "ix_media_folder", "ix_media_storage_key"} <= indexes

    run_db(run)


def test_media_table_exists() -> None:
    tables = run_db(_table_names)
    assert "media" in tables


def test_alembic_downgrade_and_upgrade_restores_latest_table() -> None:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    try:
        command.downgrade(config, "-1")
        tables_without_media = run_db(_table_names)
        assert "team_members" not in tables_without_media
    finally:
        command.upgrade(config, "head")
    tables = run_db(_table_names)
    assert "team_members" in tables

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
            mime_type="image/png",
            media_type="image",
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
        assert media.media_type == "image"
        assert media.duration_seconds is None
        assert media.uploaded_by is None

    run_db(create)


def test_media_optional_fields_default_null() -> None:
    async def create(session: AsyncSession) -> None:
        media = Media(
            original_name="logo.png",
            storage_key="def456.png",
            mime_type="image/png",
            media_type="image",
            size=512,
        )
        session.add(media)
        await session.commit()
        await session.refresh(media)
        assert media.width is None
        assert media.height is None
        assert media.alt_text is None
        assert media.folder is None
        assert media.duration_seconds is None

    run_db(create)


def test_media_public_url_is_derived_from_storage_key() -> None:
    async def create(session: AsyncSession) -> None:
        media = Media(
            original_name="a.png",
            storage_key="derived.png",
            mime_type="image/png",
            media_type="image",
            size=1,
        )
        session.add(media)
        await session.commit()
        await session.refresh(media)
        assert media.public_url == "/media/derived.png"

    run_db(create)


def test_media_uploaded_by_fk_set_null_on_user_delete() -> None:
    async def run(session: AsyncSession) -> None:
        user = User(email="uploader@example.com", password_hash="x", full_name="Uploader")
        session.add(user)
        await session.commit()

        media = Media(
            original_name="a.png",
            storage_key="fk1.png",
            mime_type="image/png",
            media_type="image",
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
                    mime_type="image/png",
                    media_type="image",
                    size=1,
                ),
                Media(
                    original_name="b.png",
                    storage_key="dup.png",
                    mime_type="image/png",
                    media_type="image",
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
                mime_type="image/png",
                media_type="image",
                size=-1,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_media_media_type_check_constraint() -> None:
    async def run(session: AsyncSession) -> None:
        session.add(
            Media(
                original_name="a.png",
                storage_key="bogus.png",
                mime_type="image/png",
                media_type="bogus",
                size=1,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_media_duration_check_constraint() -> None:
    async def run(session: AsyncSession) -> None:
        session.add(
            Media(
                original_name="v.mp4",
                storage_key="neg.mp4",
                mime_type="video/mp4",
                media_type="video",
                size=1,
                duration_seconds=-1,
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_media_required_fields_enforced() -> None:
    async def run(session: AsyncSession) -> None:
        session.add(Media(storage_key="x.png", mime_type="image/png", media_type="image", size=1))
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_media_indexes_exist() -> None:
    async def run(session: AsyncSession) -> None:
        result = await session.execute(
            text("SELECT indexname FROM pg_indexes WHERE tablename = 'media'")
        )
        indexes = {row[0] for row in result}
        assert {
            "ix_media_created_at",
            "ix_media_folder",
            "ix_media_media_type",
            "ix_media_storage_key",
        } <= indexes

    run_db(run)


def test_media_table_exists() -> None:
    tables = run_db(_table_names)
    assert "media" in tables


def test_alembic_downgrade_and_upgrade_restores_latest_table() -> None:
    async def _project_columns(session: AsyncSession) -> set[str]:
        result = await session.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = 'projects'")
        )
        return {row[0] for row in result}

    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    try:
        command.downgrade(config, "-1")
        columns_after_downgrade = run_db(_project_columns)
        assert "cover_media_id" not in columns_after_downgrade
    finally:
        command.upgrade(config, "head")
    columns = run_db(_project_columns)
    assert "cover_media_id" in columns

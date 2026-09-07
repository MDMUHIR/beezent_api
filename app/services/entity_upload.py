"""Entity-scoped file uploads: store the raw file and auto-link it to a CMS
entity in a single multipart request.

This replaces the generic ``POST /admin/files`` upload. The API reads the file
bytes together with the entity payload, validates + stores the file, then
links the resulting :class:`Media` record to the entity's image/cover and
demo-video fields automatically.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, UploadFile, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.storage import get_storage
from app.models import Media, User
from app.models.enums import DemoVideoType
from app.services.media import resolve_upload, store_media


def safe_original_name(filename: str | None) -> str:
    """Strip path components and control characters from a client filename."""
    if not filename:
        return "file"
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = name.replace("\x00", "").strip()
    return (name or "file")[:255]


def parse_payload[PayloadModelT: BaseModel](
    model: type[PayloadModelT], payload: str
) -> PayloadModelT:
    """Validate a JSON form-field payload, mapping Pydantic errors to a 422."""
    try:
        return model.model_validate_json(payload)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=[
                {"loc": list(err["loc"]), "msg": err["msg"], "type": err["type"]}
                for err in exc.errors()
            ],
        ) from None


async def store_upload(
    session: AsyncSession,
    current_user: User,
    file: UploadFile,
    *,
    folder: str | None = None,
) -> Media:
    """Validate and store an uploaded file, returning the persisted Media."""
    settings = get_settings()
    content = await file.read()
    max_size = (
        settings.media_max_video_size_bytes
        if (file.content_type or "").lower().startswith("video/")
        else settings.media_max_size_bytes
    )
    inspected, storage_key, folder, alt_text = resolve_upload(
        mime_type=file.content_type,
        folder=folder,
        alt_text=None,
        max_size=max_size,
        content=content,
    )
    return await store_media(
        session,
        original_name=safe_original_name(file.filename),
        mime_type=(file.content_type or "").lower().strip(),
        inspected=inspected,
        storage_key=storage_key,
        size=len(content),
        content=content,
        folder=folder,
        alt_text=alt_text,
        uploaded_by=current_user.id,
    )


async def attach_uploaded_image(
    session: AsyncSession,
    current_user: User,
    obj: Any,
    file: UploadFile,
    *,
    fk_attr: str,
    rel_attr: str,
    url_attr: str,
) -> Media:
    """Store an image file and wire it to an entity's image/cover fields."""
    media = await store_upload(session, current_user, file)
    setattr(obj, fk_attr, media.id)
    setattr(obj, rel_attr, media)
    setattr(obj, url_attr, media.public_url)
    return media


async def attach_uploaded_video(
    session: AsyncSession,
    current_user: User,
    obj: Any,
    file: UploadFile,
) -> Media:
    """Store a demo-video file and wire it to an entity's demo-video fields."""
    media = await store_upload(session, current_user, file)
    obj.demo_video_media_id = media.id
    obj.demo_video_media = media
    obj.demo_video_url = media.public_url
    obj.demo_video_type = DemoVideoType.UPLOAD
    return media


async def rollback_media(session: AsyncSession, media_list: list[Media]) -> None:
    """Best-effort removal of media created for an entity that failed to commit.

    Used when the parent entity insert/update raises after the files were
    already stored and committed, to avoid leaving orphaned media records.
    """
    for media in media_list:
        row = await session.get(Media, media.id)
        if row is None:
            continue
        await get_storage().delete(row.storage_key)
        await session.delete(row)
    await session.commit()

"""Helpers for wiring Media records into CMS entities.

Media UUID foreign keys are the canonical relationship. The legacy string
columns (``cover_image``, ``image_url``, ``avatar_url``, ``demo_video_url``)
are kept for backward compatibility and are automatically mirrored from the
linked media so the two never drift.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Media
from app.models.enums import DemoVideoType


async def require_media(session: AsyncSession, media_id: UUID, field_name: str) -> Media:
    """Fetch a media record or raise 422 (safe: no internal details)."""
    media = await session.get(Media, media_id)
    if media is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Referenced {field_name} does not exist",
        )
    return media


def pop_media_fields(data: dict[str, Any], fields: list[str]) -> dict[str, Any]:
    """Extract the media FK fields from a validated payload dict.

    Returned values may be a UUID or ``None`` (explicit unlink). Fields absent
    from the payload are not returned so the generic attribute loop ignores
    them (PATCH semantics preserved).
    """
    return {field: data.pop(field) for field in fields if field in data}


async def apply_image_media(
    session: AsyncSession,
    obj: Any,
    *,
    value: UUID | None,
    data: dict[str, Any],
    fk_attr: str,
    rel_attr: str,
    url_attr: str,
    field_name: str,
) -> None:
    """Set (or unlink) an image media reference and mirror the legacy URL."""
    if value is None:
        setattr(obj, fk_attr, None)
        setattr(obj, rel_attr, None)
        setattr(obj, url_attr, None)
        return
    media = await require_media(session, value, field_name)
    setattr(obj, fk_attr, media.id)
    setattr(obj, rel_attr, media)
    setattr(obj, url_attr, media.public_url)
    # The linked media is canonical: drop any legacy URL the client also sent.
    data.pop(url_attr, None)


async def apply_demo_video_media(
    session: AsyncSession,
    obj: Any,
    *,
    value: UUID | None,
    data: dict[str, Any],
) -> None:
    """Set (or unlink) an uploaded demo video.

    A linked media is canonical for ``type == "upload"`` and forces the
    ``demo_video_url``/``demo_video_type`` columns to stay consistent. External
    (YouTube) videos never get a Media row: they keep the URL + ``youtube``
    type and a ``None`` media reference.
    """
    if value is None:
        obj.demo_video_media_id = None
        obj.demo_video_media = None
        if data.get("demo_video_type") in (None, DemoVideoType.UPLOAD):
            obj.demo_video_url = None
            obj.demo_video_type = None
        return
    media = await require_media(session, value, "demo_video_media_id")
    obj.demo_video_media_id = media.id
    obj.demo_video_media = media
    obj.demo_video_url = media.public_url
    obj.demo_video_type = DemoVideoType.UPLOAD
    # The linked media is canonical: drop any legacy URL/type the client sent.
    data.pop("demo_video_url", None)
    data.pop("demo_video_type", None)

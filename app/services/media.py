"""Domain logic for uploading, inspecting and deleting media.

Routes stay thin; this service owns the safe upload/delete flow and the
interaction between the storage backend and PostgreSQL metadata. Storage and
database are intentionally *not* transactional together; failures use
best-effort cleanup (documented in the phase report).
"""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media_validation import InspectedMedia, inspect_upload
from app.core.storage import ALLOWED_MIME_TYPES, build_storage_key, get_storage
from app.models import CaseStudy, Media, Project, Solution, TeamMember
from app.schemas.files import normalize_folder


def resolve_upload(
    *,
    mime_type: str | None,
    folder: str | None,
    alt_text: str | None,
    max_size: int,
    content: bytes,
) -> tuple[InspectedMedia, str, str | None, str | None]:
    """Validate an upload's declared metadata + content.

    Returns ``(inspected, storage_key, normalized_folder, normalized_alt)``.
    Raises :class:`HTTPException` with a safe, specific status on failure.
    """
    mime_type = (mime_type or "").lower().strip()
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported file type",
        )

    if len(content) > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File is too large",
        )

    normalized_folder = None
    if folder is not None:
        try:
            normalized_folder = normalize_folder(folder)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid folder name",
            ) from None

    try:
        inspected = inspect_upload(mime_type, content)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from None

    return inspected, build_storage_key(mime_type), normalized_folder, alt_text


async def store_media(
    session: AsyncSession,
    *,
    original_name: str,
    mime_type: str,
    inspected: InspectedMedia,
    storage_key: str,
    size: int,
    content: bytes,
    folder: str | None,
    alt_text: str | None,
    uploaded_by: UUID,
) -> Media:
    """Persist the file to storage, then record metadata in PostgreSQL.

    Ordering:
      1. write the object to storage,
      2. insert the Media row,
      3. commit.

    If the database commit fails after a successful storage write, the object
    is deleted best-effort (orphan cleanup). If storage itself fails, no Media
    record is created and no cleanup is needed.
    """
    storage = get_storage()
    await storage.save(storage_key, content)

    media = Media(
        original_name=original_name,
        storage_key=storage_key,
        mime_type=mime_type,
        media_type=inspected.media_type,
        size=size,
        width=inspected.width,
        height=inspected.height,
        duration_seconds=inspected.duration_seconds,
        alt_text=alt_text,
        folder=folder,
        uploaded_by=uploaded_by,
    )
    session.add(media)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        await storage.delete(storage_key)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not store the file",
        ) from None
    await session.refresh(media)
    return media


async def media_references(session: AsyncSession, media_id: UUID) -> dict[str, int]:
    """Return a count of CMS references to a media record per entity type."""
    references: dict[str, int] = {}
    for name, stmt in (
        ("projects", select(Project.id).where(Project.cover_media_id == media_id)),
        (
            "project_demo_videos",
            select(Project.id).where(Project.demo_video_media_id == media_id),
        ),
        ("solutions", select(Solution.id).where(Solution.image_media_id == media_id)),
        (
            "solution_demo_videos",
            select(Solution.id).where(Solution.demo_video_media_id == media_id),
        ),
        ("case_studies", select(CaseStudy.id).where(CaseStudy.image_media_id == media_id)),
        ("team_members", select(TeamMember.id).where(TeamMember.avatar_media_id == media_id)),
    ):
        count = len(list((await session.scalars(stmt.limit(100))).all()))
        if count:
            references[name] = count
    return references


async def delete_media(session: AsyncSession, media: Media) -> None:
    """Safely delete a media record.

    Referenced media are rejected with ``409 Conflict`` (the CMS rows keep
    their references; media is never cascade-deleted and a Media delete never
    silently breaks a CMS reference).

    Deletion order: remove the storage object first, then the database row.
    If the row delete fails after the object is removed, the metadata row
    remains pointing at a missing object - safer than leaving an orphaned
    object with no database record.
    """
    references = await media_references(session, media.id)
    if references:
        used_in = ", ".join(f"{k} ({v})" for k, v in sorted(references.items()))
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Media is referenced by {used_in} and cannot be deleted",
        )

    await get_storage().delete(media.storage_key)
    await session.delete(media)
    await session.commit()

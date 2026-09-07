from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_staff
from app.api.v1.endpoints.common import get_object_or_404, paginate
from app.core.database import get_session
from app.models import Media, User
from app.schemas import MediaAdmin, MediaMetadataUpdate, PaginatedResponse
from app.services.media import delete_media

router = APIRouter(prefix="/admin/files", tags=["admin-files"])


@router.get("", response_model=PaginatedResponse[MediaAdmin])
async def list_media(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    folder: str | None = Query(None, max_length=100),
    media_type: Literal["image", "video", "document"] | None = Query(None),
    mime_type: str | None = Query(None, max_length=100),
    q: str | None = Query(None, max_length=100),
    sort: Literal["created_at", "size", "original_name"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[MediaAdmin]:
    stmt = select(Media)
    if folder:
        stmt = stmt.where(Media.folder == folder)
    if media_type:
        stmt = stmt.where(Media.media_type == media_type)
    if mime_type:
        stmt = stmt.where(Media.mime_type == mime_type)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Media.original_name.ilike(pattern),
                Media.mime_type.ilike(pattern),
            )
        )
    column = getattr(Media, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{media_id}", response_model=MediaAdmin)
async def get_media(
    media_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Media:
    return await get_object_or_404(session, Media, media_id)


@router.patch("/{media_id}", response_model=MediaAdmin)
async def update_media(
    media_id: UUID,
    payload: MediaMetadataUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Media:
    media = await get_object_or_404(session, Media, media_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(media, key, value)
    await session.commit()
    await session.refresh(media)
    return media


@router.delete("/{media_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_endpoint(
    media_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    media = await get_object_or_404(session, Media, media_id)
    await delete_media(session, media)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

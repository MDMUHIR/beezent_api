from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_staff
from app.api.v1.endpoints.common import get_object_or_404, paginate
from app.core.config import get_settings
from app.core.database import get_session
from app.core.storage import ALLOWED_MIME_TYPES, build_storage_key, get_storage
from app.models import Media, User
from app.schemas import MediaAdmin, MediaMetadataUpdate, PaginatedResponse
from app.schemas.files import normalize_folder

router = APIRouter(prefix="/admin/files", tags=["admin-files"])


def _safe_original_name(filename: str | None) -> str:
    """Strip path components and control characters from a client filename."""
    if not filename:
        return "file"
    name = filename.replace("\\", "/").rsplit("/", 1)[-1]
    name = name.replace("\x00", "").strip()
    return (name or "file")[:255]


@router.get("", response_model=PaginatedResponse[MediaAdmin])
async def list_media(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    folder: str | None = Query(None, max_length=100),
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


@router.post("", response_model=MediaAdmin, status_code=status.HTTP_201_CREATED)
async def upload_media(
    file: UploadFile = File(...),
    folder: str | None = Form(None, max_length=100),
    alt_text: str | None = Form(None, max_length=500),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_staff),
) -> Media:
    mime_type = (file.content_type or "").lower()
    if mime_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Unsupported file type",
        )

    if folder is not None:
        try:
            folder = normalize_folder(folder)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Invalid folder name",
            ) from None

    content = await file.read()
    if len(content) > get_settings().media_max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File is too large",
        )

    storage = get_storage()
    storage_key = build_storage_key(mime_type)
    result = await storage.save(storage_key, content)

    media = Media(
        original_name=_safe_original_name(file.filename),
        storage_key=result.storage_key,
        public_url=result.public_url,
        mime_type=mime_type,
        size=len(content),
        alt_text=alt_text,
        folder=folder,
        uploaded_by=current_user.id,
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
async def delete_media(
    media_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    media = await get_object_or_404(session, Media, media_id)
    await get_storage().delete(media.storage_key)
    await session.delete(media)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

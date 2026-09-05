from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_staff
from app.api.v1.endpoints.common import (
    get_object_or_404,
    integrity_error_response,
    paginate,
    slug_exists,
)
from app.core.database import get_session
from app.models import ServiceCategory, User
from app.schemas import (
    PaginatedResponse,
    ServiceCategoryAdmin,
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
)

router = APIRouter(prefix="/admin/service-categories", tags=["admin-service-categories"])


@router.get("", response_model=PaginatedResponse[ServiceCategoryAdmin])
async def list_service_categories(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    sort: Literal["sort_order", "name", "created_at"] = "sort_order",
    order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[ServiceCategoryAdmin]:
    stmt = select(ServiceCategory)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                ServiceCategory.name.ilike(pattern),
                ServiceCategory.slug.ilike(pattern),
            )
        )
    column = getattr(ServiceCategory, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("", response_model=ServiceCategoryAdmin, status_code=status.HTTP_201_CREATED)
async def create_service_category(
    payload: ServiceCategoryCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> ServiceCategory:
    if await slug_exists(session, ServiceCategory, payload.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{payload.slug}' is already in use",
        )
    category = ServiceCategory(**payload.model_dump())
    session.add(category)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(category)
    return category


@router.get("/{category_id}", response_model=ServiceCategoryAdmin)
async def get_service_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> ServiceCategory:
    return await get_object_or_404(session, ServiceCategory, category_id)


@router.patch("/{category_id}", response_model=ServiceCategoryAdmin)
async def update_service_category(
    category_id: UUID,
    payload: ServiceCategoryUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> ServiceCategory:
    category = await get_object_or_404(session, ServiceCategory, category_id)
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, ServiceCategory, data["slug"], exclude_id=category.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    for key, value in data.items():
        setattr(category, key, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service_category(
    category_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    category = await get_object_or_404(session, ServiceCategory, category_id)
    await session.delete(category)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

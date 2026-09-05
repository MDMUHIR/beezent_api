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
from app.models import Service, ServiceCategory, User
from app.schemas import PaginatedResponse, ServiceAdmin, ServiceCreate, ServiceUpdate

router = APIRouter(prefix="/admin/services", tags=["admin-services"])


async def _resolve_categories(session: AsyncSession, ids: list[UUID]) -> list[ServiceCategory]:
    """Resolve category ids to ORM objects, raising 422 if any is unknown."""
    if not ids:
        return []
    cats = list(
        (await session.scalars(select(ServiceCategory).where(ServiceCategory.id.in_(ids)))).all()
    )
    if len(cats) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="One or more categories do not exist",
        )
    return cats


@router.get("", response_model=PaginatedResponse[ServiceAdmin])
async def list_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    sort: Literal["sort_order", "name", "created_at"] = "sort_order",
    order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[ServiceAdmin]:
    stmt = select(Service)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Service.name.ilike(pattern), Service.slug.ilike(pattern)))
    column = getattr(Service, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("", response_model=ServiceAdmin, status_code=status.HTTP_201_CREATED)
async def create_service(
    payload: ServiceCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Service:
    if await slug_exists(session, Service, payload.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{payload.slug}' is already in use",
        )
    data = payload.model_dump(exclude={"category_ids"})
    service = Service(**data)
    if payload.category_ids:
        service.categories = await _resolve_categories(session, payload.category_ids)
    session.add(service)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(service)
    return service


@router.get("/{service_id}", response_model=ServiceAdmin)
async def get_service(
    service_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Service:
    return await get_object_or_404(session, Service, service_id)


@router.patch("/{service_id}", response_model=ServiceAdmin)
async def update_service(
    service_id: UUID,
    payload: ServiceUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Service:
    service = await get_object_or_404(session, Service, service_id)
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, Service, data["slug"], exclude_id=service.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    categories = None
    if "category_ids" in data:
        ids = data.pop("category_ids")
        categories = await _resolve_categories(session, ids) if ids else []
    for key, value in data.items():
        setattr(service, key, value)
    if categories is not None:
        service.categories = categories
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(service)
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    service = await get_object_or_404(session, Service, service_id)
    await session.delete(service)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

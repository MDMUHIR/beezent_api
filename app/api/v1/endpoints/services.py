from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.common import paginate
from app.core.database import get_session
from app.models import Service
from app.schemas import PaginatedResponse, ServicePublic

router = APIRouter(prefix="/services", tags=["services"])


@router.get("", response_model=PaginatedResponse[ServicePublic])
async def list_services(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    q: str | None = Query(None, max_length=100),
    featured: bool | None = None,
    sort: Literal["sort_order", "name", "created_at"] = "sort_order",
    order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[ServicePublic]:
    stmt = select(Service).where(Service.published.is_(True))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Service.name.ilike(pattern),
                Service.short_description.ilike(pattern),
                Service.description.ilike(pattern),
            )
        )
    if featured is not None:
        stmt = stmt.where(Service.featured.is_(featured))

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


@router.get("/{slug}", response_model=ServicePublic)
async def get_service(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> Service:
    service = await session.scalar(
        select(Service).where(Service.slug == slug, Service.published.is_(True))
    )
    if service is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return service

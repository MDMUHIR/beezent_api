from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Service, ServiceCategory
from app.schemas import ServiceCategoryDetail, ServiceCategoryPublic

router = APIRouter(prefix="/service-categories", tags=["service-categories"])


@router.get("", response_model=list[ServiceCategoryPublic])
async def list_service_categories(
    session: AsyncSession = Depends(get_session),
) -> list[ServiceCategory]:
    stmt = select(ServiceCategory).order_by(
        ServiceCategory.sort_order.asc(),
        ServiceCategory.name.asc(),
    )
    return list((await session.scalars(stmt)).all())


@router.get("/{slug}", response_model=ServiceCategoryDetail)
async def get_service_category(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> ServiceCategoryDetail:
    """Return a category together with its published services."""
    category = await session.scalar(select(ServiceCategory).where(ServiceCategory.slug == slug))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    services_stmt = (
        select(Service)
        .join(Service.categories)
        .where(ServiceCategory.slug == slug, Service.published.is_(True))
        .order_by(Service.sort_order.asc(), Service.name.asc())
    )
    services = list((await session.scalars(services_stmt)).all())

    return ServiceCategoryDetail(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        sort_order=category.sort_order,
        services=services,
    )

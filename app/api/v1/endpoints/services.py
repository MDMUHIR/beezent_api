from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_editor, get_db
from app.models.service import Service, ServiceCategory, TechStack
from app.models.user import User
from app.schemas.service import (
    ServiceCategoryCreate,
    ServiceCategoryResponse,
    ServiceCategoryUpdate,
    ServiceCategoryWithServicesResponse,
    ServiceCreate,
    ServiceResponse,
    ServiceUpdate,
    TechStackCreate,
    TechStackResponse,
    TechStackUpdate,
)

router = APIRouter()


# ------------------ Public Service Categories ------------------ #
@router.get("/categories", response_model=List[ServiceCategoryWithServicesResponse], summary="List all service categories with nested services")
async def list_categories(
    include_inactive: bool = False,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(ServiceCategory).options(
        selectinload(ServiceCategory.services).selectinload(Service.tech_stacks)
    ).order_by(ServiceCategory.display_order, ServiceCategory.name)

    if not include_inactive:
        stmt = stmt.where(ServiceCategory.is_active.is_(True))

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/categories", response_model=ServiceCategoryResponse, status_code=status.HTTP_201_CREATED, summary="Create a new service category (Editor only)")
async def create_category(
    category_in: ServiceCategoryCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    existing = await db.execute(select(ServiceCategory).where(ServiceCategory.slug == category_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category slug already exists")

    category = ServiceCategory(**category_in.model_dump())
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


# ------------------ Public Services ------------------ #
@router.get("/", response_model=List[ServiceResponse], summary="List services with filtering")
async def list_services(
    category_id: Optional[int] = None,
    category_slug: Optional[str] = None,
    featured: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(Service)
        .options(selectinload(Service.category), selectinload(Service.tech_stacks))
        .where(Service.is_active.is_(True))
        .order_by(Service.display_order, Service.title)
    )

    if category_id is not None:
        stmt = stmt.where(Service.category_id == category_id)
    if category_slug:
        stmt = stmt.join(Service.category).where(ServiceCategory.slug == category_slug)
    if featured is not None:
        stmt = stmt.where(Service.featured == featured)
    if search:
        search_pattern = f"%{search}%"
        stmt = stmt.where(
            Service.title.ilike(search_pattern) | Service.short_description.ilike(search_pattern)
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{slug}", response_model=ServiceResponse, summary="Get service by slug")
async def get_service_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(Service)
        .options(selectinload(Service.category), selectinload(Service.tech_stacks))
        .where(Service.slug == slug, Service.is_active.is_(True))
    )
    result = await db.execute(stmt)
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service


@router.post("/", response_model=ServiceResponse, status_code=status.HTTP_201_CREATED, summary="Create a new service (Editor only)")
async def create_service(
    service_in: ServiceCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    existing = await db.execute(select(Service).where(Service.slug == service_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Service slug already exists")

    data = service_in.model_dump(exclude={"tech_stack_ids"})
    service = Service(**data)

    if service_in.tech_stack_ids:
        stacks = await db.execute(select(TechStack).where(TechStack.id.in_(service_in.tech_stack_ids)))
        service.tech_stacks = list(stacks.scalars().all())

    db.add(service)
    await db.commit()
    await db.refresh(service, ["category", "tech_stacks"])
    return service


@router.put("/{service_id}", response_model=ServiceResponse, summary="Update a service (Editor only)")
async def update_service(
    service_id: int,
    service_in: ServiceUpdate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(Service).options(selectinload(Service.tech_stacks)).where(Service.id == service_id)
    result = await db.execute(stmt)
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = service_in.model_dump(exclude_unset=True)
    tech_stack_ids = update_data.pop("tech_stack_ids", None)

    for field, value in update_data.items():
        setattr(service, field, value)

    if tech_stack_ids is not None:
        stacks = await db.execute(select(TechStack).where(TechStack.id.in_(tech_stack_ids)))
        service.tech_stacks = list(stacks.scalars().all())

    await db.commit()
    await db.refresh(service, ["category", "tech_stacks"])
    return service


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a service (Admin only)")
async def delete_service(
    service_id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(Service).where(Service.id == service_id)
    service = (await db.execute(stmt)).scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    await db.delete(service)
    await db.commit()


# ------------------ Tech Stacks ------------------ #
@router.get("/tech-stacks/all", response_model=List[TechStackResponse], summary="List all active tech stacks")
async def list_tech_stacks(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(TechStack).where(TechStack.is_active.is_(True)).order_by(TechStack.category, TechStack.name)
    if category:
        stmt = stmt.where(TechStack.category.ilike(category))
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/tech-stacks", response_model=TechStackResponse, status_code=status.HTTP_201_CREATED, summary="Create a tech stack item (Editor only)")
async def create_tech_stack(
    stack_in: TechStackCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stack = TechStack(**stack_in.model_dump())
    db.add(stack)
    await db.commit()
    await db.refresh(stack)
    return stack

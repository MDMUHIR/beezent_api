from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_editor, get_db
from app.models.social_proof import CompanyStat, PressCoverage, Testimonial
from app.models.user import User
from app.schemas.social_proof import (
    CompanyStatCreate,
    CompanyStatResponse,
    CompanyStatUpdate,
    PressCoverageCreate,
    PressCoverageResponse,
    PressCoverageUpdate,
    TestimonialCreate,
    TestimonialResponse,
    TestimonialUpdate,
)

router = APIRouter()


# ------------------ Testimonials ------------------ #
@router.get("/testimonials", response_model=List[TestimonialResponse], summary="List client testimonials")
async def list_testimonials(
    featured: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(Testimonial)
        .where(Testimonial.is_active.is_(True))
        .order_by(Testimonial.display_order, Testimonial.rating.desc())
    )
    if featured is not None:
        stmt = stmt.where(Testimonial.featured == featured)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/testimonials", response_model=TestimonialResponse, status_code=status.HTTP_201_CREATED, summary="Create a testimonial (Editor only)")
async def create_testimonial(
    item_in: TestimonialCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    item = Testimonial(**item_in.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.put("/testimonials/{id}", response_model=TestimonialResponse, summary="Update a testimonial (Editor only)")
async def update_testimonial(
    id: int,
    item_in: TestimonialUpdate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(Testimonial).where(Testimonial.id == id)
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Testimonial not found")

    for k, v in item_in.model_dump(exclude_unset=True).items():
        setattr(item, k, v)

    await db.commit()
    await db.refresh(item)
    return item


# ------------------ Press Coverage ------------------ #
@router.get("/press", response_model=List[PressCoverageResponse], summary="List media and press coverage")
async def list_press(
    featured: Optional[bool] = None,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(PressCoverage)
        .where(PressCoverage.is_active.is_(True))
        .order_by(PressCoverage.display_order, PressCoverage.published_date.desc().nullslast())
    )
    if featured is not None:
        stmt = stmt.where(PressCoverage.featured == featured)

    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/press", response_model=PressCoverageResponse, status_code=status.HTTP_201_CREATED, summary="Create press item (Editor only)")
async def create_press(
    item_in: PressCoverageCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    item = PressCoverage(**item_in.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


# ------------------ Company Stats ------------------ #
@router.get("/stats", response_model=List[CompanyStatResponse], summary="List key agency metrics & stats")
async def list_stats(db: AsyncSession = Depends(get_db)) -> Any:
    stmt = select(CompanyStat).where(CompanyStat.is_active.is_(True)).order_by(CompanyStat.display_order)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/stats", response_model=CompanyStatResponse, status_code=status.HTTP_201_CREATED, summary="Create company stat (Editor only)")
async def create_stat(
    item_in: CompanyStatCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    item = CompanyStat(**item_in.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item

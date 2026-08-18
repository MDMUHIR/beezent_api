from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_editor, get_db
from app.models.case_study import CaseStudy, CaseStudyMetric, Industry
from app.models.user import User
from app.schemas.case_study import (
    CaseStudyCreate,
    CaseStudyResponse,
    CaseStudyUpdate,
    IndustryCreate,
    IndustryResponse,
    IndustryUpdate,
)

router = APIRouter()


# ------------------ Industries ------------------ #
@router.get("/industries", response_model=List[IndustryResponse], summary="List all industries")
async def list_industries(db: AsyncSession = Depends(get_db)) -> Any:
    stmt = select(Industry).order_by(Industry.name)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post("/industries", response_model=IndustryResponse, status_code=status.HTTP_201_CREATED, summary="Create an industry (Editor only)")
async def create_industry(
    industry_in: IndustryCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    existing = await db.execute(select(Industry).where(Industry.slug == industry_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Industry slug already exists")

    industry = Industry(**industry_in.model_dump())
    db.add(industry)
    await db.commit()
    await db.refresh(industry)
    return industry


# ------------------ Case Studies ------------------ #
@router.get("/", response_model=List[CaseStudyResponse], summary="List published case studies")
async def list_case_studies(
    industry_id: Optional[int] = None,
    industry_slug: Optional[str] = None,
    featured: Optional[bool] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(CaseStudy)
        .options(selectinload(CaseStudy.industry), selectinload(CaseStudy.metrics))
        .where(CaseStudy.is_published.is_(True))
        .order_by(CaseStudy.display_order, CaseStudy.created_at.desc())
    )

    if industry_id is not None:
        stmt = stmt.where(CaseStudy.industry_id == industry_id)
    if industry_slug:
        stmt = stmt.join(CaseStudy.industry).where(Industry.slug == industry_slug)
    if featured is not None:
        stmt = stmt.where(CaseStudy.featured == featured)
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            CaseStudy.title.ilike(search_term)
            | CaseStudy.client_name.ilike(search_term)
            | CaseStudy.summary.ilike(search_term)
        )

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{slug}", response_model=CaseStudyResponse, summary="Get full case study by slug")
async def get_case_study_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(CaseStudy)
        .options(selectinload(CaseStudy.industry), selectinload(CaseStudy.metrics))
        .where(CaseStudy.slug == slug, CaseStudy.is_published.is_(True))
    )
    result = await db.execute(stmt)
    case_study = result.scalar_one_or_none()
    if not case_study:
        raise HTTPException(status_code=404, detail="Case study not found")
    return case_study


@router.post("/", response_model=CaseStudyResponse, status_code=status.HTTP_201_CREATED, summary="Create a new case study (Editor only)")
async def create_case_study(
    study_in: CaseStudyCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    existing = await db.execute(select(CaseStudy).where(CaseStudy.slug == study_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Case study slug already exists")

    study_data = study_in.model_dump(exclude={"metrics"})
    case_study = CaseStudy(**study_data)

    if study_in.metrics:
        for metric_data in study_in.metrics:
            metric = CaseStudyMetric(**metric_data.model_dump())
            case_study.metrics.append(metric)

    db.add(case_study)
    await db.commit()
    await db.refresh(case_study, ["industry", "metrics"])
    return case_study


@router.put("/{id}", response_model=CaseStudyResponse, summary="Update a case study (Editor only)")
async def update_case_study(
    id: int,
    study_in: CaseStudyUpdate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(CaseStudy).options(selectinload(CaseStudy.metrics)).where(CaseStudy.id == id)
    result = await db.execute(stmt)
    case_study = result.scalar_one_or_none()
    if not case_study:
        raise HTTPException(status_code=404, detail="Case study not found")

    update_dict = study_in.model_dump(exclude_unset=True)
    metrics_data = update_dict.pop("metrics", None)

    for key, value in update_dict.items():
        setattr(case_study, key, value)

    if metrics_data is not None:
        case_study.metrics.clear()
        for m in metrics_data:
            case_study.metrics.append(CaseStudyMetric(**m))

    await db.commit()
    await db.refresh(case_study, ["industry", "metrics"])
    return case_study


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a case study (Admin only)")
async def delete_case_study(
    id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(CaseStudy).where(CaseStudy.id == id)
    case_study = (await db.execute(stmt)).scalar_one_or_none()
    if not case_study:
        raise HTTPException(status_code=404, detail="Case study not found")
    await db.delete(case_study)
    await db.commit()

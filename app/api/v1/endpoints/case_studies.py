from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.endpoints.common import paginate
from app.core.database import get_session
from app.models import CaseStudy, Project
from app.schemas import CaseStudyPublic, PaginatedResponse

router = APIRouter(prefix="/case-studies", tags=["case-studies"])


@router.get("", response_model=PaginatedResponse[CaseStudyPublic])
async def list_case_studies(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    q: str | None = Query(None, max_length=100),
    featured: bool | None = None,
    project_slug: str | None = Query(None, max_length=255),
    sort: Literal["created_at", "title"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[CaseStudyPublic]:
    stmt = (
        select(CaseStudy)
        .options(selectinload(CaseStudy.project))
        .where(CaseStudy.published.is_(True))
    )
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                CaseStudy.title.ilike(pattern),
                CaseStudy.summary.ilike(pattern),
            )
        )
    if featured is not None:
        stmt = stmt.where(CaseStudy.featured.is_(featured))
    if project_slug:
        stmt = stmt.join(Project, CaseStudy.project_id == Project.id).where(
            Project.slug == project_slug, Project.published.is_(True)
        )

    column = getattr(CaseStudy, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{slug}", response_model=CaseStudyPublic)
async def get_case_study(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> CaseStudy:
    case_study = await session.scalar(
        select(CaseStudy)
        .options(selectinload(CaseStudy.project))
        .where(CaseStudy.slug == slug, CaseStudy.published.is_(True))
    )
    if case_study is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return case_study

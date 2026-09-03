from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.common import paginate
from app.core.database import get_session
from app.models import Project, ProjectStatus
from app.schemas import PaginatedResponse, ProjectPublic

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=PaginatedResponse[ProjectPublic])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    q: str | None = Query(None, max_length=100),
    status: ProjectStatus | None = None,
    featured: bool | None = None,
    industry: str | None = Query(None, max_length=100),
    project_type: str | None = Query(None, max_length=100),
    sort: Literal["created_at", "title", "client_name"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[ProjectPublic]:
    stmt = select(Project).where(Project.published.is_(True))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Project.title.ilike(pattern),
                Project.short_description.ilike(pattern),
                Project.description.ilike(pattern),
            )
        )
    if status is not None:
        stmt = stmt.where(Project.status == status)
    if featured is not None:
        stmt = stmt.where(Project.featured.is_(featured))
    if industry:
        stmt = stmt.where(Project.industry == industry)
    if project_type:
        stmt = stmt.where(Project.project_type == project_type)

    column = getattr(Project, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{slug}", response_model=ProjectPublic)
async def get_project(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> Project:
    project = await session.scalar(
        select(Project).where(Project.slug == slug, Project.published.is_(True))
    )
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return project

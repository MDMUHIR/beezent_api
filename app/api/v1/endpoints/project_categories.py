from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Project, ProjectCategory
from app.schemas import ProjectCategoryDetail, ProjectCategoryPublic

router = APIRouter(prefix="/project-categories", tags=["project-categories"])


@router.get("", response_model=list[ProjectCategoryPublic])
async def list_project_categories(
    session: AsyncSession = Depends(get_session),
) -> list[ProjectCategory]:
    stmt = select(ProjectCategory).order_by(
        ProjectCategory.sort_order.asc(),
        ProjectCategory.name.asc(),
    )
    return list((await session.scalars(stmt)).all())


@router.get("/{slug}", response_model=ProjectCategoryDetail)
async def get_project_category(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> ProjectCategoryDetail:
    """Return a category together with its published projects."""
    category = await session.scalar(select(ProjectCategory).where(ProjectCategory.slug == slug))
    if category is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")

    projects_stmt = (
        select(Project)
        .join(Project.categories)
        .where(ProjectCategory.slug == slug, Project.published.is_(True))
        .order_by(Project.created_at.desc())
    )
    projects = list((await session.scalars(projects_stmt)).all())

    return ProjectCategoryDetail(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        sort_order=category.sort_order,
        projects=projects,
    )

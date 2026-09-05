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
from app.models import Project, ProjectCategory, User
from app.schemas import PaginatedResponse, ProjectAdmin, ProjectCreate, ProjectUpdate

router = APIRouter(prefix="/admin/projects", tags=["admin-projects"])


async def _resolve_categories(session: AsyncSession, ids: list[UUID]) -> list[ProjectCategory]:
    """Resolve category ids to ORM objects, raising 422 if any is unknown."""
    if not ids:
        return []
    cats = list(
        (await session.scalars(select(ProjectCategory).where(ProjectCategory.id.in_(ids)))).all()
    )
    if len(cats) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="One or more categories do not exist",
        )
    return cats


@router.get("", response_model=PaginatedResponse[ProjectAdmin])
async def list_projects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    sort: Literal["created_at", "title", "client_name"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[ProjectAdmin]:
    stmt = select(Project)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Project.title.ilike(pattern), Project.slug.ilike(pattern)))
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


@router.post("", response_model=ProjectAdmin, status_code=status.HTTP_201_CREATED)
async def create_project(
    payload: ProjectCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Project:
    if await slug_exists(session, Project, payload.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{payload.slug}' is already in use",
        )
    data = payload.model_dump(exclude={"category_ids"})
    project = Project(**data)
    if payload.category_ids:
        project.categories = await _resolve_categories(session, payload.category_ids)
    session.add(project)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(project)
    return project


@router.get("/{project_id}", response_model=ProjectAdmin)
async def get_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Project:
    return await get_object_or_404(session, Project, project_id)


@router.patch("/{project_id}", response_model=ProjectAdmin)
async def update_project(
    project_id: UUID,
    payload: ProjectUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Project:
    project = await get_object_or_404(session, Project, project_id)
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, Project, data["slug"], exclude_id=project.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    categories = None
    if "category_ids" in data:
        ids = data.pop("category_ids")
        categories = await _resolve_categories(session, ids) if ids else []
    for key, value in data.items():
        setattr(project, key, value)
    if categories is not None:
        project.categories = categories
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(project)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    project = await get_object_or_404(session, Project, project_id)
    await session.delete(project)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

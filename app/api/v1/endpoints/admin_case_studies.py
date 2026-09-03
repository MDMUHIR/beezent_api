from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_staff
from app.api.v1.endpoints.common import (
    ensure_record_exists,
    get_object_or_404,
    integrity_error_response,
    paginate,
    slug_exists,
)
from app.core.database import get_session
from app.models import CaseStudy, Project, User
from app.schemas import CaseStudyAdmin, CaseStudyCreate, CaseStudyUpdate, PaginatedResponse

router = APIRouter(prefix="/admin/case-studies", tags=["admin-case-studies"])


@router.get("", response_model=PaginatedResponse[CaseStudyAdmin])
async def list_case_studies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    sort: Literal["created_at", "title"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[CaseStudyAdmin]:
    stmt = select(CaseStudy)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(CaseStudy.title.ilike(pattern), CaseStudy.slug.ilike(pattern)))
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


@router.post("", response_model=CaseStudyAdmin, status_code=status.HTTP_201_CREATED)
async def create_case_study(
    payload: CaseStudyCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> CaseStudy:
    if payload.project_id is not None:
        await ensure_record_exists(session, Project, payload.project_id, field_name="project")
    if await slug_exists(session, CaseStudy, payload.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{payload.slug}' is already in use",
        )
    case_study = CaseStudy(**payload.model_dump())
    session.add(case_study)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(case_study)
    return case_study


@router.get("/{case_study_id}", response_model=CaseStudyAdmin)
async def get_case_study(
    case_study_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> CaseStudy:
    return await get_object_or_404(session, CaseStudy, case_study_id)


@router.patch("/{case_study_id}", response_model=CaseStudyAdmin)
async def update_case_study(
    case_study_id: UUID,
    payload: CaseStudyUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> CaseStudy:
    case_study = await get_object_or_404(session, CaseStudy, case_study_id)
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, CaseStudy, data["slug"], exclude_id=case_study.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    if "project_id" in data and data["project_id"] is not None:
        await ensure_record_exists(session, Project, data["project_id"], field_name="project")
    for key, value in data.items():
        setattr(case_study, key, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(case_study)
    return case_study


@router.delete("/{case_study_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_case_study(
    case_study_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    case_study = await get_object_or_404(session, CaseStudy, case_study_id)
    await session.delete(case_study)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

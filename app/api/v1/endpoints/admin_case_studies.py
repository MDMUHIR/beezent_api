from typing import Literal
from uuid import UUID

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Response,
    UploadFile,
    status,
)
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
from app.services.cms_media import apply_image_media, pop_media_fields
from app.services.entity_upload import attach_uploaded_image, parse_payload, rollback_media

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
    data = payload.model_dump(exclude_unset=True)
    media_values = pop_media_fields(data, ["image_media_id"])
    case_study = CaseStudy(**data)
    if "image_media_id" in media_values:
        await apply_image_media(
            session,
            case_study,
            value=media_values["image_media_id"],
            data=data,
            fk_attr="image_media_id",
            rel_attr="image_media",
            url_attr="image_url",
            field_name="image_media",
        )
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


@router.post("/upload", response_model=CaseStudyAdmin, status_code=status.HTTP_201_CREATED)
async def create_case_study_with_files(
    payload: str = Form(...),
    image_file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_staff),
) -> CaseStudy:
    """Create a case study, optionally uploading its image in the same request,
    storing it to media storage and linking automatically."""
    body = parse_payload(CaseStudyCreate, payload)
    if body.project_id is not None:
        await ensure_record_exists(session, Project, body.project_id, field_name="project")
    if await slug_exists(session, CaseStudy, body.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{body.slug}' is already in use",
        )
    data = body.model_dump(exclude_unset=True)
    media_values = pop_media_fields(data, ["image_media_id"])
    case_study = CaseStudy(**data)
    created: list = []
    if image_file is not None:
        created.append(
            await attach_uploaded_image(
                session,
                current_user,
                case_study,
                image_file,
                fk_attr="image_media_id",
                rel_attr="image_media",
                url_attr="image_url",
            )
        )
    elif "image_media_id" in media_values:
        await apply_image_media(
            session,
            case_study,
            value=media_values["image_media_id"],
            data=data,
            fk_attr="image_media_id",
            rel_attr="image_media",
            url_attr="image_url",
            field_name="image_media",
        )
    session.add(case_study)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        await rollback_media(session, created)
        raise integrity_error_response(exc) from None
    await session.refresh(case_study)
    return case_study


@router.patch("/{case_study_id}/upload", response_model=CaseStudyAdmin)
async def update_case_study_with_files(
    case_study_id: UUID,
    payload: str = Form(...),
    image_file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_staff),
) -> CaseStudy:
    """Update a case study, optionally uploading a new image."""
    case_study = await get_object_or_404(session, CaseStudy, case_study_id)
    body = parse_payload(CaseStudyUpdate, payload)
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, CaseStudy, data["slug"], exclude_id=case_study.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    if "project_id" in data and data["project_id"] is not None:
        await ensure_record_exists(session, Project, data["project_id"], field_name="project")
    media_values = pop_media_fields(data, ["image_media_id"])
    if "image_media_id" in media_values:
        await apply_image_media(
            session,
            case_study,
            value=media_values["image_media_id"],
            data=data,
            fk_attr="image_media_id",
            rel_attr="image_media",
            url_attr="image_url",
            field_name="image_media",
        )
    created: list = []
    if image_file is not None:
        created.append(
            await attach_uploaded_image(
                session,
                current_user,
                case_study,
                image_file,
                fk_attr="image_media_id",
                rel_attr="image_media",
                url_attr="image_url",
            )
        )
    for key, value in data.items():
        setattr(case_study, key, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        await rollback_media(session, created)
        raise integrity_error_response(exc) from None
    await session.refresh(case_study)
    return case_study


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
    media_values = pop_media_fields(data, ["image_media_id"])
    if "image_media_id" in media_values:
        await apply_image_media(
            session,
            case_study,
            value=media_values["image_media_id"],
            data=data,
            fk_attr="image_media_id",
            rel_attr="image_media",
            url_attr="image_url",
            field_name="image_media",
        )
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

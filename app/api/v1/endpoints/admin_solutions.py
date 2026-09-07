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
    get_object_or_404,
    integrity_error_response,
    paginate,
    slug_exists,
)
from app.core.database import get_session
from app.models import Solution, SolutionCategory, User
from app.schemas import PaginatedResponse, SolutionAdmin, SolutionCreate, SolutionUpdate
from app.services.cms_media import apply_demo_video_media, apply_image_media, pop_media_fields
from app.services.entity_upload import (
    attach_uploaded_image,
    attach_uploaded_video,
    parse_payload,
    rollback_media,
)

router = APIRouter(prefix="/admin/solutions", tags=["admin-solutions"])

_MEDIA_FIELDS = ("image_media_id", "demo_video_media_id")


async def _apply_media(session: AsyncSession, solution: Solution, data: dict) -> None:
    media_values = pop_media_fields(data, list(_MEDIA_FIELDS))
    if "image_media_id" in media_values:
        await apply_image_media(
            session,
            solution,
            value=media_values["image_media_id"],
            data=data,
            fk_attr="image_media_id",
            rel_attr="image_media",
            url_attr="image_url",
            field_name="image_media",
        )
    if "demo_video_media_id" in media_values:
        await apply_demo_video_media(
            session, solution, value=media_values["demo_video_media_id"], data=data
        )


async def _resolve_categories(session: AsyncSession, ids: list[UUID]) -> list[SolutionCategory]:
    """Resolve category ids to ORM objects, raising 422 if any is unknown."""
    if not ids:
        return []
    cats = list(
        (await session.scalars(select(SolutionCategory).where(SolutionCategory.id.in_(ids)))).all()
    )
    if len(cats) != len(set(ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="One or more categories do not exist",
        )
    return cats


@router.get("", response_model=PaginatedResponse[SolutionAdmin])
async def list_solutions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    sort: Literal["sort_order", "name", "created_at"] = "sort_order",
    order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[SolutionAdmin]:
    stmt = select(Solution)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(or_(Solution.name.ilike(pattern), Solution.slug.ilike(pattern)))
    column = getattr(Solution, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.post("", response_model=SolutionAdmin, status_code=status.HTTP_201_CREATED)
async def create_solution(
    payload: SolutionCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Solution:
    if await slug_exists(session, Solution, payload.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{payload.slug}' is already in use",
        )
    data = payload.model_dump(exclude={"category_ids"}, exclude_unset=True)
    solution = Solution(**data)
    await _apply_media(session, solution, data)
    if payload.category_ids:
        solution.categories = await _resolve_categories(session, payload.category_ids)
    session.add(solution)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(solution)
    return solution


@router.get("/{solution_id}", response_model=SolutionAdmin)
async def get_solution(
    solution_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Solution:
    return await get_object_or_404(session, Solution, solution_id)


@router.post("/upload", response_model=SolutionAdmin, status_code=status.HTTP_201_CREATED)
async def create_solution_with_files(
    payload: str = Form(...),
    image_file: UploadFile | None = File(None),
    demo_video_file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_staff),
) -> Solution:
    """Create a solution, optionally uploading the image and/or demo video in
    the same request, storing them to media storage and linking automatically."""
    body = parse_payload(SolutionCreate, payload)
    if await slug_exists(session, Solution, body.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{body.slug}' is already in use",
        )
    data = body.model_dump(exclude={"category_ids"}, exclude_unset=True)
    solution = Solution(**data)
    if body.category_ids:
        solution.categories = await _resolve_categories(session, body.category_ids)
    created: list = []
    if image_file is not None:
        created.append(
            await attach_uploaded_image(
                session,
                current_user,
                solution,
                image_file,
                fk_attr="image_media_id",
                rel_attr="image_media",
                url_attr="image_url",
            )
        )
    if demo_video_file is not None:
        created.append(
            await attach_uploaded_video(session, current_user, solution, demo_video_file)
        )
    session.add(solution)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        await rollback_media(session, created)
        raise integrity_error_response(exc) from None
    await session.refresh(solution)
    return solution


@router.patch("/{solution_id}/upload", response_model=SolutionAdmin)
async def update_solution_with_files(
    solution_id: UUID,
    payload: str = Form(...),
    image_file: UploadFile | None = File(None),
    demo_video_file: UploadFile | None = File(None),
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_staff),
) -> Solution:
    """Update a solution, optionally uploading a new image and/or demo video."""
    solution = await get_object_or_404(session, Solution, solution_id)
    body = parse_payload(SolutionUpdate, payload)
    data = body.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, Solution, data["slug"], exclude_id=solution.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    categories = None
    if "category_ids" in data:
        ids = data.pop("category_ids")
        categories = await _resolve_categories(session, ids) if ids else []
    created: list = []
    await _apply_media(session, solution, data)
    if image_file is not None:
        created.append(
            await attach_uploaded_image(
                session,
                current_user,
                solution,
                image_file,
                fk_attr="image_media_id",
                rel_attr="image_media",
                url_attr="image_url",
            )
        )
    if demo_video_file is not None:
        created.append(
            await attach_uploaded_video(session, current_user, solution, demo_video_file)
        )
    for key, value in data.items():
        setattr(solution, key, value)
    if categories is not None:
        solution.categories = categories
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        await rollback_media(session, created)
        raise integrity_error_response(exc) from None
    await session.refresh(solution)
    return solution


@router.patch("/{solution_id}", response_model=SolutionAdmin)
async def update_solution(
    solution_id: UUID,
    payload: SolutionUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Solution:
    solution = await get_object_or_404(session, Solution, solution_id)
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, Solution, data["slug"], exclude_id=solution.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    categories = None
    if "category_ids" in data:
        ids = data.pop("category_ids")
        categories = await _resolve_categories(session, ids) if ids else []
    await _apply_media(session, solution, data)
    for key, value in data.items():
        setattr(solution, key, value)
    if categories is not None:
        solution.categories = categories
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(solution)
    return solution


@router.delete("/{solution_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_solution(
    solution_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    solution = await get_object_or_404(session, Solution, solution_id)
    await session.delete(solution)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

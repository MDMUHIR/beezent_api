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
from app.models import Solution, User
from app.schemas import PaginatedResponse, SolutionAdmin, SolutionCreate, SolutionUpdate

router = APIRouter(prefix="/admin/solutions", tags=["admin-solutions"])


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
    solution = Solution(**payload.model_dump())
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
    for key, value in data.items():
        setattr(solution, key, value)
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

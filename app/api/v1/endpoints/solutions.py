from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.common import paginate
from app.core.database import get_session
from app.models import Solution
from app.schemas import PaginatedResponse, SolutionPublic

router = APIRouter(prefix="/solutions", tags=["solutions"])


@router.get("", response_model=PaginatedResponse[SolutionPublic])
async def list_solutions(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    q: str | None = Query(None, max_length=100),
    featured: bool | None = None,
    sort: Literal["sort_order", "name", "created_at"] = "sort_order",
    order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[SolutionPublic]:
    stmt = select(Solution).where(Solution.published.is_(True))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Solution.name.ilike(pattern),
                Solution.short_description.ilike(pattern),
                Solution.description.ilike(pattern),
            )
        )
    if featured is not None:
        stmt = stmt.where(Solution.featured.is_(featured))

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


@router.get("/{slug}", response_model=SolutionPublic)
async def get_solution(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> Solution:
    solution = await session.scalar(
        select(Solution).where(Solution.slug == slug, Solution.published.is_(True))
    )
    if solution is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return solution

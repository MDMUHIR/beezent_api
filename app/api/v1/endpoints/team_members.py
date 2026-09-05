from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.common import paginate
from app.core.database import get_session
from app.models import TeamMember, TeamMemberCategory
from app.schemas import PaginatedResponse, TeamMemberPublic

router = APIRouter(prefix="/team-members", tags=["team-members"])


@router.get("", response_model=PaginatedResponse[TeamMemberPublic])
async def list_team_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    q: str | None = Query(None, max_length=100),
    category: TeamMemberCategory | None = None,
    featured: bool | None = None,
    sort: Literal["sort_order", "name", "role", "created_at"] = "sort_order",
    order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_session),
) -> PaginatedResponse[TeamMemberPublic]:
    stmt = select(TeamMember).where(TeamMember.published.is_(True))
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                TeamMember.name.ilike(pattern),
                TeamMember.role.ilike(pattern),
                TeamMember.bio.ilike(pattern),
            )
        )
    if category is not None:
        stmt = stmt.where(TeamMember.category == category)
    if featured is not None:
        stmt = stmt.where(TeamMember.featured.is_(featured))

    column = getattr(TeamMember, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{slug}", response_model=TeamMemberPublic)
async def get_team_member(
    slug: str,
    session: AsyncSession = Depends(get_session),
) -> TeamMember:
    member = await session.scalar(
        select(TeamMember).where(TeamMember.slug == slug, TeamMember.published.is_(True))
    )
    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return member

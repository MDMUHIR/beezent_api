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
from app.models import TeamMember, User
from app.schemas import (
    PaginatedResponse,
    TeamMemberAdmin,
    TeamMemberCreate,
    TeamMemberUpdate,
)

router = APIRouter(prefix="/admin/team-members", tags=["admin-team-members"])


@router.get("", response_model=PaginatedResponse[TeamMemberAdmin])
async def list_team_members(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=100),
    category: Literal["leadership", "talent"] | None = None,
    sort: Literal["sort_order", "name", "role", "created_at"] = "sort_order",
    order: Literal["asc", "desc"] = "asc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[TeamMemberAdmin]:
    stmt = select(TeamMember)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                TeamMember.name.ilike(pattern),
                TeamMember.slug.ilike(pattern),
                TeamMember.role.ilike(pattern),
            )
        )
    if category is not None:
        stmt = stmt.where(TeamMember.category == category)
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


@router.post("", response_model=TeamMemberAdmin, status_code=status.HTTP_201_CREATED)
async def create_team_member(
    payload: TeamMemberCreate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> TeamMember:
    if await slug_exists(session, TeamMember, payload.slug):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Slug '{payload.slug}' is already in use",
        )
    member = TeamMember(**payload.model_dump())
    session.add(member)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(member)
    return member


@router.get("/{member_id}", response_model=TeamMemberAdmin)
async def get_team_member(
    member_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> TeamMember:
    return await get_object_or_404(session, TeamMember, member_id)


@router.patch("/{member_id}", response_model=TeamMemberAdmin)
async def update_team_member(
    member_id: UUID,
    payload: TeamMemberUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> TeamMember:
    member = await get_object_or_404(session, TeamMember, member_id)
    data = payload.model_dump(exclude_unset=True)
    if "slug" in data and data["slug"] is not None:
        if await slug_exists(session, TeamMember, data["slug"], exclude_id=member.id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Slug '{data['slug']}' is already in use",
            )
    for key, value in data.items():
        setattr(member, key, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(member)
    return member


@router.delete("/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_team_member(
    member_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    member = await get_object_or_404(session, TeamMember, member_id)
    await session.delete(member)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

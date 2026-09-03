from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_staff
from app.api.v1.endpoints.common import get_object_or_404, integrity_error_response, paginate
from app.core.database import get_session
from app.models import Lead, LeadStatus, User
from app.schemas import LeadAdmin, LeadUpdate, PaginatedResponse

router = APIRouter(prefix="/admin/leads", tags=["admin-leads"])


@router.get("", response_model=PaginatedResponse[LeadAdmin])
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: LeadStatus | None = None,
    q: str | None = Query(None, max_length=100),
    sort: Literal["created_at", "name", "email", "status"] = "created_at",
    order: Literal["asc", "desc"] = "desc",
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> PaginatedResponse[LeadAdmin]:
    stmt = select(Lead)
    if status is not None:
        stmt = stmt.where(Lead.status == status)
    if q:
        pattern = f"%{q}%"
        stmt = stmt.where(
            or_(
                Lead.name.ilike(pattern),
                Lead.email.ilike(pattern),
                Lead.company.ilike(pattern),
                Lead.message.ilike(pattern),
            )
        )
    column = getattr(Lead, sort)
    order_by = column.asc() if order == "asc" else column.desc()

    items, total, pages = await paginate(session, stmt, page, page_size, order_by)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "pages": pages,
    }


@router.get("/{lead_id}", response_model=LeadAdmin)
async def get_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Lead:
    return await get_object_or_404(session, Lead, lead_id)


@router.patch("/{lead_id}", response_model=LeadAdmin)
async def update_lead(
    lead_id: UUID,
    payload: LeadUpdate,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Lead:
    lead = await get_object_or_404(session, Lead, lead_id)
    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(lead, key, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise integrity_error_response(exc) from None
    await session.refresh(lead)
    return lead


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(require_staff),
) -> Response:
    lead = await get_object_or_404(session, Lead, lead_id)
    await session.delete(lead)
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)

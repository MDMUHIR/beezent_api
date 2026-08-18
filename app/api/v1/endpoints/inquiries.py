from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_db
from app.models.inquiry import ContactInquiry, InquiryStatus
from app.models.user import User
from app.schemas.inquiry import (
    ContactInquiryCreate,
    ContactInquiryResponse,
    ContactInquiryUpdate,
)

router = APIRouter()


# ------------------ Public Lead Generation ------------------ #
@router.post("/", response_model=ContactInquiryResponse, status_code=status.HTTP_201_CREATED, summary="Submit a new client project inquiry")
async def create_inquiry(
    inquiry_in: ContactInquiryCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    inquiry = ContactInquiry(
        **inquiry_in.model_dump(),
        status=InquiryStatus.NEW
    )
    db.add(inquiry)
    await db.commit()
    await db.refresh(inquiry)
    return inquiry


# ------------------ Admin CRM / Lead Management ------------------ #
@router.get("/", response_model=List[ContactInquiryResponse], summary="List contact inquiries (Admin only)")
async def list_inquiries(
    status_filter: Optional[InquiryStatus] = None,
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(ContactInquiry).order_by(ContactInquiry.created_at.desc())
    if status_filter:
        stmt = stmt.where(ContactInquiry.status == status_filter)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{id}", response_model=ContactInquiryResponse, summary="Get inquiry detail (Admin only)")
async def get_inquiry(
    id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(ContactInquiry).where(ContactInquiry.id == id)
    result = await db.execute(stmt)
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return inquiry


@router.patch("/{id}/status", response_model=ContactInquiryResponse, summary="Update inquiry CRM status and internal notes (Admin only)")
async def update_inquiry_status(
    id: int,
    inquiry_update: ContactInquiryUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(ContactInquiry).where(ContactInquiry.id == id)
    result = await db.execute(stmt)
    inquiry = result.scalar_one_or_none()
    if not inquiry:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    if inquiry_update.status is not None:
        inquiry.status = inquiry_update.status
    if inquiry_update.internal_notes is not None:
        inquiry.internal_notes = inquiry_update.internal_notes

    await db.commit()
    await db.refresh(inquiry)
    return inquiry

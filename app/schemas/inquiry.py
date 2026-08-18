from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.inquiry import InquiryStatus


class ContactInquiryBase(BaseModel):
    full_name: str = Field(..., max_length=150)
    email: EmailStr
    phone_number: Optional[str] = None
    company_name: Optional[str] = None
    service_interest: Optional[str] = None
    budget_range: Optional[str] = None
    timeline: Optional[str] = None
    message: str


class ContactInquiryCreate(ContactInquiryBase):
    pass


class ContactInquiryUpdate(BaseModel):
    status: Optional[InquiryStatus] = None
    internal_notes: Optional[str] = None


class ContactInquiryResponse(ContactInquiryBase):
    id: int
    status: InquiryStatus
    internal_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

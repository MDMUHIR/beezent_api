import enum
from typing import Optional
from sqlalchemy import Enum, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class InquiryStatus(str, enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    IN_PROGRESS = "IN_PROGRESS"
    QUALIFIED = "QUALIFIED"
    CLOSED = "CLOSED"


class ContactInquiry(Base, TimestampMixin):
    __tablename__ = "contact_inquiries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone_number: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    company_name: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    service_interest: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)  # e.g. "AI & Machine Learning"
    budget_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)     # e.g. "$25k - $50k"
    timeline: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)         # e.g. "Within 1 month"
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[InquiryStatus] = mapped_column(
        Enum(InquiryStatus, native_enum=False, length=50),
        default=InquiryStatus.NEW,
        nullable=False,
        index=True,
    )
    internal_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    def __repr__(self) -> str:
        return f"<ContactInquiry(id={self.id}, name='{self.full_name}', status='{self.status}')>"

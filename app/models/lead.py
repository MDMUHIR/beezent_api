from sqlalchemy import CheckConstraint, Enum, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LeadStatus


class Lead(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "leads"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'qualified', 'converted', 'lost')",
            name="ck_leads_status",
        ),
        # Admin list defaults to newest-first and is commonly filtered by
        # status, so a composite (status, created_at) index covers both the
        # filtered and the unfiltered default sort.
        Index("ix_leads_status_created_at", "status", "created_at"),
        # Lookups/sorting by creation time without a status filter.
        Index("ix_leads_created_at", "created_at"),
        Index("ix_leads_email", "email"),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[LeadStatus] = mapped_column(
        Enum(
            LeadStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=LeadStatus.NEW,
        nullable=False,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

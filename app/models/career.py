import enum
from datetime import date
from typing import List, Optional
from sqlalchemy import Boolean, Date, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class ApplicationStatus(str, enum.Enum):
    PENDING = "PENDING"
    REVIEWING = "REVIEWING"
    INTERVIEWING = "INTERVIEWING"
    OFFERED = "OFFERED"
    REJECTED = "REJECTED"


class JobPosting(Base, TimestampMixin):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(220), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, default="Engineering")
    location_type: Mapped[str] = mapped_column(String(50), default="Remote", nullable=False)  # Remote, Hybrid, Onsite
    location: Mapped[str] = mapped_column(String(150), default="Global / Remote", nullable=False)
    employment_type: Mapped[str] = mapped_column(String(50), default="Full-Time", nullable=False)  # Full-Time, Contract
    experience_level: Mapped[str] = mapped_column(String(50), default="Senior", nullable=False)
    salary_range: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)  # e.g., "$80,000 - $120,000 / yr"
    summary: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)  # Markdown
    requirements: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    responsibilities: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    perks: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    deadline: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    applications: Mapped[List["JobApplication"]] = relationship(
        "JobApplication",
        back_populates="job_posting",
        cascade="all, delete-orphan",
        order_by="JobApplication.created_at.desc()"
    )

    def __repr__(self) -> str:
        return f"<JobPosting(id={self.id}, title='{self.title}')>"


class JobApplication(Base, TimestampMixin):
    __tablename__ = "job_applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    job_posting_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("job_postings.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    candidate_name: Mapped[str] = mapped_column(String(150), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    phone: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    resume_url: Mapped[str] = mapped_column(String(500), nullable=False)
    cover_letter: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    years_of_experience: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus, native_enum=False, length=50),
        default=ApplicationStatus.PENDING,
        nullable=False,
        index=True,
    )
    admin_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    job_posting: Mapped["JobPosting"] = relationship("JobPosting", back_populates="applications")

    def __repr__(self) -> str:
        return f"<JobApplication(id={self.id}, candidate='{self.candidate_name}', job_id={self.job_posting_id})>"

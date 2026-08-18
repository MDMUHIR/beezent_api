from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Column, ForeignKey, Integer, JSON, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

# Many-to-many between case studies and services
case_study_service = Table(
    "case_study_service",
    Base.metadata,
    Column("case_study_id", Integer, ForeignKey("case_studies.id", ondelete="CASCADE"), primary_key=True),
    Column("service_id", Integer, ForeignKey("services.id", ondelete="CASCADE"), primary_key=True),
)


class Industry(Base, TimestampMixin):
    __tablename__ = "industries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    case_studies: Mapped[List["CaseStudy"]] = relationship("CaseStudy", back_populates="industry")

    def __repr__(self) -> str:
        return f"<Industry(id={self.id}, name='{self.name}')>"


class CaseStudy(Base, TimestampMixin):
    __tablename__ = "case_studies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    industry_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("industries.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    slug: Mapped[str] = mapped_column(String(270), unique=True, nullable=False, index=True)
    client_name: Mapped[str] = mapped_column(String(150), nullable=False)
    client_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary: Mapped[str] = mapped_column(String(600), nullable=False)
    challenge: Mapped[str] = mapped_column(Text, nullable=False)
    solution: Mapped[str] = mapped_column(Text, nullable=False)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    cover_image_url: Mapped[str] = mapped_column(String(500), nullable=False)
    gallery_images: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list, nullable=True)
    live_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    industry: Mapped[Optional["Industry"]] = relationship("Industry", back_populates="case_studies")
    metrics: Mapped[List["CaseStudyMetric"]] = relationship(
        "CaseStudyMetric",
        back_populates="case_study",
        cascade="all, delete-orphan",
        order_by="CaseStudyMetric.display_order"
    )

    def __repr__(self) -> str:
        return f"<CaseStudy(id={self.id}, title='{self.title}', client='{self.client_name}')>"


class CaseStudyMetric(Base, TimestampMixin):
    __tablename__ = "case_study_metrics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    case_study_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("case_studies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Latency Reduction", "Accuracy Rate"
    value: Mapped[str] = mapped_column(String(50), nullable=False)   # e.g., "98%", "$1.8M", "3.5x"
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    case_study: Mapped["CaseStudy"] = relationship("CaseStudy", back_populates="metrics")

    def __repr__(self) -> str:
        return f"<CaseStudyMetric(label='{self.label}', value='{self.value}')>"

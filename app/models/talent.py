from typing import List, Optional
from sqlalchemy import Boolean, Integer, JSON, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class TalentRole(Base, TimestampMixin):
    __tablename__ = "talent_roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(150), nullable=False, index=True)  # e.g., "Senior AI & LLM Engineer"
    slug: Mapped[str] = mapped_column(String(170), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), nullable=False, default="Engineering")  # AI, Mobile, Web, QA, DevOps
    experience_level: Mapped[str] = mapped_column(String(50), nullable=False, default="Senior (5+ yrs)")
    core_skills: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    short_description: Mapped[str] = mapped_column(Text, nullable=False)
    availability: Mapped[str] = mapped_column(String(50), default="Available in 48 hrs", nullable=False)
    hourly_rate_estimate: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # e.g., "$45 - $65 / hr"
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<TalentRole(id={self.id}, title='{self.title}', level='{self.experience_level}')>"

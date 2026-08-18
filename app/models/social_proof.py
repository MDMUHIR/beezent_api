from datetime import date
from typing import Optional
from sqlalchemy import Boolean, Date, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Testimonial(Base, TimestampMixin):
    __tablename__ = "testimonials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    client_name: Mapped[str] = mapped_column(String(150), nullable=False)
    client_role: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g., "CTO & Co-Founder"
    client_company: Mapped[str] = mapped_column(String(150), nullable=False)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    company_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    quote: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int] = mapped_column(Integer, default=5, nullable=False)  # 1 to 5
    video_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    project_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<Testimonial(id={self.id}, client='{self.client_name}', company='{self.client_company}')>"


class PressCoverage(Base, TimestampMixin):
    __tablename__ = "press_coverage"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    publisher_name: Mapped[str] = mapped_column(String(150), nullable=False)  # e.g. "TechCrunch", "Forbes"
    publisher_logo_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    headline: Mapped[str] = mapped_column(String(300), nullable=False)
    article_url: Mapped[str] = mapped_column(String(500), nullable=False)
    excerpt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<PressCoverage(id={self.id}, publisher='{self.publisher_name}')>"


class CompanyStat(Base, TimestampMixin):
    __tablename__ = "company_stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    label: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Projects Delivered", "Global Engineers"
    metric_value: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., "250+", "99.8%", "15M+"
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    icon: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    def __repr__(self) -> str:
        return f"<CompanyStat(label='{self.label}', value='{self.metric_value}')>"

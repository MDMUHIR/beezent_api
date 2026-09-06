from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, CheckConstraint, Enum, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DemoVideoType, ProjectStatus
from app.models.project_category import project_category_links

if TYPE_CHECKING:
    from app.models.case_study import CaseStudy
    from app.models.project_category import ProjectCategory


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"
    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'completed', 'archived')",
            name="ck_projects_status",
        ),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    client_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    industry: Mapped[str | None] = mapped_column(String(100), nullable=True)
    project_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=ProjectStatus.ACTIVE,
        nullable=False,
    )
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    cover_image: Mapped[str | None] = mapped_column(String(500), nullable=True)
    live_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    github_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_video_type: Mapped[DemoVideoType | None] = mapped_column(
        Enum(
            DemoVideoType,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=True,
    )
    technologies: Mapped[list[Any]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'"), nullable=False
    )
    results: Mapped[list[Any]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'"), nullable=False
    )

    case_studies: Mapped[list[CaseStudy]] = relationship(back_populates="project")

    categories: Mapped[list[ProjectCategory]] = relationship(
        secondary=project_category_links,
        back_populates="projects",
        lazy="selectin",
    )

from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.project import Project

# Many-to-many link between projects and their categories. Deleting a project
# or a category removes only the link rows (CASCADE), never the other side.
project_category_links = Table(
    "project_category_links",
    Base.metadata,
    Column(
        "project_id",
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("project_categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class ProjectCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_categories"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    projects: Mapped[list["Project"]] = relationship(
        secondary=project_category_links,
        back_populates="categories",
    )

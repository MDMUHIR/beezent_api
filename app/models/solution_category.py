from typing import TYPE_CHECKING

from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.solution import Solution

# Many-to-many link between solutions and their categories. Deleting a solution
# or a category removes only the link rows (CASCADE), never the other side.
solution_category_links = Table(
    "solution_category_links",
    Base.metadata,
    Column(
        "solution_id",
        ForeignKey("solutions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "category_id",
        ForeignKey("solution_categories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class SolutionCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "solution_categories"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    solutions: Mapped[list["Solution"]] = relationship(
        secondary=solution_category_links,
        back_populates="categories",
    )

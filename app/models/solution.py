from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DemoVideoType
from app.models.solution_category import solution_category_links

if TYPE_CHECKING:
    from app.models.media import Media
    from app.models.solution_category import SolutionCategory


class Solution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "solutions"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    short_description: Mapped[str | None] = mapped_column(String(300), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    icon: Mapped[str | None] = mapped_column(String(100), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True
    )
    demo_video_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    demo_video_media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True
    )
    demo_video_type: Mapped[DemoVideoType | None] = mapped_column(
        Enum(
            DemoVideoType,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=True,
    )
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    image_media: Mapped[Media | None] = relationship(foreign_keys=[image_media_id], lazy="selectin")
    demo_video_media: Mapped[Media | None] = relationship(
        foreign_keys=[demo_video_media_id], lazy="selectin"
    )

    @property
    def demo_video(self) -> Media | None:
        """Alias of :attr:`demo_video_media` (uploaded demo video)."""
        return self.demo_video_media

    categories: Mapped[list[SolutionCategory]] = relationship(
        secondary=solution_category_links,
        back_populates="solutions",
        lazy="selectin",
    )

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, CheckConstraint, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import TeamMemberCategory

if TYPE_CHECKING:
    from app.models.media import Media


class TeamMember(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "team_members"
    __table_args__ = (
        CheckConstraint(
            "category IN ('leadership', 'talent')",
            name="ck_team_members_category",
        ),
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    role: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    avatar_media_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True
    )
    category: Mapped[TeamMemberCategory] = mapped_column(
        Enum(
            TeamMemberCategory,
            native_enum=False,
            length=20,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=TeamMemberCategory.TALENT,
        nullable=False,
    )
    featured: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    avatar_media: Mapped[Media | None] = relationship(
        foreign_keys=[avatar_media_id], lazy="selectin"
    )

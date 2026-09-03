from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Media(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadata record for an uploaded media object.

    The binary content lives in the storage backend (object storage in
    production, local disk in development); this table stores only the
    reference information.
    """

    __tablename__ = "media"
    __table_args__ = (
        CheckConstraint("size >= 0", name="ck_media_size"),
        # Admin list defaults to newest-first and is often filtered by folder.
        Index("ix_media_created_at", "created_at"),
        Index("ix_media_folder", "folder"),
    )

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    public_url: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    folder: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

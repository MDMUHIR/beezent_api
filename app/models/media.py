from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.storage import get_storage
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Media(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Metadata record for an uploaded media object.

    The binary content lives in the storage backend (object storage in
    production, local disk in development); this table stores only the
    reference information. ``storage_key`` is the canonical storage identity;
    the public delivery URL is derived on demand from the storage backend so
    that changing storage/CDN configuration never requires rewriting rows.
    """

    __tablename__ = "media"
    __table_args__ = (
        CheckConstraint("size >= 0", name="ck_media_size"),
        CheckConstraint(
            "media_type IN ('image', 'video', 'document')",
            name="ck_media_media_type",
        ),
        CheckConstraint(
            "duration_seconds IS NULL OR duration_seconds >= 0", name="ck_media_duration"
        ),
        # Admin list defaults to newest-first and is often filtered by folder.
        Index("ix_media_created_at", "created_at"),
        Index("ix_media_folder", "folder"),
    )

    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    media_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    width: Mapped[int | None] = mapped_column(nullable=True)
    height: Mapped[int | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(nullable=True)
    alt_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    folder: Mapped[str | None] = mapped_column(String(100), nullable=True)
    uploaded_by: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    @property
    def public_url(self) -> str:
        """The public delivery URL, derived from the storage key.

        This is intentionally not a stored column: it is computed from the
        current storage backend configuration.
        """
        return get_storage().public_url(self.storage_key)

    @property
    def url(self) -> str:
        """Alias of :attr:`public_url` (canonical delivery representation)."""
        return self.public_url

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

FOLDER_PATTERN = re.compile(r"^[a-z0-9_-]{1,100}$")


def normalize_folder(value: str | None) -> str | None:
    """Trim and validate a folder name, or raise ValueError."""
    if value is None:
        return None
    value = value.strip()
    if not FOLDER_PATTERN.fullmatch(value):
        raise ValueError(
            "folder must contain only lowercase letters, numbers, hyphens, or underscores"
        )
    return value


class MediaPublic(BaseModel):
    """Public delivery representation of a media object.

    Exposed nested inside CMS responses. Never includes internal fields such
    as storage keys, uploader identity, or database timestamps.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    mime_type: str
    media_type: str
    size: int
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    alt_text: str | None = None


class MediaAdmin(BaseModel):
    """Admin/staff representation of a media record.

    `public_url` and `url` are the same delivery URL; `url` is the canonical,
    frontend-friendly field and `public_url` is kept for backward compatibility
    with earlier clients.
    """

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_name: str
    storage_key: str
    public_url: str
    url: str
    mime_type: str
    media_type: str
    size: int
    width: int | None = None
    height: int | None = None
    duration_seconds: int | None = None
    alt_text: str | None = None
    folder: str | None = None
    uploaded_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MediaMetadataUpdate(BaseModel):
    """Editable media metadata. The binary/storage_key are never editable."""

    alt_text: str | None = Field(default=None, max_length=500)
    folder: str | None = Field(default=None, max_length=100)

    @field_validator("alt_text")
    @classmethod
    def strip_alt_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()

    @field_validator("folder")
    @classmethod
    def validate_folder(cls, value: str | None) -> str | None:
        return normalize_folder(value)

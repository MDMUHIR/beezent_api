from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import LeadStatus


class _LeadFields(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    phone: str | None = Field(default=None, max_length=50)
    company: str | None = Field(default=None, max_length=255)
    service: str | None = Field(default=None, max_length=255)
    message: str = Field(min_length=10, max_length=5000)
    source: str | None = Field(default=None, max_length=100)

    @field_validator("name", "phone", "company", "service", "message", "source", mode="before")
    @classmethod
    def strip_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().lower()
        return value


class LeadCreate(_LeadFields):
    """Public lead-submission payload.

    Deliberately omits `id`, `status`, `notes`, `created_at`, and `updated_at`
    so the server always controls those fields.
    """


class LeadPublicResponse(BaseModel):
    id: UUID
    message: str = "Your inquiry has been received."


class LeadAdmin(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    email: EmailStr
    phone: str | None = None
    company: str | None = None
    service: str | None = None
    message: str
    source: str | None = None
    status: LeadStatus
    notes: str | None = None
    created_at: datetime
    updated_at: datetime


class LeadUpdate(_LeadFields):
    """Staff/admin partial update.

    Only these fields are editable; `id`, `created_at`, and `updated_at` are
    never accepted.
    """

    message: str | None = Field(default=None, min_length=10, max_length=5000)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    status: LeadStatus | None = None
    notes: str | None = Field(default=None, max_length=5000)

    @field_validator("notes", mode="before")
    @classmethod
    def strip_notes(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip()
        return value

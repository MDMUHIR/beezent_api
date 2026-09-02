from uuid import UUID, uuid4

from sqlalchemy import Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all application models."""


class UUIDPrimaryKeyMixin:
    """Mixin providing a UUID primary key for application models."""

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)

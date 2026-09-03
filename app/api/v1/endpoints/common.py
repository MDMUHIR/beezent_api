import math
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    session: AsyncSession,
    stmt: Any,
    page: int,
    page_size: int,
    order_by: Any | None = None,
) -> tuple[list[Any], int, int]:
    """Return (items, total, pages) for an ORM select statement."""
    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    total = total or 0
    if order_by is not None:
        stmt = stmt.order_by(order_by)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    items = list((await session.scalars(stmt)).all())
    pages = math.ceil(total / page_size) if total else 0
    return items, total, pages


async def get_object_or_404(
    session: AsyncSession,
    model: type[Any],
    obj_id: UUID,
) -> Any:
    """Fetch an object by primary key or raise 404."""
    obj = await session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    return obj


async def slug_exists(
    session: AsyncSession,
    model: type[Any],
    slug: str,
    *,
    exclude_id: UUID | None = None,
) -> bool:
    """Return True when another record uses the given slug (case-insensitive)."""
    stmt = select(model.id).where(func.lower(model.slug) == slug.lower())
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    return await session.scalar(stmt) is not None


async def ensure_record_exists(
    session: AsyncSession,
    model: type[Any],
    obj_id: UUID,
    *,
    field_name: str,
) -> None:
    """Validate that a referenced record exists, raising 422 otherwise."""
    if await session.get(model, obj_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Referenced {field_name} does not exist",
        )


def integrity_error_response(exc: IntegrityError) -> HTTPException:
    """Map a database IntegrityError to a safe, meaningful API error."""
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None)
    if sqlstate == "23505":
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A record with this slug already exists",
        )
    if sqlstate == "23503":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Referenced record does not exist",
        )
    if sqlstate == "23502":
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A required field cannot be null",
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="A database error occurred",
    )

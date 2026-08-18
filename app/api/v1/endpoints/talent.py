from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_editor, get_db
from app.models.talent import TalentRole
from app.models.user import User
from app.schemas.talent import (
    TalentRoleCreate,
    TalentRoleResponse,
    TalentRoleUpdate,
)

router = APIRouter()


@router.get("/", response_model=List[TalentRoleResponse], summary="List available talent roles & augmentation profiles")
async def list_talent_roles(
    department: Optional[str] = None,
    experience_level: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(TalentRole)
        .where(TalentRole.is_active.is_(True))
        .order_by(TalentRole.display_order, TalentRole.title)
    )
    if department:
        stmt = stmt.where(TalentRole.department.ilike(department))
    if experience_level:
        stmt = stmt.where(TalentRole.experience_level.ilike(f"%{experience_level}%"))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{slug}", response_model=TalentRoleResponse, summary="Get talent role profile by slug")
async def get_talent_role_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(TalentRole).where(TalentRole.slug == slug, TalentRole.is_active.is_(True))
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Talent profile not found")
    return role


@router.post("/", response_model=TalentRoleResponse, status_code=status.HTTP_201_CREATED, summary="Create a new talent role (Editor only)")
async def create_talent_role(
    role_in: TalentRoleCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    existing = await db.execute(select(TalentRole).where(TalentRole.slug == role_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Talent slug already exists")

    role = TalentRole(**role_in.model_dump())
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


@router.put("/{id}", response_model=TalentRoleResponse, summary="Update a talent role (Editor only)")
async def update_talent_role(
    id: int,
    role_in: TalentRoleUpdate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(TalentRole).where(TalentRole.id == id)
    result = await db.execute(stmt)
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Talent role not found")

    for key, value in role_in.model_dump(exclude_unset=True).items():
        setattr(role, key, value)

    await db.commit()
    await db.refresh(role)
    return role


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a talent role (Admin only)")
async def delete_talent_role(
    id: int,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> None:
    stmt = select(TalentRole).where(TalentRole.id == id)
    role = (await db.execute(stmt)).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=404, detail="Talent role not found")
    await db.delete(role)
    await db.commit()

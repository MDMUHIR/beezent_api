from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TeamMemberCategory
from app.schemas.cms import SlugStr


class TeamMemberBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    role: str = Field(min_length=1, max_length=255)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    category: TeamMemberCategory = TeamMemberCategory.TALENT
    featured: bool = False
    published: bool = False
    sort_order: int = 0


class TeamMemberPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    role: str
    bio: str | None = None
    avatar_url: str | None = None
    category: TeamMemberCategory
    featured: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class TeamMemberAdmin(TeamMemberBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class TeamMemberCreate(TeamMemberBase):
    pass


class TeamMemberUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    role: str | None = Field(default=None, min_length=1, max_length=255)
    bio: str | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    category: TeamMemberCategory | None = None
    featured: bool | None = None
    published: bool | None = None
    sort_order: int | None = None

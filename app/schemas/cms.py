import re
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models.enums import ProjectStatus

SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def _normalize_slug(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().lower()
    if not SLUG_PATTERN.fullmatch(value):
        raise ValueError("slug must contain only lowercase letters, numbers, and hyphens")
    return value


SlugStr = Annotated[str, AfterValidator(_normalize_slug)]


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int


class ProjectRefPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str


# --------------------------------------------------------------------------- #
# Project
# --------------------------------------------------------------------------- #
class ProjectBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = None
    client_name: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    project_type: str | None = Field(default=None, max_length=100)
    status: ProjectStatus = ProjectStatus.ACTIVE
    featured: bool = False
    published: bool = False
    cover_image: str | None = Field(default=None, max_length=500)
    live_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    technologies: list[Any] = Field(default_factory=list)
    results: list[Any] = Field(default_factory=list)


class ProjectPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    slug: str
    short_description: str | None = None
    description: str | None = None
    client_name: str | None = None
    industry: str | None = None
    project_type: str | None = None
    status: ProjectStatus
    featured: bool
    cover_image: str | None = None
    live_url: str | None = None
    github_url: str | None = None
    technologies: list[Any] = Field(default_factory=list)
    results: list[Any] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = None
    client_name: str | None = Field(default=None, max_length=255)
    industry: str | None = Field(default=None, max_length=100)
    project_type: str | None = Field(default=None, max_length=100)
    status: ProjectStatus | None = None
    featured: bool | None = None
    published: bool | None = None
    cover_image: str | None = Field(default=None, max_length=500)
    live_url: str | None = Field(default=None, max_length=500)
    github_url: str | None = Field(default=None, max_length=500)
    technologies: list[Any] | None = None
    results: list[Any] | None = None


class ProjectAdmin(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Service / Solution
# --------------------------------------------------------------------------- #
class ServiceBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=100)
    featured: bool = False
    published: bool = False
    sort_order: int = 0


class ServicePublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    short_description: str | None = None
    description: str | None = None
    icon: str | None = None
    featured: bool
    sort_order: int
    created_at: datetime
    updated_at: datetime


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=100)
    featured: bool | None = None
    published: bool | None = None
    sort_order: int | None = None


class ServiceAdmin(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class SolutionPublic(ServicePublic):
    pass


class SolutionCreate(ServiceBase):
    pass


class SolutionUpdate(ServiceUpdate):
    pass


class SolutionAdmin(ServiceAdmin):
    pass


# --------------------------------------------------------------------------- #
# CaseStudy
# --------------------------------------------------------------------------- #
class CaseStudyBase(BaseModel):
    project_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    summary: str | None = None
    challenge: str | None = None
    solution: str | None = None
    implementation: str | None = None
    results: list[Any] = Field(default_factory=list)
    technologies: list[Any] = Field(default_factory=list)
    metrics: list[Any] = Field(default_factory=list)
    featured: bool = False
    published: bool = False
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = Field(default=None, max_length=255)


class CaseStudyPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project: ProjectRefPublic | None = None
    title: str
    slug: str
    summary: str | None = None
    challenge: str | None = None
    solution: str | None = None
    implementation: str | None = None
    results: list[Any] = Field(default_factory=list)
    technologies: list[Any] = Field(default_factory=list)
    metrics: list[Any] = Field(default_factory=list)
    featured: bool
    seo_title: str | None = None
    seo_description: str | None = None
    created_at: datetime
    updated_at: datetime


class CaseStudyCreate(CaseStudyBase):
    pass


class CaseStudyUpdate(BaseModel):
    project_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    summary: str | None = None
    challenge: str | None = None
    solution: str | None = None
    implementation: str | None = None
    results: list[Any] | None = None
    technologies: list[Any] | None = None
    metrics: list[Any] | None = None
    featured: bool | None = None
    published: bool | None = None
    seo_title: str | None = Field(default=None, max_length=255)
    seo_description: str | None = Field(default=None, max_length=255)


class CaseStudyAdmin(CaseStudyBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime

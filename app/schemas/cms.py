import re
from datetime import datetime
from typing import Annotated, Any
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from app.models.enums import DemoVideoType, ProjectStatus

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
# Solution categories
# --------------------------------------------------------------------------- #
class SolutionCategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class SolutionCategoryPublic(SolutionCategoryRef):
    description: str | None = None
    sort_order: int


class SolutionCategoryDetail(SolutionCategoryPublic):
    solutions: list["SolutionPublic"] = Field(default_factory=list)


class SolutionCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    description: str | None = None
    sort_order: int = 0


class SolutionCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = None


class SolutionCategoryAdmin(SolutionCategoryRef):
    description: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Service categories
# --------------------------------------------------------------------------- #
class ServiceCategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class ServiceCategoryPublic(ServiceCategoryRef):
    description: str | None = None
    sort_order: int


class ServiceCategoryDetail(ServiceCategoryPublic):
    services: list["ServicePublic"] = Field(default_factory=list)


class ServiceCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    description: str | None = None
    sort_order: int = 0


class ServiceCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = None


class ServiceCategoryAdmin(ServiceCategoryRef):
    description: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Project categories
# --------------------------------------------------------------------------- #
class ProjectCategoryRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str


class ProjectCategoryPublic(ProjectCategoryRef):
    description: str | None = None
    sort_order: int


class ProjectCategoryDetail(ProjectCategoryPublic):
    projects: list["ProjectPublic"] = Field(default_factory=list)


class ProjectCategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    description: str | None = None
    sort_order: int = 0


class ProjectCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    sort_order: int | None = None


class ProjectCategoryAdmin(ProjectCategoryRef):
    description: str | None = None
    sort_order: int
    created_at: datetime
    updated_at: datetime


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
    demo_video_url: str | None = Field(default=None, max_length=500)
    demo_video_type: DemoVideoType | None = None
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
    demo_video_url: str | None = None
    demo_video_type: DemoVideoType | None = None
    technologies: list[Any] = Field(default_factory=list)
    results: list[Any] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    categories: list[ProjectCategoryRef] = Field(default_factory=list)


class ProjectCreate(ProjectBase):
    category_ids: list[UUID] | None = None


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
    demo_video_url: str | None = Field(default=None, max_length=500)
    demo_video_type: DemoVideoType | None = None
    category_ids: list[UUID] | None = None


class ProjectAdmin(ProjectBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    categories: list[ProjectCategoryRef] = Field(default_factory=list)


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
    categories: list[ServiceCategoryRef] = Field(default_factory=list)


class ServiceCreate(ServiceBase):
    category_ids: list[UUID] | None = None


class ServiceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    slug: SlugStr | None = Field(default=None, min_length=1, max_length=255)
    short_description: str | None = Field(default=None, max_length=300)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=100)
    featured: bool | None = None
    published: bool | None = None
    sort_order: int | None = None
    category_ids: list[UUID] | None = None


class ServiceAdmin(ServiceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    categories: list[ServiceCategoryRef] = Field(default_factory=list)


class SolutionPublic(ServicePublic):
    categories: list[SolutionCategoryRef] = Field(default_factory=list)
    image_url: str | None = None
    demo_video_url: str | None = None
    demo_video_type: DemoVideoType | None = None


class SolutionCreate(ServiceBase):
    category_ids: list[UUID] | None = None
    image_url: str | None = Field(default=None, max_length=500)
    demo_video_url: str | None = Field(default=None, max_length=500)
    demo_video_type: DemoVideoType | None = None


class SolutionUpdate(ServiceUpdate):
    category_ids: list[UUID] | None = None
    image_url: str | None = Field(default=None, max_length=500)
    demo_video_url: str | None = Field(default=None, max_length=500)
    demo_video_type: DemoVideoType | None = None


class SolutionAdmin(ServiceAdmin):
    categories: list[SolutionCategoryRef] = Field(default_factory=list)
    image_url: str | None = None
    demo_video_url: str | None = None
    demo_video_type: DemoVideoType | None = None


# --------------------------------------------------------------------------- #
# CaseStudy
# --------------------------------------------------------------------------- #
class CaseStudyBase(BaseModel):
    project_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    slug: SlugStr = Field(min_length=1, max_length=255)
    summary: str | None = None
    image_url: str | None = Field(default=None, max_length=500)
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
    image_url: str | None = None
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
    image_url: str | None = Field(default=None, max_length=500)
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


SolutionCategoryDetail.model_rebuild()
ServiceCategoryDetail.model_rebuild()
ProjectCategoryDetail.model_rebuild()

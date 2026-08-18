from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ------------------ Tech Stack Schemas ------------------ #
class TechStackBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=120)
    category: str = Field("General", max_length=100)
    icon_url: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    is_active: bool = True


class TechStackCreate(TechStackBase):
    pass


class TechStackUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    category: Optional[str] = None
    icon_url: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TechStackResponse(TechStackBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Service Category Schemas ------------------ #
class ServiceCategoryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=120)
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: int = 0
    is_active: bool = True


class ServiceCategoryCreate(ServiceCategoryBase):
    pass


class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None


class ServiceCategoryResponse(ServiceCategoryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Service Schemas ------------------ #
class ServiceBase(BaseModel):
    category_id: int
    title: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=220)
    short_description: str = Field(..., max_length=500)
    content: str  # Markdown or HTML
    icon_url: Optional[str] = None
    featured: bool = False
    display_order: int = 0
    is_active: bool = True


class ServiceCreate(ServiceBase):
    tech_stack_ids: Optional[List[int]] = []


class ServiceUpdate(BaseModel):
    category_id: Optional[int] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    short_description: Optional[str] = None
    content: Optional[str] = None
    icon_url: Optional[str] = None
    featured: Optional[bool] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    tech_stack_ids: Optional[List[int]] = None


class ServiceResponse(ServiceBase):
    id: int
    category: Optional[ServiceCategoryResponse] = None
    tech_stacks: List[TechStackResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ServiceCategoryWithServicesResponse(ServiceCategoryResponse):
    services: List[ServiceResponse] = []

    model_config = ConfigDict(from_attributes=True)

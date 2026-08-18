from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


# ------------------ Testimonial Schemas ------------------ #
class TestimonialBase(BaseModel):
    client_name: str = Field(..., max_length=150)
    client_role: str = Field(..., max_length=150)
    client_company: str = Field(..., max_length=150)
    avatar_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    quote: str
    rating: int = Field(5, ge=1, le=5)
    video_url: Optional[str] = None
    project_title: Optional[str] = None
    featured: bool = False
    is_active: bool = True
    display_order: int = 0


class TestimonialCreate(TestimonialBase):
    pass


class TestimonialUpdate(BaseModel):
    client_name: Optional[str] = None
    client_role: Optional[str] = None
    client_company: Optional[str] = None
    avatar_url: Optional[str] = None
    company_logo_url: Optional[str] = None
    quote: Optional[str] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    video_url: Optional[str] = None
    project_title: Optional[str] = None
    featured: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class TestimonialResponse(TestimonialBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Press Coverage Schemas ------------------ #
class PressCoverageBase(BaseModel):
    publisher_name: str = Field(..., max_length=150)
    publisher_logo_url: Optional[str] = None
    headline: str = Field(..., max_length=300)
    article_url: str = Field(..., max_length=500)
    excerpt: Optional[str] = None
    published_date: Optional[date] = None
    featured: bool = False
    is_active: bool = True
    display_order: int = 0


class PressCoverageCreate(PressCoverageBase):
    pass


class PressCoverageUpdate(BaseModel):
    publisher_name: Optional[str] = None
    publisher_logo_url: Optional[str] = None
    headline: Optional[str] = None
    article_url: Optional[str] = None
    excerpt: Optional[str] = None
    published_date: Optional[date] = None
    featured: Optional[bool] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class PressCoverageResponse(PressCoverageBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Company Stat Schemas ------------------ #
class CompanyStatBase(BaseModel):
    label: str = Field(..., max_length=100)
    metric_value: str = Field(..., max_length=50)
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: bool = True
    display_order: int = 0


class CompanyStatCreate(CompanyStatBase):
    pass


class CompanyStatUpdate(BaseModel):
    label: Optional[str] = None
    metric_value: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class CompanyStatResponse(CompanyStatBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

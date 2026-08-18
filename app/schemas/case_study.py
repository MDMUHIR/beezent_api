from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


# ------------------ Industry Schemas ------------------ #
class IndustryBase(BaseModel):
    name: str = Field(..., max_length=100)
    slug: str = Field(..., max_length=120)
    description: Optional[str] = None
    icon: Optional[str] = None


class IndustryCreate(IndustryBase):
    pass


class IndustryUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class IndustryResponse(IndustryBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Metric Schemas ------------------ #
class CaseStudyMetricBase(BaseModel):
    label: str = Field(..., max_length=100)
    value: str = Field(..., max_length=50)
    description: Optional[str] = None
    display_order: int = 0


class CaseStudyMetricCreate(CaseStudyMetricBase):
    pass


class CaseStudyMetricResponse(CaseStudyMetricBase):
    id: int
    case_study_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Case Study Schemas ------------------ #
class CaseStudyBase(BaseModel):
    industry_id: Optional[int] = None
    title: str = Field(..., max_length=255)
    slug: str = Field(..., max_length=270)
    client_name: str = Field(..., max_length=150)
    client_logo_url: Optional[str] = None
    summary: str = Field(..., max_length=600)
    challenge: str
    solution: str
    result: str
    cover_image_url: str
    gallery_images: Optional[List[str]] = []
    live_url: Optional[str] = None
    featured: bool = False
    is_published: bool = True
    display_order: int = 0


class CaseStudyCreate(CaseStudyBase):
    metrics: Optional[List[CaseStudyMetricCreate]] = []


class CaseStudyUpdate(BaseModel):
    industry_id: Optional[int] = None
    title: Optional[str] = None
    slug: Optional[str] = None
    client_name: Optional[str] = None
    client_logo_url: Optional[str] = None
    summary: Optional[str] = None
    challenge: Optional[str] = None
    solution: Optional[str] = None
    result: Optional[str] = None
    cover_image_url: Optional[str] = None
    gallery_images: Optional[List[str]] = None
    live_url: Optional[str] = None
    featured: Optional[bool] = None
    is_published: Optional[bool] = None
    display_order: Optional[int] = None
    metrics: Optional[List[CaseStudyMetricCreate]] = None


class CaseStudyResponse(CaseStudyBase):
    id: int
    industry: Optional[IndustryResponse] = None
    metrics: List[CaseStudyMetricResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

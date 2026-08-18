from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.career import ApplicationStatus


# ------------------ Job Application Schemas ------------------ #
class JobApplicationBase(BaseModel):
    candidate_name: str = Field(..., max_length=150)
    email: EmailStr
    phone: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    resume_url: str = Field(..., max_length=500)
    cover_letter: Optional[str] = None
    years_of_experience: Optional[int] = None


class JobApplicationCreate(JobApplicationBase):
    job_posting_id: int


class JobApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    admin_notes: Optional[str] = None


class JobApplicationResponse(JobApplicationBase):
    id: int
    job_posting_id: int
    status: ApplicationStatus
    admin_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ------------------ Job Posting Schemas ------------------ #
class JobPostingBase(BaseModel):
    title: str = Field(..., max_length=200)
    slug: str = Field(..., max_length=220)
    department: str = Field("Engineering", max_length=100)
    location_type: str = Field("Remote", max_length=50)
    location: str = Field("Global / Remote", max_length=150)
    employment_type: str = Field("Full-Time", max_length=50)
    experience_level: str = Field("Senior", max_length=50)
    salary_range: Optional[str] = None
    summary: str = Field(..., max_length=500)
    description: str
    requirements: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    perks: Optional[List[str]] = Field(default_factory=list)
    deadline: Optional[date] = None
    is_active: bool = True
    display_order: int = 0


class JobPostingCreate(JobPostingBase):
    pass


class JobPostingUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    department: Optional[str] = None
    location_type: Optional[str] = None
    location: Optional[str] = None
    employment_type: Optional[str] = None
    experience_level: Optional[str] = None
    salary_range: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    responsibilities: Optional[List[str]] = None
    perks: Optional[List[str]] = None
    deadline: Optional[date] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class JobPostingResponse(JobPostingBase):
    id: int
    applications_count: Optional[int] = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

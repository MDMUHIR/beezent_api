from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class TalentRoleBase(BaseModel):
    title: str = Field(..., max_length=150)
    slug: str = Field(..., max_length=170)
    department: str = Field("Engineering", max_length=100)
    experience_level: str = Field("Senior (5+ yrs)", max_length=50)
    core_skills: List[str] = Field(default_factory=list)
    short_description: str
    availability: str = Field("Available in 48 hrs", max_length=50)
    hourly_rate_estimate: Optional[str] = None
    is_active: bool = True
    display_order: int = 0


class TalentRoleCreate(TalentRoleBase):
    pass


class TalentRoleUpdate(BaseModel):
    title: Optional[str] = None
    slug: Optional[str] = None
    department: Optional[str] = None
    experience_level: Optional[str] = None
    core_skills: Optional[List[str]] = None
    short_description: Optional[str] = None
    availability: Optional[str] = None
    hourly_rate_estimate: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class TalentRoleResponse(TalentRoleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

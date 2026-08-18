from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin, get_current_editor, get_db
from app.models.career import ApplicationStatus, JobApplication, JobPosting
from app.models.user import User
from app.schemas.career import (
    JobApplicationBase,
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
    JobPostingCreate,
    JobPostingResponse,
    JobPostingUpdate,
)

router = APIRouter()


# ------------------ Public Job Postings ------------------ #
@router.get("/jobs", response_model=List[JobPostingResponse], summary="List open career positions")
async def list_jobs(
    department: Optional[str] = None,
    location_type: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = (
        select(JobPosting)
        .where(JobPosting.is_active.is_(True))
        .order_by(JobPosting.display_order, JobPosting.created_at.desc())
    )
    if department:
        stmt = stmt.where(JobPosting.department.ilike(department))
    if location_type:
        stmt = stmt.where(JobPosting.location_type.ilike(location_type))

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/jobs/{slug}", response_model=JobPostingResponse, summary="Get job position details by slug")
async def get_job_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(JobPosting).where(JobPosting.slug == slug, JobPosting.is_active.is_(True))
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return job


@router.post("/jobs", response_model=JobPostingResponse, status_code=status.HTTP_201_CREATED, summary="Create a new job posting (Editor only)")
async def create_job_posting(
    job_in: JobPostingCreate,
    current_user: User = Depends(get_current_editor),
    db: AsyncSession = Depends(get_db)
) -> Any:
    existing = await db.execute(select(JobPosting).where(JobPosting.slug == job_in.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Job slug already exists")

    job = JobPosting(**job_in.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


# ------------------ Job Applications ------------------ #
@router.post("/jobs/{job_id}/apply", response_model=JobApplicationResponse, status_code=status.HTTP_201_CREATED, summary="Submit candidate job application")
async def apply_for_job(
    job_id: int,
    app_in: JobApplicationBase,
    db: AsyncSession = Depends(get_db)
) -> Any:
    # Verify job exists and is active
    job = (await db.execute(select(JobPosting).where(JobPosting.id == job_id, JobPosting.is_active.is_(True)))).scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job posting is no longer active or does not exist")

    application = JobApplication(
        job_posting_id=job_id,
        candidate_name=app_in.candidate_name,
        email=app_in.email,
        phone=app_in.phone,
        linkedin_url=app_in.linkedin_url,
        portfolio_url=app_in.portfolio_url,
        resume_url=app_in.resume_url,
        cover_letter=app_in.cover_letter,
        years_of_experience=app_in.years_of_experience,
        status=ApplicationStatus.PENDING,
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)
    return application


@router.get("/applications", response_model=List[JobApplicationResponse], summary="List candidate job applications (Admin only)")
async def list_applications(
    job_id: Optional[int] = None,
    status_filter: Optional[ApplicationStatus] = None,
    skip: int = 0,
    limit: int = 50,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(JobApplication).order_by(JobApplication.created_at.desc())
    if job_id:
        stmt = stmt.where(JobApplication.job_posting_id == job_id)
    if status_filter:
        stmt = stmt.where(JobApplication.status == status_filter)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.patch("/applications/{id}", response_model=JobApplicationResponse, summary="Update candidate application review status (Admin only)")
async def update_application_status(
    id: int,
    app_update: JobApplicationUpdate,
    current_admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db)
) -> Any:
    stmt = select(JobApplication).where(JobApplication.id == id)
    result = await db.execute(stmt)
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail="Job application not found")

    if app_update.status is not None:
        app.status = app_update.status
    if app_update.admin_notes is not None:
        app.admin_notes = app_update.admin_notes

    await db.commit()
    await db.refresh(app)
    return app

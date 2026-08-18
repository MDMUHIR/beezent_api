from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    careers,
    case_studies,
    inquiries,
    services,
    social_proof,
    talent,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & Users"])
api_router.include_router(services.router, prefix="/services", tags=["Services & Tech Stack"])
api_router.include_router(case_studies.router, prefix="/case-studies", tags=["Portfolio & Case Studies"])
api_router.include_router(talent.router, prefix="/talent", tags=["Staff Augmentation & Talent"])
api_router.include_router(social_proof.router, prefix="/social-proof", tags=["Social Proof & Press"])
api_router.include_router(inquiries.router, prefix="/inquiries", tags=["Inquiries & Leads"])
api_router.include_router(careers.router, prefix="/careers", tags=["Careers & Recruitment"])

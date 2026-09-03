from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models import Lead
from app.schemas import LeadCreate, LeadPublicResponse

router = APIRouter(prefix="/leads", tags=["leads"])


@router.post("", response_model=LeadPublicResponse, status_code=status.HTTP_201_CREATED)
async def create_lead(
    payload: LeadCreate,
    session: AsyncSession = Depends(get_session),
) -> LeadPublicResponse:
    """Public lead submission. No authentication required."""
    lead = Lead(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        company=payload.company,
        service=payload.service,
        message=payload.message,
        source=payload.source,
    )
    session.add(lead)
    await session.commit()
    return LeadPublicResponse(id=lead.id)

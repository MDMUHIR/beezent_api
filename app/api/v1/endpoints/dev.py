from fastapi import APIRouter, Depends

from app.api.v1.deps import require_admin, require_staff
from app.models import User

router = APIRouter(prefix="/dev", tags=["development"])


@router.get("/staff")
async def staff_only(current_user: User = Depends(require_staff)) -> dict[str, str]:
    return {"status": "ok", "role": current_user.role, "message": "staff access granted"}


@router.get("/admin")
async def admin_only(current_user: User = Depends(require_admin)) -> dict[str, str]:
    return {"status": "ok", "role": current_user.role, "message": "admin access granted"}

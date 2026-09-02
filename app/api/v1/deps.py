from datetime import UTC, datetime

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import hash_session_token
from app.models import Role, User, UserSession

credentials_error = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
)


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise credentials_error

    user_session = await session.scalar(
        select(UserSession).where(UserSession.token_hash == hash_session_token(token))
    )
    if user_session is None:
        raise credentials_error

    if user_session.expires_at < datetime.now(UTC):
        await session.delete(user_session)
        await session.commit()
        raise credentials_error

    user = await session.get(User, user_session.user_id)
    if user is None or not user.is_active:
        raise credentials_error
    return user


def require_authenticated_user(current_user: User = Depends(get_current_user)) -> User:
    return current_user


def require_staff(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (Role.STAFF, Role.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != Role.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions",
        )
    return current_user

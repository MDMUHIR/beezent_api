from typing import Optional
from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from starlette.responses import RedirectResponse
from sqlalchemy import select

from app.core.config import settings
from app.core.database import sync_engine, SyncSessionLocal
from app.core.security import create_access_token, decode_token, verify_password
from app.models.user import User, UserRole


class AdminAuth(AuthenticationBackend):
    """
    SQLAdmin Authentication Backend handling session cookies,
    login validation, and role-based dashboard protection.
    """

    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        if not username or not password:
            return False

        with SyncSessionLocal() as session:
            stmt = select(User).where(User.email == str(username))
            user = session.execute(stmt).scalar_one_or_none()

            if not user or not verify_password(str(password), user.hashed_password):
                return False

            if not user.is_active:
                return False

            # Require Admin or Super Admin role to access SQLAdmin
            if user.role not in [UserRole.SUPER_ADMIN, UserRole.ADMIN]:
                return False

            token = create_access_token(
                subject=user.email,
                role=user.role.value
            )
            request.session.update({"token": token, "user_email": user.email, "role": user.role.value})
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request) -> Optional[RedirectResponse]:
        token = request.session.get("token")
        if not token:
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        payload = decode_token(token)
        if not payload:
            request.session.clear()
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        role = payload.get("role")
        if role not in [UserRole.SUPER_ADMIN.value, UserRole.ADMIN.value]:
            request.session.clear()
            return RedirectResponse(request.url_for("admin:login"), status_code=302)

        return True


admin_authentication_backend = AdminAuth(secret_key=settings.SECRET_KEY)

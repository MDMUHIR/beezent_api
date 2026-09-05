import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import hash_password
from app.models import Role, User

logger = logging.getLogger("app.seed")


async def seed_dev_admin(session: AsyncSession, settings: Settings) -> None:
    """Create the configured development admin if it does not already exist.

    Runs only when explicitly enabled via settings (SEED_DEV_ADMIN=true). The
    account is created with the `admin` role, active and verified, so it can
    immediately authenticate and access staff/admin endpoints.
    """
    if not settings.seed_dev_admin:
        return
    if not settings.seed_admin_email or not settings.seed_admin_password:
        logger.warning("SEED_DEV_ADMIN is enabled but email/password are not set; skipping")
        return

    email = settings.seed_admin_email.strip().lower()
    existing = await session.scalar(select(User.id).where(User.email == email))
    if existing is not None:
        return

    role = Role(settings.seed_admin_role) if settings.seed_admin_role in Role else Role.ADMIN
    user = User(
        email=email,
        password_hash=hash_password(settings.seed_admin_password),
        full_name=settings.seed_admin_full_name or "Default Admin",
        role=role,
        is_active=True,
        is_verified=True,
    )
    session.add(user)
    await session.commit()
    logger.info("Seeded dev admin account: %s", email)

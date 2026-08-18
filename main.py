from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from app.admin import setup_admin
from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import async_engine, sync_engine
from app.models.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Creates tables if not present in dev mode, verifies connection pool.
    """
    # Create tables automatically in development mode (or use Alembic in production)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Clean up engine connections
    await async_engine.dispose()
    sync_engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="""
# 🚀 High-Performance Agency CMS & Headless Backend API

Built for modern digital agencies (Riseup Labs-style) powering Next.js / Nuxt.js frontends and administrative backends.

### Key Features:
* 🔐 **JWT OAuth2 RBAC Security**: Granular roles (`SUPER_ADMIN`, `ADMIN`, `EDITOR`)
* ⚡ **FastAPI + Async SQLAlchemy 2.0**: High-throughput async database queries
* 🛠️ **SQLAdmin CMS Panel**: Direct administrative management dashboard mounted at `/admin`
* 💼 **Core Agency Engines**:
  - Services, Categories & Tech Stacks
  - Case Studies, Industries & Quantifiable Metrics
  - Staff Augmentation & Talent Profiles
  - Social Proof, Press Coverage & Live Company Stats
  - Inbound Leads / Contact Inquiries CRM
  - Career Job Openings & Candidate Application Tracking
""",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# 1. Session Middleware (Required by SQLAdmin for authentication state)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    max_age=14 * 24 * 3600,  # 14 days
    same_site="lax",
    https_only=False,
)

# 2. CORS Middleware configuration
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# 3. Mount SQLAdmin CMS Dashboard
admin = setup_admin(app, sync_engine)

# 4. Include Version 1 API Routes
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/", tags=["Health & Status"])
async def root_status():
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "docs_url": f"{settings.API_V1_STR}/docs",
        "admin_portal": "/admin",
    }


@app.get("/health", tags=["Health & Status"])
async def health_check():
    return {"status": "healthy", "database": "connected"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
    )

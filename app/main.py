import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, dispose_engine
from app.core.logging import setup_logging
from app.core.middleware import SECURITY_HEADERS, SecurityHeadersMiddleware
from app.core.seed import seed_dev_admin

logger = logging.getLogger("app.main")

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    if settings.seed_dev_admin:
        async with AsyncSessionLocal() as session:
            await seed_dev_admin(session, settings)
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

# Middleware is applied outermost-to-innermost in the order add_middleware is
# called, so SecurityHeaders (added last) is outermost and annotates every
# response, including CORS/trusted-host rejections and 500 errors.
if settings.cors_allowed_origins:
    origins = [o.strip() for o in settings.cors_allowed_origins.split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
if settings.trusted_hosts:
    allowed_hosts = [h.strip() for h in settings.trusted_hosts.split(",") if h.strip()]
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix=settings.api_v1_prefix)

# Serve locally-stored media (development). Production object storage serves
# media directly from the CDN/public URL instead.
if settings.storage_backend == "local":
    media_root = Path(settings.media_root)
    media_root.mkdir(parents=True, exist_ok=True)
    app.mount("/media", StaticFiles(directory=str(media_root)), name="media")


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Log unexpected exceptions server-side; never leak details to clients.

    FastAPI routes the `Exception` handler to Starlette's outermost
    ServerErrorMiddleware, whose response bypasses the app middleware stack,
    so the security headers are applied here explicitly as well.
    """
    logger.exception("Unhandled exception while processing %s %s", request.method, request.url.path)
    response = JSONResponse(status_code=500, content={"detail": "Internal Server Error"})
    for key, value in SECURITY_HEADERS.items():
        response.headers.setdefault(key, value)
    return response


@app.get("/health", tags=["health"])
async def root_health() -> dict[str, str]:
    return {"status": "healthy"}

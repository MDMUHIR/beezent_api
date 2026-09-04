# syntax=docker/dockerfile:1
# Beezents Backend - production-oriented, multi-stage Docker image.

# --- Builder: install production deps with uv into a venv -------------------
FROM python:3.12-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

COPY --from=ghcr.io/astral-sh/uv:0.12.8 /uv /uvx /bin/

WORKDIR /app

# Only the dependency manifests are needed here; the source is copied in the
# runtime stage. --no-install-project skips packaging the app itself.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# --- Runtime: minimal image with the venv + source, non-root ----------------
FROM python:3.12-slim AS runtime

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# Non-root runtime user.
RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app appuser

COPY --from=builder /app/.venv /app/.venv

COPY app ./app
COPY migrations ./migrations
COPY alembic.ini ./
COPY docker-entrypoint.sh ./

# Pre-create the media directory so named volumes mount it with appuser
# ownership (Docker copies directory ownership from the image at mount time).
RUN mkdir -p /app/media \
    && chown -R appuser:appuser /app \
    && chmod +x /app/docker-entrypoint.sh

USER appuser

# Liveness check with stdlib urllib (no curl needed in the runtime image).
HEALTHCHECK --interval=30s --timeout=5s --start-period=15s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4).status == 200 else 1)"

EXPOSE 8000

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
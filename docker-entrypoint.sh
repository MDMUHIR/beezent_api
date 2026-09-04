#!/bin/sh
# Beezents Backend container entrypoint.
#
# Graceful startup: apply database migrations, then hand off to the API
# server. The server itself handles graceful shutdown (SIGTERM/SIGINT),
# including disposing the SQLAlchemy engine in the FastAPI lifespan.
set -eu

if [ "${SKIP_MIGRATIONS:-0}" != "1" ]; then
    echo "[entrypoint] Running database migrations (alembic upgrade head)..."
    alembic upgrade head
    echo "[entrypoint] Migrations applied."
else
    echo "[entrypoint] SKIP_MIGRATIONS=1, skipping database migrations."
fi

WORKERS="${UVICORN_WORKERS:-1}"
echo "[entrypoint] Starting uvicorn with ${WORKERS} worker(s)."
exec python -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --workers "${WORKERS}"
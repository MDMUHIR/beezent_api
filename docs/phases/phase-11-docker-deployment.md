# Phase 11 Report — Docker & Deployment

**Project:** Beezents Backend
**Phase scope:** Production-oriented Docker configuration
**Date:** 2026-09-03
**Status:** Complete — image built and verified locally with Docker 29 / Compose 2.40

---

## 1. Phase objective

Prepare the backend for reliable deployment with production-oriented Docker
configuration: a multi-stage build, minimal runtime image, non-root user,
environment-based configuration, health check, graceful startup/shutdown,
externalized PostgreSQL, and a local-development compose stack. Verify the image
locally (build, startup, health, DB connection, migrations, API availability).

## 2. Scope

- `Dockerfile` (multi-stage, `python:3.12-slim`, non-root `appuser`).
- `docker-entrypoint.sh` (runs `alembic upgrade head`, then starts Uvicorn).
- `.dockerignore` (no venv/.env/secrets/tests/docs in the build context).
- `docker-compose.yml` (local dev: API + throwaway PostgreSQL 16).
- README environment-variable documentation.
- Local build + full runtime verification against real PostgreSQL in containers.

Out of scope: cloud deployment (K8s/ECS/etc.), CI pipeline, TLS/ingress, image
registry pushing, Gunicorn.

## 3. Acceptance criteria

| Criterion | Status |
| --- | --- |
| Multi-stage Docker build | ✅ builder + runtime stages |
| Minimal runtime image | ✅ `python:3.12-slim` + venv + source (~427 MB) |
| Non-root user | ✅ `appuser` (verified `whoami` → `appuser`) |
| Environment-based configuration | ✅ all config via env; no secrets in image |
| No secrets in image | ✅ `.env`/`.env.*` excluded by `.dockerignore` |
| Health check | ✅ Docker `HEALTHCHECK` (`/health`) — container reported `healthy` |
| Uvicorn/Gunicorn strategy | ✅ Uvicorn with configurable workers; Gunicorn documented as optional |
| PostgreSQL externalized | ✅ compose DB is dev-only; production uses external/managed PG |
| Graceful startup | ✅ migrations applied on startup, then server starts |
| Graceful shutdown | ✅ SIGTERM → "Application shutdown complete" (engine disposed) |
| docker-compose.yml useful for local dev | ✅ |
| Image built + verified locally | ✅ |
| README env-variable documentation | ✅ |
| Phase report created | ✅ |

## 4. What was implemented

- **`Dockerfile`**:
  - **Builder** (`python:3.12-slim`): copies `uv` from `ghcr.io/astral-sh/uv:0.12.8`,
    installs production dependencies only via `uv sync --frozen --no-dev
    --no-install-project` (project source is NOT packaged; it is copied into the
    runtime image directly).
  - **Runtime** (`python:3.12-slim`): copies the built venv + `app/`,
    `migrations/`, `alembic.ini`, `docker-entrypoint.sh`; creates a non-root
    `appuser`; `ENV PATH=…/.venv/bin`, `PYTHONPATH=/app`,
    `PYTHONUNBUFFERED=1`, `PYTHONDONTWRITEBYTECODE=1`.
  - Pre-creates `/app/media` owned by `appuser` so named volumes mount it with
    correct ownership (fix for an issue found during live testing, see §12).
  - `HEALTHCHECK` calls `/health` with stdlib urllib (no `curl` in the image).
  - `ENTRYPOINT` = entrypoint script; `CMD` = `python -m uvicorn app.main:app
    --host 0.0.0.0 --port 8000 --workers 1` (worker count overridable via
    `UVICORN_WORKERS`).
- **`docker-entrypoint.sh`**: `set -eu`; runs `alembic upgrade head` unless
  `SKIP_MIGRATIONS=1`; then `exec python -m uvicorn …` with `${UVICORN_WORKERS:-1}`.
- **`.dockerignore`**: excludes `.git`, `.env*` (keeping `.env.example`), `.venv`,
  `__pycache__`, tests, docs, caches, `media/`, and the Docker files themselves.
- **`docker-compose.yml`** (local dev only): `db` (postgres:16, healthchecked,
  host port `5433:5432` to avoid clashing with a local PostgreSQL) + `api`
  (`build: .`, env `DATABASE_URL` → `db`, local storage backend, `media-data`
  volume, `depends_on: db: service_healthy`). Commented `CORS_ALLOWED_ORIGINS` /
  `TRUSTED_HOSTS` for the future Next.js origin.
- **README** "Docker & deployment" section: compose usage, manual build/run,
  and the full container runtime environment-variable table.

## 5. Files created

| File | Purpose |
| --- | --- |
| `Dockerfile` | Multi-stage production image |
| `docker-entrypoint.sh` | Migrations + Uvicorn startup entrypoint |
| `.dockerignore` | Build-context exclusions (secrets/tests/docs/caches) |
| `docker-compose.yml` | Local development stack (API + PostgreSQL) |
| `docs/phases/phase-11-docker-deployment.md` | This report |

## 6. Files modified

| File | Change |
| --- | --- |
| `README.md` | Added "Docker & deployment" section + env-var table |

No application code or dependencies changed; no lockfile change.

## 7. Database changes

**None.** No schema changes; `alembic check` clean at `147c3d1fc707 (head)`. The
containerized entrypoint applies all five existing migrations on a fresh
database (verified live: `base → 0857ebb26254 → 6f5c71d4f8e6 → eef51e823865 →
f52bdc6b0961 → 147c3d1fc707`).

## 8. API endpoints

No endpoints changed. Availability was verified in-container for `/health`,
`/api/v1/health`, `/api/v1/health/db`, `/api/v1/projects`, `/api/v1/leads`
(POST), `/api/v1/admin/*` (auth + RBAC), and `/media/{key}` (uploaded file
serving).

## 9. Authentication / authorization

Unchanged and re-verified inside the container: register → role promotion (via
DB) → login (session cookie) → authenticated admin access to `/api/v1/admin/*`;
public endpoints remain unauthenticated.

## 10. Validation rules

Unchanged. The in-container lead submission and media upload exercised the
existing validation (MIME/size/length rules) end-to-end.

## 11. Testing

No new pytest tests (this phase is infrastructure). The existing full suite
still passes (**276 passed**) with ruff/format/lock/alembic clean. Docker
verification was performed live (see §19) rather than via unit tests.

## 12. Bugs discovered

1. **`/app/media` was not writable by the non-root user inside a named volume.**
   The image did not pre-create the media directory, so Docker initialized the
   `media-data` volume mount point as `root:root`. `appuser` could not write —
   the local storage backend would fail to save uploads. Confirmed live:
   `touch /app/media/…` → "media NOT writable".
2. **`.dockerignore` initially excluded `docker-entrypoint.sh`** — which the
   Dockerfile `COPY`s — which would have failed the build. Caught before
   building (removed the entrypoint line from `.dockerignore`).

## 13. Root causes

1. Docker initializes a named-volume mount point using the directory ownership
   **present in the image at mount time**; with no `/app/media` in the image,
   the mount point was created as root. The app's runtime `mkdir` is a no-op on
   the existing (root-owned) directory.
2. Over-eager build-context exclusion listed the entrypoint alongside the other
   Docker files even though it is an input to `COPY`.

## 14. Fixes applied

1. Added `mkdir -p /app/media` to the chown step in the `Dockerfile`, so the
   image ships `/app/media` owned by `appuser`; rebuilt and re-verified
   (`drwxr-xr-x appuser appuser`, write test passed, end-to-end media upload
   through the container succeeded).
2. Removed `docker-entrypoint.sh` from `.dockerignore`.

## 15. Regression tests added

No code/behavior changed in the application, so no new pytest regression tests
were required. The container-level checks (§19) serve as the regression
verification for the deployment artifacts, and the full 276-test suite still
passes.

## 16. Security checks

- **No secrets in the image**: `.env*` excluded by `.dockerignore`; all config
  is provided at runtime via environment; no credentials in any Docker file.
- **Non-root runtime**: container runs as `appuser` (verified).
- **Minimal image**: runtime stage ships only the venv + source + migrations;
  tests/docs/venv/build caches excluded.
- **Health check** uses stdlib (no extra packages).
- **Trusted hosts / CORS** remain disabled by default in the compose stack
  (dev); production operators enable them via environment.
- **PostgreSQL externalized** in production; the compose DB is explicitly a
  local-dev convenience.

## 17. Verification results (actually executed)

| Command | Result |
| --- | --- |
| `uv run pytest` | **276 passed** |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 80 files already formatted |
| `uv lock --check` | Resolved 44 packages, no drift |
| `uv run alembic check` | No new upgrade operations detected |
| `uv run alembic current` | `147c3d1fc707 (head)` |
| `docker build -t beezents-backend:phase11 .` | **Success** (image ~427 MB) |
| `docker compose up -d --build` | **Success** (db healthy → api healthy) |

## 18. Live Docker verification (actually executed)

Using `docker compose up --build` with a fresh PostgreSQL 16 container:

- **Startup**: entrypoint logged `Running database migrations (alembic upgrade
  head)…`, applied all five migrations (`base → … → 147c3d1fc707`), then
  `Starting uvicorn with 1 worker(s)` and `Application startup complete`.
- **Health endpoint**: `GET /health` → `{"status":"healthy"}` (200);
  `/api/v1/health` and `/api/v1/health/db` → 200 `{"status":"healthy"}`.
- **Container health**: `docker inspect` → `State.Health.Status = healthy`,
  `FailingStreak = 0`.
- **Database connection + migration behavior**: container connected to the
  compose PostgreSQL; all tables present (`users`, `user_sessions`, `projects`,
  `services`, `solutions`, `case_studies`, `leads`, `media`, `alembic_version`).
- **API availability**: `GET /api/v1/projects` → 200 empty envelope; public
  `POST /api/v1/leads` → 201; admin register/promote/login → admin CMS list →
  200; **media upload** → file written to `/app/media` and served via
  `GET /media/{key}` → 200 with the original bytes.
- **Non-root**: `docker exec … whoami` → `appuser`; `/app/media` owned by
  `appuser` after the fix and writable.
- **Graceful shutdown**: `docker compose stop api` → logs `Shutting down →
  Waiting for application shutdown → Application shutdown complete → Finished
  server process` (FastAPI lifespan ran `dispose_engine`).

The compose stack (containers + `pgdata`/`media-data` volumes) was torn down
after verification.

## 19. Known limitations

- **Gunicorn not used** — the image runs Uvicorn directly with a configurable
  worker count (default 1; scale via `UVICORN_WORKERS` or replicas at the
  orchestration layer). Gunicorn+UvicornWorkers is a documented alternative if
  richer process management is required.
- **Auto-migrations on startup** assume a single primary replica; with multiple
  replicas, prefer running migrations as a separate one-off job and set
  `SKIP_MIGRATIONS=1` on API replicas.
- **No CI registry push / deploy pipeline** — deferred.
- **Healthcheck port is fixed at 8000**; changing the container port requires
  updating the `HEALTHCHECK` too.
- **Image size** (~427 MB) is reasonable for a slim Python image with a full
  venv; further reduction (e.g. stripping) is possible but not required now.
- **`postgres:16` compose service** is dev-only; the roadmap's "do not
  containerize PostgreSQL for production" guidance is followed.

## 20. Architecture / design decisions

- **Uvicorn over Gunicorn**: one less dependency, simpler image, and container
  orchestration (replicas, liveness probes) already provides the scalability
  that Gunicorn's process manager would add. Documented as swappable later.
- **`uv sync --frozen --no-dev --no-install-project`** in the builder: exact
  lockfile reproducibility, production deps only, and no project packaging —
  source is copied into the runtime image, keeping the venv clean.
- **Entrypoint runs migrations then `exec`s uvicorn**: guarantees a migrated
  schema before traffic and makes `exec` forward signals so Uvicorn handles
  graceful shutdown (verified).
- **`PYTHONPATH=/app` + `python -m uvicorn`**: makes `app` importable for both
  uvicorn and alembic regardless of how they are invoked.
- **Pre-created `/app/media` in the image**: the standard fix for named-volume
  ownership so the local storage backend works out of the box.
- **Compose host DB port 5433**: avoids clashing with an existing local
  PostgreSQL on 5432 (which this project already uses in dev).

## 21. Next phase

**Phase 12 — Next.js Integration** (verify frontend-consumable APIs: CORS, API
base URL, cookies, auth flow, public CMS, admin APIs, lead submission, media
URLs, pagination, error formats; document integration patterns; test from a
Next.js dev environment where possible).

---

## 22. Environment variables (container runtime)

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | *(required)* | Async PostgreSQL DSN (`postgresql+asyncpg://…`) |
| `UVICORN_WORKERS` | `1` | Uvicorn worker count |
| `SKIP_MIGRATIONS` | `0` | `1` skips auto-migrations (separate migration job) |
| `SESSION_COOKIE_NAME` | `beezents_session` | HTTP-only session cookie name |
| `SESSION_MAX_AGE_SECONDS` | `604800` | Session lifetime |
| `COOKIE_SECURE` | `false` | Set `true` in production (HTTPS) |
| `STORAGE_BACKEND` | `local` | `local` now; `s3`/`r2` future |
| `MEDIA_ROOT` | `./media` | Local storage directory |
| `MEDIA_MAX_SIZE_BYTES` | `10485760` | Max upload size |
| `CORS_ALLOWED_ORIGINS` | *(empty)* | Comma-separated allowed CORS origins |
| `TRUSTED_HOSTS` | *(empty)* | Comma-separated allowed Host values |
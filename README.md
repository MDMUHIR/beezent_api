# Beezents Backend

FastAPI backend for the Beezents website, managed with [uv](https://docs.astral.sh/uv/).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) for project and dependency management
- PostgreSQL 16+ (running locally)

## Setup

```sh
uv sync
cp .env.example .env
```

## Run PostgreSQL locally

The simplest way to run PostgreSQL locally is Docker:

```sh
docker run --name beezents-postgres -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres -e POSTGRES_DB=beezents \
  -p 5432:5432 -d postgres:16
```

Alternatively, install PostgreSQL with your OS package manager and create the database:

```sh
sudo apt install postgresql
sudo -u postgres createdb beezents
```

## Database configuration

`DATABASE_URL` is read from `.env` (see `.env.example`). It must use the async
PostgreSQL driver:

```
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/beezents
```

The connection string and other settings are managed by Pydantic Settings in
`app/core/config.py`. Never hardcode credentials.

## Run the backend

```sh
uv run uvicorn app.main:app --reload
```

The API is available at `http://localhost:8000`; interactive docs at `/docs`.

## Alembic migrations

Alembic is the source of truth for the database schema.

Apply all migrations:

```sh
uv run alembic upgrade head
```

Create a new migration from your models:

```sh
uv run alembic revision --autogenerate -m "describe change"
```

Then review the generated file under `migrations/versions/` and apply it:

```sh
uv run alembic upgrade head
```

Other useful commands:

```sh
uv run alembic current      # show the current revision
uv run alembic history      # show migration history
uv run alembic downgrade -1 # revert the last migration
```

The database URL is read from `.env` at migration time; the migration metadata
is wired to `app.models.Base.metadata`.

## Health checks

- `GET /health` — lightweight application health check
- `GET /api/v1/health` — same under the versioned prefix
- `GET /api/v1/health/db` — verifies PostgreSQL reachability with `SELECT 1`

The DB check returns `{"status": "healthy"}` with HTTP 200 when PostgreSQL is
reachable, and HTTP 503 with `{"detail": "Database unavailable"}` otherwise. No
credentials, connection strings, or stack traces are exposed.

## Tests and linting

```sh
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The DB health integration test runs against a real PostgreSQL when the
configured `DATABASE_URL` is reachable and is skipped otherwise. The 503
(unavailable) path is tested deterministically with an unreachable engine.

## Project structure

```
app/
├── __init__.py
├── main.py            # FastAPI app entrypoint
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       └── endpoints/
│           └── health.py   # /health and /health/db
├── core/
│   ├── __init__.py
│   ├── config.py      # Pydantic Settings (incl. DATABASE_URL)
│   ├── database.py    # async engine, session factory, get_session
│   ├── logging.py
│   └── exceptions.py
└── models/
    ├── __init__.py
    └── base.py        # Declarative Base + UUID primary key mixin
migrations/            # Alembic migrations
tests/
```
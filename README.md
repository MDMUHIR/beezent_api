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

## Authentication

Authentication is **server-side and session-based**. On login, an opaque random
token is generated, hashed (SHA-256) and stored in a `user_sessions` row; the raw
token is sent to the browser as an HTTP-only cookie. Passwords are hashed with
**Argon2id**; plaintext passwords are never stored, logged, or returned by the
API.

### Available roles

| Role | Access |
| --- | --- |
| `user` | Normal authenticated access (default on registration) |
| `client` | Reserved for future client accounts |
| `staff` | Staff-level access (`require_staff`) |
| `admin` | Full administrative access (`require_admin`) |

A user can **never** choose or change their own role via the API; `role` is
ignored in registration/profile input. Roles are assigned by administrators.

### Environment variables required

| Variable | Default | Purpose |
| --- | --- | --- |
| `DATABASE_URL` | — | Async PostgreSQL connection string |
| `SESSION_COOKIE_NAME` | `beezents_session` | HTTP-only session cookie name |
| `SESSION_MAX_AGE_SECONDS` | `604800` | Session lifetime (7 days) |
| `COOKIE_SECURE` | `false` | Set to `true` in production (HTTPS only) |

### Authentication endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/auth/register` | Register a new user (role always `user`) |
| `POST` | `/api/v1/auth/login` | Log in with email + password, sets session cookie |
| `POST` | `/api/v1/auth/logout` | Invalidates the session and clears the cookie |
| `GET` | `/api/v1/auth/me` | Current authenticated user |

Development-only role checks (for testing authorization):
`GET /api/v1/dev/staff` and `GET /api/v1/dev/admin`.

### Security notes

- Session cookie is `HttpOnly` and `SameSite=lax`; `Secure` is enabled by setting
  `COOKIE_SECURE=true` (required in production).
- Logout deletes the server-side session row, so the session is truly invalidated.
- Unauthenticated requests return `401`; authenticated requests without the
  required role return `403`.
- Login failures use a generic `Invalid email or password` message and do not
  reveal whether an email exists.
- Argon2id hashing and parameterized SQLAlchemy queries are used throughout.

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

Tests use an **isolated test database** (`beezents_test`, configurable via
`TEST_DATABASE_URL`). The test database is created and migrated automatically on
the first test run; authentication tests run against the real authentication
implementation (Argon2id hashing, real session rows, real cookies).

## Project structure

```
app/
├── __init__.py
├── main.py            # FastAPI app entrypoint
├── api/
│   └── v1/
│       ├── __init__.py
│       ├── router.py
│       ├── deps.py        # get_current_user, require_staff, require_admin
│       └── endpoints/
│           ├── health.py  # /health and /health/db
│           ├── auth.py    # register / login / logout / me
│           └── dev.py     # staff/admin role checks (development only)
├── core/
│   ├── __init__.py
│   ├── config.py      # Pydantic Settings (incl. DATABASE_URL, session config)
│   ├── database.py    # async engine, session factory, get_session
│   ├── security.py    # Argon2id hashing, session tokens, cookies
│   ├── logging.py
│   └── exceptions.py
├── models/
│   ├── __init__.py
│   ├── base.py        # Declarative Base + UUID primary key mixin
│   ├── enums.py       # Role enum
│   ├── user.py        # User model
│   └── session.py     # UserSession model
└── schemas/
    ├── __init__.py
    ├── user.py        # UserResponse
    └── auth.py        # RegisterRequest, LoginRequest
migrations/            # Alembic migrations
tests/
```
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

## Public CMS API

Read-only endpoints for the Next.js marketing website. **Only content with
`published = true` is returned**; unpublished items are never exposed.

### Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/projects` | List published projects |
| `GET` | `/api/v1/projects/{slug}` | Project detail by slug |
| `GET` | `/api/v1/case-studies` | List published case studies |
| `GET` | `/api/v1/case-studies/{slug}` | Case study detail by slug |
| `GET` | `/api/v1/services` | List published services |
| `GET` | `/api/v1/services/{slug}` | Service detail by slug |
| `GET` | `/api/v1/solutions` | List published solutions |
| `GET` | `/api/v1/solutions/{slug}` | Solution detail by slug |

### Pagination

List endpoints accept `page` (default `1`, `>= 1`) and `page_size` (default
`12`, `1..50`) and return a consistent envelope:

```json
{ "items": [...], "total": 12, "page": 1, "page_size": 12, "pages": 1 }
```

### Filtering, search, sorting

| Resource | Params |
| --- | --- |
| projects | `q`, `status` (`active`/`completed`/`archived`), `featured`, `industry`, `project_type`, `sort` (`created_at`/`title`/`client_name`), `order` |
| case-studies | `q`, `featured`, `project_slug`, `sort` (`created_at`/`title`), `order` |
| services / solutions | `q`, `featured`, `sort` (`sort_order`/`name`/`created_at`), `order` |

`q` performs a case-insensitive search over the primary title/name fields.
Invalid `sort` values return `422`.

### Response schemas

Public responses use dedicated schemas (`ProjectPublic`, `ServicePublic`,
`SolutionPublic`, `CaseStudyPublic`) that never expose internal fields such as
`published`, `is_active`, or raw foreign keys. Case studies include an optional
nested `project` reference (`{slug, title}`) when linked to a project.
Admin-oriented schemas (`*Create`, `*Update`, `*Admin`) exist for the future
admin CMS API.

## Admin CMS API

Protected CRUD endpoints for managing website content. **Staff and admin users
only** (`require_staff`); normal users, clients, and unauthenticated requests are
rejected (`403` / `401`). Content visibility is never inferred from the frontend —
every endpoint enforces authorization server-side.

### Endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` / `POST` | `/api/v1/admin/projects` | List / create projects |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/projects/{id}` | Get / update / delete a project |
| `GET` / `POST` | `/api/v1/admin/services` | List / create services |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/services/{id}` | Get / update / delete a service |
| `GET` / `POST` | `/api/v1/admin/solutions` | List / create solutions |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/solutions/{id}` | Get / update / delete a solution |
| `GET` / `POST` | `/api/v1/admin/case-studies` | List / create case studies |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/case-studies/{id}` | Get / update / delete a case study |

Admin list endpoints return the same pagination envelope as the public API
(`page`, `page_size`, `q`, `sort`, `order`) but **include unpublished content**
and return the full admin schema (including `published` and, for case studies,
`project_id`).

### Behavior

- Slugs are normalized to lowercase and validated
  (`^[a-z0-9]+(?:-[a-z0-9]+)*$`); invalid slugs return `422`.
- Duplicate slugs return `409 Conflict` (case-insensitive).
- `PATCH` performs partial updates; explicit `null` for a required field returns
  `422`.
- Malformed UUIDs return `422`; unknown resource IDs return `404`.
- Case study `project_id` is validated against an existing project (`422` when
  missing); `project_id: null` unlinks the case study.
- Deleting a project sets linked case studies' `project_id` to `null`
  (FK `ON DELETE SET NULL`).
- Raw database errors are never exposed — they are mapped to safe API errors.

## Lead Management

The marketing website can capture visitor inquiries as **leads**. Submission is
public (no authentication); management is restricted to staff/admin users.

### Public submission

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/leads` | Submit a lead (no authentication required) |

Request body (all fields except `name`, `email`, `message` are optional):

```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "phone": "+8801XXXXXXXXX",
  "company": "Example Ltd",
  "service": "AI Automation",
  "message": "I want to automate our customer support.",
  "source": "website"
}
```

Response (`201 Created`):

```json
{
  "id": "93ebf2e9-7e73-48df-ba18-ecf173532991",
  "message": "Your inquiry has been received."
}
```

- `name` (1–255), `email` (valid format, normalized to lowercase), `message`
  (10–5000) are required.
- Optional fields: `phone` (≤50), `company` (≤255), `service` (≤255), `source`
  (≤100).
- Every lead is stored with `status = new`. Clients can **never** set `status`,
  `notes`, `id`, `created_at`, or `updated_at` — those fields are server
  controlled and any submitted value is ignored.

### Admin endpoints

**Staff/admin only** (`require_staff`); `user`/`client` → `403`, unauthenticated
→ `401`. There is **no** public lead-list endpoint.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/admin/leads` | Paginated list with `status`, `q`, `sort`, `order` |
| `GET` | `/api/v1/admin/leads/{id}` | Lead detail (includes internal `status`, `notes`) |
| `PATCH` | `/api/v1/admin/leads/{id}` | Partial update |
| `DELETE` | `/api/v1/admin/leads/{id}` | Delete (204) |

Lead statuses: `new`, `contacted`, `qualified`, `converted`, `lost`. Admin list
defaults to newest first (`created_at desc`); search (`q`) covers `name`, `email`,
`company`, and `message`.

Leads contain personal/contact information (PII) and are treated as sensitive
application data. The public response never exposes internal fields, and lead
data is not logged.

### Lead status flow (admin PATCH)

```json
{ "status": "contacted", "notes": "Called the client and scheduled a meeting." }
```

`PATCH` is genuinely partial (`exclude_unset=True`) — only supplied fields
change. `id`, `created_at`, and `updated_at` are never editable.

## Media / File Storage

Website media is stored in a **storage backend**, never as binaries in
PostgreSQL. The database holds only metadata/references. The current
implementation ships a clean `StorageBackend` interface plus a **local
development adapter** (`STORAGE_BACKEND=local`); production object storage
(Cloudflare R2 / S3-compatible) plugs into the same interface without changing
the API or model.

### Endpoints

**Staff/admin only** (`require_staff`).

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/api/v1/admin/files` | Upload media (multipart form) |
| `GET` | `/api/v1/admin/files` | Paginated list; params `page`, `page_size`, `folder`, `mime_type`, `q`, `sort`, `order` |
| `GET` | `/api/v1/admin/files/{id}` | Media metadata detail |
| `PATCH` | `/api/v1/admin/files/{id}` | Update `alt_text` / `folder` metadata only |
| `DELETE` | `/api/v1/admin/files/{id}` | Delete the object + metadata (204) |

Upload form fields: `file` (required), `folder` (optional), `alt_text`
(optional). In development the file is written under `MEDIA_ROOT` and served at
its `public_url` (`/media/{storage_key}`); the mount is only enabled for the
local backend.

### Security behavior

- **Allowed MIME types**: `image/jpeg`, `image/png`, `image/gif`, `image/webp`,
  `image/avif`, `image/svg+xml`, `application/pdf`. Anything else → `422`.
- **Size limit**: `MEDIA_MAX_SIZE_BYTES` (default 10 MiB); larger uploads →
  `413`.
- **Storage naming is UUID-based**: `storage_key = {uuid}{ext}`, where the
  extension comes from the validated MIME type — never from user input. Client
  filenames are sanitized to a bare basename and stored only as `original_name`
  metadata; user input never becomes a filesystem path.
- **Folder names** must match `^[a-z0-9_-]{1,100}$` (prevents path traversal).
- **Uploader tracking**: `uploaded_by` records the staff/admin user (FK, `ON
  DELETE SET NULL`).
- **No PII exposure**: metadata responses are staff/admin-only; no public media
  API exists.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `STORAGE_BACKEND` | `local` | Storage backend name (`local` now; `s3`/`r2` future) |
| `MEDIA_ROOT` | `./media` | Local backend directory |
| `MEDIA_MAX_SIZE_BYTES` | `10485760` | Max upload size (10 MiB) |

The `media` table columns: `original_name`, `storage_key` (unique), `public_url`,
`mime_type`, `size`, `width`, `height`, `alt_text`, `folder`, `uploaded_by`,
`created_at`, `updated_at`. `width`/`height` are reserved for future
image-dimension extraction and are currently `NULL`.

## API security / hardening

Defense-in-depth applied across the API:

- **Security headers** on every response (`X-Content-Type-Options: nosniff`,
  `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`,
  `Permissions-Policy`). Applied via an ASGI middleware and explicitly on 500
  responses.
- **CORS** — configurable via `CORS_ALLOWED_ORIGINS` (comma-separated); disabled
  by default. When enabled, credentials are allowed and preflight requests work.
- **Trusted hosts** — configurable via `TRUSTED_HOSTS` (comma-separated Host
  values); disabled by default (dev). Untrusted Host headers return `400`.
- **Safe errors** — malformed JSON and validation errors return `422` with no
  stack traces; unexpected server exceptions are logged server-side and return a
  safe JSON `500` (`{"detail": "Internal Server Error"}`) with no internals
  leaked.
- **Mass assignment** — request schemas whitelist every accepted field; models
  are constructed/updated from validated fields only. Clients cannot set roles,
  lead status/notes, media keys, or timestamps.
- **Parameterized SQL everywhere** — no raw SQL string interpolation.
- **Secrets** — no credentials in code; `.env` and `/media/` are gitignored;
  `.env.example` contains placeholders only.

### Auth / session hardening

- Session cookie is `HttpOnly`, `SameSite=lax`, and `Secure` when
  `COOKIE_SECURE=true` (production).
- Expired sessions are rejected with `401` and deleted server-side.
- Logout invalidates the server-side session **and** clears the browser cookie.

### Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `CORS_ALLOWED_ORIGINS` | *(empty)* | Comma-separated allowed CORS origins |
| `TRUSTED_HOSTS` | *(empty)* | Comma-separated allowed Host headers |
| `COOKIE_SECURE` | `false` | Set `true` in production (HTTPS) |

### Known hardening gaps (deferred)

- **No rate limiting** — login brute-force, registration abuse, and lead spam
  protection are not implemented (no Redis in this phase). Recommended before
  public launch: per-IP throttling on `/auth/*` and `/leads`.
- **CSP header** not set (a JSON API doesn't render HTML; revisit if the API ever
  serves HTML).
- Uploaded **SVG** is served inline and can execute scripts when opened directly;
  production should serve media from a CDN/object storage with safe headers (or
  remove SVG from the allowlist).

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
│           ├── dev.py     # staff/admin role checks (development only)
│           ├── common.py  # pagination + admin helpers
│           ├── projects.py      # public project list/detail
│           ├── case_studies.py  # public case study list/detail
│           ├── services.py      # public service list/detail
│           ├── solutions.py     # public solution list/detail
│           ├── leads.py         # public lead submission
│           ├── admin_projects.py     # admin CRUD for projects
│           ├── admin_services.py     # admin CRUD for services
│           ├── admin_solutions.py    # admin CRUD for solutions
│           ├── admin_case_studies.py # admin CRUD for case studies
│           ├── admin_leads.py        # admin CRUD for leads
│           └── admin_files.py        # admin CRUD for media files
├── core/
│   ├── __init__.py
│   ├── config.py      # Pydantic Settings (incl. DATABASE_URL, session, media)
│   ├── database.py    # async engine, session factory, get_session
│   ├── storage.py     # StorageBackend interface + local adapter + MIME rules
│   ├── security.py    # Argon2id hashing, session tokens, cookies
│   ├── logging.py
│   └── exceptions.py
├── models/
│   ├── __init__.py
│   ├── base.py        # Declarative Base + UUID primary key + timestamp mixins
│   ├── enums.py       # Role, ProjectStatus, LeadStatus enums
│   ├── user.py        # User model
│   ├── session.py     # UserSession model
│   ├── project.py     # Project model
│   ├── service.py     # Service model
│   ├── solution.py    # Solution model
│   ├── case_study.py  # CaseStudy model
│   ├── lead.py        # Lead model
│   └── media.py       # Media metadata model
└── schemas/
    ├── __init__.py
    ├── user.py        # UserResponse
    ├── auth.py        # RegisterRequest, LoginRequest
    ├── cms.py         # Public/Create/Update/Admin schemas + PaginatedResponse
    ├── leads.py       # LeadCreate, LeadPublicResponse, LeadAdmin, LeadUpdate
    └── files.py       # MediaAdmin, MediaMetadataUpdate
migrations/            # Alembic migrations
tests/
```
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

### Development seed admin (testing only)

When `SEED_DEV_ADMIN=true` (set in `.env` / `docker-compose.yml` for dev), the
app auto-creates an `admin` account on startup if it doesn't already exist. It
is active and verified, so you can immediately log in and access admin
endpoints.

| Variable | Default | Purpose |
| --- | --- | --- |
| `SEED_DEV_ADMIN` | `false` | Enable auto-seeding of the dev admin |
| `SEED_ADMIN_EMAIL` | *(empty)* | Admin email (normalized to lowercase) |
| `SEED_ADMIN_PASSWORD` | *(empty)* | Admin password (hashed with Argon2id) |
| `SEED_ADMIN_FULL_NAME` | `Default Admin` | Admin display name |
| `SEED_ADMIN_ROLE` | `admin` | Role granted to the seeded account |

**Default dev admin credentials (local dev only):**

```
Email:    MBadmin@beezents.com
Password: Bee@MB
```

Log in to obtain the session cookie, then use it for staff/admin endpoints:

```sh
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"MBadmin@beezents.com","password":"Bee@MB"}'
curl -b cookies.txt http://localhost:8000/api/v1/auth/me
```

> **Security:** this feature is development-only. Never set `SEED_DEV_ADMIN=true`
> in production — keep the default `false`.

### Auth request / response

**`POST /api/v1/auth/register`** (201 on success):

```json
{ "email": "user@example.com", "password": "strongpass123", "full_name": "Jane Doe" }
```

- `email` — valid email; normalized to lowercase. Duplicate → `409`.
- `password` — 8–128 chars, must not be blank/whitespace-only.
- `full_name` — 1–255 chars.
- Response is a `UserResponse` (see below). The `role` field is **ignored** if
  supplied — new users are always created with role `user`.

**`POST /api/v1/auth/login`** (200 on success):

```json
{ "email": "user@example.com", "password": "strongpass123" }
```

- Sets the HTTP-only session cookie on success; invalid credentials or an
  inactive account return a generic `401 Invalid email or password`.
- The session cookie is `HttpOnly`, `SameSite=lax`, and `Secure` when
  `COOKIE_SECURE=true`. Pass it to protected endpoints (e.g. via a cookie jar).

**`UserResponse`** (from `/register`, `/login`, `/me`):

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | User id |
| `email` | string | Normalized lowercase |
| `full_name` | string | Display name |
| `role` | enum | `user` / `client` / `staff` / `admin` (never self-assignable) |
| `is_active` | bool | Whether the account is enabled |
| `last_login_at` | datetime? | Last successful login |

**`GET /api/v1/auth/me`** — returns the `UserResponse` of the authenticated
user, or `401` without a valid session.

**`POST /api/v1/auth/logout`** — deletes the server-side session and clears the
cookie; returns `204`.

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

The API is available at `http://localhost:8000`; interactive docs at `/docs`
(Swagger UI) and `/redoc` (ReDoc). All endpoints are versioned under the
`/api/v1` prefix.

## Quick reference

**Base URL:** `http://<host>:8000/api/v1` — interactive docs at
`http://<host>:8000/docs`.

### Endpoint index

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/health` | — | App health check |
| `GET` | `/api/v1/health` | — | Same under the versioned prefix |
| `GET` | `/api/v1/health/db` | — | PostgreSQL reachability check |
| `POST` | `/api/v1/auth/register` | — | Register a user (`user` role) |
| `POST` | `/api/v1/auth/login` | — | Log in, sets session cookie |
| `POST` | `/api/v1/auth/logout` | cookie | Invalidate session + clear cookie |
| `GET` | `/api/v1/auth/me` | cookie | Current authenticated user |
| `GET` | `/api/v1/dev/staff` | staff | Dev-only role check |
| `GET` | `/api/v1/dev/admin` | admin | Dev-only role check |
| `GET` | `/api/v1/projects` | — | List published projects |
| `GET` | `/api/v1/projects/{slug}` | — | Published project detail |
| `GET` | `/api/v1/case-studies` | — | List published case studies |
| `GET` | `/api/v1/case-studies/{slug}` | — | Published case study detail |
| `GET` | `/api/v1/services` | — | List published services |
| `GET` | `/api/v1/services/{slug}` | — | Published service detail |
| `GET` | `/api/v1/solutions` | — | List published solutions |
| `GET` | `/api/v1/solutions/{slug}` | — | Published solution detail |
| `GET` | `/api/v1/solution-categories` | — | List solution categories (public) |
| `GET` | `/api/v1/solution-categories/{slug}` | — | Category with its published solutions |
| `POST` | `/api/v1/leads` | — | Submit a public lead (inquiry) |
| `GET`/`POST` | `/api/v1/admin/projects` | staff | List / create projects |
| `GET`/`PATCH`/`DELETE` | `/api/v1/admin/projects/{id}` | staff | Get / update / delete project |
| `GET`/`POST` | `/api/v1/admin/case-studies` | staff | List / create case studies |
| `GET`/`PATCH`/`DELETE` | `/api/v1/admin/case-studies/{id}` | staff | Get / update / delete case study |
| `GET`/`POST` | `/api/v1/admin/services` | staff | List / create services |
| `GET`/`PATCH`/`DELETE` | `/api/v1/admin/services/{id}` | staff | Get / update / delete service |
| `GET`/`POST` | `/api/v1/admin/solutions` | staff | List / create solutions |
| `GET`/`PATCH`/`DELETE` | `/api/v1/admin/solutions/{id}` | staff | Get / update / delete solution |
| `GET`/`POST` | `/api/v1/admin/solution-categories` | staff | List / create solution categories |
| `GET`/`PATCH`/`DELETE` | `/api/v1/admin/solution-categories/{id}` | staff | Get / update / delete solution category |
| `GET` | `/api/v1/admin/leads` | staff | List leads |
| `GET`/`PATCH`/`DELETE` | `/api/v1/admin/leads/{id}` | staff | Get / update / delete lead |
| `POST` | `/api/v1/admin/files` | staff | Upload media (multipart) |
| `GET` | `/api/v1/admin/files` | staff | List media |
| `GET`/`PATCH`/`DELETE` | `/api/v1/admin/files/{id}` | staff | Get / update / delete media |

> **Auth column:** `—` = public (no authentication), `cookie` = any logged-in
> user, `staff`/`admin` = role-gated (see [Authentication](#authentication)).

### Examples with curl

Authentication is **session-based**: `login` returns the token as an HTTP-only
cookie, which subsequent requests send automatically when you reuse a cookie
jar (`-c` / `-b`).

```sh
# Health checks
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/health/db

# Register a user (201) — duplicate email returns 409
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"strongpass123","full_name":"Jane Doe"}'

# Log in, saving the session cookie to a jar (200)
curl -c cookies.txt -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"strongpass123"}'

# Who am I? (200, or 401 without a valid session)
curl -b cookies.txt http://localhost:8000/api/v1/auth/me

# Public CMS reads — no auth needed
curl "http://localhost:8000/api/v1/projects?featured=true&sort=created_at&order=desc"
curl http://localhost:8000/api/v1/services/my-service

# Submit a public lead (201)
curl -X POST http://localhost:8000/api/v1/leads \
  -H "Content-Type: application/json" \
  -d '{"name":"Jane Doe","email":"jane@example.com","message":"Please reach out about AI automation."}'

# Log out (204)
curl -b cookies.txt -X POST http://localhost:8000/api/v1/auth/logout
```

Admin endpoints (`/admin/*`) require a **staff/admin** session cookie. A
user with only the `user` role receives `403`; a missing/invalid session gets
`401`:

```sh
# Create a project (requires staff role)
curl -b cookies.txt -X POST http://localhost:8000/api/v1/admin/projects \
  -H "Content-Type: application/json" \
  -d '{"title":"AI Chatbot","slug":"ai-chatbot","published":true,"featured":true}'

# List unpublished + published leads (requires staff role)
curl -b cookies.txt "http://localhost:8000/api/v1/admin/leads?status=new&order=desc"

# Upload media (multipart form: file + optional folder/alt_text)
curl -b cookies.txt -X POST http://localhost:8000/api/v1/admin/files \
  -F "file=@./photo.png" -F "folder=hero" -F "alt_text=Hero image"
```

See each section below for query parameters, filters, and request/response
schemas.

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

`solutions` additionally accepts `category` (a category **slug**) to filter
solutions that belong to that category.

`q` performs a case-insensitive search over the primary title/name fields.
Invalid `sort` values return `422`.

### Solution categories

Solutions have an optional **many-to-many** relationship with **solution
categories**. A solution can belong to any number of categories, and a category
can be shared by many solutions. Categories are independent, CRUD-able
resources; deleting a category only removes its links (solutions are never
deleted).

**Public:**

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/solution-categories` | List all categories (for filter UI) |
| `GET` | `/api/v1/solution-categories/{slug}` | Category with its published solutions |

`GET /api/v1/solutions?category={slug}` filters published solutions by category.

The category **detail** endpoint returns a category together with its published
solutions, so the frontend can render a category page directly:

```json
{
  "id": "bf1be62b-56b9-4e1b-b6f3-d0ca07873bcb",
  "name": "GenAI",
  "slug": "genai",
  "description": "Generative AI solutions",
  "sort_order": 1,
  "solutions": [
    {
      "id": "7f1809ca-417b-45a5-b5b5-ca9dca3eb072",
      "name": "GenAI Copilot",
      "slug": "genai-copilot",
      "featured": false,
      "categories": [{ "id": "bf1be62b-...", "name": "GenAI", "slug": "genai" }]
    }
  ]
}
```

Unknown category slugs return `404`.

`SolutionPublic` / `SolutionAdmin` include a nested `categories` array of
`{id, name, slug}` objects, e.g.:

```json
{
  "name": "AI Support Bot",
  "slug": "ai-support-bot",
  "categories": [
    { "id": "90587ded-...", "name": "AI Automation", "slug": "ai-automation" }
  ]
}
```

**Admin CRUD** (staff/admin only, under `/api/v1/admin/solution-categories`):

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` / `POST` | `/api/v1/admin/solution-categories` | List / create categories |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/solution-categories/{id}` | Get / update / delete |

Category fields: `name` (required, unique), `slug` (required, unique,
lowercase-hyphenated), `description` (optional), `sort_order` (int). Duplicate
`slug` or `name` → `409`; invalid `slug` → `422`.

To attach categories to a solution, pass `category_ids` (an array of category
UUIDs) in the admin create/update body:

```json
{
  "name": "AI Support Bot",
  "slug": "ai-support-bot",
  "category_ids": ["90587ded-07e2-494c-8292-8526ffe8cc30"]
}
```

Unknown `category_ids` → `422`; omit the field (or use `null`) to leave
categories unchanged.

### Response schemas

Public responses use dedicated schemas (`ProjectPublic`, `ServicePublic`,
`SolutionPublic`, `CaseStudyPublic`) that never expose internal fields such as
`published`, `is_active`, or raw foreign keys. Case studies include an optional
nested `project` reference (`{slug, title}`) when linked to a project.
Admin-oriented schemas (`*Create`, `*Update`, `*Admin`) exist for the future
admin CMS API.

**`ProjectPublic`** (also applies to `ServicePublic` / `SolutionPublic` where
noted):

| Field | Type | Notes |
| --- | --- | --- |
| `id` | UUID | Resource id |
| `title` / `name` | string | Primary title (services/solutions use `name`) |
| `slug` | string | URL-friendly identifier |
| `short_description` | string? | ≤ 300 chars |
| `description` | string? | Long-form body |
| `client_name` | string? | Project only |
| `industry` | string? | Project only |
| `project_type` | string? | Project only |
| `status` | enum | Project only: `active` / `completed` / `archived` |
| `featured` | bool | Highlighted in listings |
| `cover_image` | string? | Project only (media URL) |
| `live_url` / `github_url` | string? | Project only |
| `technologies` | array | List of tech tags |
| `results` | array | List of outcome highlights |
| `icon` | string? | Service/solution only |
| `sort_order` | int | Service/solution only |
| `created_at` / `updated_at` | datetime (ISO 8601) | Server timestamps |

**`CaseStudyPublic`** adds/changes:

| Field | Type | Notes |
| --- | --- | --- |
| `project` | object? | `{slug, title}` of the linked project |
| `summary` | string? | Short overview |
| `challenge` / `solution` / `implementation` | string? | Narrative sections |
| `metrics` | array | Outcome metrics |
| `seo_title` / `seo_description` | string? | Metadata for search engines |

All list endpoints wrap items in a consistent pagination envelope:

```json
{ "items": [...], "total": 12, "page": 1, "page_size": 12, "pages": 1 }
```

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

## HTTP error reference

Errors return JSON in the shape `{"detail": "..."}` (a single string, or a
list of objects for validation errors).

| Status | Meaning | Common causes |
| --- | --- | --- |
| `400` | Bad request | Untrusted `Host` header (when `TRUSTED_HOSTS` is set) |
| `401` | Unauthenticated | Missing/invalid/expired session, bad credentials |
| `403` | Forbidden | Authenticated but lacks the required role (`staff`/`admin`) |
| `404` | Not found | Unknown resource id, slug, or route |
| `409` | Conflict | Duplicate email (register), duplicate slug (admin create) |
| `413` | Payload too large | Upload larger than `MEDIA_MAX_SIZE_BYTES` |
| `422` | Validation error | Malformed body/query, invalid slug/UUID, unsupported file type, bad `sort` value |
| `500` | Server error | Always `{"detail": "Internal Server Error"}` — no internals leaked |

Validation errors use FastAPI's default shape with a `detail` array, e.g.:

```json
{
  "detail": [
    { "loc": ["body", "password"], "msg": "String should have at least 8 characters", "type": "string_too_short" }
  ]
}
```

See the [API security / hardening](#api-security--hardening) section for how
these are produced.

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

## Docker & deployment

A production-oriented, multi-stage `Dockerfile` builds a minimal
`python:3.12-slim` runtime image with a non-root user, a health check, and an
entrypoint that applies migrations before starting Uvicorn.

### Local development with docker compose

`docker-compose.yml` runs the API together with a throwaway PostgreSQL 16 for
local development (host DB port mapped to `5433` to avoid clashes):

```sh
docker compose up --build
```

The API is then at `http://localhost:8000`. The container entrypoint runs
`alembic upgrade head` automatically on startup; PostgreSQL is **not**
containerized for production — use an external/managed database and configure
`DATABASE_URL` via the environment.

### Building and running the image manually

```sh
docker build -t beezents-backend .
docker run --rm -p 8000:8000 \
  -e DATABASE_URL=postgresql+asyncpg://postgres:postgres@host:5432/beezents \
  beezents-backend
```

### Container runtime environment variables

| Variable | Default | Notes |
| --- | --- | --- |
| `DATABASE_URL` | *(required)* | Async PostgreSQL DSN (`postgresql+asyncpg://…`) |
| `UVICORN_WORKERS` | `1` | Uvicorn worker count |
| `SKIP_MIGRATIONS` | `0` | Set `1` to skip auto-migrations (e.g. when a separate job runs them) |
| `SESSION_COOKIE_NAME` | `beezents_session` | Session cookie name |
| `SESSION_MAX_AGE_SECONDS` | `604800` | Session lifetime |
| `COOKIE_SECURE` | `false` | Set `true` in production (HTTPS) |
| `STORAGE_BACKEND` | `local` | `local` now; `s3`/`r2` future |
| `MEDIA_ROOT` | `./media` | Local storage directory |
| `MEDIA_MAX_SIZE_BYTES` | `10485760` | Max upload size |
| `CORS_ALLOWED_ORIGINS` | *(empty)* | Comma-separated allowed origins |
| `TRUSTED_HOSTS` | *(empty)* | Comma-separated allowed Host values |

No secrets are baked into the image; `.env` is excluded via `.dockerignore`.
The image's `HEALTHCHECK` calls `/health` with stdlib urllib (no `curl`
required). Uvicorn handles graceful shutdown (`SIGTERM`/`SIGINT`), and the
FastAPI lifespan disposes the SQLAlchemy engine on exit.

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
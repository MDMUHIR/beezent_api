# Phase 3 Report — Users + Authentication + Authorization

**Project:** Beezents Backend
**Phase scope:** User model, server-side session authentication, role-based authorization
**Date:** 2026-09-02
**Status:** Complete and verified against a live PostgreSQL instance

---

## 1. Overview

Phase 2 established the async PostgreSQL/SQLAlchemy/Alembic foundation. Phase 3
added the user system on top of it:

- `User` model (UUID PK, unique email, role, timestamps) plus a `user_sessions`
  table for server-side sessions
- Argon2id password hashing (never stored/logged/returned)
- HTTP-only cookie session authentication with genuine logout invalidation
- Role-based authorization (`user`, `client`, `staff`, `admin`)
- Auth endpoints: register, login, logout, me
- Development-only role-check endpoints
- Comprehensive tests against an isolated `beezents_test` database
- Alembic migration for both new tables

No business models, admin CMS, Redis/Celery, or AI features were implemented.

---

## 2. What changed

### New files
| File | Purpose |
| --- | --- |
| `app/models/enums.py` | `Role` enum (`user`, `client`, `staff`, `admin`) |
| `app/models/user.py` | `User` ORM model |
| `app/models/session.py` | `UserSession` ORM model |
| `app/core/security.py` | Argon2id hashing, session token generation/hashing, cookie helpers |
| `app/schemas/user.py` | `UserResponse` |
| `app/schemas/auth.py` | `RegisterRequest`, `LoginRequest` (with email normalization) |
| `app/schemas/__init__.py` | Schema package re-exports |
| `app/api/v1/deps.py` | `get_current_user`, `require_authenticated_user`, `require_staff`, `require_admin` |
| `app/api/v1/endpoints/auth.py` | `register`, `login`, `logout`, `me` |
| `app/api/v1/endpoints/dev.py` | Development-only `/dev/staff` and `/dev/admin` role checks |
| `migrations/versions/6f5c71d4f8e6_create_users_and_user_sessions_tables.py` | Migration |
| `tests/conftest.py` | Isolated test DB setup + per-test cleanup + `client` fixture |
| `tests/test_auth.py` | 14 authentication/authorization tests |

### Modified files
| File | Change |
| --- | --- |
| `app/models/__init__.py` | Imports/re-exports `User`, `UserSession`, `Role` (so Alembic sees them) |
| `app/core/config.py` | Added `SESSION_COOKIE_NAME`, `SESSION_MAX_AGE_SECONDS`, `COOKIE_SECURE` |
| `app/api/v1/router.py` | Includes `auth` and `dev` routers |
| `.env.example` | Added session/cookie variables |
| `pyproject.toml` | Added `argon2-cffi`, `email-validator` |
| `README.md` | Authentication overview, roles, env vars, endpoints, security notes |
| `uv.lock` | Updated dependency graph |

---

## 3. Dependencies added (via `uv add`)

| Package | Version | Why |
| --- | --- | --- |
| `argon2-cffi` | >=25.1.0 | Argon2id password hashing (modern, recommended) |
| `email-validator` | >=2.3.0 | Pydantic `EmailStr` validation |

Transitive: `argon2-cffi-bindings`, `cffi`, `pycparser`, `dnspython`.

No authentication framework was added — the session system is implemented
cleanly with the existing stack (secrets module + SQLAlchemy).

---

## 4. User model

`app/models/user.py` (extends `Base` + `UUIDPrimaryKeyMixin`):

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | PK, `uuid4` default |
| `email` | VARCHAR(255) | `unique=True`, indexed, normalized (lowercased/stripped) |
| `password_hash` | VARCHAR(255) | Argon2id hash only — never plaintext |
| `full_name` | VARCHAR(255) | required |
| `avatar_url` | VARCHAR(500) | nullable |
| `role` | VARCHAR(20) | `Enum` non-native + `CheckConstraint ck_users_role` (values `user/client/staff/admin`) |
| `is_active` | BOOLEAN | default `true` |
| `is_verified` | BOOLEAN | default `false` (verification flow is a future feature) |
| `created_at` | timestamptz | `server_default=now()` |
| `updated_at` | timestamptz | `server_default=now()`, `onupdate=now()` |
| `last_login_at` | timestamptz | nullable |

`app/models/session.py` — `UserSession`:

| Column | Type | Notes |
| --- | --- | --- |
| `id` | UUID | PK |
| `user_id` | UUID | FK → `users.id` `ON DELETE CASCADE`, indexed |
| `token_hash` | VARCHAR(64) | SHA-256 of the raw token, `unique=True`, indexed |
| `created_at` | timestamptz | `server_default=now()` |
| `expires_at` | timestamptz | session expiry |

---

## 5. Authentication strategy

**Server-side, session-based** (no JWT, no localStorage).

1. On **login**: an opaque random token (`secrets.token_urlsafe(32)`) is generated.
   Only its SHA-256 digest is stored in `user_sessions`. `last_login_at` is
   updated.
2. The raw token is returned to the browser in an **HTTP-only cookie**
   (`beezents_session`):
   - `HttpOnly` (never readable by JS)
   - `SameSite=lax`
   - `Secure` when `COOKIE_SECURE=true` (production)
   - `Max-Age`/expires from `SESSION_MAX_AGE_SECONDS` (default 7 days)
3. On each request, `get_current_user` reads the cookie, hashes it, looks up the
   session row, checks expiry, and loads the user (also checking `is_active`).
4. On **logout**, the session row is deleted → genuine server-side invalidation —
   then the cookie is cleared.

Passwords use **Argon2id** (`argon2-cffi` `PasswordHasher`). Plaintext passwords
never appear in responses, logs, or the database.

---

## 6. Authorization / RBAC

| Role | Level |
| --- | --- |
| `user` | Normal authenticated access (default on registration) |
| `client` | Reserved for future client accounts |
| `staff` | `require_staff` access |
| `admin` | `require_admin` access |

Dependencies (`app/api/v1/deps.py`):

- `get_current_user` → resolves session, returns `User`; raises **401**
  (`Not authenticated`) on missing/invalid/expired session or inactive user.
- `require_authenticated_user` → alias for authenticated-only access.
- `require_staff` → **403** (`Insufficient permissions`) unless role is staff or admin.
- `require_admin` → **403** unless role is admin.

Roles are **never settable by the user** — the API ignores `role` in
registration input. Role assignment is an admin/server-side operation.

---

## 7. API endpoints

| Method | Endpoint | Auth | Status codes |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | — | 201, 409 (duplicate email), 422 |
| `POST` | `/api/v1/auth/login` | — | 200 (sets cookie), 401 |
| `POST` | `/api/v1/auth/logout` | — | 204 |
| `GET` | `/api/v1/auth/me` | required | 200, 401 |
| `GET` | `/api/v1/dev/staff` | staff+admin | 200, 401, 403 (development only) |
| `GET` | `/api/v1/dev/admin` | admin | 200, 401, 403 (development only) |

Request/response schemas are separate from ORM models. `UserResponse` never
includes `password_hash`.

### Error handling
- Duplicate email → 409 `An account with this email already exists`
- Invalid credentials → 401 `Invalid email or password` (same for unknown email,
  wrong password, and inactive users — no account enumeration)
- Missing/invalid session → 401 `Not authenticated`
- Insufficient role → 403 `Insufficient permissions`
- Invalid input → 422 (FastAPI validation)

---

## 8. Migration

`migrations/versions/6f5c71d4f8e6_create_users_and_user_sessions_tables.py`

- Creates `users` and `user_sessions`
- Unique index on `users.email`
- `ON DELETE CASCADE` FK from `user_sessions.user_id` → `users.id`
- Unique index on `user_sessions.token_hash`
- `CheckConstraint ck_users_role` on the role column
- Full `downgrade()` drops tables/indexes

`Base.metadata.create_all()` is **not** used anywhere.

---

## 9. Testing

### Test database isolation
`tests/conftest.py`:
- Points the app at `beezents_test` via `TEST_DATABASE_URL` (created
  automatically if missing) before any app import
- Runs `alembic upgrade head` on the test DB at session start
- Truncates `users`/`user_sessions` before every test (clean isolation)
- Provides a per-test `TestClient` fixture (fresh cookie jar each test)

Tests run against the **real** authentication implementation — real Argon2id
hashing, real session rows, real cookies.

### Test list (`tests/test_auth.py`)
| Test | Verifies |
| --- | --- |
| `test_register_success` | 201; role=`user`; password stored as `$argon2id$` hash, not plaintext; no `password_hash` in response |
| `test_register_normalizes_email` | email lowercased/stripped |
| `test_register_duplicate_email_rejected` | 409 + safe message |
| `test_register_invalid_data_rejected` | 422 for bad email / short password / empty name / missing name |
| `test_register_cannot_assign_role` | `role:"admin"` in payload ignored → stored role stays `user` |
| `test_login_success` | 200; `last_login_at` set; cookie present; no hash exposed |
| `test_login_incorrect_credentials_fail` | 401 for wrong password AND unknown email (same detail) |
| `test_unauthenticated_me_rejected` | 401 |
| `test_me_authenticated` | 200 with correct email/role |
| `test_logout_invalidates_session` | session row count → 0; `/me` → 401 after logout |
| `test_normal_user_cannot_access_staff_or_admin` | 403 on both dev endpoints |
| `test_staff_role_checks` | staff → `/dev/staff` 200, `/dev/admin` 403 |
| `test_admin_role_checks` | admin → both 200 |
| `test_inactive_user_cannot_login` | 401 generic message |

Existing Phase 1 + Phase 2 tests (`test_health.py`, `test_database.py`,
`test_alembic.py`, `test_health_db.py`) continue to pass unchanged.

---

## 10. Verification results (actually executed)

| Command | Result |
| --- | --- |
| `uv sync` | Clean, 43 packages |
| `uv lock --check` | Resolved 43 packages, no drift |
| `uv run pytest` | **26 passed** (12 existing + 14 new) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 35 files already formatted |
| `uv run alembic check` | No new upgrade operations detected |
| `uv run alembic upgrade head` | Applied `6f5c71d4f8e6` → `(head)` |
| `uv run alembic current` | `6f5c71d4f8e6 (head)` |

### Live endpoint verification (uvicorn + curl against real PostgreSQL)
- `POST /auth/register` → 201, no `password_hash` in body
- `POST /auth/register` (same email) → 409
- `POST /auth/login` → 200; cookie `beezents_session` with
  `HttpOnly; SameSite=lax; Max-Age=604800; Path=/`
- `POST /auth/login` (wrong password) → 401 `Invalid email or password`
- `GET /auth/me` with cookie → 200; without cookie → 401
- `GET /dev/admin` as normal user → 403
- After DB promotion to admin → `GET /dev/admin` 200, `GET /dev/staff` 200
- `POST /auth/logout` → 204; `user_sessions` count → 0; `/me` → 401
- Live test user cleaned up afterwards

### DB schema verification
`users` and `user_sessions` exist with correct columns, unique indexes
(`ix_users_email`, `ix_user_sessions_token_hash`), FK cascade, and
`ck_users_role` CHECK constraint.

---

## 11. Issues found & fixed during testing

1. **`MissingGreenlet` on login response** — after `commit()`, the server-side
   `onupdate` value of `updated_at` was expired and response serialization tried
   to lazy-load it outside the async context. Fixed by `await session.refresh(user)`
   after commit in `login`.
2. **No role CHECK constraint generated** — SQLAlchemy's non-native `Enum` with
   `values_callable` did not emit a CHECK constraint automatically. Added an
   explicit `CheckConstraint("role IN (...)")` to the model.
3. **Enum stored as names, not values** — default persisted `USER`/`CLIENT`
   (enum names). Switched to `values_callable` so the DB stores lowercase
   `user`/`client`/`staff`/`admin`.
4. **Alembic state after re-generation** — deleting an already-applied revision
   stranded the dev DB at a missing revision; resolved by resetting
   `alembic_version` and re-applying the regenerated migration.

---

## 12. Known limitations / assumptions

- `COOKIE_SECURE` defaults to `false` (dev over HTTP); **must be `true` in
  production** behind HTTPS.
- **Email verification** and **password reset** are not implemented yet
  (documented future features). `is_verified` column exists but is always
  `false` until then.
- No OAuth/social login (future).
- No login rate-limiting/brute-force protection yet (future hardening).
- `client` role exists but has no distinct permissions yet.
- Dev role-check endpoints (`/api/v1/dev/*`) are for testing authorization and
  should be removed or gated before public deployment.
- One pre-existing framework warning remains (starlette `httpx` → `httpx2`
  deprecation notice); harmless, framework-level.

---

## 13. What Phase 4 should implement

1. Business models + CRUD: `Project`, `Service`, `Solution`, `CaseStudy`,
   `Lead`, `File` (upload), using the established async session, UUID base,
   RBAC deps, and Alembic workflow.
2. Email verification + password reset (if the roadmap needs them before
   public-facing registration).
3. Admin panel support (role management, user list) reusing `require_admin`.

Still out of scope until explicitly requested: Redis, Celery, AI agents,
LangChain/LangGraph, RAG, vector database.
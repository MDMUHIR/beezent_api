# Phase 7 Report — Lead Management System

**Project:** Beezents Backend
**Phase scope:** Secure lead/contact management for the marketing website
**Date:** 2026-09-02
**Status:** Complete and verified against a live PostgreSQL instance

---

## 1. Phase objective

Build a secure lead/contact submission system: a public, unauthenticated
`POST /api/v1/leads` endpoint for the marketing website, plus a protected
staff/admin lead-management API (list, detail, patch, delete) with validation,
pagination, filtering, search, sorting, mass-assignment protection, a database
migration, comprehensive tests, and regression coverage for Phases 1–6.

## 2. Scope

- `Lead` model + `LeadStatus` enum (no FK to `Service` — a plain value for this
  phase, per instructions).
- Alembic migration (`create leads table`) with upgrade/downgrade.
- Public `POST /api/v1/leads` (no auth) with a minimal confirmation response.
- Admin `GET/PATCH/DELETE /api/v1/admin/leads[/{id}]` protected by
  `require_staff`.
- Input validation, mass-assignment protection, safe error handling, PII
  review.
- 61 new tests (API + model/database), README docs, and this report.

Out of scope (per instructions): email sending, rate limiting infrastructure
(Redis), CAPTCHA, soft-delete, Lead workflow state machine, Phase 8+ features.

## 3. Acceptance criteria

| Criterion | Status |
| --- | --- |
| `Lead` model implemented | ✅ |
| Alembic migration created | ✅ `f52bdc6b0961` |
| Public `POST /api/v1/leads` works without auth | ✅ |
| Status always initializes to `new` | ✅ (tested + live) |
| Admin list / detail / patch / delete work | ✅ |
| Staff/admin authorization; user/client blocked | ✅ (401/403 matrix) |
| No public lead-list endpoint | ✅ (`GET /api/v1/leads` → 405) |
| Mass-assignment protection | ✅ (status/notes/id/timestamps ignored) |
| PII not exposed publicly | ✅ (public response = `{id, message}` only) |
| Pagination / filtering / search / sorting | ✅ |
| Database migration tested (up/down/up) | ✅ |
| Full suite passes, no regressions | ✅ 172 passed |
| README updated | ✅ |
| Phase report created | ✅ |

## 4. What was implemented

- **`LeadStatus` enum** in `app/models/enums.py` (`new`, `contacted`,
  `qualified`, `converted`, `lost`) following the existing `StrEnum` pattern.
- **`Lead` model** (`app/models/lead.py`): UUID PK, `name`/`email` (NOT NULL),
  optional `phone`/`company`/`service`/`source`, `message` (Text, NOT NULL),
  `status` (enum, default `new`), `notes` (Text, nullable), timezone-aware
  timestamps via the shared `TimestampMixin`.
- **Lead schemas** (`app/schemas/leads.py`):
  - `LeadCreate` — public input; omits `id`, `status`, `notes`, timestamps.
  - `LeadPublicResponse` — `{id, message}` confirmation only.
  - `LeadAdmin` — full internal representation for staff/admin.
  - `LeadUpdate` — staff/admin partial update; `id`/`created_at`/`updated_at`
    never accepted.
- **Public endpoint** (`app/api/v1/endpoints/leads.py`): builds the ORM object
  field-by-field (no `**payload.model_dump()`), so internal fields cannot be
  mass-assigned.
- **Admin endpoint** (`app/api/v1/endpoints/admin_leads.py`): paginated list
  with `status`/`q`/`sort`/`order`, detail, partial `PATCH`
  (`exclude_unset=True`), `DELETE` → 204.
- **Router wiring**, model/schema exports, conftest truncate list update,
  README section.

## 5. Files created

| File | Purpose |
| --- | --- |
| `app/models/lead.py` | `Lead` model |
| `app/schemas/leads.py` | `LeadCreate`, `LeadPublicResponse`, `LeadAdmin`, `LeadUpdate` |
| `app/api/v1/endpoints/leads.py` | Public `POST /api/v1/leads` |
| `app/api/v1/endpoints/admin_leads.py` | Admin lead CRUD |
| `migrations/versions/f52bdc6b0961_create_leads_table.py` | Alembic migration |
| `tests/test_leads_api.py` | 54 API tests |
| `tests/test_leads_models.py` | 7 model/database tests |
| `docs/phases/phase-07-leads.md` | This report |

## 6. Files modified

| File | Change |
| --- | --- |
| `app/models/enums.py` | Added `LeadStatus` |
| `app/models/__init__.py` | Export `Lead`, `LeadStatus` |
| `app/schemas/__init__.py` | Export lead schemas |
| `app/api/v1/router.py` | Include `leads` and `admin_leads` routers |
| `tests/conftest.py` | Added `leads` to the truncate list |
| `tests/test_health_db.py` | Fixed test-infrastructure bug (see §15) |
| `README.md` | Lead Management section + project structure |

No new dependencies were added.

## 7. Database model

```
leads
├── id          uuid        PK
├── name        varchar(255)   NOT NULL
├── email       varchar(255)   NOT NULL
├── phone       varchar(50)    NULL
├── company     varchar(255)   NULL
├── service     varchar(255)   NULL
├── message     text           NOT NULL
├── source      varchar(100)   NULL
├── status      varchar(20)    NOT NULL  default 'new'
├── notes       text           NULL
├── created_at  timestamptz    NOT NULL  server_default now()
└── updated_at  timestamptz    NOT NULL  server_default now()
```

- `status` is a `native_enum=False` `Enum` with a `CheckConstraint`
  (`ck_leads_status`) matching the project's existing pattern.
- `created_at`/`updated_at` use the shared `TimestampMixin`
  (timezone-aware, `server_default=now()`).
- No unique constraints — a person may submit more than once.

## 8. Database migration

`f52bdc6b0961_create_leads_table.py`:

- **upgrade** creates the `leads` table, the status check constraint, and three
  indexes.
- **downgrade** drops the table and its indexes.

### Indexes (and why)

| Index | Rationale |
| --- | --- |
| `ix_leads_status_created_at` on `(status, created_at)` | Admin list is most commonly filtered by `status` and sorted by `created_at`; one composite index serves both. |
| `ix_leads_created_at` on `created_at` | Default admin sort (newest first) without a status filter. |
| `ix_leads_email` on `email` | Support email-based lookups/reporting without scanning. |

No index was added for the `q` search — `ILIKE '%…%'` cannot use a B-tree index
(consistent with Phase 5 search behavior).

Migration was verified against real PostgreSQL: `upgrade head` →
`downgrade -1` (table gone) → `upgrade head` (table restored), on both the test
database (automated test) and the development database (manual). `alembic
check` reports no pending operations; revision is `f52bdc6b0961 (head)`.

## 9. Public API

### `POST /api/v1/leads` (no authentication)

Example request:

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

The server always initializes `status = new`. Clients cannot set `id`, `status`,
`notes`, `created_at`, or `updated_at` — the `LeadCreate` schema does not define
them (extra input is ignored by Pydantic) and the endpoint constructs the ORM
object field-by-field.

There is **no** public `GET /api/v1/leads` (`405 Method Not Allowed`).

## 10. Admin API

Protected by `require_staff` (staff and admin only), consistent with Phase 6.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/admin/leads` | Paginated list; params `page` (1+), `page_size` (1–100, default 20), `status`, `q`, `sort` (`created_at`/`name`/`email`/`status`), `order` (`asc`/`desc`, default `desc`). Default sort `created_at desc`. |
| `GET` | `/api/v1/admin/leads/{id}` | Full internal representation incl. `status` and `notes`. |
| `PATCH` | `/api/v1/admin/leads/{id}` | Partial update of editable fields. |
| `DELETE` | `/api/v1/admin/leads/{id}` | Hard delete → `204 No Content`. |

Admin response uses `LeadAdmin` (`id`, `name`, `email`, `phone`, `company`,
`service`, `message`, `source`, `status`, `notes`, `created_at`, `updated_at`).
It never includes password/session/auth data (leads have no user linkage).

## 11. Authentication / authorization

| User | Public POST | Admin GET | Admin PATCH | Admin DELETE |
| --- | ---: | ---: | ---: | ---: |
| Unauthenticated | allowed | 401 | 401 | 401 |
| user | allowed | 403 | 403 | 403 |
| client | allowed | 403 | 403 | 403 |
| staff | allowed | 200 | 200 | 204 |
| admin | allowed | 200 | 200 | 204 |

- Authorization is enforced server-side via `require_staff`; no frontend-only
  protection.
- Admin object access is staff-scoped by design: any staff/admin may read any
  lead (CMS/lead administration is a staff capability). There is no per-user
  lead ownership, so no IDOR surface exists.

## 12. Validation rules

| Field | Rules |
| --- | --- |
| `name` | required; trimmed; 1–255 |
| `email` | required; valid format (`EmailStr`); trimmed + lowercased |
| `phone` | optional; ≤ 50; no country-specific format assumptions |
| `company` | optional; trimmed; ≤ 255 |
| `service` | optional; trimmed; ≤ 255 |
| `message` | required; trimmed; 10–5000 (whitespace-only → 422) |
| `source` | optional; trimmed; ≤ 100 |
| `status` | admin PATCH only; must be a `LeadStatus` value |
| `notes` | admin PATCH only; trimmed; ≤ 5000 |

- Trimming is applied **before** length validation (a message of 10 spaces is
  rejected as empty, not stored blank).
- All length constraints reject oversized input with `422`.
- `PATCH` uses `exclude_unset=True`, so omitted fields are untouched; explicit
  `null` on a required (NOT NULL) field → `422`.

## 13. Security and privacy checks

- **Mass assignment**: `LeadCreate`/`LeadUpdate` define exactly the acceptable
  fields; the create endpoint assigns field-by-field; update iterates only over
  validated, whitelisted keys. Injected `status`/`notes`/`id`/`created_at`/
  `updated_at` are ignored (proven by tests and live verification).
- **Data exposure**: public response is `{id, message}` only — no `status`,
  `notes`, email, or timestamps. Admin schema is the only place internal fields
  appear.
- **SQL injection**: all queries are SQLAlchemy expressions with bound
  parameters; `q` uses parameterized `ILIKE`.
- **Error leakage**: raw `IntegrityError`/SQLSTATE mapped to safe 422/500 via
  the existing `integrity_error_response`; the public endpoint relies on
  FastAPI's safe generic 500 (debug disabled). No connection strings, stack
  traces, or DB details reach clients.
- **PII**: leads (email/phone/message/notes) are sensitive. No endpoint logs
  lead bodies; tests use only fictional data; no real personal information is
  committed.
- **Abuse**: strict field limits and validation are in place. Rate limiting /
  CAPTCHA / honeypots are **not** implemented (no Redis this phase) — deferred
  to Phase 9 hardening (documented in §23).
- **Secrets**: no credentials added; `.env` remains gitignored.

## 14. Testing

All tests run against the real PostgreSQL test database (`beezents_test`) with
real HTTP requests via `TestClient` and real seeded rows — no mocks.

### `tests/test_leads_api.py` (54 tests)

**Public submission:** minimal submit; full submit (all fields persisted);
status always `new`; response leaks no internal fields.

**Public validation:** missing name/email/message → 422; invalid email → 422;
message too short/blank/whitespace → 422; oversized `name`/`email`/`phone`/
`company`/`service`/`message`/`source` → 422; empty and null optional fields →
201; Unicode names/companies/messages accepted; whitespace/case normalization;
5000-char message accepted.

**Mass assignment:** injecting `status`, `notes`, `id`, `created_at`,
`updated_at` → 201 but stored row keeps `status=new`, `notes=NULL`, and real
server timestamps; no public list endpoint (`GET /api/v1/leads` → 405).

**Authorization matrix:** unauthenticated admin GET/PATCH/DELETE → 401; `user`
and `client` → 403 on list/detail/patch/delete; `staff` and `admin` → allowed.

**Admin CRUD:** list + detail include internal `status`/`notes`; partial PATCH
(only supplied fields change, notes trimmed); status transitions
`new→contacted→qualified→converted` and `qualified→lost`; invalid status → 422;
invalid email → 422; null required field → 422; delete → 204 then 404 with the
row actually gone; unknown UUID → 404; malformed UUID → 422.

**Filtering/search/pagination/sorting:** status filter; invalid status filter →
422; search by name/company/email; no-match → empty; special characters in `q`
(`100%`, `%_[]`) → 200 without errors; pagination envelope + `page=0`/`page_size
=101` → 422; default sort newest-first; `sort=name` asc/desc; invalid `sort` →
422.

### `tests/test_leads_models.py` (7 tests)

Lead creation with defaults; status defaults to `new`; enum values; NOT NULL
required fields enforced (`IntegrityError`); indexes present
(`ix_leads_status_created_at`, `ix_leads_created_at`, `ix_leads_email`); leads
table exists; Alembic downgrade removes the table and upgrade restores it.

Full suite: **172 passed** (111 prior + 61 new), no regressions.

## 15. Bugs discovered

1. **Cross-event-loop database failure in the full suite.** After adding the
   lead tests, `test_public_submit_minimal` intermittently failed with
   `RuntimeError: Task ... got Future ... attached to a different loop` from
   asyncpg. Reproduced, root-caused, fixed, and verified across two full-suite
   runs.
2. **`notes` not trimmed in `LeadUpdate`.** The shared `strip_text` validator
   in the base schema covered name/phone/company/service/message/source but not
   `notes`, which is only defined on the update schema (Pydantic rejects a
   validator on a field absent from the declaring class). Initial interactive
   check showed `notes` kept surrounding whitespace.

## 16. Root causes

1. `tests/test_health_db.py` used a **module-level `TestClient(app)` outside a
   context manager**, so the app lifespan (which calls `dispose_engine()` on the
   shared global engine) never ran for that client. Its requests created asyncpg
   connections bound to that client's event loop, which remained in the global
   connection pool. The next test's `TestClient` runs on a different event loop,
   checked out the orphaned connection, and asyncpg raised "attached to a
   different loop". The failure was order/timing dependent (which connection the
   pool handed out), which is why it surfaced only after the new test file
   changed execution order. This is a latent Phase 1–6 test-infrastructure bug,
   not a Phase 7 code defect.
2. The shared base schema intentionally excludes `notes` (public submissions
   must not accept it), so it needed its own trim validator on `LeadUpdate`.

## 17. Fixes applied

1. **`tests/test_health_db.py`** — replaced the module-level `TestClient` with
   the conftest `client` fixture (a context-managed client that runs the app
   lifespan and disposes the engine between tests). Removed the now-unused
   `TestClient`/`app` imports. This makes the engine pool fresh per test and
   eliminates cross-loop reuse. Verified by running the full suite twice
   consecutively (both 172 passed). A regression guard: the fix itself is the
   removal of the leaking pattern; no behavioral test change was needed.
2. Added a dedicated `strip_notes` `before`-validator on `LeadUpdate` so
   `notes` is trimmed like every other text field.

## 18. Regression tests added

- The Phase 7 suite includes authorization-matrix tests, mass-assignment tests,
  PII-exposure tests, and the model/index/migration tests listed in §14.
- The `test_health_db.py` fix is covered by the existing health-DB tests, which
  now pass reliably in full-suite runs.
- Full Phase 1–6 regression: all 111 prior tests (auth, RBAC, models, health,
  public CMS, admin CMS) still pass unchanged; live checks confirmed `/health`,
  `/api/v1/health/db`, public CMS, and admin CMS endpoints unaffected.

## 19. Verification results (actually executed)

| Command | Result |
| --- | --- |
| `uv sync` | Clean (43 packages) |
| `uv lock --check` | Resolved 43 packages, no drift |
| `uv run pytest` | **172 passed** (111 existing + 61 new); run twice consecutively |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 66 files already formatted |
| `uv run alembic check` | No new upgrade operations detected |
| `uv run alembic current` | `f52bdc6b0961 (head)` |
| Migration up/down/up (test DB) | `test_leads_models.py::test_alembic_downgrade_and_upgrade_restores_leads_table` (passing) |
| Migration up/down/up (dev DB) | Manual: downgrade drops table (`None`), upgrade restores (`leads`) |

## 20. Live API verification

Ran `uvicorn app.main:app` on `:8010` against the real development PostgreSQL
DB (migrated to head) and verified with curl:

- `POST /api/v1/leads` full payload → 201, `{id, message}` response.
- Minimal payload with mixed-case email → 201; email stored lowercase.
- Mass-assignment attempt (`status=converted`, `notes=hacked`) → 201 but the DB
  row shows `status=new`, `notes=NULL`.
- Invalid email → 422; too-short message → 422.
- Unauthenticated `GET /api/v1/admin/leads` → 401.
- Normal `user`: `GET`/`DELETE` admin leads → 403.
- `admin`: list (newest-first) → 200; detail → 200; PATCH
  `{status: contacted, notes: "  Called and scheduled  "}` → only those fields
  changed, notes trimmed, name untouched; invalid status → 422; filter
  `?status=contacted` → 1; search `?q=john` → 1; DELETE → 204 then 404; unknown
  UUID → 404; malformed UUID → 422.
- `staff`: `GET` → 200; `DELETE` → 204 (staff may manage leads).
- `GET /api/v1/leads` → 405 (no public list).
- Regression: `/health`, `/api/v1/health/db`, public `/api/v1/projects`, and
  staff admin CMS endpoints all returned 200; staff `POST /api/v1/admin/projects`
  → 201.

All development test leads and test users were truncated after verification.

## 21. Known limitations

- **No anti-spam infrastructure** — validation and size limits only. Rate
  limiting, CAPTCHA, and honeypots are deferred (Phase 9); Redis is not used.
- **No email sending / notifications** for new leads (deferred by design).
- **Hard delete** — admin `DELETE` removes the row; soft-delete/archive is not
  modeled.
- **No rigid status workflow** — any authorized staff/admin can set any status
  (no state-machine enforcement), per instructions.
- **`service` is a free-text value**, not a FK to the `services` table.
- **Search is `ILIKE` substring** over name/email/company/message — no ranking.
- **Indexes favor the common admin query shape**; the `q` search still does a
  sequential scan (acceptable at current scale).

## 22. Architecture / design decisions

- **No new abstractions or dependencies** — reuses `get_session`,
  `require_staff`, the shared `paginate`/`get_object_or_404`/
  `integrity_error_response` helpers, and existing schema conventions.
- **Dedicated public response schema** (`{id, message}`) — the public surface
  is minimal and deliberately decoupled from the internal `Lead` ORM/schema.
- **Explicit request-to-model construction** in the create endpoint (rather
  than `**payload.model_dump()`) so no future field addition to the input
  schema can silently flow into the ORM.
- **`_LeadFields` base + `LeadUpdate` override** keeps one canonical set of
  text rules while allowing the update schema to make fields optional and add
  `status`/`notes`.
- **`require_staff` (not `require_admin`) for admin lead operations**,
  consistent with the Phase 6 CMS policy.
- **Composite `(status, created_at)` index** over two single-column indexes
  because the dominant admin query filters by status and sorts by creation
  time.

## 23. Deferred work

- Rate limiting / spam protection for the public endpoint (Phase 9).
- Email notifications for new leads.
- Soft-delete / archive and status history.
- Admin UI for leads (future frontend phase).
- Export (CSV) of leads.

## 24. Next phase

**Phase 8 — File / Media Storage** (storage abstraction, media metadata model,
secure upload handling, local dev adapter, migration, tests).
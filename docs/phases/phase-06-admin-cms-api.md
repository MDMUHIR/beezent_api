# Phase 6 Report — Admin CMS CRUD API

**Project:** Beezents Backend
**Phase scope:** Protected CMS administration API
**Date:** 2026-09-02
**Status:** Complete and verified against a live PostgreSQL instance

---

## 1. Phase objective

Build the protected CMS administration API on top of the Phase 4 models
(`Project`, `Service`, `Solution`, `CaseStudy`) and the Phase 5 admin-oriented
schemas (`*Create`, `*Update`, `*Admin`), exposing full CRUD for each resource
behind server-side RBAC (`require_staff`).

This phase adds **no** Lead, File, or AI functionality and introduces **no
schema changes** — the Phase 4/5 tables already model everything the admin API
needs.

## 2. Scope

- `POST / GET / GET{id} / PATCH{id} / DELETE{id}` for projects, services,
  solutions, case studies under `/api/v1/admin/...`.
- Staff/admin authorization (server-enforced), slug-conflict handling (409),
  partial updates, foreign-key validation, malformed-UUID handling, 404s, safe
  deletion, and preservation of the existing public API.
- Slug normalization + format validation on create/update input.
- Comprehensive authorization and CRUD tests against the real test database.

Out of scope (per roadmap): Lead system, File storage, API hardening, caching,
Redis/Celery, AI features.

## 3. Acceptance criteria

| Criterion | Status |
| --- | --- |
| Protected with appropriate RBAC | ✅ `require_staff` on every admin route |
| Staff/admin access only | ✅ staff + admin permitted |
| Normal user cannot access admin APIs | ✅ 403 (user, client) |
| Unauthenticated requests rejected | ✅ 401 |
| Duplicate slugs rejected | ✅ 409 (case-insensitive) |
| Partial updates (PATCH) | ✅ `exclude_unset=True` |
| Foreign keys validated | ✅ case-study `project_id` checked (422) |
| Malformed UUIDs handled | ✅ 422 |
| Nonexistent resources → 404 | ✅ |
| Deletion handled safely | ✅ FK `ON DELETE SET NULL`; 204 |
| Public API behavior preserved | ✅ all 55 prior tests still pass |

## 4. What was implemented

- **Slug validation** (`app/schemas/cms.py`): a shared `SlugStr` annotated type
  (`Annotated[str, AfterValidator]`) applied to the slug fields of the
  `*Base`/`*Update` schemas. Slugs are trimmed, lowercased, and validated
  against `^[a-z0-9]+(?:-[a-z0-9]+)*$`; invalid slugs → 422. Applies to
  `ProjectCreate/Update`, `ServiceCreate/Update`, `CaseStudyCreate/Update`, and
  the `Solution*` schemas that inherit them.
- **Shared admin helpers** (`app/api/v1/endpoints/common.py`):
  - `get_object_or_404()` — PK fetch or 404.
  - `slug_exists()` — case-insensitive slug conflict check with optional
    `exclude_id` (a record may keep its own slug on update).
  - `ensure_record_exists()` — referenced-record validation (422).
  - `integrity_error_response()` — maps `IntegrityError` SQLSTATE codes
    (23505 unique → 409, 23503 FK → 422, 23502 not-null → 422, else → 500) to
    safe messages; never leaks raw database errors.
- **Four admin endpoint modules** (`admin_projects.py`, `admin_services.py`,
  `admin_solutions.py`, `admin_case_studies.py`), each with `GET` (paginated
  list incl. unpublished + `q`/`sort`/`order`), `POST`, `GET/{id}`,
  `PATCH/{id}`, `DELETE/{id}`.
- **Router wiring** in `app/api/v1/router.py`.
- **README** documentation for the admin CMS API.
- **Tests** (`tests/test_admin_cms_api.py`, 56 tests).

## 5. Files created

| File | Purpose |
| --- | --- |
| `app/api/v1/endpoints/admin_projects.py` | Admin CRUD for projects |
| `app/api/v1/endpoints/admin_services.py` | Admin CRUD for services |
| `app/api/v1/endpoints/admin_solutions.py` | Admin CRUD for solutions |
| `app/api/v1/endpoints/admin_case_studies.py` | Admin CRUD for case studies (FK checks) |
| `tests/test_admin_cms_api.py` | 56 admin API tests |
| `docs/phases/phase-06-admin-cms-api.md` | This report |

## 6. Files modified

| File | Change |
| --- | --- |
| `app/schemas/cms.py` | Added `SlugStr` annotated type; applied to slug fields in `*Base`/`*Update` schemas |
| `app/api/v1/endpoints/common.py` | Added `get_object_or_404`, `slug_exists`, `ensure_record_exists`, `integrity_error_response` |
| `app/api/v1/router.py` | Includes the four admin routers |
| `README.md` | Admin CMS API section + updated project structure |

No new dependencies were added.

## 7. Database changes

**None.** The Phase 4/5 tables and constraints already support the admin CRUD.
`alembic check` reports no pending operations and the revision stays at
`eef51e823865 (head)`.

Existing DB-level protections relied upon:

- unique index on `slug` for all four tables (case-sensitive; the app-level
  `slug_exists` check is case-insensitive),
- `case_studies.project_id` FK with `ON DELETE SET NULL`,
- NOT NULL constraints on required columns.

## 8. API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/admin/projects` | Paginated list (all projects, incl. unpublished) |
| `POST` | `/api/v1/admin/projects` | Create project (201) |
| `GET` | `/api/v1/admin/projects/{id}` | Get project by UUID |
| `PATCH` | `/api/v1/admin/projects/{id}` | Partial update |
| `DELETE` | `/api/v1/admin/projects/{id}` | Delete (204) |
| `GET` / `POST` | `/api/v1/admin/services` | List / create services |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/services/{id}` | Get / update / delete service |
| `GET` / `POST` | `/api/v1/admin/solutions` | List / create solutions |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/solutions/{id}` | Get / update / delete solution |
| `GET` / `POST` | `/api/v1/admin/case-studies` | List / create case studies |
| `GET` / `PATCH` / `DELETE` | `/api/v1/admin/case-studies/{id}` | Get / update / delete case study |

List endpoints reuse the public pagination envelope (`items/total/page/
page_size/pages`; default `page_size=20`, max `100`) and support `q` (search
over title/name + slug), `sort`, `order`. They return the **admin** schemas
(`*Admin`), which include internal fields (`published`; for case studies also
`project_id`).

## 9. Authentication / authorization

- Every admin route depends on `require_staff` (`app/api/v1/deps.py`), which
  permits only `STAFF` and `ADMIN`. Enforcement is entirely server-side; no
  client-supplied role or hidden UI state is trusted.
- Unauthenticated → `401 Not authenticated`.
- `user` and `client` roles → `403 Insufficient permissions`.
- `staff` and `admin` → full CRUD access (chosen CMS policy: content editing is
  a staff capability).
- Registration never assigns an elevated role, and role fields in request
  bodies are ignored by the auth schemas (existing Phase 3 behavior, unchanged).

## 10. Validation rules

- **Slug**: trimmed → lowercased → regex `^[a-z0-9]+(?:-[a-z0-9]+)*$`;
  violation → 422. Duplicate slug (case-insensitive) → `409 Conflict`.
- **Required fields**: `title`/`slug` (projects, case studies), `name`/`slug`
  (services, solutions). Missing → 422.
- **Explicit `null` for a required field** on PATCH → 422 (caught by the NOT
  NULL constraint and mapped via `integrity_error_response`).
- **Malformed UUID** in the path → 422 (FastAPI `UUID` type).
- **Unknown resource** → 404.
- **Foreign key** (`case_study.project_id`): must reference an existing project,
  otherwise 422; `null` is allowed (unlinks the case study).
- **Pagination**: `page >= 1`, `page_size` in `1..100`; invalid → 422.
- Pydantic length constraints from the Phase 5 schemas remain in force.

## 11. Testing

All tests run against the real PostgreSQL test database (`beezents_test`) with
real HTTP requests via `TestClient` and real seeded rows — no mocks.

### `tests/test_admin_cms_api.py` (56 tests)

**Authorization matrix:**

| Test | Verifies |
| --- | --- |
| `test_unauthenticated_requests_401` | 401 for GET/POST on all four resources |
| `test_unauthenticated_item_endpoints_401` | 401 for item GET/PATCH/DELETE |
| `test_non_staff_roles_forbidden` | `user` and `client` → 403 for all resources |
| `test_staff_and_admin_allowed` | `staff` and `admin` → 200/201 for all resources |
| `test_user_forbidden_on_item_endpoints` | `user` → 403 on item GET/PATCH/DELETE |

**Projects:**

| Test | Verifies |
| --- | --- |
| `test_create_project_full_payload` | 201 + all fields, JSONB arrays, no auth fields |
| `test_create_project_defaults` | default status/featured/published/arrays |
| `test_admin_list_includes_unpublished` | admin sees all; public still hides unpublished |
| `test_admin_list_pagination_and_search` | envelope + `q` search |
| `test_get_project_by_id` | 200 detail |
| `test_project_patch_partial_update` | only supplied fields change |
| `test_delete_project` | 204 then 404 |
| `test_duplicate_slug_create_409` | duplicate create → 409 |
| `test_duplicate_slug_case_insensitive_409` | `alpha` vs `ALPHA` → 409 |
| `test_patch_to_existing_slug_409` | update to another record's slug → 409 |
| `test_patch_own_slug_allowed` | keeping own slug on update → 200 |
| `test_slug_normalized_on_create` | `AI-Commerce` → `ai-commerce` |
| `test_invalid_slug_format_422` | spaces / underscores / empty → 422 |
| `test_create_missing_required_fields_422` | missing title/slug → 422 |
| `test_malformed_uuid_422` | non-UUID path → 422 |
| `test_nonexistent_id_404` | unknown UUID → 404 for GET/PATCH/DELETE |
| `test_update_null_required_field_422` | explicit `{"title": null}` → 422 |

**Services / Solutions / Case studies** (parametrized):

| Test | Verifies |
| --- | --- |
| `test_admin_crud_roundtrip` | create → 409 dup → list → get → patch → delete → 404 |
| `test_admin_duplicate_slug_409` | duplicate create → 409 per resource |

**Case-study foreign keys:**

| Test | Verifies |
| --- | --- |
| `test_case_study_create_with_project` | valid `project_id` → 201 |
| `test_case_study_create_invalid_project_422` | unknown project → 422 |
| `test_case_study_patch_link_invalid_project_422` | link to unknown project → 422 |
| `test_case_study_patch_unlink_project` | `project_id: null` unlinks (200) |
| `test_delete_project_sets_case_study_project_null` | deleting project nulls FK |

**Response shape + regression:**

| Test | Verifies |
| --- | --- |
| `test_admin_response_includes_internal_fields` | admin sees `published`, `project_id` |
| `test_public_api_unchanged_after_admin_operations` | public endpoints unaffected |

Full suite: **111 passed** (55 prior + 56 new), no regressions.

## 12. Bugs discovered

1. **Starlette 422 deprecation** — `status.HTTP_422_UNPROCESSABLE_ENTITY` is
   deprecated in the installed Starlette in favor of
   `HTTP_422_UNPROCESSABLE_CONTENT`, producing deprecation warnings in the new
   error paths. The existing codebase never raised 422 explicitly, so this was
   not caught earlier.
2. **Unused imports** in the new test module (`Service`, `Solution`) — flagged
   by Ruff after the CRUD round-trip tests were written to use HTTP requests
   only.

## 13. Root causes

1. The project pins very recent FastAPI/Starlette where the 422 constant was
   renamed.
2. The parametrized CRUD tests exercise resources over HTTP, so direct model
   imports became dead code.

## 14. Fixes applied

1. Replaced all explicit uses with `status.HTTP_422_UNPROCESSABLE_CONTENT`
   (verified the constant exists in the installed Starlette before using it).
2. Removed the unused imports; `ruff check .` and `ruff format --check .` pass.

### Design issue caught during schema work

The initial instinct was class-method `field_validator`s on each slug-bearing
schema (6+ classes), duplicating logic. The `Annotated[str, AfterValidator]`
(`SlugStr`) approach was validated interactively against the installed Pydantic
2.13 before adoption, confirming: normalization (`AI-Commerce` →
`ai-commerce`) works; omitted and explicit-`null` slugs in `*Update` schemas
are tolerated (AfterValidator receives `None` and returns it), so partial
updates remain safe; invalid formats produce clean `422`s.

## 15. Regression tests added

- `test_public_api_unchanged_after_admin_operations` — proves Phase 5 public
  behavior is intact after admin writes.
- `test_admin_list_includes_unpublished` — also asserts the public list still
  excludes unpublished rows after admin-visible data is present.
- The full Phase 1–5 suite (55 tests) passes unchanged, including auth, RBAC,
  models, health, and public CMS tests.

## 16. Security checks

- **Authorization** — `require_staff` on every admin route; 401/403 verified
  live and in tests; no endpoint relies on frontend-only restrictions.
- **No privilege escalation** — request-body role fields are ignored (Phase 3
  behavior); admin endpoints never alter roles.
- **No sensitive data exposure** — admin responses use `*Admin` schemas
  (content fields + `published`/`project_id` only); no password hashes, session
  tokens, or internal auth fields. Public schemas unchanged.
- **SQL injection** — all queries built with SQLAlchemy expressions /
  parameter binding; `q` uses `ILIKE` with bound parameters.
- **Error leakage** — raw `IntegrityError`/SQLSTATE details are mapped to safe
  messages; unknown DB errors become a generic 500.
- **IDOR** — object access is by authenticated-staff UUID lookup; there is no
  per-user object ownership model for CMS content (by design), so no IDOR
  surface.
- **Secrets** — `.env` is gitignored; no API keys/credentials are committed
  (verified with a repo scan; only `.env.example` with placeholder values is
  tracked).

## 17. Verification results (actually executed)

| Command | Result |
| --- | --- |
| `uv sync` | Clean (43 packages) |
| `uv lock --check` | Resolved 43 packages, no drift |
| `uv run pytest` | **111 passed** (55 existing + 56 new) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 58 files already formatted |
| `uv run alembic check` | No new upgrade operations detected (no schema change this phase) |
| `uv run alembic current` | `eef51e823865 (head)` |
| Migration downgrade/upgrade | Covered by `test_alembic_downgrade_and_upgrade_restores_schema` (passing) |

### Live endpoint verification (uvicorn on :8010 + curl against real PostgreSQL)

Ran the dev DB at head, seeded via the API as an **admin** user, then verified
with curl:

- Unauthenticated `GET`/`POST` `/api/v1/admin/projects` → 401.
- Create project → 201; slug normalized `AI-Commerce-Platform` →
  `ai-commerce-platform`; status/published/technologies/results persisted.
- Admin list → `total: 1`; get-by-id → 200; PATCH (title + live_url) → only
  supplied fields changed, slug untouched.
- Duplicate slug POST (`AI-COMMERCE-PLATFORM`) → 409.
- Malformed UUID → 422; unknown UUID → 404; invalid slug `Bad Slug!` → 422;
  explicit `{"title": null}` PATCH → 422.
- Case study with valid `project_id` → 201; with unknown project → 422.
- Services/solutions: create 201, duplicate slug → 409, delete → 204.
- Public API preservation: `/api/v1/projects` returned only the published
  project, no `published` field leaked; unpublished slug → 404.
- Deleting the project set the linked case study's `project_id` → null.
- Patch-to-taken-slug → 409; patch-own-slug → 200.
- A normal `user` (live) got 403 on admin GET and POST.

Dev tables were truncated after verification.

## 18. Known limitations

- `slug_exists` uses `func.lower()` on the slug column, so it does not use the
  unique index (it is a conflict pre-check, not a hot path). The DB unique
  constraint remains the final arbiter; concurrency races fall through to the
  `IntegrityError` mapping.
- Admin list filtering is limited to `q`, `sort`, `order`. Status/featured/
  published filter params can be added when the admin frontend needs them.
- Deletion is a hard delete; soft-delete/archive is not modeled.
- `q` search is simple `ILIKE` substring matching (consistent with Phase 5).

## 19. Architecture / design decisions

- **Per-resource admin modules** (mirroring the public endpoints) instead of a
  generic CRUD factory — explicit, readable, and aligned with the project rule
  against generic CRUD frameworks; the genuinely shared logic lives in
  `common.py` helpers.
- **`require_staff` for all admin CRUD** — content editing is a staff
  capability; admin retains it (a superset). No operation was made admin-only
  in this phase.
- **Case-insensitive slug conflicts at the app layer** + the DB unique index as
  the race-condition backstop, with `IntegrityError` mapped by SQLSTATE.
- **`exclude_unset=True` for PATCH** distinguishes "not provided" from explicit
  `null`, enabling true partial updates while letting explicit `null` on
  required fields surface as 422.
- **No new dependencies, no schema change** — the Phase 5 schemas and Phase 4
  tables were sufficient.

## 20. Deferred work

- Admin list filter params (status/featured/published).
- Soft delete / archive / restore.
- Audit logging of admin writes.
- Bulk operations / import.
- Any frontend for the admin API.

## 21. Next phase

**Phase 7 — Lead Management System** (secure lead/contact submission, `Lead`
model, public `POST /api/v1/leads`, admin lead management, migration, tests).
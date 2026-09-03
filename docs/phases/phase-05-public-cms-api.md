# Phase 5 Report — Public Website/CMS API

**Project:** Beezents Backend
**Phase scope:** Read-only public API for the Next.js marketing website
**Date:** 2026-09-02
**Status:** Complete and verified against a live PostgreSQL instance

---

## 1. Phase objective

Phase 4 delivered the core CMS database models (`Project`, `Service`, `Solution`,
`CaseStudy`). Phase 5 builds the **public read-only API** the Next.js marketing
website consumes.

Only content with `published = true` is ever returned. Endpoints support
pagination, filtering, sorting, slug lookup, and text search, using dedicated
public response schemas that never expose internal fields.

This phase adds **no write endpoints** — admin CRUD is deferred to a later
phase.

---

## 2. Acceptance criteria

| Criterion | Status |
| --- | --- |
| Next.js can retrieve website content | ✅ Verified (8 endpoints) |
| Unpublished content is hidden | ✅ Verified |
| Pagination works | ✅ Verified |
| Slug lookup works | ✅ Verified |
| Invalid resources return 404 | ✅ Verified |
| Response schemas do not expose internal fields | ✅ Verified |

---

## 3. What was implemented

- CMS API schemas: public + admin-oriented (create/update/admin) + pagination envelope
- Shared pagination helper
- Four public endpoint modules (list + detail for each resource)
- Router wiring for `/api/v1/projects`, `/case-studies`, `/services`, `/solutions`
- 15 new API tests + a shared DB test helper
- README documentation for the public API

No new dependencies were added; the existing stack (FastAPI, SQLAlchemy 2.x,
asyncpg, PostgreSQL) was sufficient.

---

## 4. Files created

| File | Purpose |
| --- | --- |
| `app/schemas/cms.py` | Public/Create/Update/Admin schemas, `ProjectRefPublic`, `PaginatedResponse` |
| `app/api/v1/endpoints/common.py` | Shared `paginate()` helper (count + offset/limit) |
| `app/api/v1/endpoints/projects.py` | `GET /projects`, `GET /projects/{slug}` |
| `app/api/v1/endpoints/case_studies.py` | `GET /case-studies`, `GET /case-studies/{slug}` |
| `app/api/v1/endpoints/services.py` | `GET /services`, `GET /services/{slug}` |
| `app/api/v1/endpoints/solutions.py` | `GET /solutions`, `GET /solutions/{slug}` |
| `tests/_db.py` | Shared `run_db()` async test-database helper |
| `tests/test_cms_api.py` | 15 public CMS API tests |

## 5. Files modified

| File | Change |
| --- | --- |
| `app/api/v1/router.py` | Includes the four public routers |
| `app/schemas/__init__.py` | Exports the new CMS schemas + `PaginatedResponse` |
| `tests/test_cms_models.py` | Refactored to use the shared `tests/_db.py` helper |
| `README.md` | Public CMS API section + updated project structure |

---

## 6. API endpoints

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

All queries are scoped to `published = true`. Unknown or unpublished slugs
return `404 Not found`.

### Pagination

List endpoints accept `page` (default `1`, `>= 1`) and `page_size` (default
`12`, `1..50`) and return a consistent envelope:

```json
{ "items": [...], "total": 12, "page": 1, "page_size": 12, "pages": 1 }
```

Invalid values (`page = 0`, `page_size = 100`) return `422`.

### Filtering, search, sorting

| Resource | Params |
| --- | --- |
| projects | `q`, `status` (`active`/`completed`/`archived`), `featured`, `industry`, `project_type`, `sort` (`created_at`/`title`/`client_name`), `order` (`asc`/`desc`) |
| case-studies | `q`, `featured`, `project_slug`, `sort` (`created_at`/`title`), `order` |
| services / solutions | `q`, `featured`, `sort` (`sort_order`/`name`/`created_at`), `order` |

- `q` — case-insensitive `ILIKE` search over title/name and description fields.
- Invalid `sort` values return `422` (enforced with `Literal` query types).
- Default sorts: projects/case-studies `created_at desc`; services/solutions
  `sort_order asc`.

---

## 7. Response schemas

`app/schemas/cms.py` separates public from internal representations:

- **Public** (`ProjectPublic`, `ServicePublic`, `SolutionPublic`,
  `CaseStudyPublic`) — serialized with `from_attributes=True`, **never exposing**
  `published`, `is_active`, or raw FK columns. Case studies expose an optional
  nested `project: {slug, title}` (eager-loaded) instead of `project_id`.
- **Admin-oriented** (`*Create`, `*Update`, `*Admin`) — defined now for the
  future admin CMS phase (including `published`, `sort_order`, `project_id`).
- **Pagination** — `PaginatedResponse[T]` (PEP 695 generic on `BaseModel`).

ORM models are never returned directly from endpoints.

---

## 8. Implementation notes

- A single `paginate(session, stmt, page, page_size, order_by)` helper performs
  a `count()` over a subquery plus `offset`/`limit`, returning
  `(items, total, pages)` — reused by all four resources to avoid duplication.
- Case study lists/details eager-load the `project` relationship with
  `selectinload` to avoid lazy-load in async context.
- SQL is built with SQLAlchemy `select` expressions (parameterized, no string
  concatenation) — no SQL injection surface.

---

## 9. Testing

### New tests (`tests/test_cms_api.py`, 15 tests)

| Test | Verifies |
| --- | --- |
| `test_list_projects_only_published` | unpublished rows hidden, correct total |
| `test_unpublished_project_detail_404` | unpublished slug → 404 |
| `test_project_pagination` | page/page_size/total/pages across pages |
| `test_invalid_pagination_params_422` | `page=0`, `page_size=100` → 422 |
| `test_project_slug_lookup` | detail fields + JSONB arrays |
| `test_project_invalid_slug_404` | unknown slug → 404 |
| `test_project_search` | `q` filters by title |
| `test_project_filters` | `featured`, `status`, `industry` filters |
| `test_project_sorting` | `sort`/`order` asc/desc + default created_at |
| `test_services_list_and_detail` | published-only list, detail, 404s, sort_order |
| `test_solutions_list_and_detail` | published-only list, detail, 404s |
| `test_case_studies_list_and_detail_with_project` | nested project ref, standalone None, 404s |
| `test_case_studies_filter_by_project_slug` | `project_slug` filter |
| `test_response_schemas_do_not_expose_internal_fields` | no `published`/`is_active`/`project_id` |
| `test_empty_results` | empty envelope `{items: [], total: 0, pages: 0}` |

Tests use the real PostgreSQL test database (`beezents_test`) with real HTTP
requests via `TestClient` and real seeded rows — no fakes.

### Seed helper bug caught during testing

The initial `_seed` helper added rows without `commit()`, so nothing persisted.
Fixed by committing inside the seed coroutine. A second bug: `project.id` is
`None` before flush, so case studies referenced `project_id=None`; fixed by
setting the `project=` relationship instead of `project_id=`. Both were caught
by actual test failures, not guessed.

---

## 10. Verification results (actually executed)

| Command | Result |
| --- | --- |
| `uv sync` | Clean (43 packages) |
| `uv lock --check` | Resolved 43 packages, no drift |
| `uv run pytest` | **55 passed** (40 existing + 15 new) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 51 files already formatted |
| `uv run alembic check` | No new upgrade operations detected (no schema change this phase) |
| `uv run alembic current` | `eef51e823865 (head)` |

### Live endpoint verification (uvicorn + curl against real PostgreSQL)

Seeded the dev DB with published and unpublished rows for all four resources,
then verified:

- `GET /api/v1/projects` → only the published project returned (`total: 1`); the
  unpublished project was absent.
- `GET /api/v1/projects/ai-commerce` → 200, full public body.
- `GET /api/v1/projects/hidden-project` and `/nope` → 404.
- Pagination: `?page_size=1&page=2` → correct `total/page/pages` envelope.
- `GET /api/v1/services` → 2 published (hidden RAG Systems excluded);
  `?featured=true` → 1; slug detail 200; unpublished slug → 404.
- `GET /api/v1/solutions` → 2 published.
- `GET /api/v1/case-studies` → linked case study shows
  `project: {slug: "ai-commerce", title: ...}`; standalone shows `project: null`.
- `GET /api/v1/projects?q=commerce` → search matched.
- `GET /api/v1/projects?sort=bad` → 422.
- `published` key absent from every response body.

Dev CMS tables were truncated after verification.

---

## 11. Issues found and fixes

1. **Seed helper never committed** — `_seed` inserted into the session without
   `commit()`, so seeded rows were rolled back and endpoint assertions failed
   (`total == 0`). Fixed by committing in the seed coroutine.
2. **`project.id` was `None` pre-flush** — case studies created with
   `project_id=project.id` referenced `None`. Fixed by using the ORM
   relationship (`project=project`) so the FK resolves at flush.
3. **Pydantic generics** — the `BaseModel, Generic[T]` pattern triggered ruff
   `UP046`; the PEP 695 `BaseModel[T]` form failed on the installed pydantic
   (2.13.5). The working form is `class PaginatedResponse[T](BaseModel)` (PEP 695
   type parameters), which satisfies ruff and pydantic.

---

## 12. Known limitations

- Search is simple `ILIKE` substring matching (no full-text ranking) — adequate
  for the marketing site; can be upgraded to PostgreSQL FTS/trigram later.
- No caching (e.g., CDN headers / Redis) — public content is served live; add
  `Cache-Control` headers or an edge cache in a later phase.
- Public responses include `id` and timestamps (stable, non-sensitive); the
  internal flags excluded are `published`, `is_active`, and raw FK columns.
- No write/admin endpoints yet (by design).

---

## 13. Decisions / assumptions

- **Published-only scope** applied in every query (`published.is_(True)`),
  including slug detail lookups (unpublished → 404, no information leak).
- **Pagination envelope** (`items/total/page/page_size/pages`) chosen over bare
  arrays so Next.js can render page controls and SEO-friendly pagination.
- **`sort_order` default sort for services/solutions** — reflects editorial
  ordering intent; projects/case-studies default to newest first.
- **Separate public/admin schemas now** — avoids ORM leakage and gives the admin
  phase ready-made create/update/admin models.
- **Nested `project` ref on case studies** (rather than `project_id`) — exposes a
  usable link target without leaking internal keys.
- **No new dependencies** — pagination/filtering/search implemented cleanly with
  the existing stack.

---

## 14. What the next phase should implement

1. **Admin CMS CRUD API** protected by `require_admin`/`require_staff`, using the
   already-defined `*Create`/`*Update`/`*Admin` schemas: create/update/delete for
   projects, services, solutions, case studies — with slug-uniqueness handling
   (409), partial updates, and validation.
2. **Content/seed management** — how initial services/solutions content is
   introduced.
3. Later phases: `Lead` capture, `File` uploads, caching, then the AI features.

Still out of scope until explicitly requested: Lead system, File uploads, Redis,
Celery, AI agents, LangChain/LangGraph, RAG, vector database, email verification,
password reset, OAuth/social login.
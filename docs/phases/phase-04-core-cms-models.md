# Phase 4 Report — Core CMS Database Models

**Project:** Beezents Backend
**Phase scope:** Database models only for Project, Service, Solution, CaseStudy (no API)
**Date:** 2026-09-02
**Status:** Complete and verified against a live PostgreSQL instance

---

## 1. Phase objective

Phase 3 delivered the User + authentication + authorization foundation. Phase 4
adds the **core CMS database models** for the Beezents website — `Project`,
`Service`, `Solution`, and `CaseStudy` — with their relationships, constraints,
indexes, and an Alembic migration.

This phase is deliberately **models-only**:
- No public CMS API endpoints
- No admin API endpoints
- No seed/content data
- No `Lead` or `File` models yet

The goal is a correct, verified database structure that later phases will build
APIs on top of.

---

## 2. What was implemented

- `ProjectStatus` enum (active / completed / archived) in `app/models/enums.py`
- `TimestampMixin` (created_at / updated_at) in `app/models/base.py`
- `Project`, `Service`, `Solution`, `CaseStudy` ORM models
- All models registered in `app/models/__init__.py` so Alembic autogenerate sees them
- Alembic migration `eef51e823865` creating all four tables
- 14 new model/database tests
- Test isolation extended to truncate the new tables

---

## 3. Files created

| File | Purpose |
| --- | --- |
| `app/models/project.py` | `Project` model |
| `app/models/service.py` | `Service` model |
| `app/models/solution.py` | `Solution` model |
| `app/models/case_study.py` | `CaseStudy` model |
| `migrations/versions/eef51e823865_create_projects_services_solutions_case_.py` | Migration |
| `tests/test_cms_models.py` | 14 CMS model/database tests |

## 4. Files modified

| File | Change |
| --- | --- |
| `app/models/base.py` | Added `TimestampMixin` |
| `app/models/enums.py` | Added `ProjectStatus` enum |
| `app/models/__init__.py` | Import/export new models + `ProjectStatus`, `TimestampMixin` |
| `tests/conftest.py` | Truncates `projects`, `services`, `solutions`, `case_studies` per test |

No dependencies were added — all features use the existing stack (SQLAlchemy 2.x,
PostgreSQL, Alembic).

---

## 5. Database models

All models extend `Base` + `UUIDPrimaryKeyMixin` (UUID PK, `uuid4`) and
`TimestampMixin` (timezone-aware `created_at`/`updated_at`).

### Project — `projects`

| Field | Type | Constraints |
| --- | --- | --- |
| `id` | UUID | PK, default `uuid4` |
| `title` | VARCHAR(255) | NOT NULL |
| `slug` | VARCHAR(255) | NOT NULL, **UNIQUE**, indexed |
| `short_description` | VARCHAR(300) | nullable |
| `description` | TEXT | nullable |
| `client_name` | VARCHAR(255) | nullable |
| `industry` | VARCHAR(100) | nullable |
| `project_type` | VARCHAR(100) | nullable |
| `status` | VARCHAR(20) | NOT NULL, default `active`, CHECK `ck_projects_status` |
| `featured` | BOOLEAN | NOT NULL, default `false` |
| `published` | BOOLEAN | NOT NULL, default `false`, indexed |
| `cover_image` | VARCHAR(500) | nullable |
| `live_url` | VARCHAR(500) | nullable |
| `github_url` | VARCHAR(500) | nullable |
| `technologies` | JSONB | NOT NULL, default `[]` |
| `results` | JSONB | NOT NULL, default `[]` |
| `created_at` / `updated_at` | timestamptz | NOT NULL, `now()` / `now()` onupdate |

### Service — `services`

| Field | Type | Constraints |
| --- | --- | --- |
| `id` | UUID | PK |
| `name` | VARCHAR(255) | NOT NULL |
| `slug` | VARCHAR(255) | NOT NULL, **UNIQUE**, indexed |
| `short_description` | VARCHAR(300) | nullable |
| `description` | TEXT | nullable |
| `icon` | VARCHAR(100) | nullable |
| `featured` | BOOLEAN | NOT NULL, default `false` |
| `published` | BOOLEAN | NOT NULL, default `false`, indexed |
| `sort_order` | INTEGER | NOT NULL, default `0` |
| `created_at` / `updated_at` | timestamptz | NOT NULL |

### Solution — `solutions`

Identical shape to `Service` (name, slug, short_description, description, icon,
featured, published, sort_order, timestamps).

### CaseStudy — `case_studies`

| Field | Type | Constraints |
| --- | --- | --- |
| `id` | UUID | PK |
| `project_id` | UUID | nullable, FK → `projects.id` **ON DELETE SET NULL**, indexed |
| `title` | VARCHAR(255) | NOT NULL |
| `slug` | VARCHAR(255) | NOT NULL, **UNIQUE**, indexed |
| `summary` | TEXT | nullable |
| `challenge` | TEXT | nullable |
| `solution` | TEXT | nullable |
| `implementation` | TEXT | nullable |
| `results` | JSONB | NOT NULL, default `[]` |
| `technologies` | JSONB | NOT NULL, default `[]` |
| `metrics` | JSONB | NOT NULL, default `[]` |
| `featured` | BOOLEAN | NOT NULL, default `false` |
| `published` | BOOLEAN | NOT NULL, default `false`, indexed |
| `seo_title` | VARCHAR(255) | nullable |
| `seo_description` | VARCHAR(255) | nullable |
| `created_at` / `updated_at` | timestamptz | NOT NULL |

---

## 6. Relationships

- **CaseStudy → Project** (many-to-one / one-to-many): a `Project` may have zero
  or more `CaseStudy` rows; each `CaseStudy` references at most one `Project`.
- `CaseStudy.project_id` is **nullable** with `ON DELETE SET NULL`.

### Decision: nullable `project_id`

`project_id` was intentionally made **nullable**:

- A case study can exist independently of an internal project page (e.g., client
  work not linked to a public project).
- Content authors may write case studies before the matching project exists.
- Deleting a project does not destroy its case studies — the reference is set to
  NULL, preserving the content.

This keeps the relationship simple while avoiding over-constraining CMS authoring.

---

## 7. Constraints and indexes

| Model | Unique | Indexes | Checks |
| --- | --- | --- | --- |
| `projects` | `slug` (unique index) | `published`, `slug` | `ck_projects_status` on `status` |
| `services` | `slug` (unique index) | `published`, `slug` | — |
| `solutions` | `slug` (unique index) | `published`, `slug` | — |
| `case_studies` | `slug` (unique index) | `published`, `slug`, `project_id` (FK) | — |

Foreign key: `case_studies.project_id` → `projects.id` with `ON DELETE SET NULL`.

JSONB structured fields (`technologies`, `results`, `metrics`) default to `[]`
at both the Python and DB (`server_default`) level.

---

## 8. Alembic migration

**Revision:** `eef51e823865` — `create projects services solutions case_studies tables`
**Parent:** `6f5c71d4f8e6` (users + user_sessions)

- Creates `projects`, `services`, `solutions`, `case_studies`
- Unique indexes on all slugs, published indexes, FK + FK index
- `ck_projects_status` CHECK constraint
- Full `downgrade()` that drops tables/indexes in dependency-safe order

Migration chain: `0857ebb26254` (empty) → `6f5c71d4f8e6` (users) → `eef51e823865` (CMS, head).

`Base.metadata.create_all()` is not used anywhere; Alembic remains the schema
source of truth.

---

## 9. Migration verification

```sh
uv run alembic upgrade head   # applied eef51e823865 (head)
uv run alembic current        # eef51e823865 (head)
uv run alembic check          # No new upgrade operations detected
uv run alembic history        # full chain: 0857... -> 6f5c71d4f8e6 -> eef51e823865 (head)
```

The downgrade path was verified programmatically in the test suite
(`test_alembic_downgrade_and_upgrade_restores_schema`): `downgrade -1` drops the
CMS tables, `upgrade head` restores them, and the tables are confirmed present
afterwards.

---

## 10. PostgreSQL schema verification (direct)

Verified directly against the live `beezents` database:

- **Tables exist:** `projects`, `services`, `solutions`, `case_studies`
- **Column types/nullability/defaults:** confirmed for every column (VARCHAR/TEXT
  lengths, JSONB `'[]'::jsonb` defaults, `now()` timestamps)
- **Constraints:**
  - `projects_pkey`, `services_pkey`, `solutions_pkey`, `case_studies_pkey`
  - `ck_projects_status` → `CHECK status IN ('active','completed','archived')`
  - `case_studies_project_id_fkey` → `FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE SET NULL`
- **Indexes:**
  - `ix_projects_slug` (UNIQUE), `ix_projects_published`
  - `ix_services_slug` (UNIQUE), `ix_services_published`
  - `ix_solutions_slug` (UNIQUE), `ix_solutions_published`
  - `ix_case_studies_slug` (UNIQUE), `ix_case_studies_published`, `ix_case_studies_project_id`
- **No seed data:** all four tables contain 0 rows.

---

## 11. Tests performed

```sh
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv lock --check
uv run alembic check
uv run alembic upgrade head
uv run alembic current
```

### New tests (`tests/test_cms_models.py`, 14 tests)

| Test | Verifies |
| --- | --- |
| `test_project_can_be_created` | Project insert, defaults, JSONB fields |
| `test_service_can_be_created` | Service insert, defaults |
| `test_solution_can_be_created` | Solution insert, defaults |
| `test_case_study_can_be_created` | CaseStudy insert, standalone (project_id NULL) |
| `test_case_study_references_project` | FK relationship both directions |
| `test_project_delete_sets_case_study_project_null` | `ON DELETE SET NULL` behavior |
| `test_duplicate_project_slug_rejected` | unique slug → IntegrityError |
| `test_duplicate_service_slug_rejected` | unique slug → IntegrityError |
| `test_duplicate_solution_slug_rejected` | unique slug → IntegrityError |
| `test_duplicate_case_study_slug_rejected` | unique slug → IntegrityError |
| `test_required_fields_enforced` | NOT NULL violation → IntegrityError |
| `test_defaults_work` | featured/published false, status active, JSONB `[]`, sort_order 0 |
| `test_cms_tables_exist` | all 4 tables present in schema |
| `test_alembic_downgrade_and_upgrade_restores_schema` | downgrade → upgrade round trip |

Tests use the real PostgreSQL test database (`beezents_test`) with real
SQLAlchemy sessions — no fakes or mocks.

---

## 12. Ruff / format verification

```sh
uv run ruff check .          # All checks passed
uv run ruff format --check . # 42 files already formatted
```

9 files were auto-formatted once (`ruff format`); the final `check`/`format`
both pass clean.

---

## 13. Actual verification results

| Command | Result |
| --- | --- |
| `uv sync` | Clean (43 packages) |
| `uv lock --check` | Resolved 43 packages, no drift |
| `uv run pytest` | **40 passed** (26 Phase 1–3 + 14 Phase 4) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 42 files already formatted |
| `uv run alembic check` | No new upgrade operations detected |
| `uv run alembic upgrade head` | Applied, at head |
| `uv run alembic current` | `eef51e823865 (head)` |
| PostgreSQL schema inspection | All 4 tables, constraints, indexes verified directly |

No dependency was added in this phase.

---

## 14. Issues found and fixes

1. **Unused imports** in the initial `Service` draft (`JSONB`, `text`) — removed
   before the first test run; `ruff check` stayed clean.
2. **Autogenerated migration formatting** — long generated lines triggered
   `E501`; the existing `migrations/versions/*` per-file ignore already covered
   `E501` (extended in Phase 3), so autogenerated files remain lint-clean.
3. **Relationship collection lazy-load** — asserting `project.case_studies`
   needed an explicit `refresh(project, ["case_studies"])` to avoid an async
   `MissingGreenlet`; the test uses the async-safe loading path.

No model/schema design changes were required after the migration was generated —
`alembic check` reported no drift on the first run.

---

## 15. Known limitations

- `project_type` and `industry` are free-form strings (no constrained enums yet);
  if a taxonomy is needed later, they can be converted to enums/tables.
- `client_name` duplicates user data; if clients become real entities in a later
  phase, this should become a FK to a `clients` table.
- No `Lead` or `File` models (explicitly deferred).
- No seed content — services/solutions examples (AI Agents, AI Automation, RAG;
  E-commerce, SaaS, Business Automation) are documented concepts only and have
  not been inserted.
- Public vs internal schema separation is deferred to the API phase; models are
  designed so dedicated public/admin/create/update Pydantic schemas can be added
  without exposing ORM models.

---

## 16. Decisions / assumptions

- **`project_id` nullable** on CaseStudy (documented in section 6) with
  `ON DELETE SET NULL`.
- **JSONB** for `technologies`, `results`, `metrics` — clean, flexible storage of
  structured content without premature relational tables.
- **Status as a constrained string enum** (non-native PG enum + CHECK), matching
  the Phase 3 `Role` convention; default `active`.
- **Single `published` index** per table; enough for the upcoming public listing
  queries without over-indexing.
- **`sort_order` defaults to 0** for services/solutions — manual ordering control
  for the admin UI.
- **No generic repository/base-class abstraction** — each model is explicit;
  only the shared `TimestampMixin` was introduced to avoid duplicated timestamp
  definitions across four models.

---

## 17. What the next phase should implement

1. **Public CMS API** — read-only endpoints for published projects, services,
   solutions, and case studies (respecting `published`/`featured`), using
   dedicated public Pydantic schemas (never the ORM models directly).
2. **Admin CMS API** — CRUD endpoints protected by `require_admin` (and
   `require_staff` where appropriate), with separate create/update/admin schemas
   and proper validation (slug uniqueness, enum values).
3. **Seed/content management** — how initial services/solutions content is
   introduced (admin UI, script, or seed migration).
4. Later phases: `Lead` model + lead capture, `File` upload/storage, then the AI
   features.

Still out of scope until explicitly requested: Lead system, File uploads,
Redis, Celery, AI agents, LangChain/LangGraph, RAG, vector database, email
verification, password reset, OAuth/social login.
# Phase 8 — File & Media Storage

**Project:** Beezents AI Agency backend
**Phase scope:** Production-hardening the existing file/media system and making
`Media` a first-class domain entity with UUID relationships to CMS content.
**Date:** 2026-09-07
**Status:** Complete and verified against real PostgreSQL, Alembic, and live HTTP

---

## Phase Objective

Improve the existing (already functional) media system so that:

- `Media` is a first-class domain entity referenced by CMS content through
  **UUID foreign keys**, not arbitrary URL strings.
- `storage_key` is the canonical storage identity and public URLs are derived
  at runtime from the storage backend (no stored URL rows that go stale when
  storage/CDN configuration changes).
- Uploads are validated beyond the client-declared `Content-Type` (file
  signature / content decoding, extension derivation, size, folder safety).
- SVG is removed from the allowlist (Option A — recommended) to eliminate
  active-content risk.
- Media deletion is safe: referenced media returns `409`, media is never
  cascade-deleted, and storage/DB ordering is deliberately chosen and
  documented.
- Everything remains behind the existing RBAC (`require_staff`), with a clean
  Router → Service → (Models + StorageBackend) architecture.

## Scope

In scope:

- Media model improvements (`media_type`, `duration_seconds`, computed URL).
- Storage backend hardening (atomic writes, path safety, no stored URLs).
- Content-signature validation module (Pillow for images, magic bytes for
  video/PDF).
- Media service layer (upload + safe deletion + reference checks).
- CMS Media UUID relationships (Project, Solution, CaseStudy, TeamMember).
- Admin + public API response changes (structured nested media).
- Alembic migration with legacy-URL backfill (upgrade + downgrade tested).
- Comprehensive tests; README + phase report.

Out of scope (per roadmap): actual R2/S3 implementation, video duration
extraction (FFmpeg), thumbnails/transcoding, public media browse API, rate
limiting, CDN/caching.

## Acceptance Criteria

| Criterion | Status |
| --- | --- |
| Media UUID FKs on CMS entities (`ON DELETE SET NULL`) | ✅ |
| `media_type` = image/video/document; `duration_seconds` field | ✅ |
| `public_url` derived from `storage_key` (no stored URL) | ✅ |
| Storage abstraction preserved; local backend atomic writes | ✅ |
| Content signature validation (MIME spoofing blocked) | ✅ |
| SVG removed from allowlist (documented decision) | ✅ |
| Delete referenced media → `409`; unlinked delete works | ✅ |
| Upload: storage-first then DB, best-effort cleanup on DB failure | ✅ |
| RBAC unchanged (`401`/`403`/staff/admin) | ✅ |
| Public CMS returns nested media objects; internal fields never exposed | ✅ |
| Migration upgrade + downgrade + `alembic check` clean | ✅ |
| Full suite passes | ✅ 320 passed |
| Ruff check + format + `uv lock --check` pass | ✅ |
| Live HTTP verification performed | ✅ |

## Existing Architecture Reviewed

Reviewed before any change:

- `app/core/storage.py` — `StorageBackend` ABC + `LocalStorageBackend` +
  `StorageResult` + `build_storage_key` + `ALLOWED_MIME_TYPES` (incl. SVG).
- `app/models/media.py` — metadata model with a stored `public_url` column.
- `app/models/{project,solution,case_study,team_member}.py` — URL string fields
  (`cover_image`, `image_url`, `avatar_url`, `demo_video_url`,
  `demo_video_type`).
- `app/schemas/files.py`, `app/schemas/cms.py`, `app/schemas/team.py`.
- `app/api/v1/endpoints/admin_files.py` (upload/list/get/patch/delete inline),
  admin CMS endpoints, public CMS endpoints, `common.py`, `deps.py`.
- Migrations chain (head `a1c3e5f7b9d2` at start), `migrations/env.py`.
- `tests/` (conftest uses real PostgreSQL `beezents_test`; run_db helper; media
  test helpers seeded rows with `public_url`).
- `README.md` media section, `.env.example`, previous phase reports.

## Architecture Before

```text
API (routes) ──▶ Media model (public_url stored) ──▶ LocalStorageBackend
CMS entities reference media by URL strings:
  Project.cover_image / demo_video_url + demo_video_type
  Solution.image_url / demo_video_url + demo_video_type
  CaseStudy.image_url
  TeamMember.avatar_url
public_url was a stored column; SVG was allowed; only Content-Type was checked.
```

## Architecture After

```text
Router ─▶ Media Service ─▶ PostgreSQL (Media metadata) + StorageBackend
                                   ├── LocalStorageBackend  (dev)
                                   └── future R2/S3 backend (same interface)

Media.id ─▶ Media.storage_key ─▶ StorageBackend.public_url() ─▶ delivery URL

CMS entities reference media by UUID FKs:
  Project.cover_media_id, demo_video_media_id
  Solution.image_media_id, demo_video_media_id
  CaseStudy.image_media_id
  TeamMember.avatar_media_id
Legacy URL columns remain and are auto-mirrored (backward compatibility).
```

## What Was Implemented

- **`app/core/media_validation.py`** — application-level validation boundary:
  `inspect_upload(mime_type, content)` verifies the byte stream against the
  declared MIME (Pillow decode + format match for images, `ftyp`/EBML/Ogg magic
  for videos, `%PDF-` for PDFs) and extracts image `width`/`height`.
  `media_type_from_mime()` maps MIME → `image`/`video`/`document`.
- **`app/services/media.py`** — `resolve_upload()` (size/folder/MIME/signature
  validation), `store_media()` (storage-first then DB, best-effort cleanup on
  DB failure), `media_references()` and `delete_media()` (409 on references,
  storage-first delete ordering).
- **`app/services/cms_media.py`** — helpers to wire Media into CMS entities and
  mirror legacy URL columns (canonical-media-wins).
- **`app/core/storage.py`** — removed `StorageResult`; `save()` returns `None`;
  local writes are atomic (temp file + `os.replace` + `fsync`); `public_url()`
  derives the delivery URL; `image/svg+xml` removed from `ALLOWED_MIME_TYPES`.
- **`app/models/media.py`** — added `media_type` (check constraint + index) and
  `duration_seconds` (check constraint); removed stored `public_url` column;
  `public_url`/`url` are now runtime properties derived from the storage key.
- **`app/models/{project,solution,case_study,team_member}.py`** — added Media
  UUID FK columns (`ON DELETE SET NULL`, indexed) and `lazy="selectin"`
  relationships; `demo_video` property aliases on Project/Solution.
- **`app/api/v1/endpoints/admin_files.py`** — thin route handlers using the
  media service; added `media_type` list filter; safe deletion.
- **Admin CMS endpoints** — resolve media FK ids (422 if missing), unlink with
  `null`, mirror legacy columns.
- **`app/main.py`** — fixed a pre-existing bug where `DEBUG=true` made
  Starlette's `ServerErrorMiddleware` return raw tracebacks and bypass the
  installed safe-500 handler (see Bugs Discovered).

## Media Model Changes

Before: `original_name`, `storage_key` (unique), `public_url` (stored),
`mime_type`, `size`, `width`, `height`, `alt_text`, `folder`, `uploaded_by`,
timestamps.

After:

```text
id, original_name, storage_key (unique), mime_type, media_type
(image|video|document, NOT NULL + check), size, width, height,
duration_seconds (nullable + check >= 0), alt_text, folder,
uploaded_by (FK users SET NULL), created_at, updated_at
public_url / url = derived property (not stored)
```

Design decision (documented): `public_url` is **generated dynamically** from
`storage_key` + storage configuration rather than stored, so changing
storage/CDN configuration never requires rewriting every database row.

## CMS Relationship Changes

| Entity | Image FK | Demo video FK |
| --- | --- | --- |
| Project | `cover_media_id` | `demo_video_media_id` |
| Solution | `image_media_id` | `demo_video_media_id` |
| CaseStudy | `image_media_id` | — |
| TeamMember | `avatar_media_id` | — |

All FKs are `ON DELETE SET NULL`. Deleting a Media never deletes a CMS row and
never silently breaks a reference (deletion of referenced media → `409`).

## Storage Architecture

- `StorageBackend` ABC: `save()`, `delete()`, `public_url()` (Protocol-style
  interface already present; preserved and simplified).
- `LocalStorageBackend`: path-traversal-safe `_resolve`, atomic writes
  (temp file + rename), idempotent delete.
- `get_storage()` factory keyed on `STORAGE_BACKEND`.
- Future R2/S3 plugs into the same interface; no S3/R2 SDKs added this phase.

Upload ordering: validate → read → signature check + metadata → storage key →
**storage write** → Media row insert → commit. On DB commit failure the storage
object is deleted best-effort. On storage failure no Media row is created.
PostgreSQL and storage are *not* transactionally atomic — documented
best-effort design.

Delete ordering: reference check (409) → **storage delete** → DB row delete. If
the row delete fails after the object is removed, the metadata row remains
pointing at a missing object — safer than an orphaned object with no row.
Documented tradeoff.

## Upload Validation

- Allowed MIME allowlist (extension derived from it; never from the filename).
- Maximum size (image/file 10 MiB, video 100 MiB) → `413`.
- Folder pattern `^[a-z0-9_-]{1,100}$` → `422`.
- **Content signature validation** (new): Pillow decode + format match for
  images (also extracts `width`/`height`); `ftyp`/EBML/Ogg magic bytes for
  videos; `%PDF-` for PDFs. Mismatch → `422`.
- Filename sanitization to a bare basename (`original_name` only); UUID-based
  storage keys; safe folder names.
- Stored extension is derived from the validated MIME type, never from the
  original filename.

## Security Changes

- SVG removed from the allowlist (see SVG Decision).
- MIME spoofing blocked (content signature check).
- Mass assignment: `PATCH /admin/files` accepts only `alt_text`/`folder`;
  `storage_key`, `size`, `mime_type`, timestamps, uploader are never editable
  via the API.
- Safe deletion ordering + `409` on referenced media.
- Internal storage fields never exposed publicly (nested media objects only;
  `storage_key`, media FKs, uploader, timestamps omitted).
- Fixed pre-existing safe-500 bug (traceback leak in `DEBUG=true` mode).
- All media operations remain under the existing RBAC (`require_staff`);
  no second authorization system added.

## SVG Decision

**Option A (recommended) adopted: SVG is not accepted for uploads.** The
marketing site does not genuinely require user-uploaded SVG, and SVG can carry
active scripts/event handlers. `image/svg+xml` was removed from
`ALLOWED_MIME_TYPES`; uploads are rejected with `422`. The README documents
that if SVG is ever required it must be served through a separate asset
origin/CDN with sanitization and safe headers — never as trusted inline HTML.

## External Video Handling

Uploaded videos and external (YouTube) videos are two distinct concepts and are
never conflated:

- **Uploaded video**: `demo_video_media_id` → Media row (`media_type=video`).
  The API mirrors `demo_video_url` and forces `demo_video_type = "upload"`.
- **External video**: `demo_video_media_id` unset; `demo_video_url` holds the
  YouTube URL with `demo_video_type = "youtube"`. External URLs are never
  stored as Media records.

## Database Migration

`eb1af61cf576 — add media relationships and media metadata` (revises
`a1c3e5f7b9d2`):

**upgrade()**
1. Add `media.media_type` (nullable → backfill from `mime_type` → NOT NULL) and
   `media.duration_seconds` (+ check constraints + index).
2. Add CMS FK columns (nullable) to projects/solutions/case_studies/team_members.
3. Backfill FKs from existing string URLs that exactly match a media row's
   `public_url` (deterministic single-id-per-URL via `DISTINCT ON`). Unmatched
   URLs (e.g. external `https://...` covers, YouTube links) are left untouched —
   no Media records are fabricated.
4. Add named FK constraints (`ON DELETE SET NULL`) + indexes.
5. Drop `media.public_url` (becomes derived).

**downgrade()** reverses all of the above and restores `public_url`
(`'/media/' || storage_key` backfill, then NOT NULL).

Migration limitation documented: backfill only converts URLs that exactly match
a stored media `public_url`. Existing arbitrary/external URLs are preserved in
the legacy columns but are not promoted to Media references.

## API Changes

- `POST /api/v1/admin/files` — validates content signature; returns
  `MediaAdmin` incl. `media_type`, `duration_seconds`, `url` (derived).
- `GET /api/v1/admin/files` — added `media_type` filter.
- `DELETE /api/v1/admin/files/{id}` — returns `409 Conflict` with reference
  details when the media is referenced by CMS content; `204` otherwise.
- Admin CMS create/update — accept `cover_media_id`, `demo_video_media_id`,
  `image_media_id`, `avatar_media_id` (UUID links media and mirrors legacy URL;
  explicit `null` unlinks). Invalid media id → `422`.
- Admin CMS responses — include media FK ids and nested media objects.
- Public CMS responses — embed nested `cover_media` / `image_media` /
  `avatar_media` / `demo_video` objects (`id`, `url`, `mime_type`, `media_type`,
  `size`, `width`, `height`, `duration_seconds`, `alt_text`). Legacy string
  fields retained (deprecated). Media FK ids and internal fields never exposed
  publicly.
- `/files` endpoint prefix retained (no breaking rename).

## Files Created

- `app/core/media_validation.py`
- `app/services/media.py`
- `app/services/cms_media.py`
- `migrations/versions/eb1af61cf576_add_media_relationships_and_media_.py`
- `tests/media_fixtures.py`
- `tests/test_media_cms_relationships.py`

## Files Modified

- `app/core/storage.py`
- `app/models/media.py`
- `app/models/project.py`, `solution.py`, `case_study.py`, `team_member.py`
- `app/models/project_category.py`, `service_category.py`,
  `solution_category.py` (declared the link-table `category_id` indexes that the
  DB already had, so `alembic check` reflects reality)
- `app/schemas/files.py`, `cms.py`, `team.py`, `__init__.py`
- `app/api/v1/endpoints/admin_files.py`, `admin_projects.py`,
  `admin_solutions.py`, `admin_case_studies.py`, `admin_team_members.py`
- `app/main.py`
- `tests/test_files_api.py`, `test_files_models.py`, `test_core_units.py`,
  `test_alembic.py`
- `pyproject.toml` (+ `pillow` dependency), `uv.lock`
- `README.md`
- `migrations/versions/a1c3e5f7b9d2_*.py`, `b2e7c9d4a6f8_*.py`,
  `c3f7a1b2e9d4_*.py`, `d7a9c5e8f2b1_*.py`, `e4b8d6a1c3f5_*.py` (reformatted by
  `ruff format`; see Known Limitations)

## Tests Added

- `tests/test_media_cms_relationships.py` (15 tests) — Project/Solution/
  CaseStudy/TeamMember media FK create/read/update/unlink/delete, invalid media
  id → 422, public nested media (no internal leaks), delete-referenced → 409,
  delete-after-unlink → 204, legacy string compatibility, canonical-media-wins.
- `tests/test_files_api.py` — updated for the new validation (valid image/video/
  PDF bytes), new MIME-spoofing tests, SVG rejection, `media_type` filter,
  `media_type`/`duration_seconds` in responses, width/height extraction.
- `tests/test_files_models.py` — updated Media constructions (no `public_url`),
  new `media_type`/`duration` check-constraint tests, derived-URL test, updated
  downgrade test for the new head migration.
- `tests/test_core_units.py` — updated storage tests (no `StorageResult`),
  new `inspect_upload` signature/metadata unit tests.
- `tests/test_alembic.py` — new migration legacy-URL backfill test.

## Verification Performed

```text
uv run pytest
Result: 320 passed (baseline was 275 passed + 1 pre-existing failure)

uv run ruff check .
Result: All checks passed!

uv run ruff format --check .
Result: 106 files already formatted

uv lock --check
Result: Resolved 45 packages
```

## PostgreSQL Verification

Tests run against a real PostgreSQL instance (`beezents_test`) via asyncpg;
the test database is created, migrated to head, and truncated per test in
`tests/conftest.py`. Model/database behavior (FKs, check constraints, unique
constraints, `ON DELETE SET NULL`, index existence) is exercised against real
PostgreSQL, not SQLite or mocks.

## Alembic Verification

```text
uv run alembic upgrade head        -> runs to eb1af61cf576 (head)
uv run alembic current             -> eb1af61cf576 (head)
uv run alembic check               -> No new upgrade operations detected.
uv run alembic downgrade a1c3e5f7b9d2 -> OK
uv run alembic upgrade head        -> OK (back to head)
```

The migration's legacy-URL backfill is tested end-to-end in
`test_migration_backfills_cms_media_links_from_legacy_urls` (insert legacy rows
at the previous revision → upgrade → assert FKs backfilled and unmatched
external URLs are *not* fabricated). Downgrade/upgrade is also exercised by the
existing suite (`test_alembic.py`, `test_files_models.py`,
`test_cms_models.py`).

## Live HTTP Verification

The backend was started with `uvicorn` and verified with `curl` against the
local dev database (migrated to head):

| Flow | Result |
| --- | --- |
| `POST /api/v1/admin/files` (PNG) | 201, `width=640 height=360 media_type=image`, derived `url` |
| `POST /api/v1/admin/files` (MP4) | 201, `media_type=video` |
| `GET /api/v1/admin/files?folder=projects` | 200, correct items |
| `GET /api/v1/admin/files/{id}` | 200 |
| `PATCH /api/v1/admin/files/{id}` (alt_text/folder) | 200 |
| `PATCH` with `storage_key`/`size` (mass assignment) | ignored (values unchanged) |
| `DELETE /api/v1/admin/files/{id}` (unreferenced) | 204 |
| MIME spoof (text as `image/png`) | 422 |
| SVG upload | 422 |
| `.exe` upload | 422 |
| Oversized upload | 413 |
| Path-traversal filename | 201, sanitized `original_name` |
| Malformed UUID | 422 |
| Project create with `cover_media_id` + `demo_video_media_id` | 201, nested media + mirrored legacy URL |
| Public `GET /projects/{slug}` | nested `cover_media`/`demo_video`; no FK/`storage_key` leak |
| `DELETE` referenced media | 409 (reference detail) |
| Unlink then delete | 204 |
| Unauthenticated media ops | 401 |
| Plain `user` media ops | 403 |
| Admin (seeded) media ops | 200/201 |

## Bugs Discovered

1. **Pre-existing (baseline): safe-500 regression.** With `DEBUG=true` (set in
   `.env`), Starlette 1.6's `ServerErrorMiddleware` returned raw tracebacks to
   clients and bypassed the app's installed `@app.exception_handler(Exception)`
   safe handler. This made `test_security.py::test_unhandled_exception_returns_safe_500`
   fail at baseline (before any Phase 8 change).
2. **`MediaAdmin`/`MediaPublic` missing `url` attribute.** The schema exposed
   `url` but the Media model only had `public_url`, causing
   `ResponseValidationError` on every media response.
3. **Schema/model name mismatch for `demo_video`.** Public/admin responses
   defined `demo_video` but the ORM relationship was `demo_video_media`, so the
   nested object serialized as `null`.
4. **`SolutionAdmin` omitted the media FK ids** (`image_media_id`,
   `demo_video_media_id`), so responses were missing them.
5. **Ordering bug in the new test**: rows were sorted by slug and unpacked in
   the wrong order (my test bug, not an implementation bug).
6. **Pre-existing `alembic check` drift**: the DB had `category_id` indexes on
   the three many-to-many link tables that the models did not declare.
7. **Pre-existing format debt**: five old migration files were committed
   unformatted, so `ruff format --check .` failed at baseline.

## Root Causes

1. `app.main` passed `debug=settings.debug` to FastAPI; Starlette's
   ServerErrorMiddleware treats debug mode as "return traceback" and never calls
   the installed handler. Fix: construct the app with `debug=False` and rely on
   the existing handler (tracebacks go to server logs; `settings.debug` still
   controls the log level).
2. `url` was only declared in the schema, not the model.
3. Naming mismatch between the API field and the ORM relationship.
4. Schema omission.
5. Test unpack order assumption.
6. The link-table models had the index declaration removed after their
   migrations were written.
7. Old migration files were never run through `ruff format`.

## Fixes

1. `app/main.py`: `debug=False` with a comment; the safe JSON 500 handler now
   always runs and security headers are applied. `DEBUG` env still controls log
   verbosity. The previously failing test now passes.
2. Added `Media.url` property (alias of `public_url`).
3. Added `demo_video` properties to `Project` and `Solution`.
4. Added the FK id fields to `SolutionAdmin`.
5. Fixed the migration-backfill test unpack order.
6. Declared the `category_id` indexes on the link tables in the models
   (matches the actual DB; `alembic check` now clean).
7. Ran `ruff format` on the five legacy migration files (semantics unchanged).

## Regression Tests

- The previously failing `test_unhandled_exception_returns_safe_500` now passes.
- All existing CMS/admin/auth/lead/security/database tests continue to pass.
- Added regression tests for canonical-media-wins, mass-assignment immunity,
  MIME spoofing, SVG rejection, and delete-referenced → 409.

## Security Review

Performed against the requirements list:

| Check | Result |
| --- | --- |
| Path traversal | ✅ storage keys never from user input; `_resolve` rejects `..`/absolute; folder pattern |
| Malicious filenames | ✅ basename-only sanitization (`original_name`) |
| Executable uploads | ✅ allowlist + content signature |
| MIME spoofing | ✅ Pillow decode/format match + video/PDF magic bytes |
| Oversized files | ✅ size caps → 413 |
| Unauthorized uploads/deletion/modification | ✅ `require_staff` (401/403) |
| IDOR | ✅ object access always by id with authorization enforced |
| SVG script injection | ✅ SVG not accepted |
| Leaking filesystem paths / storage config | ✅ responses expose only derived URLs |
| Mass assignment | ✅ PATCH schema whitelist (`alt_text`, `folder`) |
| Malformed UUIDs | ✅ 422 |
| Unsafe folder names | ✅ pattern validation |
| SQL injection | ✅ parameterized queries (SQLAlchemy) |
| Unsafe error messages | ✅ safe detail strings; pre-existing debug-traceback leak fixed |
| CMS media deletion safety | ✅ 409 when referenced; `ON DELETE SET NULL` |

## Dependency Changes

- Added **`pillow`** (image decoding for content signature verification +
  `width`/`height` extraction). Justified: stdlib cannot decode images, and this
  avoids a heavier media-processing pipeline. No S3/R2 SDK, Redis, Celery,
  FFmpeg, or ClamAV introduced.

## Known Limitations

- **Video duration is not extracted** (`duration_seconds` stays `NULL` for
  uploaded videos). Requires FFmpeg/ffprobe — intentionally deferred and
  documented rather than faked.
- **Storage/PostgreSQL are not transactionally atomic.** Best-effort cleanup is
  implemented and documented; orphan objects are possible if cleanup itself
  fails (e.g. a process crash between storage write and DB commit).
- **Media-type compatibility is not enforced at link time** (e.g. a video can
  be linked as a project cover). Type constraints are enforced at upload;
  link-time enforcement is documented as a possible future improvement.
- **Migration backfill only converts URLs that exactly match a stored media
  `public_url`.** Arbitrary/external legacy URLs are preserved in the legacy
  columns but are not promoted to Media references (no Media records are
  fabricated).
- **Five pre-existing migration files were reformatted** by `ruff format`
  (cosmetic line wrapping only; no SQL changes) to satisfy the required
  `ruff format --check .` gate.
- The user-facing legacy string fields remain in responses (deprecated) for
  backward compatibility and will be removed once the frontend consumes the
  nested media objects.

## Design Decisions

- `storage_key` is the canonical identity; `public_url` is **derived at
  runtime** (not stored) so storage/CDN changes never require rewriting rows.
- CMS media relationships use real FKs with `ON DELETE SET NULL`; media is
  never cascade-deleted from CMS content, and deleting referenced media is
  rejected with `409`.
- Delete ordering: storage first, then DB (a metadata row pointing at a missing
  object is preferred over an orphaned object with no metadata).
- Legacy URL columns are retained and auto-mirrored from linked media
  (backward compatibility), with public nested media objects as the canonical
  frontend contract.
- SVG: Option A (removed from allowlist).
- `/files` endpoint prefix kept (no breaking rename).
- Service layer added only where it earns its keep (media upload/delete);
  CMS endpoints stay thin and reuse the existing `common.py` helpers.
- Video duration extraction deferred (no FFmpeg dependency this phase).

## Deferred Work

- Actual R2/S3 storage backend implementation.
- Video duration extraction (FFprobe/FFmpeg) once videos need real durations.
- Media-type compatibility enforcement at CMS link time.
- Public media browse/caching/CDN.
- Rate limiting / upload throttling (Phase 9 territory).

## Frontend Compatibility Notes

- Consume `media.id`, `media.url`, `media.mime_type`, `media.media_type`,
  `media.width`, `media.height`, `media.duration_seconds`, `media.alt_text`
  from the nested media objects in public CMS responses.
- Admin responses also expose the media FK ids (`cover_media_id`, ...) for
  wiring content to media.
- Legacy string fields are deprecated but present; migrate the frontend off
  them when convenient.
- No internal storage details, filesystem paths, or FKs are exposed publicly.

## Production Recommendations

- Implement the R2/S3 backend against the existing `StorageBackend` interface;
  add `STORAGE_BACKEND=s3|r2` + credential/bucket config via environment
  variables (never committed).
- Serve media from the object-storage origin/CDN with
  `Content-Type`/`Content-Disposition` and `X-Content-Type-Options: nosniff`.
- Reconsider SVG only if genuinely required, and then only via a separate asset
  origin with sanitization and safe headers.
- Set `COOKIE_SECURE=true`, configure `TRUSTED_HOSTS`, and keep `DEBUG=false`
  in production (safe 500 handler is now enforced regardless).

## Next Phase

Phase 9 — API Hardening & Security (per the roadmap in `docs/phases/phases.md`).
Not implemented in this phase.
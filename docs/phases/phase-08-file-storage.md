# Phase 8 Report — File / Media Storage

**Project:** Beezents Backend
**Phase scope:** Clean media storage abstraction + media metadata management
**Date:** 2026-09-02
**Status:** Complete and verified against a live PostgreSQL instance + local storage

---

## 1. Phase objective

Give the backend a clean way to manage website media. Binary content is **never
stored in PostgreSQL**; the database holds only metadata/reference information.
The API is designed so production object storage (Cloudflare R2 / S3-compatible)
can be added behind the same interface without changing the API or the data
model. Because no cloud credentials are available, this phase delivers a
**testable storage interface and a local development adapter**.

## 2. Scope

- `Media` metadata model (`id`, `original_name`, `storage_key`, `public_url`,
  `mime_type`, `size`, `width`, `height`, `alt_text`, `folder`, `uploaded_by`,
  timestamps).
- `StorageBackend` interface + `LocalStorageBackend` + config-driven factory.
- Alembic migration (`create media table`) with upgrade/downgrade.
- Admin media CRUD: `POST /api/v1/admin/files` (multipart upload),
  `GET` (paginated list with `folder`/`mime_type`/`q`/`sort`/`order`),
  `GET/{id}`, `PATCH/{id}` (metadata only), `DELETE/{id}` (204).
- MIME allowlist, size limit, UUID-based storage naming, sanitized filenames,
  path-traversal-safe folders, uploader tracking.
- 39 new tests (API + model/database), README + `.env.example` docs, and this
  report.

Out of scope (per roadmap): actual R2/S3 implementation, image dimension
extraction, thumbnails, image processing, public media API, CDN/caching.

## 3. Acceptance criteria

| Criterion | Status |
| --- | --- |
| Binaries not stored in PostgreSQL | ✅ (only metadata in `media` table) |
| Storage abstraction + local dev adapter | ✅ |
| No hardcoded cloud credentials / secrets committed | ✅ |
| `Media` model + migration | ✅ `147c3d1fc707` |
| Secure filename handling | ✅ (basename only; UUID-based keys) |
| MIME validation | ✅ (allowlist; else 422) |
| Size validation | ✅ (default 10 MiB; else 413) |
| UUID-based storage naming | ✅ `{uuid}.{ext}` |
| No arbitrary filesystem paths from users | ✅ (folder pattern; key never from input) |
| Ownership/uploader tracking | ✅ (`uploaded_by` FK, SET NULL) |
| Admin authorization | ✅ `require_staff` (401/403 matrix) |
| Metadata storage | ✅ |
| Full suite passes, no regressions | ✅ 211 passed |
| README + `.env.example` updated | ✅ |
| Phase report created | ✅ |

## 4. What was implemented

- **Storage abstraction** (`app/core/storage.py`):
  - `StorageResult` (`storage_key`, `public_url`).
  - `StorageBackend` ABC with `save(storage_key, content)`,
    `delete(storage_key)`, `public_url(storage_key)`.
  - `LocalStorageBackend` — writes to `MEDIA_ROOT` via `asyncio.to_thread`
    (no event-loop blocking), ignores missing objects on delete, and guards
    storage keys against absolute paths / `..`.
  - `ALLOWED_MIME_TYPES` map (MIME → canonical extension),
    `build_storage_key(mime_type)` (random UUID hex + extension derived from the
    validated MIME, never from user input), and `get_storage()` factory driven by
    `STORAGE_BACKEND` (only `"local"` supported; unknown backends raise).
- **`Media` model** (`app/models/media.py`): all requested fields; `storage_key`
  unique + indexed; `uploaded_by` FK to `users.id` `ON DELETE SET NULL`;
  `size` `BigInteger` with `CHECK (size >= 0)`; indexes on `created_at` and
  `folder`; timezone-aware timestamps via `TimestampMixin`.
- **Schemas** (`app/schemas/files.py`): `MediaAdmin` (full metadata,
  `from_attributes=True`) and `MediaMetadataUpdate` (`alt_text`, `folder`;
  `folder` validated against `^[a-z0-9_-]{1,100}$`).
- **Admin endpoints** (`app/api/v1/endpoints/admin_files.py`), all
  `require_staff`:
  - `POST` — validates MIME + folder, reads content, enforces size, builds a
    UUID storage key, saves to storage, inserts the DB row. If the DB insert
    fails, the just-written storage object is deleted (no orphaned blobs).
  - `GET` list with `folder`/`mime_type` filters, `q` search over
    `original_name`/`mime_type`, `sort` (`created_at`/`size`/`original_name`),
    `order`; default `created_at desc`.
  - `GET/{id}`, `PATCH/{id}` (metadata only — binary/storage_key never
    editable), `DELETE/{id}` (removes the storage object then the row → 204).
- **Config** (`app/core/config.py`): `storage_backend` (`local`),
  `media_root` (`./media`), `media_max_size_bytes` (10 MiB).
- **Static serving** (`app/main.py`): for the local backend only, mounts
  `StaticFiles` at `/media` (creates `MEDIA_ROOT`), so uploaded files are
  reachable at their `public_url`.
- **Dependency**: added `python-multipart` (required by FastAPI for
  `Form`/`UploadFile`). No other new dependencies.

## 5. Files created

| File | Purpose |
| --- | --- |
| `app/core/storage.py` | Storage abstraction + local adapter + MIME rules |
| `app/models/media.py` | `Media` metadata model |
| `app/schemas/files.py` | `MediaAdmin`, `MediaMetadataUpdate`, `normalize_folder` |
| `app/api/v1/endpoints/admin_files.py` | Admin media CRUD |
| `migrations/versions/147c3d1fc707_create_media_table.py` | Alembic migration |
| `tests/test_files_api.py` | 32 API tests |
| `tests/test_files_models.py` | 7 model/database tests |
| `docs/phases/phase-08-file-storage.md` | This report |

## 6. Files modified

| File | Change |
| --- | --- |
| `app/core/config.py` | Added `storage_backend`, `media_root`, `media_max_size_bytes` |
| `app/models/__init__.py` | Export `Media` |
| `app/schemas/__init__.py` | Export media schemas |
| `app/api/v1/router.py` | Include `admin_files` router |
| `app/main.py` | Conditional `/media` StaticFiles mount (local backend) |
| `pyproject.toml` | Added `python-multipart` dependency |
| `tests/conftest.py` | Isolated test `MEDIA_ROOT` + small size cap + per-test media cleanup |
| `tests/test_leads_models.py` | Pinned downgrade target to the leads migration's parent revision |
| `.gitignore` | Ignore `/media/` (dev uploads) |
| `.env.example` | Documented the three media/storage variables |
| `README.md` | Media / File Storage section + project structure |

## 7. Database changes

New `media` table:

```
media
├── id            uuid        PK
├── original_name varchar(255)   NOT NULL
├── storage_key   varchar(255)   NOT NULL  UNIQUE
├── public_url    varchar(500)   NOT NULL
├── mime_type     varchar(100)   NOT NULL
├── size          bigint         NOT NULL  CHECK (size >= 0)
├── width         integer        NULL
├── height        integer        NULL
├── alt_text      varchar(500)   NULL
├── folder        varchar(100)   NULL
├── uploaded_by   uuid           NULL  FK users.id ON DELETE SET NULL
├── created_at    timestamptz    NOT NULL  server_default now()
└── updated_at    timestamptz    NOT NULL  server_default now()
```

Indexes: unique `ix_media_storage_key`, `ix_media_created_at`,
`ix_media_folder`, `ix_media_uploaded_by` (FK).

Index decisions: `created_at` (default admin sort), `folder` (common admin
filter), `uploaded_by` (FK lookups); `storage_key` unique. The `q` search is
`ILIKE '%…%'` over `original_name`/`mime_type`, which cannot use a B-tree index
(consistent with Phases 5–7 search).

Migration `147c3d1fc707` (`create media table`): upgrade creates the table +
constraints + indexes; downgrade drops them. Verified `upgrade` /
`downgrade -1` / `upgrade` on both the test database (automated) and the dev
database (manual). `alembic check` reports no pending operations; revision is
`147c3d1fc707 (head)`.

## 8. API endpoints

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/api/v1/admin/files` | Paginated list; `page`, `page_size` (1–100, default 20), `folder`, `mime_type`, `q`, `sort` (`created_at`/`size`/`original_name`), `order` |
| `POST` | `/api/v1/admin/files` | Upload (multipart: `file` required; `folder`, `alt_text` optional) → 201 |
| `GET` | `/api/v1/admin/files/{id}` | Media metadata detail |
| `PATCH` | `/api/v1/admin/files/{id}` | Update `alt_text`/`folder` only |
| `DELETE` | `/api/v1/admin/files/{id}` | Delete object + row → 204 |

In development, files are served at their `public_url` (`/media/{storage_key}`)
by the local backend's static mount. There is **no** public media API; metadata
is staff/admin-only.

## 9. Authentication / authorization

- Every admin route depends on `require_staff` (staff and admin only),
  consistent with Phases 6–7; enforcement is entirely server-side.
- Unauthenticated → `401`; `user`/`client` → `403`; `staff`/`admin` → allowed.
- `uploaded_by` records the authenticated user's UUID (server-set, never from
  the client).

## 10. Validation rules

- **MIME**: must be in `ALLOWED_MIME_TYPES`; otherwise `422 Unsupported file
  type`.
- **Size**: `len(content) > media_max_size_bytes` → `413 File is too large`.
- **Folder** (upload form + PATCH): optional; `^[a-z0-9_-]{1,100}$` (rejects
  path separators, `..`, spaces, uppercase) → `422`.
- **alt_text**: optional; ≤ 500 chars; trimmed.
- **original_name**: sanitized to a bare basename (path separators and NUL
  stripped), truncated to 255; never used as a storage path.
- **storage_key**: server-generated `{uuid4().hex}{ext}`; client cannot supply
  it.
- **Pagination**: `page >= 1`, `page_size` 1–100 → invalid 422.
- **PATCH**: `exclude_unset=True` (genuinely partial); `null` clears optional
  metadata.
- Unknown UUID → 404; malformed UUID → 422.

## 11. Testing

All tests run against the real PostgreSQL test database with real HTTP requests
via `TestClient`; media uploads write real bytes to an isolated temp
`MEDIA_ROOT` and the suite verifies files on disk — no mocks.

### `tests/test_files_api.py` (32 tests)

- **Upload happy paths**: PNG with folder/alt_text → 201 with all fields, file
  present on disk, `public_url` correct, `uploaded_by` set; minimal upload;
  PDF upload; filename sanitization (`../../etc/passwd.png` → `passwd.png`,
  key contains no `/` or `..`).
- **Upload validation**: unsupported MIME (`application/x-msdownload`,
  `text/plain`) → 422; oversize (> test cap) → 413; missing file → 422;
  invalid folder values → 422; overlong alt_text → 422.
- **Authorization matrix**: unauthenticated GET/PATCH/DELETE/upload → 401;
  `user`/`client` → 403 on all operations; `staff`/`admin` → allowed.
- **Admin CRUD**: list + detail; PATCH metadata only (alt_text trimmed, folder
  updated, storage_key unchanged); clearing optional metadata via `null`;
  invalid folder on PATCH → 422; DELETE → 204 with row and on-disk file gone;
  DELETE with already-missing storage object still removes the row; unknown
  UUID → 404; malformed UUID → 422.
- **Filtering/search/pagination/sorting**: folder + mime filters; `q` search;
  pagination envelope + invalid params → 422; sort by `size` asc/desc; invalid
  sort → 422.
- **Serving**: the uploaded file is served from its `public_url` with the
  original bytes.

### `tests/test_files_models.py` (7 tests)

`Media` creation with all fields; optional fields default null; `uploaded_by`
FK `ON DELETE SET NULL` when the uploader is deleted; `storage_key` unique;
`CHECK (size >= 0)` rejects negative size; NOT NULL required fields enforced;
indexes present; table exists; Alembic downgrade removes the table and upgrade
restores it.

Full suite: **211 passed** (172 prior + 39 new), no regressions.

## 12. Bugs discovered

1. **Stale migration test after adding a newer migration.** Adding the `media`
   migration made `tests/test_leads_models.py::test_alembic_downgrade_and_
   upgrade_restores_leads_table` fail: it used `alembic downgrade -1`, which
   from the new head drops the `media` table (the newest migration), not the
   `leads` table — so the `"leads" not in tables` assertion failed.
2. **Missing `python-multipart`.** Importing the upload endpoint raised
   `RuntimeError: Form data requires "python-multipart" to be installed`.

## 13. Root causes

1. The migration test hard-coded the "latest migration" assumption (`-1`)
   rather than targeting the revision it was testing. Phase 8 added a newer
   migration, invalidating that assumption. This was a real regression in the
   test suite (it caught a genuine consequence of the schema change).
2. FastAPI's `Form`/`UploadFile` multipart parsing requires the optional
   `python-multipart` package, which had not been needed before (no endpoint
   previously accepted multipart/form-data).

## 14. Fixes applied

1. Pinned the downgrade target in `test_leads_models.py` to the leads
   migration's parent revision (`eef51e823865`), so the test verifies the leads
   migration's downgrade regardless of which migrations are newer. (The CMS
   downgrade test in `test_cms_models.py` is unaffected: its assertion — CMS
   tables exist after downgrade/upgrade — remains true.)
2. Added `python-multipart>=0.0.20` to `pyproject.toml`; `uv sync` updated the
   lockfile (now 44 packages). This is a justified, first-party dependency for
   file uploads.

## 15. Regression tests added

- `test_delete_removes_file_and_row`, `test_delete_missing_storage_object_
  still_deletes_row`, `test_uploaded_file_served_from_public_url`,
  `test_upload_original_name_sanitized` — cover the storage lifecycle and the
  security-critical filename handling.
- `test_media_uploaded_by_fk_set_null_on_user_delete`, `test_media_size_check_
  constraint`, `test_media_storage_key_unique` — DB-level guarantees.
- The fixed `test_leads_models.py` downgrade test now runs green again.
- Full Phase 1–7 regression: all 172 prior tests still pass unchanged; live
  checks confirmed `/health`, `/api/v1/health/db`, public CMS, admin CMS,
  public leads, and admin leads unaffected.

## 16. Security checks

- **Path traversal**: storage keys are server-generated UUIDs; `_resolve` rejects
  absolute paths and `..`; folder names are regex-constrained; client filenames
  are reduced to a basename and never used in paths.
- **MIME / size limits** enforced server-side before any write.
- **No arbitrary filesystem paths from users** — user input never reaches the
  storage key or filesystem path.
- **Uploader tracking** recorded from the authenticated session, not the client.
- **Authorization** enforced via `require_staff` on every route (401/403
  verified live + in tests).
- **Transaction safety**: on DB-insert failure the freshly written storage
  object is deleted (no orphaned blobs); delete removes storage first, then the
  row, inside a transaction.
- **SQL injection**: all queries are SQLAlchemy parameterized expressions.
- **Error leakage**: safe, meaningful errors only (422/413/404); no stack
  traces, connection strings, or DB details; the `ValueError` from storage key
  validation is caught and mapped.
- **Secrets**: no cloud credentials anywhere; `STORAGE_BACKEND` defaults to
  `local`; `.env` and `/media/` are gitignored (verified by repo scan).
- **PII**: media metadata is staff/admin-only; no public exposure.
- **Note (deferred hardening)**: SVG is in the MIME allowlist; served inline,
  uploaded SVG could be an XSS vector if opened directly. Safe inline rendering
  (or removing SVG) is deferred to Phase 9 / production serving via CDN.

## 17. Verification results (actually executed)

| Command | Result |
| --- | --- |
| `uv sync` | Clean (44 packages, incl. `python-multipart`) |
| `uv lock --check` | Resolved 44 packages, no drift |
| `uv run pytest` | **211 passed** (172 existing + 39 new) |
| `uv run ruff check .` | All checks passed |
| `uv run ruff format --check .` | 74 files already formatted |
| `uv run alembic check` | No new upgrade operations detected |
| `uv run alembic current` | `147c3d1fc707 (head)` |
| Migration up/down/up (test DB) | `test_files_models.py` + pinned leads test (passing) |
| Migration up/down/up (dev DB) | Manual `upgrade head` → `downgrade -1` → `upgrade head` (passing) |

### Live endpoint verification (uvicorn on :8010 + curl against real PostgreSQL and local storage)

- `POST /api/v1/admin/files` (PNG + folder + alt_text) → 201 with full metadata;
  UUID-based `storage_key` (`c5237e62…png`), correct `size`, `uploaded_by` set.
- File written to `MEDIA_ROOT`; `GET /media/{storage_key}` served the exact
  bytes (200).
- `text/plain` upload → 422; `folder=../etc` → 422; 11 MiB upload → 413.
- Unauthenticated `GET` → 401; normal `user` `GET`/`DELETE` → 403.
- Admin list → 200 (newest first); detail → 200; PATCH `{alt_text, folder}` →
  only those fields changed, `storage_key` unchanged; unknown UUID → 404;
  malformed UUID → 422; `?folder=` filter → 1; `?q=` search → 1.
- DELETE → 204; subsequent GET → 404; on-disk file removed.
- Regression: `/health`, `/api/v1/health/db`, public CMS, admin CMS, public
  lead submission, and admin leads all still returned the expected codes.

Dev media and dev DB tables were truncated/removed after verification.

## 18. Known limitations

- **Local-only backend** — `STORAGE_BACKEND=local` is the only implemented
  backend; R2/S3 is designed for but not implemented (no credentials, no
  `boto3`/`aioboto3` dependency added). Unknown backend names raise at request
  time.
- **MIME is trust-based** — the declared `Content-Type` is validated against the
  allowlist; there is no magic-byte sniffing (no Pillow / libmagic). A client
  could label arbitrary bytes as an allowed type.
- **`width`/`height` are always `NULL`** — image dimension extraction (Pillow)
  is deferred; the columns exist for when it is added.
- **No thumbnails / image processing / EXIF stripping.**
- **Static serving of SVG** can be an XSS vector when opened directly (see §16);
  production should serve media from a CDN/object storage with safe headers.
- **`folder` is metadata only** — it is not a storage prefix; moving a file to
  another folder does not relocate the object.

## 19. Architecture / design decisions

- **`Media` model name** (not `File`) — avoids the `FastAPI File` import
  collision in endpoint modules.
- **Storage abstraction = one ABC + local adapter + factory** — exactly what the
  phase requires ("clean storage abstraction", "testable interface + local
  adapter"), without a service layer, DI container, or other overengineering.
- **Storage keys are purely UUID-based** and derived from the validated MIME
  type; user input never participates in key/path construction — the strongest
  interpretation of "no arbitrary filesystem paths from users".
- **`folder` as pure metadata** (not a path component) — keeps storage naming
  fully server-controlled and avoids the inconsistency of "renaming a folder
  doesn't move the object".
- **Write ordering for uploads** — persist to storage, then insert metadata;
  on DB failure, delete the just-written object so a failed upload leaves no
  orphan blob.
- **`require_staff` for all media operations** — consistent with the CMS and
  lead admin policies.
- **Local serving via a conditional `StaticFiles` mount** only when
  `STORAGE_BACKEND=local` — production will serve from the object storage/CDN
  URL instead, so the mount never ships to production.
- **No image-processing dependency** this phase — dimensions/thumbnails are
  deferred to keep the dependency footprint minimal.

## 20. Deferred work

- R2 / S3-compatible backend implementation (with credentials via environment,
  never committed).
- Image dimension extraction (Pillow) to populate `width`/`height`.
- Thumbnails / resize / format conversion / EXIF stripping.
- Magic-byte MIME sniffing.
- Safe SVG handling or SVG removal.
- Public (read-only) media URL / CDN integration; caching headers.
- Orphan-blob cleanup job (e.g., scheduled sweep of storage objects with no DB
  row) — currently handled on the upload failure path only.

## 21. Next phase

**Phase 9 — API Hardening & Security** (auth/cookie audit, authorization audit,
validation review, CORS/headers/error-leakage review, abuse protection,
secrets scan, and a security audit checklist).
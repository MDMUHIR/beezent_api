# Beezents API — Combined Entity + Media Upload

**Project:** Beezents backend
**Date:** 2026-09-07
**Status:** Implemented and tested

---

## Overview

The backend now supports uploading photos and videos **directly from the
client's local storage** and merging them into CMS records (Projects,
Solutions, Case Studies) **in a single multipart request**.

The API:

1. Validates the uploaded files (MIME type, size, content signature).
2. Stores the binary content in the media storage backend (local disk in
   development; object storage in production).
3. Creates a `Media` metadata record.
4. Automatically links the media to the entity's image/cover and demo-video
   fields (UUID FK + mirrored legacy URL columns).

The previous generic upload endpoint `POST /api/v1/admin/files` has been
**removed**. The media *library* endpoints (`GET`, `PATCH`, `DELETE` under
`/api/v1/admin/files`) remain for browsing/managing already-uploaded media.

---

## Authentication

All endpoints require a **staff** or **admin** session cookie:

- Log in via `POST /api/v1/auth/login` with the admin email/password.
- The API sets an HTTP-only session cookie; the browser sends it automatically.
- `401` = not authenticated, `403` = authenticated but not staff/admin.

---

## Request format (multipart/form-data)

Every endpoint accepts **one** multipart request with:

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `payload` | string (JSON) | Yes | The entity fields as a JSON string (see payload fields below). |
| `cover_file` / `image_file` | file | No | Photo (image/jpeg, png, gif, webp, avif). |
| `demo_video_file` | file | No | Video (mp4, webm, mov, ogv). |

> The entity fields are sent **as a JSON string** in the `payload` form field,
> not as individual form fields. The file(s) are sent as regular multipart
> file parts.

### Accepted MIME types

- **Images:** `image/jpeg`, `image/png`, `image/gif`, `image/webp`, `image/avif`
- **Videos:** `video/mp4`, `video/webm`, `video/quicktime`, `video/ogg`
- **Documents:** `application/pdf`
- SVG is rejected (active-script risk). Content is verified by signature, so
  a mismatched `Content-Type`/bytes are rejected with `422`.

### Size limits (from backend config)

- Images/files: **10 MiB** default
- Videos: **100 MiB** default

---

## Endpoints

| Method | Path | Files |
| --- | --- | --- |
| `POST` | `/api/v1/admin/projects/upload` | `cover_file`, `demo_video_file` |
| `PATCH` | `/api/v1/admin/projects/{id}/upload` | `cover_file`, `demo_video_file` |
| `POST` | `/api/v1/admin/solutions/upload` | `image_file`, `demo_video_file` |
| `PATCH` | `/api/v1/admin/solutions/{id}/upload` | `image_file`, `demo_video_file` |
| `POST` | `/api/v1/admin/case-studies/upload` | `image_file` |
| `PATCH` | `/api/v1/admin/case-studies/{id}/upload` | `image_file` |

All are relative to the API prefix `/api/v1`.

### Project payload fields

```json
{
  "title": "AI Dashboard",
  "slug": "ai-dashboard",
  "short_description": "Optional one-liner",
  "description": "Optional long text",
  "client_name": "Optional client",
  "industry": "Optional industry",
  "project_type": "Optional type",
  "status": "active",
  "featured": false,
  "published": false,
  "live_url": "https://...",
  "github_url": "https://...",
  "technologies": [],
  "results": [],
  "category_ids": [],
  "cover_media_id": "uuid-or-null",
  "demo_video_media_id": "uuid-or-null"
}
```

`PATCH` payload fields are all optional; send only what you want to change.
`slug` must be lowercase letters/numbers/hyphens.

### Solution payload fields

`name`, `slug`, `short_description`, `description`, `icon`, `featured`,
`published`, `sort_order`, `category_ids`, plus `image_media_id`,
`demo_video_media_id`, `demo_video_type`.

### Case Study payload fields

`title`, `slug`, `project_id`, `summary`, `challenge`, `solution`,
`implementation`, `results`, `technologies`, `metrics`, `featured`,
`published`, `seo_title`, `seo_description`, `image_media_id`.

---

## Example: create a Project with a cover photo and demo video

```bash
curl -X POST "http://localhost:8000/api/v1/admin/projects/upload" \
  -H "Cookie: beezents_session=<SESSION_COOKIE>" \
  -F 'payload={"title":"AI Dashboard","slug":"ai-dashboard","published":true}' \
  -F "cover_file=@/path/to/hero.png;type=image/png" \
  -F "demo_video_file=@/path/to/demo.mp4;type=video/mp4"
```

### Successful response — `201 Created` (create) / `200 OK` (update)

```json
{
  "id": "6f9c...",
  "title": "AI Dashboard",
  "slug": "ai-dashboard",
  "status": "active",
  "featured": false,
  "published": true,
  "cover_image": "/media/<storage-key>.png",
  "cover_media_id": "b7c1...",
  "cover_media": {
    "id": "b7c1...",
    "url": "/media/<storage-key>.png",
    "mime_type": "image/png",
    "media_type": "image",
    "size": 48213,
    "width": 16,
    "height": 9,
    "duration_seconds": null,
    "alt_text": null
  },
  "demo_video_url": "/media/<storage-key>.mp4",
  "demo_video_media_id": "8a2f...",
  "demo_video": {
    "id": "8a2f...",
    "url": "/media/<storage-key>.mp4",
    "mime_type": "video/mp4",
    "media_type": "video",
    "size": 1073,
    "width": null,
    "height": null,
    "duration_seconds": null,
    "alt_text": null
  },
  "demo_video_type": "upload",
  "technologies": [],
  "results": [],
  "categories": [],
  "created_at": "2026-09-07T22:00:00Z",
  "updated_at": "2026-09-07T22:00:00Z"
}
```

`cover_image`/`demo_video_url` are always mirrored from the linked media, so
use those for `<img src>` and `<video src>`.

---

## Example: update a Project (replace cover photo only)

```bash
curl -X PATCH "http://localhost:8000/api/v1/admin/projects/<PROJECT_ID>/upload" \
  -H "Cookie: beezents_session=<SESSION_COOKIE>" \
  -F 'payload={"title":"Renamed"}' \
  -F "cover_file=@/path/to/new.png;type=image/png"
```

A file present in the request **wins over** any `*_media_id` in the payload.
Omitting both file fields and media ids leaves existing media untouched.

---

## Errors

| Status | Meaning |
| --- | --- |
| `401` | Not authenticated |
| `403` | Authenticated but not staff/admin |
| `409` | Slug already in use (or media referenced on delete) |
| `413` | File exceeds the size limit |
| `422` | Invalid JSON payload, missing required field, unsupported/ spoofed file, invalid category/project id, invalid slug |

Error bodies are JSON: `{"detail": [...]}` for validation errors and
`{"detail": "message"}` otherwise. Validation `detail` is an array of
`{loc, msg, type}` entries (Pydantic format).

---

## Frontend integration notes (Next.js)

1. Build a `FormData` body:
   - `payload` → `JSON.stringify({ title, slug, ... })`
   - `coverFile`/`demoVideoFile` → the selected `File` objects (or omit).
2. Send with `method: POST`/`PATCH`, **do not** set `Content-Type` manually —
   let the browser set the multipart boundary.
3. Session cookie is sent automatically (same-origin or `credentials: "include"`).
4. After success, update your local state/optimistic UI with the response
   (`cover_image`, `demo_video_url`, `cover_media`, `demo_video`).
5. Show progress using `XMLHttpRequest` (not `fetch`) if you need upload
   progress bars.
6. Handle the errors in the table above; render `detail` (string or array).
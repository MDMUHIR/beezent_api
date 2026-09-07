# Frontend Implementation Prompt — Combined Media Upload

Copy and paste the block below into your coding assistant (or give it to a
frontend developer). Read `docs/frontend-upload-integration.md` in the backend
repo for the full API reference.

---

You are implementing a new feature in the Beezents Next.js frontend: **admins
must be able to upload a photo and/or video directly from their PC and have it
stored on the backend and automatically attached to a Project, Solution, or
Case Study record — in a single request.**

## Backend API contract (already implemented)

The backend now exposes multipart endpoints (staff/admin auth via the existing
`beezents_session` cookie). Base URL: `/api/v1`.

| Method | Path | File fields |
| --- | --- | --- |
| POST | `/admin/projects/upload` | `cover_file`, `demo_video_file` |
| PATCH | `/admin/projects/{id}/upload` | `cover_file`, `demo_video_file` |
| POST | `/admin/solutions/upload` | `image_file`, `demo_video_file` |
| PATCH | `/admin/solutions/{id}/upload` | `image_file`, `demo_video_file` |
| POST | `/admin/case-studies/upload` | `image_file` |
| PATCH | `/admin/case-studies/{id}/upload` | `image_file` |

Request format — `multipart/form-data`:

- `payload`: a **JSON string** containing the entity fields
  (e.g. `{"title":"AI Dashboard","slug":"ai-dashboard","published":true}`).
  On PATCH, only send fields to change.
- `cover_file` / `image_file`: optional image file.
- `demo_video_file`: optional video file.

Rules:

- Accept MIME types: images `image/jpeg|png|gif|webp|avif`, videos
  `video/mp4|webm|quicktime|ogg`. SVG is rejected.
- Limits: 10 MiB for images/files, 100 MiB for videos.
- A file sent in the request overrides any media id in `payload`.
- Errors: `401`/`403` auth, `409` duplicate slug, `413` too large, `422`
  invalid/malformed input (detail may be a string or an array of pydantic
  errors).
- Response is the full entity, including nested `cover_media`/`demo_video`
  objects with a `url` used for rendering, plus mirrored `cover_image` /
  `demo_video_url` / `image_url` string fields.

The old generic upload endpoint `POST /api/v1/admin/files` is removed and must
no longer be called; the media library GET/PATCH/DELETE endpoints still exist.

## What to build

1. **API client functions** (e.g. in `lib/api/admin.ts`):
   - `createProjectWithFiles(payload, coverFile?, demoVideoFile?)`
   - `updateProjectWithFiles(id, payload, coverFile?, demoVideoFile?)`
   - `createSolutionWithFiles(...)`, `updateSolutionWithFiles(...)`
   - `createCaseStudyWithFiles(...)`, `updateCaseStudyWithFiles(...)`
   - Each builds a `FormData`, appends `payload` = `JSON.stringify(payload)`
     and the provided `File`s, and uses `credentials: "include"`. Do NOT set
     `Content-Type` manually.
   - Type the responses using the existing entity types (the backend returns
     the entity admin shape with nested media).

2. **Admin UI** — extend the existing create/edit forms for Projects, Solutions,
   and Case Studies so the form includes file pickers:
   - Cover/image photo picker (accept `image/*`).
   - Demo video picker (accept `video/*`; Projects + Solutions only).
   - Optional "remove current image/video" action (send `*_media_id: null` in
     the payload when applicable).
   - Show the currently attached media (thumbnail for images, `<video>` preview
     for videos) using the `url` returned by the backend.
   - Submit through the new upload endpoints so the whole save + file upload is
     one request. Keep existing JSON-only forms working when no files are
     chosen.

3. **Upload UX**:
   - Disable the submit button while uploading; show a spinner.
   - If upload progress bars are wanted, use `XMLHttpRequest` for the upload
     calls (fetch has no upload progress).
   - Map backend errors to readable messages: duplicate slug (409), file too
     large (413), unsupported/ spoofed file (422). Show validation `detail`
     from the response body.

4. **Types** — ensure TypeScript types match the backend responses: entities
   include optional `cover_media`, `image_media`, `demo_video` objects shaped
   `{ id, url, mime_type, media_type, size, width, height, duration_seconds,
   alt_text }` and the string mirrors (`cover_image`, `image_url`,
   `demo_video_url`, `demo_video_type`).

## Acceptance criteria

- [ ] Admin can create a Project in one request with a cover photo and/or demo
      video from their PC, and the saved project shows the media URLs.
- [ ] Admin can update a Project and replace its cover photo or demo video with
      a new file from their PC.
- [ ] Same flows work for Solutions (image + demo video) and Case Studies
      (image only).
- [ ] Forms still work with no files attached (plain JSON save).
- [ ] Backend errors (409, 413, 422, 401/403) are surfaced to the user.
- [ ] No calls to the removed `POST /api/v1/admin/files` remain.
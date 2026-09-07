import asyncio
import json
import uuid
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from tests import media_fixtures

MEDIA_ROOT = Path(get_settings().media_root)
MAX_SIZE = get_settings().media_max_size_bytes


def _db_rows(sql: str, *args: object) -> list[asyncpg.Record]:
    async def run() -> list[asyncpg.Record]:
        url = make_url(get_settings().database_url)
        conn = await asyncpg.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            database=url.database,
        )
        try:
            return await conn.fetch(sql, *args)
        finally:
            await conn.close()

    return asyncio.run(run())


def _set_role(email: str, role: str) -> None:
    _db_rows("UPDATE users SET role = $1 WHERE email = $2", role, email)


def _login(client, email: str = "staff@example.com", role: str = "staff") -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "full_name": "Test User"},
    )
    if role != "user":
        _set_role(email, role)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strong-password"},
    )
    assert response.status_code == 200


def _media_count() -> int:
    return _db_rows("SELECT COUNT(*) AS c FROM media")[0]["c"]


# --------------------------------------------------------------------------- #
# Project: create with inline files
# --------------------------------------------------------------------------- #
def test_project_create_with_cover_and_demo_video(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": json.dumps({"title": "AI Dashboard", "slug": "ai-dashboard"})},
        files={
            "cover_file": ("hero.png", media_fixtures.PNG, "image/png"),
            "demo_video_file": ("demo.mp4", media_fixtures.MP4, "video/mp4"),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["title"] == "AI Dashboard"
    assert body["cover_media"]["media_type"] == "image"
    assert body["cover_media"]["url"].startswith("/media/")
    assert body["cover_image"] == body["cover_media"]["url"]
    assert body["demo_video"]["mime_type"] == "video/mp4"
    assert body["demo_video_type"] == "upload"
    assert body["demo_video_url"] == body["demo_video"]["url"]

    # Files are physically on disk in media storage.
    assert (MEDIA_ROOT / body["cover_media"]["url"].split("/media/")[1]).is_file()
    assert (MEDIA_ROOT / body["demo_video"]["url"].split("/media/")[1]).is_file()


def test_project_create_without_files_creates_plain_record(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": json.dumps({"title": "Plain", "slug": "plain"})},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["cover_media"] is None
    assert body["demo_video"] is None
    assert _media_count() == 0


def test_project_create_with_only_cover(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": json.dumps({"title": "Cover Only", "slug": "cover-only"})},
        files={"cover_file": ("c.png", media_fixtures.PNG, "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["cover_media"] is not None
    assert body["demo_video"] is None


def test_project_create_original_name_sanitized(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": json.dumps({"title": "Safe", "slug": "safe"})},
        files={"cover_file": ("../../etc/passwd.png", media_fixtures.PNG, "image/png")},
    )
    assert response.status_code == 201
    assert response.json()["cover_media"]["url"].startswith("/media/")
    rows = _db_rows("SELECT original_name FROM media")
    assert rows[0]["original_name"] == "passwd.png"


def test_project_update_replaces_cover_with_file(client) -> None:
    _login(client)
    created = client.post(
        "/api/v1/admin/projects",
        json={"title": "P", "slug": "p"},
    ).json()

    response = client.patch(
        f"/api/v1/admin/projects/{created['id']}/upload",
        data={"payload": json.dumps({"title": "P Updated"})},
        files={"cover_file": ("new.png", media_fixtures.PNG, "image/png")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["title"] == "P Updated"
    assert body["cover_media"] is not None
    assert body["cover_image"] == body["cover_media"]["url"]


# --------------------------------------------------------------------------- #
# Solution: create with inline files
# --------------------------------------------------------------------------- #
def test_solution_create_with_image_and_demo_video(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/solutions/upload",
        data={"payload": json.dumps({"name": "E-commerce", "slug": "ecommerce"})},
        files={
            "image_file": ("s.png", media_fixtures.PNG, "image/png"),
            "demo_video_file": ("s.webm", media_fixtures.WEBM, "video/webm"),
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["image_media"]["media_type"] == "image"
    assert body["image_url"] == body["image_media"]["url"]
    assert body["demo_video"]["mime_type"] == "video/webm"
    assert body["demo_video_type"] == "upload"


# --------------------------------------------------------------------------- #
# CaseStudy: create with inline image
# --------------------------------------------------------------------------- #
def test_case_study_create_with_image(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/case-studies/upload",
        data={"payload": json.dumps({"title": "CS", "slug": "cs"})},
        files={"image_file": ("c.png", media_fixtures.PNG, "image/png")},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["image_media"]["media_type"] == "image"
    assert body["image_url"] == body["image_media"]["url"]


# --------------------------------------------------------------------------- #
# Payload validation
# --------------------------------------------------------------------------- #
def test_missing_payload_422(client) -> None:
    _login(client)
    assert client.post("/api/v1/admin/projects/upload").status_code == 422


def test_invalid_json_payload_422(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": "{not json"},
    )
    assert response.status_code == 422


def test_payload_schema_error_422(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": json.dumps({"slug": "ai-dashboard"})},  # missing title
    )
    assert response.status_code == 422


def test_slug_conflict_409(client) -> None:
    _login(client)
    first = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": json.dumps({"title": "A", "slug": "dup"})},
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/admin/projects/upload",
        data={"payload": json.dumps({"title": "B", "slug": "dup"})},
    )
    assert second.status_code == 409


# --------------------------------------------------------------------------- #
# Upload content validation (now handled in the entity upload path)
# --------------------------------------------------------------------------- #
def _project_upload(client, *, payload=None, **files) -> object:
    data = {"payload": json.dumps(payload or {"title": "P", "slug": "p"})}
    return client.post("/api/v1/admin/projects/upload", data=data, files=files)


def test_upload_unsupported_mime_422(client) -> None:
    _login(client)
    response = _project_upload(client, cover_file=("x.exe", b"MZ", "application/x-msdownload"))
    assert response.status_code == 422


def test_upload_svg_rejected_422(client) -> None:
    _login(client)
    svg = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    response = _project_upload(client, cover_file=("evil.svg", svg, "image/svg+xml"))
    assert response.status_code == 422


def test_upload_oversize_413(client) -> None:
    _login(client)
    response = _project_upload(client, cover_file=("big.png", b"x" * (MAX_SIZE + 1), "image/png"))
    assert response.status_code == 413


def test_upload_spoofed_image_content_422(client) -> None:
    _login(client)
    response = _project_upload(
        client, cover_file=("fake.png", b"not-an-image", "image/png")
    )
    assert response.status_code == 422


def test_upload_png_declared_as_jpeg_422(client) -> None:
    _login(client)
    response = _project_upload(
        client, cover_file=("fake.jpg", media_fixtures.PNG, "image/jpeg")
    )
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Rollback: no orphan media on a failed commit
# --------------------------------------------------------------------------- #
def test_no_orphan_media_when_entity_commit_fails(client) -> None:
    """A bad category id fails validation before files are stored."""
    _login(client)
    before = _media_count()
    response = _project_upload(
        client,
        payload={"title": "P", "slug": "p", "category_ids": [str(uuid.uuid4())]},
        cover_file=("c.png", media_fixtures.PNG, "image/png"),
    )
    assert response.status_code == 422
    assert _media_count() == before


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
def test_unauth_401(client) -> None:
    assert client.post("/api/v1/admin/projects/upload", data={"payload": "{}"}).status_code == 401


@pytest.mark.parametrize("role", ["user", "client"])
def test_user_and_client_forbidden(client, role) -> None:
    _login(client, f"{role}@example.com", role)
    assert client.post("/api/v1/admin/projects/upload", data={"payload": "{}"}).status_code == 403

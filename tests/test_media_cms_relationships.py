import asyncio
import uuid

import asyncpg
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from tests import media_fixtures


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


def _upload_media(client, *, mime: str, content: bytes, filename: str) -> str:
    response = client.post("/api/v1/admin/files", files={"file": (filename, content, mime)})
    assert response.status_code == 201, response.text
    return response.json()["id"]


# --------------------------------------------------------------------------- #
# Project -> Media
# --------------------------------------------------------------------------- #
def test_project_create_with_cover_and_demo_video(client) -> None:
    _login(client)
    cover_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")
    video_id = _upload_media(client, mime="video/mp4", content=media_fixtures.MP4, filename="v.mp4")

    response = client.post(
        "/api/v1/admin/projects",
        json={
            "title": "AI Dashboard",
            "slug": "ai-dashboard",
            "cover_media_id": cover_id,
            "demo_video_media_id": video_id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["cover_media_id"] == cover_id
    assert body["cover_media"]["id"] == cover_id
    assert body["cover_media"]["media_type"] == "image"
    assert body["cover_media"]["url"].startswith("/media/")
    assert body["cover_image"] == body["cover_media"]["url"]
    assert body["demo_video_media_id"] == video_id
    assert body["demo_video"]["id"] == video_id
    assert body["demo_video"]["mime_type"] == "video/mp4"
    assert body["demo_video_type"] == "upload"
    assert body["demo_video_url"] == body["demo_video"]["url"]


def test_project_update_unlinks_cover_media(client) -> None:
    _login(client)
    cover_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")
    project = client.post(
        "/api/v1/admin/projects",
        json={"title": "P", "slug": "p", "cover_media_id": cover_id},
    ).json()
    project_id = project["id"]

    updated = client.patch(f"/api/v1/admin/projects/{project_id}", json={"cover_media_id": None})
    assert updated.status_code == 200
    body = updated.json()
    assert body["cover_media_id"] is None
    assert body["cover_media"] is None
    assert body["cover_image"] is None


def test_project_create_invalid_cover_media_422(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects",
        json={"title": "P", "slug": "p", "cover_media_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_project_patch_invalid_cover_media_422(client) -> None:
    _login(client)
    project = client.post("/api/v1/admin/projects", json={"title": "P", "slug": "p"}).json()
    response = client.patch(
        f"/api/v1/admin/projects/{project['id']}",
        json={"cover_media_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_project_legacy_string_fields_still_work(client) -> None:
    _login(client)
    response = client.post(
        "/api/v1/admin/projects",
        json={
            "title": "Legacy",
            "slug": "legacy",
            "cover_image": "/media/legacy-cover.png",
            "demo_video_url": "https://www.youtube.com/watch?v=abc123",
            "demo_video_type": "youtube",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["cover_image"] == "/media/legacy-cover.png"
    assert body["cover_media_id"] is None
    assert body["demo_video_url"] == "https://www.youtube.com/watch?v=abc123"
    assert body["demo_video_type"] == "youtube"
    assert body["demo_video"] is None


# --------------------------------------------------------------------------- #
# Solution -> Media
# --------------------------------------------------------------------------- #
def test_solution_create_with_image_and_demo_video(client) -> None:
    _login(client)
    image_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="s.png")
    video_id = _upload_media(
        client, mime="video/webm", content=media_fixtures.WEBM, filename="s.webm"
    )

    response = client.post(
        "/api/v1/admin/solutions",
        json={
            "name": "E-commerce",
            "slug": "ecommerce",
            "image_media_id": image_id,
            "demo_video_media_id": video_id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["image_media_id"] == image_id
    assert body["image_media"]["id"] == image_id
    assert body["image_url"] == body["image_media"]["url"]
    assert body["demo_video_media_id"] == video_id
    assert body["demo_video"]["mime_type"] == "video/webm"
    assert body["demo_video_type"] == "upload"


# --------------------------------------------------------------------------- #
# CaseStudy -> Media
# --------------------------------------------------------------------------- #
def test_case_study_create_with_image(client) -> None:
    _login(client)
    image_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")

    response = client.post(
        "/api/v1/admin/case-studies",
        json={"title": "CS", "slug": "cs", "image_media_id": image_id},
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["image_media_id"] == image_id
    assert body["image_media"]["id"] == image_id
    assert body["image_url"] == body["image_media"]["url"]


def test_case_study_update_unlinks_image(client) -> None:
    _login(client)
    image_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")
    cs = client.post(
        "/api/v1/admin/case-studies",
        json={"title": "CS", "slug": "cs", "image_media_id": image_id},
    ).json()

    updated = client.patch(f"/api/v1/admin/case-studies/{cs['id']}", json={"image_media_id": None})
    assert updated.status_code == 200
    body = updated.json()
    assert body["image_media_id"] is None
    assert body["image_media"] is None
    assert body["image_url"] is None


# --------------------------------------------------------------------------- #
# TeamMember -> Media
# --------------------------------------------------------------------------- #
def test_team_member_create_with_avatar(client) -> None:
    _login(client)
    avatar_id = _upload_media(
        client, mime="image/png", content=media_fixtures.PNG, filename="a.png"
    )

    response = client.post(
        "/api/v1/admin/team-members",
        json={
            "name": "Sarah Khan",
            "slug": "sarah-khan",
            "role": "CEO",
            "avatar_media_id": avatar_id,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["avatar_media_id"] == avatar_id
    assert body["avatar_media"]["id"] == avatar_id
    assert body["avatar_url"] == body["avatar_media"]["url"]


# --------------------------------------------------------------------------- #
# Public API nested media
# --------------------------------------------------------------------------- #
def test_public_api_exposes_nested_media(client) -> None:
    _login(client)
    cover_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")
    client.post(
        "/api/v1/admin/projects",
        json={"title": "Public", "slug": "public", "cover_media_id": cover_id, "published": True},
    )

    project = client.get("/api/v1/projects/public").json()
    assert project["cover_media"]["id"] == cover_id
    assert project["cover_media"]["url"].startswith("/media/")
    assert project["cover_media"]["media_type"] == "image"
    assert project["cover_media"]["width"] == 16
    # Internal fields are never exposed publicly.
    assert "cover_media_id" not in project
    assert "storage_key" not in project["cover_media"]
    assert "uploaded_by" not in project["cover_media"]


# --------------------------------------------------------------------------- #
# Deletion safety
# --------------------------------------------------------------------------- #
def test_delete_media_referenced_by_project_409(client) -> None:
    _login(client)
    cover_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")
    client.post(
        "/api/v1/admin/projects",
        json={"title": "P", "slug": "p", "cover_media_id": cover_id},
    )

    response = client.delete(f"/api/v1/admin/files/{cover_id}")
    assert response.status_code == 409
    assert "referenced" in response.json()["detail"].lower()

    # Media row is still present (no broken reference was created).
    detail = client.get(f"/api/v1/admin/files/{cover_id}")
    assert detail.status_code == 200


def test_delete_media_after_unlink_succeeds(client) -> None:
    _login(client)
    cover_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")
    project = client.post(
        "/api/v1/admin/projects",
        json={"title": "P", "slug": "p", "cover_media_id": cover_id},
    ).json()
    client.patch(f"/api/v1/admin/projects/{project['id']}", json={"cover_media_id": None})

    assert client.delete(f"/api/v1/admin/files/{cover_id}").status_code == 204


def test_delete_media_referenced_by_team_member_409(client) -> None:
    _login(client)
    avatar_id = _upload_media(
        client, mime="image/png", content=media_fixtures.PNG, filename="a.png"
    )
    client.post(
        "/api/v1/admin/team-members",
        json={"name": "N", "slug": "n", "role": "R", "avatar_media_id": avatar_id},
    )

    response = client.delete(f"/api/v1/admin/files/{avatar_id}")
    assert response.status_code == 409
    assert "team_members" in response.json()["detail"]


def test_referencing_non_media_type_is_not_enforced_at_link_time(client) -> None:
    """Linking is by Media id; media_type constraints are enforced at upload."""
    _login(client)
    video_id = _upload_media(client, mime="video/mp4", content=media_fixtures.MP4, filename="v.mp4")
    response = client.post(
        "/api/v1/admin/projects",
        json={"title": "P", "slug": "p", "cover_media_id": video_id},
    )
    assert response.status_code == 201
    assert response.json()["cover_media"]["media_type"] == "video"


def test_linked_media_is_canonical_over_conflicting_legacy_url(client) -> None:
    """When both a media FK and a conflicting legacy URL are sent, the media
    wins and the legacy column is mirrored from the linked media."""
    _login(client)
    cover_id = _upload_media(client, mime="image/png", content=media_fixtures.PNG, filename="c.png")
    response = client.post(
        "/api/v1/admin/projects",
        json={
            "title": "P",
            "slug": "p",
            "cover_media_id": cover_id,
            "cover_image": "/media/other-url.png",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["cover_media"]["id"] == cover_id
    assert body["cover_image"] == body["cover_media"]["url"]
    assert body["cover_image"] != "/media/other-url.png"

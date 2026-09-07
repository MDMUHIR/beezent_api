import asyncio
import uuid
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.models import Media
from tests import media_fixtures
from tests._db import run_db


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


def _login(client, email: str, role: str = "staff") -> None:
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


def _seed(*objects) -> None:
    async def insert(session) -> None:
        session.add_all(objects)
        await session.commit()

    run_db(insert)


def _media(storage_key: str, **kwargs) -> Media:
    mime_type = kwargs.pop("mime_type", "image/png")
    media_type = kwargs.pop("media_type", "image" if mime_type.startswith("image/") else "video")
    return Media(
        original_name=kwargs.pop("original_name", "photo.png"),
        storage_key=storage_key,
        mime_type=mime_type,
        media_type=media_type,
        size=kwargs.pop("size", 1024),
        **kwargs,
    )


def _media_id(storage_key: str) -> str:
    rows = _db_rows("SELECT id FROM media WHERE storage_key = $1", storage_key)
    assert len(rows) == 1
    return str(rows[0]["id"])


MEDIA_ROOT = Path(get_settings().media_root)


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_unauthenticated_401(client, method) -> None:
    media_id = str(uuid.uuid4())
    kwargs = {"json": {"alt_text": "x"}} if method == "patch" else {}
    assert client.request(method, f"/api/v1/admin/files/{media_id}", **kwargs).status_code == 401
    assert client.get("/api/v1/admin/files").status_code == 401


@pytest.mark.parametrize("role", ["user", "client"])
def test_user_and_client_forbidden(client, role) -> None:
    _login(client, f"{role}@example.com", role)
    assert client.get("/api/v1/admin/files").status_code == 403
    assert client.get(f"/api/v1/admin/files/{uuid.uuid4()}").status_code == 403
    assert (
        client.patch(f"/api/v1/admin/files/{uuid.uuid4()}", json={"alt_text": "x"}).status_code
        == 403
    )
    assert client.delete(f"/api/v1/admin/files/{uuid.uuid4()}").status_code == 403


@pytest.mark.parametrize("role", ["staff", "admin"])
def test_staff_and_admin_allowed(client, role) -> None:
    _login(client, f"{role}@example.com", role)
    assert client.get("/api/v1/admin/files").status_code == 200


# --------------------------------------------------------------------------- #
# Admin CRUD
# --------------------------------------------------------------------------- #
def test_list_and_detail(client) -> None:
    _seed(_media("abc.png", original_name="Banner", folder="projects", alt_text="A banner"))
    _seed(_media("def.png", original_name="Logo", mime_type="image/png"))
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/files").json()
    assert body["total"] == 2
    by_name = {item["original_name"]: item for item in body["items"]}
    assert by_name["Banner"]["folder"] == "projects"
    assert by_name["Banner"]["alt_text"] == "A banner"
    assert by_name["Logo"]["storage_key"] == "def.png"
    assert by_name["Banner"]["media_type"] == "image"

    detail = client.get(f"/api/v1/admin/files/{_media_id('abc.png')}").json()
    assert detail["original_name"] == "Banner"


def test_patch_metadata_only(client) -> None:
    _seed(_media("abc.png", original_name="Banner"))
    _login(client, "staff@example.com", "staff")
    media_id = _media_id("abc.png")
    response = client.patch(
        f"/api/v1/admin/files/{media_id}",
        json={"alt_text": "  Updated alt  ", "folder": "case-studies"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["alt_text"] == "Updated alt"
    assert body["folder"] == "case-studies"
    assert body["storage_key"] == "abc.png"
    assert body["original_name"] == "Banner"


def test_patch_empty_body_noop(client) -> None:
    _seed(_media("abc.png", original_name="Banner", folder="projects"))
    _login(client, "staff@example.com", "staff")
    media_id = _media_id("abc.png")
    body = client.patch(f"/api/v1/admin/files/{media_id}", json={}).json()
    assert body["storage_key"] == "abc.png"
    assert body["original_name"] == "Banner"
    assert body["folder"] == "projects"


def test_patch_clear_optional_metadata(client) -> None:
    _seed(_media("abc.png", original_name="Banner", folder="projects", alt_text="Alt"))
    _login(client, "staff@example.com", "staff")
    media_id = _media_id("abc.png")
    body = client.patch(f"/api/v1/admin/files/{media_id}", json={"folder": None}).json()
    assert body["folder"] is None
    assert body["alt_text"] == "Alt"


def test_patch_invalid_folder_422(client) -> None:
    _seed(_media("abc.png"))
    _login(client, "staff@example.com", "staff")
    media_id = _media_id("abc.png")
    assert (
        client.patch(f"/api/v1/admin/files/{media_id}", json={"folder": "has space"}).status_code
        == 422
    )


def test_delete_removes_file_and_row(client) -> None:
    _seed(_media("abc.png"))
    _login(client, "staff@example.com", "staff")
    media_id = _media_id("abc.png")
    (MEDIA_ROOT / "abc.png").write_bytes(b"data")

    assert client.delete(f"/api/v1/admin/files/{media_id}").status_code == 204
    assert client.get(f"/api/v1/admin/files/{media_id}").status_code == 404
    assert not (MEDIA_ROOT / "abc.png").exists()
    assert len(_db_rows("SELECT 1 FROM media WHERE id = $1", media_id)) == 0


def test_delete_missing_storage_object_still_deletes_row(client) -> None:
    _seed(_media("abc.png"))
    _login(client, "staff@example.com", "staff")
    media_id = _media_id("abc.png")
    assert client.delete(f"/api/v1/admin/files/{media_id}").status_code == 204
    assert client.get(f"/api/v1/admin/files/{media_id}").status_code == 404


def test_unknown_id_404(client) -> None:
    _login(client, "staff@example.com", "staff")
    fake = str(uuid.uuid4())
    assert client.get(f"/api/v1/admin/files/{fake}").status_code == 404
    assert client.patch(f"/api/v1/admin/files/{fake}", json={"alt_text": "x"}).status_code == 404
    assert client.delete(f"/api/v1/admin/files/{fake}").status_code == 404


def test_malformed_uuid_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    assert client.get("/api/v1/admin/files/not-a-uuid").status_code == 422
    assert client.patch("/api/v1/admin/files/not-a-uuid", json={"alt_text": "x"}).status_code == 422
    assert client.delete("/api/v1/admin/files/not-a-uuid").status_code == 422


# --------------------------------------------------------------------------- #
# Filtering / search / pagination / sorting
# --------------------------------------------------------------------------- #
def test_list_filter_by_folder_and_mime(client) -> None:
    _seed(
        _media("a.png", original_name="A", folder="projects"),
        _media("b.png", original_name="B", folder="avatars"),
        _media("c.jpg", original_name="C", mime_type="image/jpeg"),
    )
    _login(client, "staff@example.com", "staff")
    by_folder = client.get("/api/v1/admin/files", params={"folder": "projects"}).json()
    assert [i["original_name"] for i in by_folder["items"]] == ["A"]

    by_mime = client.get("/api/v1/admin/files", params={"mime_type": "image/jpeg"}).json()
    assert [i["original_name"] for i in by_mime["items"]] == ["C"]


def test_list_filter_by_media_type(client) -> None:
    _seed(
        _media("img.png", original_name="Image"),
        Media(
            original_name="Video",
            storage_key="v.mp4",
            mime_type="video/mp4",
            media_type="video",
            size=100,
        ),
    )
    _login(client, "staff@example.com", "staff")
    images = client.get("/api/v1/admin/files", params={"media_type": "image"}).json()
    assert [i["original_name"] for i in images["items"]] == ["Image"]
    videos = client.get("/api/v1/admin/files", params={"media_type": "video"}).json()
    assert [i["original_name"] for i in videos["items"]] == ["Video"]


def test_list_search(client) -> None:
    _seed(
        _media("a.png", original_name="Hero Banner"),
        _media("b.png", original_name="Logo"),
    )
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/files", params={"q": "banner"}).json()
    assert body["total"] == 1
    assert body["items"][0]["original_name"] == "Hero Banner"


def test_list_pagination(client) -> None:
    _seed(*[_media(f"f{i}.png", original_name=f"file{i}") for i in range(5)])
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/files", params={"page": 1, "page_size": 2}).json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert len(body["items"]) == 2
    assert client.get("/api/v1/admin/files", params={"page": 0}).status_code == 422
    assert client.get("/api/v1/admin/files", params={"page_size": 101}).status_code == 422


def test_list_sort_by_size_and_order(client) -> None:
    _seed(
        _media("s.png", original_name="Small", size=10),
        _media("l.png", original_name="Large", size=1000),
        _media("m.png", original_name="Medium", size=100),
    )
    _login(client, "staff@example.com", "staff")
    asc = client.get("/api/v1/admin/files", params={"sort": "size", "order": "asc"}).json()
    assert [i["original_name"] for i in asc["items"]] == ["Small", "Medium", "Large"]

    desc = client.get("/api/v1/admin/files", params={"sort": "size", "order": "desc"}).json()
    assert [i["original_name"] for i in desc["items"]] == ["Large", "Medium", "Small"]

    assert client.get("/api/v1/admin/files", params={"sort": "bogus"}).status_code == 422


# --------------------------------------------------------------------------- #
# Local media serving
# --------------------------------------------------------------------------- #
def test_seeded_file_served_from_public_url(client) -> None:
    _seed(_media("served.png", original_name="Served"))
    (MEDIA_ROOT / "served.png").write_bytes(media_fixtures.PNG)
    _login(client, "staff@example.com", "staff")

    body = client.get(f"/api/v1/admin/files/{_media_id('served.png')}").json()
    response = client.get(body["public_url"])
    assert response.status_code == 200
    assert response.content == media_fixtures.PNG

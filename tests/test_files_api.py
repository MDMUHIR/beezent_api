import asyncio
import uuid
from pathlib import Path

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.models import Media
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
    return Media(
        original_name=kwargs.pop("original_name", "photo.png"),
        storage_key=storage_key,
        public_url=f"/media/{storage_key}",
        mime_type=kwargs.pop("mime_type", "image/png"),
        size=kwargs.pop("size", 1024),
        **kwargs,
    )


def _media_id(storage_key: str) -> str:
    rows = _db_rows("SELECT id FROM media WHERE storage_key = $1", storage_key)
    assert len(rows) == 1
    return str(rows[0]["id"])


def _user_id(email: str) -> str:
    rows = _db_rows("SELECT id FROM users WHERE email = $1", email)
    assert len(rows) == 1
    return str(rows[0]["id"])


def _upload(client, filename="photo.png", content=b"fake-png-bytes", mime="image/png", **form):
    files = {"file": (filename, content, mime)}
    return client.post("/api/v1/admin/files", files=files, data=form)


MEDIA_ROOT = Path(get_settings().media_root)
MAX_SIZE = get_settings().media_max_size_bytes


# --------------------------------------------------------------------------- #
# Upload happy paths
# --------------------------------------------------------------------------- #
def test_upload_png_with_metadata(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(
        client,
        filename="hero-banner.png",
        content=b"png-bytes",
        mime="image/png",
        folder="projects",
        alt_text="Hero banner",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["original_name"] == "hero-banner.png"
    assert body["mime_type"] == "image/png"
    assert body["size"] == len(b"png-bytes")
    assert body["folder"] == "projects"
    assert body["alt_text"] == "Hero banner"
    assert body["storage_key"].endswith(".png")
    assert body["storage_key"].count(".") == 1
    assert body["public_url"] == f"/media/{body['storage_key']}"
    assert body["uploaded_by"] == _user_id("staff@example.com")
    assert body["width"] is None
    assert body["height"] is None

    assert (MEDIA_ROOT / body["storage_key"]).is_file()
    assert (MEDIA_ROOT / body["storage_key"]).read_bytes() == b"png-bytes"


def test_upload_minimal(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(client, filename="logo.jpg", content=b"jpeg", mime="image/jpeg")
    assert response.status_code == 201
    body = response.json()
    assert body["folder"] is None
    assert body["alt_text"] is None
    assert body["storage_key"].endswith(".jpg")


def test_upload_original_name_sanitized(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(client, filename="../../etc/passwd.png", content=b"x", mime="image/png")
    assert response.status_code == 201
    body = response.json()
    assert body["original_name"] == "passwd.png"
    assert "/" not in body["storage_key"]
    assert ".." not in body["storage_key"]


def test_upload_pdf(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(client, filename="brochure.pdf", content=b"%PDF-1.4", mime="application/pdf")
    assert response.status_code == 201
    assert response.json()["storage_key"].endswith(".pdf")


# --------------------------------------------------------------------------- #
# Upload validation
# --------------------------------------------------------------------------- #
def test_upload_unsupported_mime_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(client, filename="virus.exe", content=b"MZ", mime="application/x-msdownload")
    assert response.status_code == 422


def test_upload_unsupported_text_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(client, filename="notes.txt", content=b"hello", mime="text/plain")
    assert response.status_code == 422


def test_upload_oversize_413(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(client, filename="big.png", content=b"x" * (MAX_SIZE + 1), mime="image/png")
    assert response.status_code == 413


def test_upload_missing_file_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = client.post("/api/v1/admin/files")
    assert response.status_code == 422


def test_upload_invalid_folder_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    for folder in ["../projects", "has space", "UPPER", "bad/folder"]:
        response = _upload(client, folder=folder)
        assert response.status_code == 422, folder


def test_upload_long_alt_text_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = _upload(client, alt_text="x" * 501)
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_unauthenticated_401(client, method) -> None:
    media_id = str(uuid.uuid4())
    kwargs = {"json": {"alt_text": "x"}} if method == "patch" else {}
    assert client.request(method, f"/api/v1/admin/files/{media_id}", **kwargs).status_code == 401
    assert client.get("/api/v1/admin/files").status_code == 401
    assert _upload(client).status_code == 401


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
    assert _upload(client).status_code == 403


@pytest.mark.parametrize("role", ["staff", "admin"])
def test_staff_and_admin_allowed(client, role) -> None:
    _login(client, f"{role}@example.com", role)
    assert client.get("/api/v1/admin/files").status_code == 200
    assert _upload(client, filename="ok.png").status_code == 201


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
def test_uploaded_file_served_from_public_url(client) -> None:
    _login(client, "staff@example.com", "staff")
    body = _upload(client, filename="served.png", content=b"serve-me", mime="image/png").json()
    response = client.get(body["public_url"])
    assert response.status_code == 200
    assert response.content == b"serve-me"

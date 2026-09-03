import asyncio
import uuid

import asyncpg
import pytest
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.models import Lead, LeadStatus
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


def _lead(email: str, **kwargs) -> Lead:
    return Lead(
        name=kwargs.pop("name", "John Doe"),
        email=email,
        message=kwargs.pop("message", "I want to automate our support workflows."),
        **kwargs,
    )


def _lead_id_by_email(email: str) -> str:
    rows = _db_rows("SELECT id FROM leads WHERE email = $1", email)
    assert len(rows) == 1
    return str(rows[0]["id"])


PUBLIC_PAYLOAD = {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+8801XXXXXXXXX",
    "company": "Example Ltd",
    "service": "AI Automation",
    "message": "I want to automate our customer support.",
    "source": "website",
}


# --------------------------------------------------------------------------- #
# Public submission
# --------------------------------------------------------------------------- #
def test_public_submit_minimal(client) -> None:
    response = client.post(
        "/api/v1/leads",
        json={"name": "Alice", "email": "alice@example.com", "message": "Hello, I need AI help."},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["message"] == "Your inquiry has been received."
    assert set(body) == {"id", "message"}


def test_public_submit_full(client) -> None:
    response = client.post("/api/v1/leads", json=PUBLIC_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    row = _db_rows(
        "SELECT name, email, phone, company, service, message, source, status, notes "
        "FROM leads WHERE id = $1",
        body["id"],
    )[0]
    assert row["name"] == "John Doe"
    assert row["email"] == "john@example.com"
    assert row["phone"] == "+8801XXXXXXXXX"
    assert row["company"] == "Example Ltd"
    assert row["service"] == "AI Automation"
    assert row["source"] == "website"
    assert row["status"] == "new"
    assert row["notes"] is None


def test_public_submit_status_always_new(client) -> None:
    response = client.post("/api/v1/leads", json=PUBLIC_PAYLOAD)
    assert response.status_code == 201
    row = _db_rows("SELECT status FROM leads WHERE id = $1", response.json()["id"])[0]
    assert row["status"] == "new"


def test_public_response_no_internal_fields(client) -> None:
    response = client.post("/api/v1/leads", json=PUBLIC_PAYLOAD)
    body = response.json()
    for key in ("status", "notes", "email", "name", "message_body", "created_at", "updated_at"):
        assert key not in body, key


# --------------------------------------------------------------------------- #
# Public validation
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "payload",
    [
        {"email": "a@b.com", "message": "long enough message here"},
        {"name": "X", "message": "long enough message here"},
        {"name": "X", "email": "a@b.com"},
    ],
)
def test_missing_required_fields_422(client, payload) -> None:
    assert client.post("/api/v1/leads", json=payload).status_code == 422


def test_invalid_email_422(client) -> None:
    payload = {**PUBLIC_PAYLOAD, "email": "not-an-email"}
    assert client.post("/api/v1/leads", json=payload).status_code == 422


@pytest.mark.parametrize("message", ["short", "", "          "])
def test_message_too_short_or_blank_422(client, message) -> None:
    payload = {**PUBLIC_PAYLOAD, "message": message}
    assert client.post("/api/v1/leads", json=payload).status_code == 422


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", "x" * 256),
        ("email", f"{'a' * 250}@example.com"),
        ("phone", "1" * 51),
        ("company", "x" * 256),
        ("service", "x" * 256),
        ("message", "x" * 5001),
        ("source", "x" * 101),
    ],
)
def test_oversized_fields_422(client, field, value) -> None:
    payload = {**PUBLIC_PAYLOAD, field: value}
    assert client.post("/api/v1/leads", json=payload).status_code == 422


def test_empty_optional_fields_ok(client) -> None:
    payload = {"name": "Alice", "email": "a@b.com", "message": "long enough message here"}
    assert client.post("/api/v1/leads", json=payload).status_code == 201


def test_null_optional_fields_ok(client) -> None:
    payload = {
        **PUBLIC_PAYLOAD,
        "phone": None,
        "company": None,
        "service": None,
        "source": None,
    }
    assert client.post("/api/v1/leads", json=payload).status_code == 201


def test_unicode_name_and_company_accepted(client) -> None:
    payload = {
        **PUBLIC_PAYLOAD,
        "name": "José María García",
        "company": "株式会社ベーゼンツ",
        "message": "Möchten Sie unsere Dienste kennenlernen? Wir freuen uns auf Ihre Nachricht.",
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201


def test_whitespace_and_case_normalized(client) -> None:
    payload = {
        "name": "  John  ",
        "email": "  JOHN@Example.COM ",
        "message": "  Please contact me about automation.  ",
        "company": "  Acme  ",
    }
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201
    row = _db_rows(
        "SELECT name, email, company, message FROM leads WHERE id = $1", response.json()["id"]
    )[0]
    assert row["name"] == "John"
    assert row["email"] == "john@example.com"
    assert row["company"] == "Acme"
    assert row["message"] == "Please contact me about automation."


def test_very_long_message_accepted(client) -> None:
    payload = {**PUBLIC_PAYLOAD, "message": "x" * 5000}
    assert client.post("/api/v1/leads", json=payload).status_code == 201


# --------------------------------------------------------------------------- #
# Mass assignment protection
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "converted"),
        ("notes", "internal note injection"),
        ("id", str(uuid.uuid4())),
        ("created_at", "2020-01-01T00:00:00Z"),
        ("updated_at", "2020-01-01T00:00:00Z"),
    ],
)
def test_client_cannot_inject_internal_fields(client, field, value) -> None:
    payload = {**PUBLIC_PAYLOAD, field: value}
    response = client.post("/api/v1/leads", json=payload)
    assert response.status_code == 201
    row = _db_rows(
        "SELECT status, notes, created_at, updated_at FROM leads WHERE id = $1",
        response.json()["id"],
    )[0]
    assert row["status"] == "new"
    assert row["notes"] is None
    assert row["created_at"] is not None
    assert row["updated_at"] is not None
    assert response.json()["id"] != value


def test_no_public_lead_list_endpoint(client) -> None:
    response = client.get("/api/v1/leads")
    assert response.status_code in (404, 405)


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("method", ["get", "patch", "delete"])
def test_unauthenticated_admin_401(client, method) -> None:
    lead_id = str(uuid.uuid4())
    kwargs = {"json": {"status": "new"}} if method == "patch" else {}
    assert client.request(method, f"/api/v1/admin/leads/{lead_id}", **kwargs).status_code == 401
    assert client.get("/api/v1/admin/leads").status_code == 401


@pytest.mark.parametrize("role", ["user", "client"])
def test_user_and_client_forbidden(client, role) -> None:
    _login(client, f"{role}@example.com", role)
    assert client.get("/api/v1/admin/leads").status_code == 403
    assert client.get(f"/api/v1/admin/leads/{uuid.uuid4()}").status_code == 403
    assert (
        client.patch(
            f"/api/v1/admin/leads/{uuid.uuid4()}", json={"status": "contacted"}
        ).status_code
        == 403
    )
    assert client.delete(f"/api/v1/admin/leads/{uuid.uuid4()}").status_code == 403


@pytest.mark.parametrize("role", ["staff", "admin"])
def test_staff_and_admin_allowed(client, role) -> None:
    _seed(_lead("staff@example.com"))
    _login(client, f"{role}@example.com", role)
    assert client.get("/api/v1/admin/leads").status_code == 200
    lead_id = _lead_id_by_email("staff@example.com")
    assert client.get(f"/api/v1/admin/leads/{lead_id}").status_code == 200
    assert (
        client.patch(f"/api/v1/admin/leads/{lead_id}", json={"status": "contacted"}).status_code
        == 200
    )
    assert client.delete(f"/api/v1/admin/leads/{lead_id}").status_code == 204


# --------------------------------------------------------------------------- #
# Admin CRUD
# --------------------------------------------------------------------------- #
def test_admin_list_and_detail_include_internal_fields(client) -> None:
    _seed(_lead("alice@example.com", notes="Internal note"))
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/leads").json()
    assert body["total"] == 1
    item = body["items"][0]
    assert item["email"] == "alice@example.com"
    assert item["status"] == "new"
    assert item["notes"] == "Internal note"
    assert "created_at" in item
    assert "updated_at" in item

    detail = client.get(f"/api/v1/admin/leads/{item['id']}").json()
    assert detail["notes"] == "Internal note"


def test_admin_patch_partial_update(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    response = client.patch(
        f"/api/v1/admin/leads/{lead_id}", json={"status": "contacted", "notes": "  Called client  "}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "contacted"
    assert body["notes"] == "Called client"
    assert body["name"] == "John Doe"
    assert body["email"] == "alice@example.com"


def test_admin_patch_empty_body_noop(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    body = client.patch(f"/api/v1/admin/leads/{lead_id}", json={}).json()
    assert body["status"] == "new"
    assert body["name"] == "John Doe"
    assert body["email"] == "alice@example.com"


def test_admin_patch_status_transitions(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    for status in ["contacted", "qualified", "converted"]:
        body = client.patch(f"/api/v1/admin/leads/{lead_id}", json={"status": status}).json()
        assert body["status"] == status


def test_admin_patch_qualified_to_lost(client) -> None:
    _seed(_lead("alice@example.com", status=LeadStatus.QUALIFIED))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    body = client.patch(f"/api/v1/admin/leads/{lead_id}", json={"status": "lost"}).json()
    assert body["status"] == "lost"


def test_admin_patch_invalid_status_422(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    assert (
        client.patch(f"/api/v1/admin/leads/{lead_id}", json={"status": "spammy"}).status_code == 422
    )


def test_admin_patch_invalid_email_422(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    assert (
        client.patch(f"/api/v1/admin/leads/{lead_id}", json={"email": "not-an-email"}).status_code
        == 422
    )


def test_admin_patch_null_required_field_422(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    assert client.patch(f"/api/v1/admin/leads/{lead_id}", json={"name": None}).status_code == 422


def test_admin_delete(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    lead_id = _lead_id_by_email("alice@example.com")
    assert client.delete(f"/api/v1/admin/leads/{lead_id}").status_code == 204
    assert client.get(f"/api/v1/admin/leads/{lead_id}").status_code == 404
    assert len(_db_rows("SELECT 1 FROM leads WHERE id = $1", lead_id)) == 0


def test_admin_unknown_lead_404(client) -> None:
    _login(client, "staff@example.com", "staff")
    fake = str(uuid.uuid4())
    assert client.get(f"/api/v1/admin/leads/{fake}").status_code == 404
    assert client.patch(f"/api/v1/admin/leads/{fake}", json={"status": "new"}).status_code == 404
    assert client.delete(f"/api/v1/admin/leads/{fake}").status_code == 404


def test_admin_malformed_uuid_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    assert client.get("/api/v1/admin/leads/not-a-uuid").status_code == 422
    assert client.patch("/api/v1/admin/leads/not-a-uuid", json={"status": "new"}).status_code == 422
    assert client.delete("/api/v1/admin/leads/not-a-uuid").status_code == 422


# --------------------------------------------------------------------------- #
# Admin filtering / search / pagination / sorting
# --------------------------------------------------------------------------- #
def test_admin_list_status_filter(client) -> None:
    _seed(
        _lead("new@example.com", status=LeadStatus.NEW),
        _lead("contacted@example.com", status=LeadStatus.CONTACTED),
        _lead("converted@example.com", status=LeadStatus.CONVERTED),
    )
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/leads", params={"status": "contacted"}).json()
    assert body["total"] == 1
    assert body["items"][0]["email"] == "contacted@example.com"


def test_admin_list_status_filter_invalid_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    assert client.get("/api/v1/admin/leads", params={"status": "bogus"}).status_code == 422


def test_admin_list_search(client) -> None:
    _seed(
        _lead("alice@example.com", name="Alice Wonderland", company="Acme"),
        _lead("bob@example.com", name="Bob Builder", company="Beta"),
    )
    _login(client, "staff@example.com", "staff")
    by_name = client.get("/api/v1/admin/leads", params={"q": "wonder"}).json()
    assert [i["email"] for i in by_name["items"]] == ["alice@example.com"]

    by_company = client.get("/api/v1/admin/leads", params={"q": "beta"}).json()
    assert [i["email"] for i in by_company["items"]] == ["bob@example.com"]

    by_email = client.get("/api/v1/admin/leads", params={"q": "alice@"}).json()
    assert by_email["total"] == 1


def test_admin_list_search_no_match(client) -> None:
    _seed(_lead("alice@example.com"))
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/leads", params={"q": "zzznothing"}).json()
    assert body["total"] == 0
    assert body["items"] == []


def test_admin_list_search_special_characters(client) -> None:
    _seed(_lead("alice@example.com", message="We achieved a 100% ROI within a quarter."))
    _login(client, "staff@example.com", "staff")
    response = client.get("/api/v1/admin/leads", params={"q": "100%"})
    assert response.status_code == 200
    response = client.get("/api/v1/admin/leads", params={"q": "%_[]"})
    assert response.status_code == 200


def test_admin_list_pagination(client) -> None:
    _seed(*[_lead(f"lead{i}@example.com") for i in range(5)])
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/leads", params={"page": 1, "page_size": 2}).json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert len(body["items"]) == 2

    page3 = client.get("/api/v1/admin/leads", params={"page": 3, "page_size": 2}).json()
    assert len(page3["items"]) == 1

    assert client.get("/api/v1/admin/leads", params={"page": 0}).status_code == 422
    assert client.get("/api/v1/admin/leads", params={"page_size": 101}).status_code == 422


def test_admin_list_default_sort_newest_first(client) -> None:
    from datetime import UTC, datetime

    _seed(
        _lead("old@example.com", created_at=datetime(2020, 1, 1, tzinfo=UTC)),
        _lead("new@example.com", created_at=datetime(2024, 1, 1, tzinfo=UTC)),
        _lead("mid@example.com", created_at=datetime(2022, 1, 1, tzinfo=UTC)),
    )
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/leads").json()
    assert [i["email"] for i in body["items"]] == [
        "new@example.com",
        "mid@example.com",
        "old@example.com",
    ]


def test_admin_list_sort_by_name_and_order(client) -> None:
    _seed(
        _lead("z@example.com", name="Zulu"),
        _lead("a@example.com", name="Alpha"),
        _lead("m@example.com", name="Mike"),
    )
    _login(client, "staff@example.com", "staff")
    asc = client.get("/api/v1/admin/leads", params={"sort": "name", "order": "asc"}).json()
    assert [i["name"] for i in asc["items"]] == ["Alpha", "Mike", "Zulu"]

    desc = client.get("/api/v1/admin/leads", params={"sort": "name", "order": "desc"}).json()
    assert [i["name"] for i in desc["items"]] == ["Zulu", "Mike", "Alpha"]

    assert client.get("/api/v1/admin/leads", params={"sort": "bogus"}).status_code == 422

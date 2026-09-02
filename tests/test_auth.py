import asyncio

import asyncpg
from sqlalchemy.engine import make_url

from app.core.config import get_settings


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


def _get_user(email: str) -> asyncpg.Record:
    rows = _db_rows(
        "SELECT email, password_hash, role, is_active, is_verified FROM users WHERE email = $1",
        email,
    )
    assert len(rows) == 1
    return rows[0]


def _set_user_role(email: str, role: str) -> None:
    _db_rows("UPDATE users SET role = $1 WHERE email = $2", role, email)


def _set_user_active(email: str, active: bool) -> None:
    _db_rows("UPDATE users SET is_active = $1 WHERE email = $2", active, email)


def _session_count() -> int:
    rows = _db_rows("SELECT count(*) AS n FROM user_sessions")
    return rows[0]["n"]


REGISTER_PAYLOAD = {
    "email": "user@example.com",
    "password": "strong-password",
    "full_name": "Example User",
}


def test_register_success(client) -> None:
    response = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["full_name"] == "Example User"
    assert body["role"] == "user"
    assert body["id"]
    assert "password_hash" not in body
    assert "password" not in body

    row = _get_user("user@example.com")
    assert row["role"] == "user"
    assert row["password_hash"].startswith("$argon2id$")
    assert row["password_hash"] != "strong-password"


def test_register_normalizes_email(client) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "  Mixed.Case@Example.COM ",
            "password": "strong-password",
            "full_name": "Mixed Case",
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "mixed.case@example.com"


def test_register_duplicate_email_rejected(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    assert response.status_code == 409
    assert response.json()["detail"] == "An account with this email already exists"


def test_register_invalid_data_rejected(client) -> None:
    cases = [
        {"email": "not-an-email", "password": "strong-password", "full_name": "X"},
        {"email": "a@b.com", "password": "short", "full_name": "X"},
        {"email": "a@b.com", "password": "strong-password", "full_name": ""},
        {"email": "a@b.com", "password": "strong-password"},  # missing full_name
    ]
    for payload in cases:
        response = client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 422, payload


def test_register_cannot_assign_role(client) -> None:
    payload = {**REGISTER_PAYLOAD, "role": "admin"}
    payload["email"] = "hacker@example.com"
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["role"] == "user"
    assert _get_user("hacker@example.com")["role"] == "user"


def test_login_success(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "user@example.com"
    assert body["last_login_at"] is not None
    assert "password_hash" not in body
    assert response.cookies.get("beezents_session")


def test_login_incorrect_credentials_fail(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    for payload in (
        {"email": "user@example.com", "password": "wrong-password"},
        {"email": "unknown@example.com", "password": "strong-password"},
    ):
        response = client.post("/api/v1/auth/login", json=payload)
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid email or password"


def test_unauthenticated_me_rejected(client) -> None:
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_me_authenticated(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == "user@example.com"
    assert response.json()["role"] == "user"


def test_logout_invalidates_session(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    assert client.get("/api/v1/auth/me").status_code == 200
    assert _session_count() == 1

    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    assert _session_count() == 0
    assert client.get("/api/v1/auth/me").status_code == 401


def test_normal_user_cannot_access_staff_or_admin(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    assert client.get("/api/v1/dev/staff").status_code == 403
    assert client.get("/api/v1/dev/admin").status_code == 403


def test_staff_role_checks(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    _set_user_role("user@example.com", "staff")
    client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    staff_response = client.get("/api/v1/dev/staff")
    assert staff_response.status_code == 200
    assert staff_response.json()["role"] == "staff"
    assert client.get("/api/v1/dev/admin").status_code == 403


def test_admin_role_checks(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    _set_user_role("user@example.com", "admin")
    client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    admin_response = client.get("/api/v1/dev/admin")
    assert admin_response.status_code == 200
    assert admin_response.json()["role"] == "admin"
    assert client.get("/api/v1/dev/staff").status_code == 200


def test_inactive_user_cannot_login(client) -> None:
    client.post("/api/v1/auth/register", json=REGISTER_PAYLOAD)
    _set_user_active("user@example.com", False)
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "strong-password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"

import asyncio
from datetime import UTC, datetime, timedelta

import asyncpg
from fastapi.testclient import TestClient
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.core.database import get_session
from app.core.security import hash_session_token
from app.main import app
from app.models import User, UserSession
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


def _session_count() -> int:
    return _db_rows("SELECT count(*) AS n FROM user_sessions")[0]["n"]


def _seed_expired_session() -> None:
    async def insert(session) -> None:
        user = User(email="expired@example.com", password_hash="x", full_name="Expired User")
        session.add(user)
        await session.commit()
        session.add(
            UserSession(
                user_id=user.id,
                token_hash=hash_session_token("expired-token"),
                expires_at=datetime.now(UTC) - timedelta(hours=1),
            )
        )
        await session.commit()

    run_db(insert)


def _register_and_login(client, email: str = "user@example.com") -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "strong-password", "full_name": "Security User"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "strong-password"},
    )
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Security headers
# --------------------------------------------------------------------------- #
def test_security_headers_present_on_success(client) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"
    assert response.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert response.headers.get("permissions-policy")


def test_security_headers_present_on_errors(client) -> None:
    response = client.get("/api/v1/does-not-exist")
    assert response.status_code == 404
    assert response.headers.get("x-content-type-options") == "nosniff"


# --------------------------------------------------------------------------- #
# CORS (enabled in tests via CORS_ALLOWED_ORIGINS)
# --------------------------------------------------------------------------- #
def test_cors_allowed_origin(client) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://localhost:3000"})
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin(client) -> None:
    response = client.get("/api/v1/health", headers={"Origin": "http://evil.com"})
    assert response.headers.get("access-control-allow-origin") is None


def test_cors_preflight_allowed(client) -> None:
    response = client.options(
        "/api/v1/leads",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


# --------------------------------------------------------------------------- #
# Trusted hosts (enabled in tests via TRUSTED_HOSTS)
# --------------------------------------------------------------------------- #
def test_untrusted_host_rejected(client) -> None:
    response = client.get("/api/v1/health", headers={"Host": "evil.com"})
    assert response.status_code == 400


def test_trusted_host_accepted(client) -> None:
    response = client.get("/api/v1/health", headers={"Host": "localhost"})
    assert response.status_code == 200


# --------------------------------------------------------------------------- #
# Error leakage
# --------------------------------------------------------------------------- #
def test_malformed_json_safe_422(client) -> None:
    response = client.post(
        "/api/v1/leads", content="{not json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
    body = response.json()
    assert "detail" in body
    assert "Traceback" not in response.text
    assert "Exception" not in body


def test_unexpected_fields_do_not_crash(client) -> None:
    response = client.post(
        "/api/v1/leads",
        json={
            "name": "Jane",
            "email": "jane@example.com",
            "message": "Please contact me about AI.",
            "status": "converted",
            "notes": "injected",
            "role": "admin",
        },
    )
    assert response.status_code == 201


def test_unhandled_exception_returns_safe_500() -> None:
    async def broken() -> object:
        raise RuntimeError("database password hunter2 leaked in memory")
        yield  # pragma: no cover

    app.dependency_overrides[get_session] = broken
    try:
        with TestClient(app, raise_server_exceptions=False) as test_client:
            response = test_client.get("/api/v1/projects")
            assert response.status_code == 500
            assert response.json() == {"detail": "Internal Server Error"}
            assert "hunter2" not in response.text
            assert "Traceback" not in response.text
            assert response.headers.get("x-content-type-options") == "nosniff"
    finally:
        app.dependency_overrides.clear()


def test_validation_error_has_no_internal_details(client) -> None:
    response = client.post("/api/v1/leads", json={"name": "X", "email": "nope"})
    assert response.status_code == 422
    assert "Traceback" not in response.text


# --------------------------------------------------------------------------- #
# Session / cookie hardening
# --------------------------------------------------------------------------- #
def test_session_cookie_flags(client) -> None:
    client.post(
        "/api/v1/auth/register",
        json={"email": "flags@example.com", "password": "strong-password", "full_name": "Flags"},
    )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "flags@example.com", "password": "strong-password"},
    )
    header = response.headers.get("set-cookie", "")
    assert "beezents_session=" in header
    assert "HttpOnly" in header
    assert "SameSite=lax" in header
    assert "Path=/" in header
    assert "Secure" not in header  # dev default


def test_invalid_session_token_rejected(client) -> None:
    client.cookies.set("beezents_session", "garbage-not-a-real-token")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_expired_session_rejected_and_cleaned(client) -> None:
    _seed_expired_session()
    client.cookies.set("beezents_session", "expired-token")
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert _session_count() == 0


def test_logout_clears_session_cookie(client) -> None:
    _register_and_login(client)
    response = client.post("/api/v1/auth/logout")
    assert response.status_code == 204
    cookie = response.headers.get("set-cookie", "")
    assert "beezents_session=" in cookie
    assert _session_count() == 0

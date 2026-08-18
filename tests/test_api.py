import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from main import app


@pytest_asyncio.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_root_status(client):
    resp = await client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "online"
    assert data["docs_url"] == "/api/v1/docs"


@pytest.mark.asyncio
async def test_health_check(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_openapi_schema(client):
    resp = await client.get("/api/v1/openapi.json")
    assert resp.status_code == 200
    schema = resp.json()
    assert "paths" in schema
    assert "/api/v1/auth/login" in schema["paths"]


@pytest.mark.asyncio
async def test_login_with_seeded_admin(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@agency.com", "password": "admin123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["token_type"] == "bearer"
    assert data["access_token"]
    assert data["user"]["email"] == "admin@agency.com"
    assert data["user"]["role"] == "SUPER_ADMIN"


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "admin@agency.com", "password": "wrong-password"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_services(client):
    resp = await client.get("/api/v1/services/")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_admin_login_grants_dashboard_access(client):
    login_page = await client.get("/admin/login")
    assert login_page.status_code == 200
    client.cookies.clear()
    login = await client.post(
        "/admin/login",
        data={"username": "admin@agency.com", "password": "admin123"},
    )
    assert login.status_code == 302
    dashboard = await client.get("/admin/")
    assert dashboard.status_code == 200


@pytest.mark.asyncio
async def test_admin_login_rejects_wrong_password(client):
    client.cookies.clear()
    login = await client.post(
        "/admin/login",
        data={"username": "admin@agency.com", "password": "wrong-password"},
    )
    assert login.status_code == 400
    client.cookies.clear()
    dashboard = await client.get("/admin/")
    assert dashboard.status_code == 302
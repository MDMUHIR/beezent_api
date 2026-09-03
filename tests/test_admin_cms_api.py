import asyncio
import uuid

import asyncpg
import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from app.core.config import get_settings
from app.models import Project
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


def _project(slug: str, **kwargs) -> Project:
    return Project(
        title=kwargs.pop("title", slug.replace("-", " ").title()),
        slug=slug,
        **kwargs,
    )


def _project_id(slug: str) -> str:
    async def q(session) -> str | None:
        return await session.scalar(select(Project.id).where(Project.slug == slug))

    return str(run_db(q))


def _payload(resource: str) -> dict:
    if resource == "projects":
        return {"title": "Project", "slug": "project"}
    if resource == "services":
        return {"name": "Service", "slug": "service"}
    if resource == "solutions":
        return {"name": "Solution", "slug": "solution"}
    return {"title": "Case Study", "slug": "case-study"}


RESOURCES = ["projects", "services", "solutions", "case-studies"]


# --------------------------------------------------------------------------- #
# Authorization
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("method", ["get", "post"])
def test_unauthenticated_requests_401(client, resource, method) -> None:
    response = client.request(method, f"/api/v1/admin/{resource}", json=_payload(resource))
    assert response.status_code == 401


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("role", ["user", "client"])
def test_non_staff_roles_forbidden(client, resource, role) -> None:
    _login(client, f"{role}@example.com", role)
    base = f"/api/v1/admin/{resource}"
    assert client.get(base).status_code == 403
    assert client.post(base, json=_payload(resource)).status_code == 403


@pytest.mark.parametrize("resource", RESOURCES)
@pytest.mark.parametrize("role", ["staff", "admin"])
def test_staff_and_admin_allowed(client, resource, role) -> None:
    _login(client, f"{role}@example.com", role)
    base = f"/api/v1/admin/{resource}"
    assert client.get(base).status_code == 200
    assert client.post(base, json=_payload(resource)).status_code == 201


def test_user_forbidden_on_item_endpoints(client) -> None:
    _seed(_project("alpha"))
    project_id = _project_id("alpha")
    _login(client, "user@example.com", "user")
    assert client.get(f"/api/v1/admin/projects/{project_id}").status_code == 403
    assert (
        client.patch(f"/api/v1/admin/projects/{project_id}", json={"title": "X"}).status_code == 403
    )
    assert client.delete(f"/api/v1/admin/projects/{project_id}").status_code == 403


def test_unauthenticated_item_endpoints_401(client) -> None:
    fake = str(uuid.uuid4())
    assert client.get(f"/api/v1/admin/projects/{fake}").status_code == 401
    assert client.patch(f"/api/v1/admin/projects/{fake}", json={"title": "X"}).status_code == 401
    assert client.delete(f"/api/v1/admin/projects/{fake}").status_code == 401


# --------------------------------------------------------------------------- #
# Projects
# --------------------------------------------------------------------------- #
def test_create_project_full_payload(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = client.post(
        "/api/v1/admin/projects",
        json={
            "title": "AI Commerce Platform",
            "slug": "ai-commerce-platform",
            "short_description": "Short",
            "description": "Long description",
            "client_name": "Acme",
            "industry": "Retail",
            "project_type": "E-commerce",
            "status": "completed",
            "featured": True,
            "published": True,
            "cover_image": "https://example.com/cover.jpg",
            "live_url": "https://example.com",
            "github_url": "https://github.com/example",
            "technologies": ["FastAPI", "PostgreSQL"],
            "results": [{"metric": "conversion", "value": "+32%"}],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["status"] == "completed"
    assert body["featured"] is True
    assert body["published"] is True
    assert body["technologies"] == ["FastAPI", "PostgreSQL"]
    assert body["results"] == [{"metric": "conversion", "value": "+32%"}]
    assert "password_hash" not in body


def test_create_project_defaults(client) -> None:
    _login(client, "staff@example.com", "staff")
    body = client.post("/api/v1/admin/projects", json={"title": "Plain", "slug": "plain"}).json()
    assert body["status"] == "active"
    assert body["featured"] is False
    assert body["published"] is False
    assert body["technologies"] == []
    assert body["results"] == []


def test_admin_list_includes_unpublished(client) -> None:
    _seed(_project("alpha", published=True), _project("hidden", published=False))
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/projects").json()
    assert body["total"] == 2
    assert {item["slug"] for item in body["items"]} == {"alpha", "hidden"}

    public = client.get("/api/v1/projects").json()
    assert public["total"] == 1


def test_admin_list_pagination_and_search(client) -> None:
    _seed(*[_project(f"p{i}") for i in range(5)])
    _login(client, "staff@example.com", "staff")
    body = client.get("/api/v1/admin/projects", params={"page": 1, "page_size": 2}).json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert len(body["items"]) == 2

    search = client.get("/api/v1/admin/projects", params={"q": "p3"}).json()
    assert search["total"] == 1
    assert search["items"][0]["slug"] == "p3"


def test_get_project_by_id(client) -> None:
    _seed(_project("alpha", published=True))
    _login(client, "staff@example.com", "staff")
    response = client.get(f"/api/v1/admin/projects/{_project_id('alpha')}")
    assert response.status_code == 200
    assert response.json()["slug"] == "alpha"
    assert response.json()["published"] is True


def test_project_patch_partial_update(client) -> None:
    _seed(_project("alpha"))
    _login(client, "staff@example.com", "staff")
    project_id = _project_id("alpha")
    response = client.patch(
        f"/api/v1/admin/projects/{project_id}", json={"title": "New Title", "published": True}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "New Title"
    assert body["published"] is True
    assert body["slug"] == "alpha"
    assert body["client_name"] is None


def test_delete_project(client) -> None:
    _seed(_project("alpha"))
    _login(client, "staff@example.com", "staff")
    project_id = _project_id("alpha")
    assert client.delete(f"/api/v1/admin/projects/{project_id}").status_code == 204
    assert client.get(f"/api/v1/admin/projects/{project_id}").status_code == 404


def test_duplicate_slug_create_409(client) -> None:
    _seed(_project("alpha"))
    _login(client, "staff@example.com", "staff")
    response = client.post("/api/v1/admin/projects", json={"title": "B", "slug": "alpha"})
    assert response.status_code == 409
    assert "already in use" in response.json()["detail"]


def test_duplicate_slug_case_insensitive_409(client) -> None:
    _seed(_project("alpha"))
    _login(client, "staff@example.com", "staff")
    response = client.post("/api/v1/admin/projects", json={"title": "B", "slug": "ALPHA"})
    assert response.status_code == 409


def test_patch_to_existing_slug_409(client) -> None:
    _seed(_project("alpha"), _project("beta"))
    _login(client, "staff@example.com", "staff")
    beta_id = _project_id("beta")
    response = client.patch(f"/api/v1/admin/projects/{beta_id}", json={"slug": "alpha"})
    assert response.status_code == 409


def test_patch_own_slug_allowed(client) -> None:
    _seed(_project("alpha"))
    _login(client, "staff@example.com", "staff")
    response = client.patch(
        f"/api/v1/admin/projects/{_project_id('alpha')}", json={"slug": "alpha"}
    )
    assert response.status_code == 200
    assert response.json()["slug"] == "alpha"


def test_slug_normalized_on_create(client) -> None:
    _login(client, "staff@example.com", "staff")
    body = client.post("/api/v1/admin/projects", json={"title": "A", "slug": "AI-Commerce"}).json()
    assert body["slug"] == "ai-commerce"


def test_invalid_slug_format_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    for slug in ["Bad Slug", "has_underscore", ""]:
        response = client.post("/api/v1/admin/projects", json={"title": "A", "slug": slug})
        assert response.status_code == 422, slug


def test_create_missing_required_fields_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    assert client.post("/api/v1/admin/projects", json={"slug": "no-title"}).status_code == 422
    assert client.post("/api/v1/admin/projects", json={"title": "No slug"}).status_code == 422


def test_malformed_uuid_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    assert client.get("/api/v1/admin/projects/not-a-uuid").status_code == 422
    assert client.patch("/api/v1/admin/projects/not-a-uuid", json={"title": "X"}).status_code == 422
    assert client.delete("/api/v1/admin/projects/not-a-uuid").status_code == 422


def test_nonexistent_id_404(client) -> None:
    _login(client, "staff@example.com", "staff")
    fake = str(uuid.uuid4())
    assert client.get(f"/api/v1/admin/projects/{fake}").status_code == 404
    assert client.patch(f"/api/v1/admin/projects/{fake}", json={"title": "X"}).status_code == 404
    assert client.delete(f"/api/v1/admin/projects/{fake}").status_code == 404


def test_update_null_required_field_422(client) -> None:
    _seed(_project("alpha"))
    _login(client, "staff@example.com", "staff")
    project_id = _project_id("alpha")
    response = client.patch(f"/api/v1/admin/projects/{project_id}", json={"title": None})
    assert response.status_code == 422


# --------------------------------------------------------------------------- #
# Services / Solutions / Case studies CRUD round-trip
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "resource,payload",
    [
        ("services", {"name": "AI Agents", "slug": "ai-agents"}),
        ("solutions", {"name": "E-commerce", "slug": "ecommerce"}),
        ("case-studies", {"title": "Case study", "slug": "cs-1"}),
    ],
)
def test_admin_crud_roundtrip(client, resource, payload) -> None:
    _login(client, "staff@example.com", "staff")
    base = f"/api/v1/admin/{resource}"

    created = client.post(base, json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body["slug"] == payload["slug"]
    assert body["published"] is False
    item_id = body["id"]

    assert client.post(base, json=payload).status_code == 409

    listing = client.get(base)
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    detail = client.get(f"{base}/{item_id}")
    assert detail.status_code == 200
    assert detail.json()["id"] == item_id

    patched = client.patch(f"{base}/{item_id}", json={"published": True})
    assert patched.status_code == 200
    assert patched.json()["published"] is True
    assert patched.json()["slug"] == payload["slug"]

    assert client.delete(f"{base}/{item_id}").status_code == 204
    assert client.get(f"{base}/{item_id}").status_code == 404


@pytest.mark.parametrize(
    "resource,payload",
    [
        ("services", {"name": "S1", "slug": "s1"}),
        ("solutions", {"name": "S2", "slug": "s2"}),
        ("case-studies", {"title": "CS", "slug": "cs"}),
    ],
)
def test_admin_duplicate_slug_409(client, resource, payload) -> None:
    _login(client, "staff@example.com", "staff")
    base = f"/api/v1/admin/{resource}"
    assert client.post(base, json=payload).status_code == 201
    assert client.post(base, json=payload).status_code == 409


# --------------------------------------------------------------------------- #
# Case studies foreign keys
# --------------------------------------------------------------------------- #
def test_case_study_create_with_project(client) -> None:
    _login(client, "staff@example.com", "staff")
    project = client.post("/api/v1/admin/projects", json={"title": "P", "slug": "p"}).json()
    response = client.post(
        "/api/v1/admin/case-studies",
        json={"title": "CS", "slug": "cs", "project_id": project["id"]},
    )
    assert response.status_code == 201
    assert response.json()["project_id"] == project["id"]


def test_case_study_create_invalid_project_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    response = client.post(
        "/api/v1/admin/case-studies",
        json={"title": "CS", "slug": "cs", "project_id": str(uuid.uuid4())},
    )
    assert response.status_code == 422


def test_case_study_patch_link_invalid_project_422(client) -> None:
    _login(client, "staff@example.com", "staff")
    cs = client.post("/api/v1/admin/case-studies", json={"title": "CS", "slug": "cs"}).json()
    response = client.patch(
        f"/api/v1/admin/case-studies/{cs['id']}", json={"project_id": str(uuid.uuid4())}
    )
    assert response.status_code == 422


def test_case_study_patch_unlink_project(client) -> None:
    _login(client, "staff@example.com", "staff")
    project = client.post("/api/v1/admin/projects", json={"title": "P", "slug": "p"}).json()
    cs = client.post(
        "/api/v1/admin/case-studies",
        json={"title": "CS", "slug": "cs", "project_id": project["id"]},
    ).json()
    response = client.patch(f"/api/v1/admin/case-studies/{cs['id']}", json={"project_id": None})
    assert response.status_code == 200
    assert response.json()["project_id"] is None


def test_delete_project_sets_case_study_project_null(client) -> None:
    _login(client, "staff@example.com", "staff")
    project = client.post("/api/v1/admin/projects", json={"title": "P", "slug": "p"}).json()
    cs = client.post(
        "/api/v1/admin/case-studies",
        json={"title": "CS", "slug": "cs", "project_id": project["id"]},
    ).json()
    assert client.delete(f"/api/v1/admin/projects/{project['id']}").status_code == 204
    detail = client.get(f"/api/v1/admin/case-studies/{cs['id']}")
    assert detail.status_code == 200
    assert detail.json()["project_id"] is None


# --------------------------------------------------------------------------- #
# Response shape + public API preservation
# --------------------------------------------------------------------------- #
def test_admin_response_includes_internal_fields(client) -> None:
    _login(client, "staff@example.com", "staff")
    project = client.post("/api/v1/admin/projects", json={"title": "A", "slug": "alpha"}).json()
    assert "published" in project
    assert project["published"] is False

    cs = client.post("/api/v1/admin/case-studies", json={"title": "CS", "slug": "cs"}).json()
    assert "project_id" in cs
    assert cs["project_id"] is None


def test_public_api_unchanged_after_admin_operations(client) -> None:
    _login(client, "staff@example.com", "staff")
    client.post(
        "/api/v1/admin/projects", json={"title": "Visible", "slug": "visible", "published": True}
    )
    client.post(
        "/api/v1/admin/projects", json={"title": "Hidden", "slug": "hidden", "published": False}
    )

    public = client.get("/api/v1/projects").json()
    assert public["total"] == 1
    assert public["items"][0]["slug"] == "visible"
    assert client.get("/api/v1/projects/hidden").status_code == 404
    assert client.get("/api/v1/projects/visible").status_code == 200

    assert client.get("/api/v1/admin/projects").json()["total"] == 2


def test_project_patch_empty_body_noop(client) -> None:
    _seed(_project("alpha", published=True))
    _login(client, "staff@example.com", "staff")
    project_id = _project_id("alpha")
    response = client.patch(f"/api/v1/admin/projects/{project_id}", json={})
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "alpha"
    assert body["published"] is True


def test_project_patch_invalid_status_422(client) -> None:
    _seed(_project("alpha"))
    _login(client, "staff@example.com", "staff")
    project_id = _project_id("alpha")
    response = client.patch(f"/api/v1/admin/projects/{project_id}", json={"status": "bogus"})
    assert response.status_code == 422


def test_project_patch_clears_optional_fields(client) -> None:
    _seed(_project("alpha", client_name="Acme", industry="Retail"))
    _login(client, "staff@example.com", "staff")
    project_id = _project_id("alpha")
    body = client.patch(
        f"/api/v1/admin/projects/{project_id}", json={"client_name": None, "industry": None}
    ).json()
    assert body["client_name"] is None
    assert body["industry"] is None

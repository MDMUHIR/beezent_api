from datetime import UTC, datetime

from app.models import CaseStudy, Project, ProjectStatus, Service, Solution
from tests._db import run_db


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


def _service(slug: str, **kwargs) -> Service:
    return Service(name=kwargs.pop("name", slug.replace("-", " ").title()), slug=slug, **kwargs)


def _solution(slug: str, **kwargs) -> Solution:
    return Solution(name=kwargs.pop("name", slug.replace("-", " ").title()), slug=slug, **kwargs)


def test_list_projects_only_published(client) -> None:
    _seed(
        _project("alpha", published=True),
        _project("beta", published=True),
        _project("hidden", published=False),
    )
    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["pages"] == 1
    slugs = {item["slug"] for item in body["items"]}
    assert slugs == {"alpha", "beta"}


def test_unpublished_project_detail_404(client) -> None:
    _seed(_project("hidden", published=False))
    response = client.get("/api/v1/projects/hidden")
    assert response.status_code == 404


def test_project_pagination(client) -> None:
    _seed(*[_project(f"p{i}", published=True) for i in range(5)])
    response = client.get("/api/v1/projects", params={"page": 1, "page_size": 2})
    body = response.json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert body["page"] == 1
    assert len(body["items"]) == 2

    page3 = client.get("/api/v1/projects", params={"page": 3, "page_size": 2}).json()
    assert len(page3["items"]) == 1

    page4 = client.get("/api/v1/projects", params={"page": 4, "page_size": 2}).json()
    assert len(page4["items"]) == 0


def test_invalid_pagination_params_422(client) -> None:
    _seed(_project("alpha", published=True))
    assert client.get("/api/v1/projects", params={"page": 0}).status_code == 422
    assert client.get("/api/v1/projects", params={"page_size": 100}).status_code == 422


def test_project_slug_lookup(client) -> None:
    _seed(
        _project(
            "ai-commerce",
            published=True,
            short_description="Short",
            technologies=["FastAPI", "PostgreSQL"],
            results=[{"metric": "conversion", "value": "+32%"}],
        )
    )
    response = client.get("/api/v1/projects/ai-commerce")
    assert response.status_code == 200
    body = response.json()
    assert body["slug"] == "ai-commerce"
    assert body["technologies"] == ["FastAPI", "PostgreSQL"]
    assert body["results"] == [{"metric": "conversion", "value": "+32%"}]


def test_project_invalid_slug_404(client) -> None:
    _seed(_project("alpha", published=True))
    assert client.get("/api/v1/projects/does-not-exist").status_code == 404


def test_project_search(client) -> None:
    _seed(
        _project("alpha", title="Retail Platform", published=True),
        _project("beta", title="SaaS Dashboard", published=True),
    )
    result = client.get("/api/v1/projects", params={"q": "retail"}).json()
    assert [item["slug"] for item in result["items"]] == ["alpha"]
    assert result["total"] == 1


def test_project_filters(client) -> None:
    _seed(
        _project(
            "a",
            published=True,
            status=ProjectStatus.ACTIVE,
            featured=True,
            industry="retail",
        ),
        _project("b", published=True, status=ProjectStatus.COMPLETED, industry="saas"),
        _project("c", published=False, status=ProjectStatus.ACTIVE),
    )
    featured = client.get("/api/v1/projects", params={"featured": "true"}).json()
    assert [item["slug"] for item in featured["items"]] == ["a"]

    completed = client.get("/api/v1/projects", params={"status": "completed"}).json()
    assert [item["slug"] for item in completed["items"]] == ["b"]

    by_industry = client.get("/api/v1/projects", params={"industry": "retail"}).json()
    assert [item["slug"] for item in by_industry["items"]] == ["a"]


def test_project_sorting(client) -> None:
    _seed(
        _project("zebra", published=True, created_at=datetime(2021, 1, 1, tzinfo=UTC)),
        _project("apple", published=True, created_at=datetime(2022, 1, 1, tzinfo=UTC)),
        _project("mango", published=True, created_at=datetime(2020, 1, 1, tzinfo=UTC)),
    )
    asc = client.get("/api/v1/projects", params={"sort": "title", "order": "asc"}).json()
    assert [item["slug"] for item in asc["items"]] == ["apple", "mango", "zebra"]

    desc = client.get("/api/v1/projects", params={"sort": "title", "order": "desc"}).json()
    assert [item["slug"] for item in desc["items"]] == ["zebra", "mango", "apple"]

    newest = client.get("/api/v1/projects", params={"sort": "created_at"}).json()
    assert newest["items"][0]["slug"] == "apple"


def test_services_list_and_detail(client) -> None:
    _seed(
        _service("ai-agents", published=True, sort_order=1),
        _service("ai-automation", published=True, sort_order=2),
        _service("secret", published=False),
    )
    listing = client.get("/api/v1/services").json()
    assert listing["total"] == 2
    assert [item["slug"] for item in listing["items"]] == ["ai-agents", "ai-automation"]

    detail = client.get("/api/v1/services/ai-agents")
    assert detail.status_code == 200
    assert detail.json()["sort_order"] == 1

    assert client.get("/api/v1/services/secret").status_code == 404
    assert client.get("/api/v1/services/missing").status_code == 404


def test_solutions_list_and_detail(client) -> None:
    _seed(
        _solution("ecommerce", published=True, sort_order=1),
        _solution("saas", published=True, sort_order=2),
        _solution("hidden", published=False),
    )
    listing = client.get("/api/v1/solutions").json()
    assert listing["total"] == 2
    assert [item["slug"] for item in listing["items"]] == ["ecommerce", "saas"]

    detail = client.get("/api/v1/solutions/ecommerce")
    assert detail.status_code == 200
    assert detail.json()["name"] == "Ecommerce"

    assert client.get("/api/v1/solutions/hidden").status_code == 404


def test_case_studies_list_and_detail_with_project(client) -> None:
    project = _project("ai-commerce", published=True)
    _seed(
        project,
        CaseStudy(
            project_id=None,
            title="Standalone case",
            slug="standalone",
            published=True,
            summary="Standalone summary",
        ),
        CaseStudy(
            project=project,
            title="Tied to project",
            slug="tied",
            published=True,
            summary="Tied summary",
            metrics=[{"name": "cost reduction", "value": "-40%"}],
        ),
        CaseStudy(title="Hidden", slug="hidden", published=False),
    )

    listing = client.get("/api/v1/case-studies").json()
    assert listing["total"] == 2
    by_slug = {item["slug"]: item for item in listing["items"]}
    assert by_slug["tied"]["project"]["slug"] == "ai-commerce"
    assert by_slug["standalone"]["project"] is None

    detail = client.get("/api/v1/case-studies/tied")
    assert detail.status_code == 200
    assert detail.json()["project"]["title"] == "Ai Commerce"
    assert detail.json()["metrics"] == [{"name": "cost reduction", "value": "-40%"}]

    assert client.get("/api/v1/case-studies/hidden").status_code == 404
    assert client.get("/api/v1/case-studies/missing").status_code == 404


def test_case_studies_filter_by_project_slug(client) -> None:
    project = _project("ai-commerce", published=True)
    _seed(
        project,
        CaseStudy(title="Tied", slug="tied", published=True, project=project),
        CaseStudy(title="Other", slug="other", published=True, project_id=None),
    )
    result = client.get("/api/v1/case-studies", params={"project_slug": "ai-commerce"}).json()
    assert result["total"] == 1
    assert result["items"][0]["slug"] == "tied"


def test_response_schemas_do_not_expose_internal_fields(client) -> None:
    _seed(
        _project("alpha", published=True, featured=True),
        _service("svc", published=True),
        _solution("sol", published=True),
        CaseStudy(title="CS", slug="cs", published=True, seo_title="SEO"),
    )
    project = client.get("/api/v1/projects/alpha").json()
    assert "published" not in project
    assert "is_active" not in project

    service = client.get("/api/v1/services/svc").json()
    assert "published" not in service

    solution = client.get("/api/v1/solutions/sol").json()
    assert "published" not in solution

    case_study = client.get("/api/v1/case-studies/cs").json()
    assert "published" not in case_study
    assert "project_id" not in case_study


def test_empty_results(client) -> None:
    response = client.get("/api/v1/projects")
    body = response.json()
    assert body == {"items": [], "total": 0, "page": 1, "page_size": 12, "pages": 0}


def test_public_invalid_status_filter_422(client) -> None:
    _seed(_project("alpha", published=True))
    assert client.get("/api/v1/projects", params={"status": "bogus"}).status_code == 422


def test_public_invalid_sort_422(client) -> None:
    _seed(_project("alpha", published=True))
    assert client.get("/api/v1/projects", params={"sort": "bogus"}).status_code == 422
    assert client.get("/api/v1/services", params={"sort": "bogus"}).status_code == 422
    assert client.get("/api/v1/solutions", params={"sort": "bogus"}).status_code == 422
    assert client.get("/api/v1/case-studies", params={"sort": "bogus"}).status_code == 422


def test_public_search_special_characters(client) -> None:
    _seed(
        _project("alpha", title="100% AI Automation", published=True),
        _project("beta", title="R&D Platform", published=True),
    )
    assert client.get("/api/v1/projects", params={"q": "100%"}).status_code == 200
    assert client.get("/api/v1/projects", params={"q": "%_[]"}).status_code == 200
    assert client.get("/api/v1/projects", params={"q": "%"}).status_code == 200


def test_public_featured_and_project_type_filters(client) -> None:
    _seed(
        _project("a", published=True, featured=True, project_type="ecommerce"),
        _project("b", published=True, project_type="saas"),
    )
    featured = client.get("/api/v1/projects", params={"featured": "false"}).json()
    assert [item["slug"] for item in featured["items"]] == ["b"]

    by_type = client.get("/api/v1/projects", params={"project_type": "ecommerce"}).json()
    assert [item["slug"] for item in by_type["items"]] == ["a"]

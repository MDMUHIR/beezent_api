import asyncio
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models import CaseStudy, Project, ProjectStatus, Service, Solution

BASE_DIR = Path(__file__).resolve().parent.parent


def run_db(coro) -> Any:
    async def _runner() -> Any:
        engine = create_async_engine(get_settings().database_url)
        factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        try:
            async with factory() as session:
                return await coro(session)
        finally:
            await engine.dispose()

    return asyncio.run(_runner())


async def _table_names(session: AsyncSession) -> set[str]:
    result = await session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    return {row[0] for row in result}


def test_project_can_be_created() -> None:
    async def create(session: AsyncSession) -> None:
        project = Project(
            title="AI Commerce Platform",
            slug="ai-commerce-platform",
            short_description="Short",
            description="Long description",
            client_name="Acme",
            industry="Retail",
            project_type="E-commerce",
            cover_image="https://example.com/cover.jpg",
            live_url="https://example.com",
            github_url="https://github.com/example",
            technologies=["FastAPI", "PostgreSQL"],
            results=[{"metric": "conversion", "value": "+32%"}],
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)
        assert project.id is not None
        assert project.created_at is not None
        assert project.updated_at is not None
        assert project.status == ProjectStatus.ACTIVE
        assert project.featured is False
        assert project.published is False
        assert project.technologies == ["FastAPI", "PostgreSQL"]

    run_db(create)


def test_service_can_be_created() -> None:
    async def create(session: AsyncSession) -> None:
        service = Service(
            name="AI Agents",
            slug="ai-agents",
            short_description="Autonomous AI agents",
            description="Long description",
            icon="bot",
            sort_order=1,
        )
        session.add(service)
        await session.commit()
        await session.refresh(service)
        assert service.id is not None
        assert service.created_at is not None
        assert service.featured is False
        assert service.published is False
        assert service.sort_order == 1

    run_db(create)


def test_solution_can_be_created() -> None:
    async def create(session: AsyncSession) -> None:
        solution = Solution(
            name="E-commerce",
            slug="ecommerce",
            short_description="Commerce solutions",
            description="Long description",
            icon="cart",
        )
        session.add(solution)
        await session.commit()
        await session.refresh(solution)
        assert solution.id is not None
        assert solution.created_at is not None
        assert solution.featured is False
        assert solution.published is False
        assert solution.sort_order == 0

    run_db(create)


def test_case_study_can_be_created() -> None:
    async def create(session: AsyncSession) -> None:
        case_study = CaseStudy(
            title="How we shipped AI commerce",
            slug="ai-commerce-case-study",
            summary="Summary",
            challenge="Challenge",
            solution="Solution",
            implementation="Implementation",
            technologies=["LangGraph"],
            metrics=[{"name": "cost reduction", "value": "-40%"}],
            seo_title="SEO title",
            seo_description="SEO description",
        )
        session.add(case_study)
        await session.commit()
        await session.refresh(case_study)
        assert case_study.id is not None
        assert case_study.project_id is None
        assert case_study.featured is False
        assert case_study.published is False
        assert case_study.metrics == [{"name": "cost reduction", "value": "-40%"}]

    run_db(create)


def test_case_study_references_project() -> None:
    async def create(session: AsyncSession) -> None:
        project = Project(title="AI Commerce", slug="ai-commerce")
        session.add(project)
        await session.commit()

        case_study = CaseStudy(project_id=project.id, title="Case study", slug="case-study")
        session.add(case_study)
        await session.commit()
        await session.refresh(case_study)

        assert case_study.project_id == project.id

        await session.refresh(project, ["case_studies"])
        assert len(project.case_studies) == 1
        assert project.case_studies[0].id == case_study.id

    run_db(create)


def test_project_delete_sets_case_study_project_null() -> None:
    async def run(session: AsyncSession) -> None:
        project = Project(title="AI Commerce", slug="ai-commerce-2")
        session.add(project)
        await session.commit()

        case_study = CaseStudy(project_id=project.id, title="Case study", slug="case-study-2")
        session.add(case_study)
        await session.commit()

        await session.delete(project)
        await session.commit()
        await session.refresh(case_study)

        assert case_study.project_id is None

    run_db(run)


def test_duplicate_project_slug_rejected() -> None:
    async def run(session: AsyncSession) -> None:
        session.add_all(
            [Project(title="A", slug="duplicate"), Project(title="B", slug="duplicate")]
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_duplicate_service_slug_rejected() -> None:
    async def run(session: AsyncSession) -> None:
        session.add_all([Service(name="A", slug="duplicate"), Service(name="B", slug="duplicate")])
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_duplicate_solution_slug_rejected() -> None:
    async def run(session: AsyncSession) -> None:
        session.add_all(
            [Solution(name="A", slug="duplicate"), Solution(name="B", slug="duplicate")]
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_duplicate_case_study_slug_rejected() -> None:
    async def run(session: AsyncSession) -> None:
        session.add_all(
            [CaseStudy(title="A", slug="duplicate"), CaseStudy(title="B", slug="duplicate")]
        )
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_required_fields_enforced() -> None:
    async def run(session: AsyncSession) -> None:
        session.add(Project(title="Missing slug"))
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_defaults_work() -> None:
    async def run(session: AsyncSession) -> None:
        project = Project(title="P", slug="defaults-project")
        service = Service(name="S", slug="defaults-service")
        solution = Solution(name="Sol", slug="defaults-solution")
        case_study = CaseStudy(title="CS", slug="defaults-case-study")
        session.add_all([project, service, solution, case_study])
        await session.commit()

        for obj in (project, service, solution, case_study):
            await session.refresh(obj)
            assert obj.featured is False
            assert obj.published is False
            assert obj.created_at is not None
            assert obj.updated_at is not None
        assert project.status == ProjectStatus.ACTIVE
        assert project.technologies == []
        assert project.results == []
        assert case_study.technologies == []
        assert case_study.metrics == []
        assert service.sort_order == 0
        assert solution.sort_order == 0

    run_db(run)


def test_cms_tables_exist() -> None:
    tables = run_db(_table_names)
    assert {"projects", "services", "solutions", "case_studies"} <= tables


def test_alembic_downgrade_and_upgrade_restores_schema() -> None:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    try:
        command.downgrade(config, "-1")
    finally:
        command.upgrade(config, "head")
    tables = run_db(_table_names)
    assert {"projects", "services", "solutions", "case_studies"} <= tables

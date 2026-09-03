from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Lead, LeadStatus
from tests._db import run_db

BASE_DIR = Path(__file__).resolve().parent.parent


async def _table_names(session: AsyncSession) -> set[str]:
    result = await session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    )
    return {row[0] for row in result}


def test_lead_can_be_created() -> None:
    async def create(session: AsyncSession) -> None:
        lead = Lead(
            name="John Doe",
            email="john@example.com",
            phone="+8801XXXXXXXXX",
            company="Example Ltd",
            service="AI Automation",
            message="I want to automate our customer support.",
            source="website",
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        assert lead.id is not None
        assert lead.created_at is not None
        assert lead.updated_at is not None
        assert lead.status == LeadStatus.NEW
        assert lead.notes is None
        assert lead.phone == "+8801XXXXXXXXX"

    run_db(create)


def test_lead_default_status_and_optional_fields() -> None:
    async def create(session: AsyncSession) -> None:
        lead = Lead(name="Alice", email="alice@example.com", message="Long enough message here")
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        assert lead.status == LeadStatus.NEW
        assert lead.phone is None
        assert lead.company is None
        assert lead.service is None
        assert lead.source is None
        assert lead.notes is None

    run_db(create)


def test_lead_status_enum_values() -> None:
    async def create(session: AsyncSession) -> None:
        lead = Lead(
            name="Bob",
            email="bob@example.com",
            message="Long enough message here",
            status=LeadStatus.CONTACTED,
        )
        session.add(lead)
        await session.commit()
        await session.refresh(lead)
        assert lead.status == LeadStatus.CONTACTED
        assert lead.status.value == "contacted"

    run_db(create)


def test_lead_required_fields_enforced() -> None:
    async def run(session: AsyncSession) -> None:
        session.add(Lead(name="No message", email="x@example.com"))
        with pytest.raises(IntegrityError):
            await session.commit()

    run_db(run)


def test_leads_table_has_indexes() -> None:
    async def run(session: AsyncSession) -> None:
        result = await session.execute(
            text(
                "SELECT indexname FROM pg_indexes "
                "WHERE tablename = 'leads' AND schemaname = 'public'"
            )
        )
        indexes = {row[0] for row in result}
        assert {
            "ix_leads_status_created_at",
            "ix_leads_created_at",
            "ix_leads_email",
        } <= indexes

    run_db(run)


def test_leads_table_exists() -> None:
    tables = run_db(_table_names)
    assert "leads" in tables


def test_alembic_downgrade_and_upgrade_restores_leads_table() -> None:
    config = Config(str(BASE_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BASE_DIR / "migrations"))
    try:
        # Downgrade through the leads migration (eef51e823865 -> f52bdc6b0961)
        # regardless of which migrations are newer than it.
        command.downgrade(config, "eef51e823865")
        tables_without_leads = run_db(_table_names)
        assert "leads" not in tables_without_leads
    finally:
        command.upgrade(config, "head")
    tables = run_db(_table_names)
    assert "leads" in tables

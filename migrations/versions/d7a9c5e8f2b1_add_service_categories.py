"""add service categories

Revision ID: d7a9c5e8f2b1
Revises: c3f7a1b2e9d4
Create Date: 2026-09-05 17:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d7a9c5e8f2b1"
down_revision: Union[str, Sequence[str], None] = "c3f7a1b2e9d4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "service_categories",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(
        op.f("ix_service_categories_slug"), "service_categories", ["slug"], unique=True
    )
    op.create_table(
        "service_category_links",
        sa.Column("service_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["service_categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["service_id"], ["services.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("service_id", "category_id"),
    )
    op.create_index(
        "ix_service_category_links_category_id",
        "service_category_links",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_service_category_links_category_id", table_name="service_category_links"
    )
    op.drop_table("service_category_links")
    op.drop_index(op.f("ix_service_categories_slug"), table_name="service_categories")
    op.drop_table("service_categories")
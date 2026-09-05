"""add project categories

Revision ID: e4b8d6a1c3f5
Revises: d7a9c5e8f2b1
Create Date: 2026-09-05 18:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4b8d6a1c3f5"
down_revision: Union[str, Sequence[str], None] = "d7a9c5e8f2b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "project_categories",
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
        op.f("ix_project_categories_slug"), "project_categories", ["slug"], unique=True
    )
    op.create_table(
        "project_category_links",
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["project_categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("project_id", "category_id"),
    )
    op.create_index(
        "ix_project_category_links_category_id",
        "project_category_links",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_project_category_links_category_id", table_name="project_category_links"
    )
    op.drop_table("project_category_links")
    op.drop_index(op.f("ix_project_categories_slug"), table_name="project_categories")
    op.drop_table("project_categories")
"""add solution categories

Revision ID: c3f7a1b2e9d4
Revises: 147c3d1fc707
Create Date: 2026-09-05 16:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c3f7a1b2e9d4"
down_revision: Union[str, Sequence[str], None] = "147c3d1fc707"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "solution_categories",
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
        op.f("ix_solution_categories_slug"), "solution_categories", ["slug"], unique=True
    )
    op.create_table(
        "solution_category_links",
        sa.Column("solution_id", sa.Uuid(), nullable=False),
        sa.Column("category_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["solution_categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["solution_id"], ["solutions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("solution_id", "category_id"),
    )
    op.create_index(
        "ix_solution_category_links_category_id",
        "solution_category_links",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_solution_category_links_category_id", table_name="solution_category_links"
    )
    op.drop_table("solution_category_links")
    op.drop_index(op.f("ix_solution_categories_slug"), table_name="solution_categories")
    op.drop_table("solution_categories")

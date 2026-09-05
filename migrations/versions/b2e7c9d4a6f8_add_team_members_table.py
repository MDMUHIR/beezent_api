"""add team members table

Revision ID: b2e7c9d4a6f8
Revises: e4b8d6a1c3f5
Create Date: 2026-09-05 19:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b2e7c9d4a6f8"
down_revision: Union[str, Sequence[str], None] = "e4b8d6a1c3f5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "team_members",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("slug", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=255), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("avatar_url", sa.String(length=500), nullable=True),
        sa.Column(
            "category",
            sa.Enum(
                "leadership",
                "talent",
                name="teammembercategory",
                native_enum=False,
                length=20,
            ),
            nullable=False,
        ),
        sa.Column("featured", sa.Boolean(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
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
        sa.CheckConstraint(
            "category IN ('leadership', 'talent')", name="ck_team_members_category"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_team_members_published"), "team_members", ["published"], unique=False)
    op.create_index(op.f("ix_team_members_slug"), "team_members", ["slug"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_team_members_slug"), table_name="team_members")
    op.drop_index(op.f("ix_team_members_published"), table_name="team_members")
    op.drop_table("team_members")
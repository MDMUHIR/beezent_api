"""add images and demo videos

Revision ID: a1c3e5f7b9d2
Revises: b2e7c9d4a6f8
Create Date: 2026-09-05 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1c3e5f7b9d2"
down_revision: Union[str, Sequence[str], None] = "b2e7c9d4a6f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    demovideotype = sa.Enum(
        "youtube",
        "upload",
        name="demovideotype",
        native_enum=False,
        length=20,
    )

    op.add_column(
        "projects",
        sa.Column("demo_video_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "projects",
        sa.Column("demo_video_type", demovideotype, nullable=True),
    )
    op.add_column(
        "solutions",
        sa.Column("image_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "solutions",
        sa.Column("demo_video_url", sa.String(length=500), nullable=True),
    )
    op.add_column(
        "solutions",
        sa.Column("demo_video_type", demovideotype, nullable=True),
    )
    op.add_column(
        "case_studies",
        sa.Column("image_url", sa.String(length=500), nullable=True),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("case_studies", "image_url")
    op.drop_column("solutions", "demo_video_type")
    op.drop_column("solutions", "demo_video_url")
    op.drop_column("solutions", "image_url")
    op.drop_column("projects", "demo_video_type")
    op.drop_column("projects", "demo_video_url")
    sa.Enum(name="demovideotype", native_enum=False, length=20).drop(
        op.get_bind(), checkfirst=True
    )
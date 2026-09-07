"""add media relationships and media metadata

Revision ID: eb1af61cf576
Revises: a1c3e5f7b9d2
Create Date: 2026-09-07 02:41:02.144236

Makes Media a first-class domain entity:

* CMS tables gain optional Media UUID foreign keys (ON DELETE SET NULL).
* Media gains `media_type` / `duration_seconds`; `public_url` stops being a
  stored column (it is derived from the storage key at runtime).
* Existing string URL references are backfilled into the new FKs when they
  exactly match an existing media row's `public_url` (deterministic: a single
  media id per URL via DISTINCT ON). URLs that match no media row are left
  untouched and are not fabricated into Media records.

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "eb1af61cf576"
down_revision: Union[str, Sequence[str], None] = "a1c3e5f7b9d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_media_type() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("UPDATE media SET media_type = 'image' WHERE mime_type LIKE 'image/%'"))
    bind.execute(sa.text("UPDATE media SET media_type = 'video' WHERE mime_type LIKE 'video/%'"))
    bind.execute(
        sa.text("UPDATE media SET media_type = 'document' WHERE mime_type = 'application/pdf'")
    )


def _backfill_cms_media_links() -> None:
    """Link existing string URL references to media rows by public_url."""
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            UPDATE projects p
               SET cover_media_id = m.id
              FROM (SELECT DISTINCT ON (public_url) id, public_url
                      FROM media ORDER BY public_url, created_at) m
             WHERE m.public_url = p.cover_image AND p.cover_media_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE projects p
               SET demo_video_media_id = m.id
              FROM (SELECT DISTINCT ON (public_url) id, public_url
                      FROM media ORDER BY public_url, created_at) m
             WHERE m.public_url = p.demo_video_url
               AND p.demo_video_type = 'upload'
               AND p.demo_video_media_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE solutions s
               SET image_media_id = m.id
              FROM (SELECT DISTINCT ON (public_url) id, public_url
                      FROM media ORDER BY public_url, created_at) m
             WHERE m.public_url = s.image_url AND s.image_media_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE solutions s
               SET demo_video_media_id = m.id
              FROM (SELECT DISTINCT ON (public_url) id, public_url
                      FROM media ORDER BY public_url, created_at) m
             WHERE m.public_url = s.demo_video_url
               AND s.demo_video_type = 'upload'
               AND s.demo_video_media_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE case_studies c
               SET image_media_id = m.id
              FROM (SELECT DISTINCT ON (public_url) id, public_url
                      FROM media ORDER BY public_url, created_at) m
             WHERE m.public_url = c.image_url AND c.image_media_id IS NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE team_members t
               SET avatar_media_id = m.id
              FROM (SELECT DISTINCT ON (public_url) id, public_url
                      FROM media ORDER BY public_url, created_at) m
             WHERE m.public_url = t.avatar_url AND t.avatar_media_id IS NULL
            """
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    # --- Media metadata -----------------------------------------------------
    op.add_column("media", sa.Column("media_type", sa.String(length=20), nullable=True))
    op.add_column("media", sa.Column("duration_seconds", sa.Integer(), nullable=True))
    _backfill_media_type()
    op.alter_column("media", "media_type", nullable=False)
    op.create_check_constraint(
        "ck_media_media_type", "media", "media_type IN ('image', 'video', 'document')"
    )
    op.create_check_constraint(
        "ck_media_duration", "media", "duration_seconds IS NULL OR duration_seconds >= 0"
    )
    op.create_index(op.f("ix_media_media_type"), "media", ["media_type"], unique=False)

    # --- CMS Media foreign keys --------------------------------------------
    op.add_column("projects", sa.Column("cover_media_id", sa.Uuid(), nullable=True))
    op.add_column("projects", sa.Column("demo_video_media_id", sa.Uuid(), nullable=True))
    op.add_column("solutions", sa.Column("image_media_id", sa.Uuid(), nullable=True))
    op.add_column("solutions", sa.Column("demo_video_media_id", sa.Uuid(), nullable=True))
    op.add_column("case_studies", sa.Column("image_media_id", sa.Uuid(), nullable=True))
    op.add_column("team_members", sa.Column("avatar_media_id", sa.Uuid(), nullable=True))

    # Backfill existing string URLs before public_url is removed.
    _backfill_cms_media_links()

    op.create_foreign_key(
        "fk_projects_cover_media_id_media",
        "projects",
        "media",
        ["cover_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_projects_demo_video_media_id_media",
        "projects",
        "media",
        ["demo_video_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_solutions_image_media_id_media",
        "solutions",
        "media",
        ["image_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_solutions_demo_video_media_id_media",
        "solutions",
        "media",
        ["demo_video_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_case_studies_image_media_id_media",
        "case_studies",
        "media",
        ["image_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_team_members_avatar_media_id_media",
        "team_members",
        "media",
        ["avatar_media_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_projects_cover_media_id"), "projects", ["cover_media_id"], unique=False
    )
    op.create_index(
        op.f("ix_projects_demo_video_media_id"), "projects", ["demo_video_media_id"], unique=False
    )
    op.create_index(
        op.f("ix_solutions_image_media_id"), "solutions", ["image_media_id"], unique=False
    )
    op.create_index(
        op.f("ix_solutions_demo_video_media_id"), "solutions", ["demo_video_media_id"], unique=False
    )
    op.create_index(
        op.f("ix_case_studies_image_media_id"), "case_studies", ["image_media_id"], unique=False
    )
    op.create_index(
        op.f("ix_team_members_avatar_media_id"), "team_members", ["avatar_media_id"], unique=False
    )

    # --- Media public_url becomes derived, not stored -----------------------
    op.drop_column("media", "public_url")


def downgrade() -> None:
    """Downgrade schema."""
    # Restore stored public_url (best effort: local-backend convention).
    op.add_column(
        "media",
        sa.Column("public_url", sa.VARCHAR(length=500), autoincrement=False, nullable=True),
    )
    op.execute(sa.text("UPDATE media SET public_url = '/media/' || storage_key"))
    op.alter_column("media", "public_url", nullable=False)

    op.drop_constraint("fk_team_members_avatar_media_id_media", "team_members", type_="foreignkey")
    op.drop_index(op.f("ix_team_members_avatar_media_id"), table_name="team_members")
    op.drop_column("team_members", "avatar_media_id")
    op.drop_constraint("fk_solutions_demo_video_media_id_media", "solutions", type_="foreignkey")
    op.drop_constraint("fk_solutions_image_media_id_media", "solutions", type_="foreignkey")
    op.drop_index(op.f("ix_solutions_image_media_id"), table_name="solutions")
    op.drop_index(op.f("ix_solutions_demo_video_media_id"), table_name="solutions")
    op.drop_column("solutions", "demo_video_media_id")
    op.drop_column("solutions", "image_media_id")
    op.drop_constraint("fk_projects_demo_video_media_id_media", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_cover_media_id_media", "projects", type_="foreignkey")
    op.drop_index(op.f("ix_projects_demo_video_media_id"), table_name="projects")
    op.drop_index(op.f("ix_projects_cover_media_id"), table_name="projects")
    op.drop_column("projects", "demo_video_media_id")
    op.drop_column("projects", "cover_media_id")
    op.drop_constraint("fk_case_studies_image_media_id_media", "case_studies", type_="foreignkey")
    op.drop_index(op.f("ix_case_studies_image_media_id"), table_name="case_studies")
    op.drop_column("case_studies", "image_media_id")

    op.drop_constraint("ck_media_media_type", "media", type_="check")
    op.drop_constraint("ck_media_duration", "media", type_="check")
    op.drop_index(op.f("ix_media_media_type"), table_name="media")
    op.drop_column("media", "duration_seconds")
    op.drop_column("media", "media_type")

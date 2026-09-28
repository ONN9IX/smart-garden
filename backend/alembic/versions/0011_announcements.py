"""Operational announcements. Revision ID: 0011; down_revision: 0010."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "announcements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("target_type", sa.String(16), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=True),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("body", sa.String(2000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("target_type IN ('all', 'group')", name="ck_announcements_target_type"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_announcements_status"),
        sa.CheckConstraint(
            "(target_type = 'all' AND group_id IS NULL) OR (target_type = 'group' AND group_id IS NOT NULL)",
            name="ck_announcements_target_group",
        ),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_announcements_title_nonempty"),
        sa.CheckConstraint("length(btrim(body)) > 0", name="ck_announcements_body_nonempty"),
    )
    op.create_index(
        "ix_announcements_organization_status_created_at",
        "announcements",
        ["organization_id", "status", "created_at"],
    )
    op.create_index(
        "ix_announcements_organization_group",
        "announcements",
        ["organization_id", "group_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_announcements_organization_group", table_name="announcements")
    op.drop_index("ix_announcements_organization_status_created_at", table_name="announcements")
    op.drop_table("announcements")

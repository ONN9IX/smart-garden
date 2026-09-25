"""Tenant guardians and child links. Revision ID: 0006; down_revision: 0005."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "guardians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("middle_name", sa.String(100)),
        sa.Column("phone", sa.String(32)),
        sa.Column("email", sa.String(254)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_guardians_status"),
        sa.UniqueConstraint("user_id", name="uq_guardians_user_id"),
    )
    op.create_index("ix_guardians_organization_status", "guardians", ["organization_id", "status"])
    op.create_table(
        "child_guardians",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("guardian_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("guardians.id"), nullable=False),
        sa.Column("relation_type", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_child_guardians_status"),
        sa.CheckConstraint(
            "relation_type IN ('mother', 'father', 'legal_guardian', 'other')",
            name="ck_child_guardians_relation_type",
        ),
        sa.UniqueConstraint("child_id", "guardian_id", name="uq_child_guardians_pair"),
    )
    op.create_index("ix_child_guardians_organization_status", "child_guardians", ["organization_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_child_guardians_organization_status", table_name="child_guardians")
    op.drop_table("child_guardians")
    op.drop_index("ix_guardians_organization_status", table_name="guardians")
    op.drop_table("guardians")

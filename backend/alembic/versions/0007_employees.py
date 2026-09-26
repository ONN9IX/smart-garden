"""Minimal tenant employee cards. Revision ID: 0007; down_revision: 0006."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employees",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("first_name", sa.String(100), nullable=False),
        sa.Column("last_name", sa.String(100), nullable=False),
        sa.Column("middle_name", sa.String(100)),
        sa.Column("position", sa.String(100), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_employees_status"),
        sa.CheckConstraint("length(btrim(first_name)) > 0", name="ck_employees_first_name_nonempty"),
        sa.CheckConstraint("length(btrim(last_name)) > 0", name="ck_employees_last_name_nonempty"),
        sa.CheckConstraint("length(btrim(position)) > 0", name="ck_employees_position_nonempty"),
        sa.UniqueConstraint("user_id", name="uq_employees_user_id"),
    )
    op.create_index("ix_employees_organization_status", "employees", ["organization_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_employees_organization_status", table_name="employees")
    op.drop_table("employees")

"""Manual attendance with a group snapshot. Revision ID: 0008; down_revision: 0007."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "attendance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("arrival_time", sa.Time(timezone=False)),
        sa.Column("departure_time", sa.Time(timezone=False)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("status IN ('present', 'absent', 'unknown')", name="ck_attendance_status"),
        sa.CheckConstraint(
            "(status = 'present' AND (departure_time IS NULL OR arrival_time IS NOT NULL) "
            "AND (departure_time IS NULL OR departure_time >= arrival_time)) "
            "OR (status IN ('absent', 'unknown') AND arrival_time IS NULL AND departure_time IS NULL)",
            name="ck_attendance_time_state",
        ),
        sa.UniqueConstraint("child_id", "date", name="uq_attendance_child_date"),
    )
    op.create_index("ix_attendance_organization_date_group", "attendance", ["organization_id", "date", "group_id"])
    op.create_index("ix_attendance_organization_date_status", "attendance", ["organization_id", "date", "status"])


def downgrade() -> None:
    op.drop_index("ix_attendance_organization_date_status", table_name="attendance")
    op.drop_index("ix_attendance_organization_date_group", table_name="attendance")
    op.drop_table("attendance")

"""Add per-user operational view state and tenant notification preferences."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "operational_alert_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("alert_key", sa.String(160), nullable=False),
        sa.Column("viewed_at", sa.DateTime(timezone=True)),
        sa.Column("snoozed_until", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("organization_id", "user_id", "alert_key", name="uq_operational_alert_state_owner_key"),
    )
    op.create_index("ix_operational_alert_state_owner", "operational_alert_states", ["organization_id", "user_id"])
    op.create_table(
        "organization_notification_settings",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("show_informational_notifications", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("attendance_checkpoint_time", sa.Time()),
        sa.Column("schedule_missing_alert_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("organization_notification_settings")
    op.drop_index("ix_operational_alert_state_owner", table_name="operational_alert_states")
    op.drop_table("operational_alert_states")

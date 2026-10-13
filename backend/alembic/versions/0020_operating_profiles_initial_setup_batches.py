"""Add organization operating profiles and initial setup batch receipts.

Revision ID: 0020
Revises: 0019
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0020"
down_revision = "0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "organizations",
        sa.Column(
            "operating_profile", sa.String(length=16), nullable=False,
            server_default="KINDERGARTEN",
        ),
    )
    op.create_check_constraint(
        "ck_organizations_operating_profile", "organizations",
        "operating_profile IN ('KINDERGARTEN', 'GYMNASTICS')",
    )
    op.create_table(
        "initial_setup_batches",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.Column("employee_count", sa.Integer(), nullable=False),
        sa.Column("schedule_count", sa.Integer(), nullable=False),
        sa.Column("created_by_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("employee_count >= 0", name="ck_initial_setup_employee_count"),
        sa.CheckConstraint("schedule_count >= 0", name="ck_initial_setup_schedule_count"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "idempotency_key", name="uq_initial_setup_batch_key"),
    )


def downgrade() -> None:
    op.drop_table("initial_setup_batches")
    op.drop_constraint("ck_organizations_operating_profile", "organizations", type_="check")
    op.drop_column("organizations", "operating_profile")

"""Separate group communication audiences. Revision ID: 0013; down_revision: 0012."""

import sqlalchemy as sa

from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "communication_threads",
        sa.Column("audience", sa.String(16), nullable=False, server_default="all"),
    )
    op.create_check_constraint(
        "ck_communication_threads_audience",
        "communication_threads",
        "audience IN ('all', 'parents', 'teachers')",
    )
    op.create_check_constraint(
        "ck_communication_threads_direct_audience",
        "communication_threads",
        "thread_type = 'group' OR audience = 'all'",
    )
    op.drop_index("uq_communication_threads_group", table_name="communication_threads")
    op.create_index(
        "uq_communication_threads_group",
        "communication_threads",
        ["group_id", "audience"],
        unique=True,
        postgresql_where=sa.text("thread_type = 'group'"),
    )


def downgrade() -> None:
    op.drop_index("uq_communication_threads_group", table_name="communication_threads")
    op.create_index(
        "uq_communication_threads_group",
        "communication_threads",
        ["group_id"],
        unique=True,
        postgresql_where=sa.text("thread_type = 'group'"),
    )
    op.drop_constraint(
        "ck_communication_threads_direct_audience", "communication_threads", type_="check",
    )
    op.drop_constraint(
        "ck_communication_threads_audience", "communication_threads", type_="check",
    )
    op.drop_column("communication_threads", "audience")

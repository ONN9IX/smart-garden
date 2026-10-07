"""Add announcement create idempotency. Revision ID: 0014; down_revision: 0013."""

import sqlalchemy as sa

from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("announcements", sa.Column("idempotency_key", sa.String(64), nullable=True))
    op.create_index(
        "uq_announcements_idempotency",
        "announcements",
        ["organization_id", "created_by", "idempotency_key"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_announcements_idempotency", table_name="announcements")
    op.drop_column("announcements", "idempotency_key")

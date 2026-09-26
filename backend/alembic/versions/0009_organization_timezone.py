"""Tenant IANA timezone. Revision ID: 0009; down_revision: 0008."""

import sqlalchemy as sa

from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("organizations", sa.Column("timezone", sa.String(64), nullable=True))
    op.execute(sa.text("UPDATE organizations SET timezone = 'Europe/Moscow' WHERE timezone IS NULL"))
    op.alter_column(
        "organizations",
        "timezone",
        existing_type=sa.String(64),
        nullable=False,
        server_default="Europe/Moscow",
    )


def downgrade() -> None:
    op.drop_column("organizations", "timezone")

"""Add digest-only account access tokens. Revision: 0016."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_access_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("guardian_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("purpose", sa.String(length=24), nullable=False),
        sa.Column("token_digest", sa.String(length=64), nullable=False),
        sa.Column("delivery_status", sa.String(length=16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("purpose IN ('activation', 'password_reset')", name="ck_account_access_tokens_purpose"),
        sa.CheckConstraint("delivery_status IN ('pending', 'sent', 'failed')", name="ck_account_access_tokens_delivery_status"),
        sa.CheckConstraint(
            "(guardian_id IS NOT NULL AND employee_id IS NULL) OR (guardian_id IS NULL AND employee_id IS NOT NULL)",
            name="ck_account_access_tokens_single_profile",
        ),
        sa.ForeignKeyConstraint(["employee_id"], ["employees.id"]),
        sa.ForeignKeyConstraint(["guardian_id"], ["guardians.id"]),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_digest"),
    )
    op.create_index("ix_account_access_tokens_user_purpose", "account_access_tokens", ["user_id", "purpose"])
    op.create_index("ix_account_access_tokens_organization_user", "account_access_tokens", ["organization_id", "user_id"])


def downgrade() -> None:
    op.drop_index("ix_account_access_tokens_organization_user", table_name="account_access_tokens")
    op.drop_index("ix_account_access_tokens_user_purpose", table_name="account_access_tokens")
    op.drop_table("account_access_tokens")

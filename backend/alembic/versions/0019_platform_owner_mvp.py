"""Separate platform identities, sessions, Audit, onboarding and commercial metadata."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0019"
down_revision = "0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_operators",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(64), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("totp_secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("last_totp_counter", sa.BigInteger(), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('active','blocked')", name="ck_platform_operator_status"
        ),
    )
    op.create_table(
        "platform_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_operators.id"),
        ),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("purpose", sa.String(16), nullable=False),
        sa.Column("ip_hash", sa.String(64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("mfa_verified_at", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "purpose IN ('session','login_attempt')", name="ck_platform_session_purpose"
        ),
        sa.CheckConstraint(
            "purpose != 'session' OR operator_id IS NOT NULL",
            name="ck_platform_session_identity",
        ),
    )
    op.create_index(
        "ix_platform_sessions_operator_id", "platform_sessions", ["operator_id"]
    )
    op.create_index("ix_platform_sessions_ip_hash", "platform_sessions", ["ip_hash"])
    op.create_table(
        "platform_audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_operators.id"),
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "platform_provisioning_requests",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operator_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("platform_operators.id"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "director_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
            unique=True,
        ),
        sa.Column("request_fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_table(
        "tenant_subscriptions",
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            primary_key=True,
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("plan_code", sa.String(64), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("interval", sa.String(16), nullable=False),
        sa.Column("price_minor", sa.BigInteger(), nullable=False),
        sa.Column("trial_ends_at", sa.DateTime(timezone=True)),
        sa.Column("period_start", sa.DateTime(timezone=True)),
        sa.Column("period_end", sa.DateTime(timezone=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('trial','active','past_due','cancel_at_period_end','cancelled')",
            name="ck_tenant_subscription_status",
        ),
        sa.CheckConstraint(
            "interval IN ('monthly','half_year','yearly')",
            name="ck_tenant_subscription_interval",
        ),
        sa.CheckConstraint(
            "currency = 'RUB' AND price_minor >= 0 AND price_minor <= 1000000000000",
            name="ck_tenant_subscription_price",
        ),
        sa.CheckConstraint(
            "plan_code = 'standard'", name="ck_tenant_subscription_plan"
        ),
        sa.CheckConstraint(
            "period_start IS NULL OR period_end IS NULL OR period_end > period_start",
            name="ck_tenant_subscription_period",
        ),
    )


def downgrade() -> None:
    op.drop_table("tenant_subscriptions")
    op.drop_table("platform_provisioning_requests")
    op.drop_table("platform_audit_events")
    op.drop_index("ix_platform_sessions_ip_hash", table_name="platform_sessions")
    op.drop_index("ix_platform_sessions_operator_id", table_name="platform_sessions")
    op.drop_table("platform_sessions")
    op.drop_table("platform_operators")

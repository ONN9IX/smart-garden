"""Immutable tenant business audit. Revision ID: 0010; down_revision: 0009."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("organizations.id"),
            nullable=False,
        ),
        sa.Column(
            "actor_user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index(
        "ix_audit_events_organization_created_at",
        "audit_events",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "ix_audit_events_organization_entity",
        "audit_events",
        ["organization_id", "entity_type", "entity_id"],
    )
    op.create_index(
        "ix_audit_events_organization_actor_created_at",
        "audit_events",
        ["organization_id", "actor_user_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_audit_events_organization_actor_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_entity", table_name="audit_events")
    op.drop_index("ix_audit_events_organization_created_at", table_name="audit_events")
    op.drop_table("audit_events")

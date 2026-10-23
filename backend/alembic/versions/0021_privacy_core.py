"""Privacy core: metadata only; no legal content is preapproved."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "privacy_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=True),
        sa.Column("document_type", sa.String(length=24), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("operator", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approval_reference", sa.String(length=200), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "document_type IN ('policy', 'notice', 'paper_consent')",
            name="ck_privacy_document_type",
        ),
        sa.CheckConstraint(
            "status = 'draft' OR (approved_at IS NOT NULL AND approval_reference IS NOT NULL AND effective_at IS NOT NULL)",
            name="ck_privacy_document_approval",
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name="ck_privacy_document_status",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_privacy_document_scope",
        "privacy_documents",
        ["organization_id", "status"],
        unique=False,
    )
    op.create_table(
        "privacy_purposes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("version", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("consent_document_id", sa.UUID(), nullable=True),
        sa.Column(
            "subject_categories",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "data_categories", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "operations", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column(
            "access_roles", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("legal_basis", sa.Text(), nullable=True),
        sa.Column("retention", sa.Text(), nullable=True),
        sa.Column("processors", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("locations", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("consent_required", sa.Boolean(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.CheckConstraint(
            "NOT enabled OR (legal_basis IS NOT NULL AND retention IS NOT NULL AND consent_required IS NOT NULL)",
            name="ck_privacy_purpose_basis",
        ),
        sa.ForeignKeyConstraint(
            ["consent_document_id"],
            ["privacy_documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["privacy_documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id", "code", "version", name="uq_privacy_purpose_version"
        ),
    )
    op.create_index(
        op.f("ix_privacy_purposes_organization_id"),
        "privacy_purposes",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "privacy_attestations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("profile_type", sa.String(length=16), nullable=False),
        sa.Column("profile_id", sa.UUID(), nullable=False),
        sa.Column("purpose_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["purpose_id"],
            ["privacy_purposes.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_privacy_attestation_profile",
        "privacy_attestations",
        ["organization_id", "profile_type", "profile_id"],
        unique=False,
    )
    op.create_table(
        "privacy_paper_consents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("purpose_id", sa.UUID(), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("subject_user_id", sa.UUID(), nullable=True),
        sa.Column("child_id", sa.UUID(), nullable=True),
        sa.Column("guardian_id", sa.UUID(), nullable=True),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("received_on", sa.Date(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.UUID(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.CheckConstraint(
            "(subject_user_id IS NOT NULL AND child_id IS NULL AND guardian_id IS NULL) OR (subject_user_id IS NULL AND child_id IS NOT NULL AND guardian_id IS NOT NULL)",
            name="ck_privacy_consent_subject",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
        ),
        sa.ForeignKeyConstraint(
            ["document_id"],
            ["privacy_documents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["guardian_id"],
            ["guardians.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["purpose_id"],
            ["privacy_purposes.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subject_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "actor_user_id",
            "idempotency_key",
            name="uq_privacy_consent_retry",
        ),
    )
    op.create_index(
        op.f("ix_privacy_paper_consents_organization_id"),
        "privacy_paper_consents",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "privacy_requests",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("requester_user_id", sa.UUID(), nullable=False),
        sa.Column("child_id", sa.UUID(), nullable=True),
        sa.Column("kind", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.UUID(), nullable=False),
        sa.Column("request_digest", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(
            ["child_id"],
            ["children.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["requester_user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "organization_id",
            "requester_user_id",
            "idempotency_key",
            name="uq_privacy_request_retry",
        ),
    )
    op.create_index(
        op.f("ix_privacy_requests_organization_id"),
        "privacy_requests",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "privacy_consent_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("consent_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('recorded', 'withdrawn')", name="ck_privacy_consent_action"
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["consent_id"],
            ["privacy_paper_consents.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("consent_id", "action", name="uq_privacy_consent_event"),
    )
    op.create_index(
        op.f("ix_privacy_consent_events_organization_id"),
        "privacy_consent_events",
        ["organization_id"],
        unique=False,
    )
    op.create_table(
        "privacy_request_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("request_id", sa.UUID(), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("decision_code", sa.String(length=32), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["privacy_requests.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_privacy_request_events_organization_id"),
        "privacy_request_events",
        ["organization_id"],
        unique=False,
    )

    # Legal evidence is append-only even for an accidental ORM writer.
    op.execute("""
        CREATE FUNCTION privacy_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF TG_TABLE_NAME = 'privacy_documents' AND TG_OP = 'UPDATE'
               AND OLD.status = 'published' AND NEW.status = 'retired'
               AND (to_jsonb(OLD) - 'status') = (to_jsonb(NEW) - 'status') THEN
                RETURN NEW;
            END IF;
            RAISE EXCEPTION 'privacy evidence is immutable';
        END; $$;
    """)
    for table in (
        "privacy_documents",
        "privacy_purposes",
        "privacy_attestations",
        "privacy_paper_consents",
        "privacy_consent_events",
        "privacy_request_events",
    ):
        op.execute(
            f"CREATE TRIGGER privacy_immutable BEFORE UPDATE OR DELETE ON {table} "
            "FOR EACH ROW EXECUTE FUNCTION privacy_immutable()"
        )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_privacy_request_events_organization_id"),
        table_name="privacy_request_events",
    )
    op.drop_table("privacy_request_events")
    op.drop_index(
        op.f("ix_privacy_consent_events_organization_id"),
        table_name="privacy_consent_events",
    )
    op.drop_table("privacy_consent_events")
    op.drop_index(
        op.f("ix_privacy_requests_organization_id"), table_name="privacy_requests"
    )
    op.drop_table("privacy_requests")
    op.drop_index(
        op.f("ix_privacy_paper_consents_organization_id"),
        table_name="privacy_paper_consents",
    )
    op.drop_table("privacy_paper_consents")
    op.drop_index("ix_privacy_attestation_profile", table_name="privacy_attestations")
    op.drop_table("privacy_attestations")
    op.drop_index(
        op.f("ix_privacy_purposes_organization_id"), table_name="privacy_purposes"
    )
    op.drop_table("privacy_purposes")
    op.drop_index("ix_privacy_document_scope", table_name="privacy_documents")
    op.drop_table("privacy_documents")
    op.execute("DROP FUNCTION privacy_immutable()")

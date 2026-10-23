"""Minimal legal metadata. No scans, signatures, passport fields or request text."""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LegalDocument(Base):
    __tablename__ = "privacy_documents"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'retired')",
            name="ck_privacy_document_status",
        ),
        CheckConstraint(
            "document_type IN ('policy', 'notice', 'paper_consent')",
            name="ck_privacy_document_type",
        ),
        CheckConstraint(
            "status = 'draft' OR (approved_at IS NOT NULL AND approval_reference IS NOT NULL AND effective_at IS NOT NULL)",
            name="ck_privacy_document_approval",
        ),
        Index("ix_privacy_document_scope", "organization_id", "status"),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # NULL is provider's own legal context, never a tenant wildcard.
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id")
    )
    document_type: Mapped[str] = mapped_column(String(24))
    version: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    operator: Mapped[dict[str, Any]] = mapped_column(JSONB)
    content: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(16), default="draft")
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approval_reference: Mapped[str | None] = mapped_column(String(200))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class ProcessingPurpose(Base):
    __tablename__ = "privacy_purposes"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "code", "version", name="uq_privacy_purpose_version"
        ),
        CheckConstraint(
            "NOT enabled OR (legal_basis IS NOT NULL AND retention IS NOT NULL AND consent_required IS NOT NULL)",
            name="ck_privacy_purpose_basis",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    code: Mapped[str] = mapped_column(String(40))
    version: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(200))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("privacy_documents.id"))
    consent_document_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("privacy_documents.id")
    )
    subject_categories: Mapped[list[str]] = mapped_column(JSONB)
    data_categories: Mapped[list[str]] = mapped_column(JSONB)
    operations: Mapped[list[str]] = mapped_column(JSONB)
    access_roles: Mapped[list[str]] = mapped_column(JSONB)
    legal_basis: Mapped[str | None] = mapped_column(Text)
    retention: Mapped[str | None] = mapped_column(Text)
    # NULL means not established, not "no contractors" or "no consent needed".
    processors: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    locations: Mapped[list[str] | None] = mapped_column(JSONB, nullable=True)
    consent_required: Mapped[bool | None] = mapped_column(Boolean)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)


class BasisAttestation(Base):
    __tablename__ = "privacy_attestations"
    __table_args__ = (
        Index(
            "ix_privacy_attestation_profile",
            "organization_id",
            "profile_type",
            "profile_id",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    profile_type: Mapped[str] = mapped_column(String(16))
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    purpose_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("privacy_purposes.id"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PaperConsent(Base):
    __tablename__ = "privacy_paper_consents"
    __table_args__ = (
        CheckConstraint(
            "(subject_user_id IS NOT NULL AND child_id IS NULL AND guardian_id IS NULL) OR (subject_user_id IS NULL AND child_id IS NOT NULL AND guardian_id IS NOT NULL)",
            name="ck_privacy_consent_subject",
        ),
        UniqueConstraint(
            "organization_id",
            "actor_user_id",
            "idempotency_key",
            name="uq_privacy_consent_retry",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    purpose_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("privacy_purposes.id"))
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("privacy_documents.id"))
    subject_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    child_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("children.id"))
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("guardians.id"))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    received_on: Mapped[date] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    request_digest: Mapped[str] = mapped_column(String(64))


class ConsentEvent(Base):
    __tablename__ = "privacy_consent_events"
    __table_args__ = (
        UniqueConstraint("consent_id", "action", name="uq_privacy_consent_event"),
        CheckConstraint(
            "action IN ('recorded', 'withdrawn')", name="ck_privacy_consent_action"
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    consent_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("privacy_paper_consents.id")
    )
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PrivacyRequest(Base):
    __tablename__ = "privacy_requests"
    __table_args__ = (
        UniqueConstraint(
            "organization_id",
            "requester_user_id",
            "idempotency_key",
            name="uq_privacy_request_retry",
        ),
    )
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    requester_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    child_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("children.id"))
    kind: Mapped[str] = mapped_column(String(24))
    status: Mapped[str] = mapped_column(String(24), default="submitted")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))
    request_digest: Mapped[str] = mapped_column(String(64))


class RequestEvent(Base):
    __tablename__ = "privacy_request_events"
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"), index=True
    )
    request_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("privacy_requests.id"))
    actor_user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(24))
    decision_code: Mapped[str | None] = mapped_column(String(32))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

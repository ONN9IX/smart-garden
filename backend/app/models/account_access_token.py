"""One-time account activation and password-reset grants; raw secrets are never persisted."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AccountAccessToken(Base):
    __tablename__ = "account_access_tokens"
    __table_args__ = (
        CheckConstraint("purpose IN ('activation', 'password_reset')", name="ck_account_access_tokens_purpose"),
        CheckConstraint("delivery_status IN ('pending', 'sent', 'failed')", name="ck_account_access_tokens_delivery_status"),
        CheckConstraint(
            "(guardian_id IS NOT NULL AND employee_id IS NULL) OR (guardian_id IS NULL AND employee_id IS NOT NULL)",
            name="ck_account_access_tokens_single_profile",
        ),
        Index("ix_account_access_tokens_user_purpose", "user_id", "purpose"),
        Index("ix_account_access_tokens_organization_user", "organization_id", "user_id"),
        Index(
            "uq_account_access_tokens_effective_user_purpose",
            "user_id", "purpose", unique=True,
            postgresql_where=text("used_at IS NULL AND revoked_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("guardians.id"))
    employee_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"))
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    purpose: Mapped[str] = mapped_column(String(24), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


"""PII-minimized idempotency receipt for confirmed initial setup batches."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class InitialSetupBatch(Base):
    __tablename__ = "initial_setup_batches"
    __table_args__ = (
        UniqueConstraint("organization_id", "idempotency_key", name="uq_initial_setup_batch_key"),
        CheckConstraint("employee_count >= 0", name="ck_initial_setup_employee_count"),
        CheckConstraint("schedule_count >= 0", name="ck_initial_setup_schedule_count"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False,
    )
    idempotency_key: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    request_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    employee_count: Mapped[int] = mapped_column(Integer, nullable=False)
    schedule_count: Mapped[int] = mapped_column(Integer, nullable=False)
    created_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(),
    )

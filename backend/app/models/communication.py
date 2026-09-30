"""Immutable Stage 6 Group and direct communication records."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommunicationThread(Base):
    __tablename__ = "communication_threads"
    __table_args__ = (
        CheckConstraint("thread_type IN ('group', 'direct')", name="ck_communication_threads_type"),
        CheckConstraint(
            "(thread_type = 'group' AND child_id IS NULL AND guardian_id IS NULL) OR "
            "(thread_type = 'direct' AND child_id IS NOT NULL AND guardian_id IS NOT NULL)",
            name="ck_communication_threads_context",
        ),
        Index(
            "uq_communication_threads_group", "group_id", unique=True,
            postgresql_where=text("thread_type = 'group'"),
        ),
        Index(
            "uq_communication_threads_direct", "group_id", "child_id", "guardian_id", unique=True,
            postgresql_where=text("thread_type = 'direct'"),
        ),
        Index("ix_communication_threads_organization_group", "organization_id", "group_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    thread_type: Mapped[str] = mapped_column(String(16), nullable=False)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    child_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("children.id"))
    guardian_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("guardians.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class CommunicationMessage(Base):
    __tablename__ = "communication_messages"
    __table_args__ = (
        CheckConstraint("length(btrim(body)) > 0", name="ck_communication_messages_body_nonempty"),
        Index("ix_communication_messages_organization_thread_created", "organization_id", "thread_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    thread_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("communication_threads.id"), nullable=False)
    sender_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(String(4000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

"""Immediately published, tenant-scoped operational announcement."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.group import Group


class Announcement(Base):
    __tablename__ = "announcements"
    __table_args__ = (
        CheckConstraint("target_type IN ('all', 'group')", name="ck_announcements_target_type"),
        CheckConstraint("status IN ('active', 'archived')", name="ck_announcements_status"),
        CheckConstraint(
            "(target_type = 'all' AND group_id IS NULL) OR "
            "(target_type = 'group' AND group_id IS NOT NULL)",
            name="ck_announcements_target_group",
        ),
        CheckConstraint("length(btrim(title)) > 0", name="ck_announcements_title_nonempty"),
        CheckConstraint("length(btrim(body)) > 0", name="ck_announcements_body_nonempty"),
        Index("ix_announcements_organization_status_created_at", "organization_id", "status", "created_at"),
        Index("ix_announcements_organization_group", "organization_id", "group_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    target_type: Mapped[str] = mapped_column(String(16), nullable=False)
    group_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"))
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(String(2000), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )

    group: Mapped["Group | None"] = relationship(lazy="joined")

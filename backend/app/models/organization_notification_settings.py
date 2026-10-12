"""Tenant-owned presentation policy for routine operational signals."""

import uuid
from datetime import datetime, time

from sqlalchemy import Boolean, DateTime, ForeignKey, Time, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class OrganizationNotificationSettings(Base):
    __tablename__ = "organization_notification_settings"

    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True,
    )
    show_informational_notifications: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    attendance_checkpoint_time: Mapped[time | None] = mapped_column(Time)
    schedule_missing_alert_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now(),
    )

"""Manual child attendance; group is a historical snapshot, never inferred after transfer."""

import uuid
from datetime import date, datetime, time
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.child import Child
    from app.models.group import Group


class Attendance(Base):
    __tablename__ = "attendance"
    __table_args__ = (
        CheckConstraint("status IN ('present', 'absent', 'unknown')", name="ck_attendance_status"),
        CheckConstraint(
            "(status = 'present' AND (departure_time IS NULL OR arrival_time IS NOT NULL) "
            "AND (departure_time IS NULL OR departure_time >= arrival_time)) "
            "OR (status IN ('absent', 'unknown') AND arrival_time IS NULL AND departure_time IS NULL)",
            name="ck_attendance_time_state",
        ),
        UniqueConstraint("child_id", "date", name="uq_attendance_child_date"),
        Index("ix_attendance_organization_date_group", "organization_id", "date", "group_id"),
        Index("ix_attendance_organization_date_status", "organization_id", "date", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)
    child_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("children.id"), nullable=False)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    arrival_time: Mapped[time | None] = mapped_column(Time(timezone=False))
    departure_time: Mapped[time | None] = mapped_column(Time(timezone=False))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    updated_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    child: Mapped["Child"] = relationship()
    group: Mapped["Group"] = relationship()

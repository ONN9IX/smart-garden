"""Explicit many-to-many TEACHER Employee assignment to a tenant Group."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TeacherGroupAssignment(Base):
    __tablename__ = "teacher_group_assignments"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'archived')", name="ck_teacher_group_assignments_status"),
        UniqueConstraint("employee_id", "group_id", name="uq_teacher_group_assignments_employee_group"),
        Index(
            "ix_teacher_group_assignments_organization_employee_status",
            "organization_id", "employee_id", "status",
        ),
        Index(
            "ix_teacher_group_assignments_organization_group_status",
            "organization_id", "group_id", "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False,
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("employees.id"), nullable=False)
    group_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    assigned_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

"""Tenant root: one organization corresponds to one kindergarten."""

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates

from app.core.organization_time import (
    DEFAULT_ORGANIZATION_TIMEZONE,
    validate_iana_timezone,
)
from app.db.base import Base


class Organization(Base):
    __tablename__ = "organizations"
    __table_args__ = (
        CheckConstraint("status IN ('active', 'blocked', 'archived')"),
        CheckConstraint(
            "operating_profile IN ('KINDERGARTEN', 'GYMNASTICS')",
            name="ck_organizations_operating_profile",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    timezone: Mapped[str] = mapped_column(
        String(64), nullable=False, default=DEFAULT_ORGANIZATION_TIMEZONE,
        server_default=DEFAULT_ORGANIZATION_TIMEZONE,
    )
    operating_profile: Mapped[str] = mapped_column(
        String(16), nullable=False, default="KINDERGARTEN", server_default="KINDERGARTEN",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @validates("timezone")
    def validate_timezone(self, _key: str, value: str) -> str:
        return validate_iana_timezone(value)

    @validates("operating_profile")
    def validate_operating_profile(self, _key: str, value: str) -> str:
        if value not in {"KINDERGARTEN", "GYMNASTICS"}:
            raise ValueError("Unsupported organization operating profile")
        return value

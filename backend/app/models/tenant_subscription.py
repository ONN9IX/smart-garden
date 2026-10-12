"""Commercial metadata only; never changes Organization access status."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TenantSubscription(Base):
    __tablename__ = "tenant_subscriptions"
    __table_args__ = (
        CheckConstraint(
            "status IN ('trial','active','past_due','cancel_at_period_end','cancelled')",
            name="ck_tenant_subscription_status",
        ),
        CheckConstraint(
            "interval IN ('monthly','half_year','yearly')",
            name="ck_tenant_subscription_interval",
        ),
        CheckConstraint(
            "currency = 'RUB' AND price_minor >= 0 AND price_minor <= 1000000000000",
            name="ck_tenant_subscription_price",
        ),
        CheckConstraint("plan_code = 'standard'", name="ck_tenant_subscription_plan"),
        CheckConstraint(
            "period_start IS NULL OR period_end IS NULL OR period_end > period_start",
            name="ck_tenant_subscription_period",
        ),
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), primary_key=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    plan_code: Mapped[str] = mapped_column(String(64), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    price_minor: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

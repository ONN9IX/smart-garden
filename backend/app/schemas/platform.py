"""Whitelisted platform input/response shapes; never serialize tenant User rows."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.organization_time import validate_iana_timezone
from app.core.security import normalize_username


class StrictInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LoginInput(StrictInput):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=10, max_length=128)


class MFAInput(StrictInput):
    code: str = Field(pattern=r"^\d{6}$")


class SubscriptionInput(StrictInput):
    status: Literal["trial", "active", "past_due", "cancel_at_period_end", "cancelled"]
    plan_code: Literal["standard"] = "standard"
    currency: Literal["RUB"] = "RUB"
    interval: Literal["monthly", "half_year", "yearly"] = "monthly"
    price_minor: int = Field(ge=0, le=1000000000000, strict=True)
    trial_ends_at: datetime | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None

    @field_validator("trial_ends_at", "period_start", "period_end")
    @classmethod
    def aware_time(cls, value: datetime | None) -> datetime | None:
        if value and value.utcoffset() is None:
            raise ValueError("Timezone required")
        return value

    @model_validator(mode="after")
    def periods(self):
        if self.status == "trial" and self.trial_ends_at is None:
            raise ValueError("Trial end required")
        if (
            self.period_start
            and self.period_end
            and self.period_end <= self.period_start
        ):
            raise ValueError("Invalid period")
        return self


class CreateOrganizationInput(StrictInput):
    idempotency_key: UUID
    name: str = Field(min_length=1, max_length=200)
    timezone: str = Field(max_length=64)
    director_username: str = Field(min_length=3, max_length=64)
    credential_handoff_confirmed: Literal[True]
    subscription: SubscriptionInput

    @field_validator("name")
    @classmethod
    def name_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Name required")
        return value.strip()

    @field_validator("timezone")
    @classmethod
    def timezone_name(cls, value: str) -> str:
        return validate_iana_timezone(value)

    @field_validator("director_username")
    @classmethod
    def username(cls, value: str) -> str:
        return normalize_username(value)


class LifecycleInput(StrictInput):
    confirmation_name: str = Field(min_length=1, max_length=200)
    reason: Literal["owner_request", "security", "administrative"]


class SubscriptionChangeInput(StrictInput):
    confirmation_name: str = Field(min_length=1, max_length=200)
    subscription: SubscriptionInput


class SubscriptionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    status: str
    plan_code: str
    currency: str
    interval: str
    price_minor: int
    trial_ends_at: datetime | None
    period_start: datetime | None
    period_end: datetime | None


class OrganizationView(BaseModel):
    id: UUID
    name: str
    timezone: str
    status: str
    created_at: datetime
    onboarding_status: Literal[
        "not_platform_provisioned", "password_change_required", "active", "blocked"
    ]
    subscription: SubscriptionView | None


class ProvisioningView(BaseModel):
    organization: OrganizationView
    temporary_password: str | None = None
    replayed: bool


class IdentityView(BaseModel):
    username: str
    role: Literal["PLATFORM_OWNER"] = "PLATFORM_OWNER"
    csrf_token: str
    credential_handoff_enabled: bool
    step_up_required: bool


class AuditView(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    operator_id: UUID | None
    organization_id: UUID | None
    action: str
    details: dict
    created_at: datetime

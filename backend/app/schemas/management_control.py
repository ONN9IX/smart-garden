"""Safe management Control transport; tenant and owner are server-derived."""

from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class OperationalAlert(BaseModel):
    alert_key: str
    kind: str
    priority: Literal["important", "info"]
    title: str
    context: str
    action_href: str
    viewed_at: datetime | None = None
    snoozed_until: datetime | None = None


class ControlNotification(BaseModel):
    id: UUID
    title: str
    priority: Literal["important", "info"]
    read_at: datetime | None
    created_at: datetime


class ControlSummary(BaseModel):
    new: int
    important: int
    snoozed: int


class ManagementControl(BaseModel):
    alerts: list[OperationalAlert]
    event_notifications: list[ControlNotification]
    summary: ControlSummary


class AlertViewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alert_key: str = Field(min_length=1, max_length=160)


class AlertSnoozeRequest(AlertViewRequest):
    duration: Literal["one_hour", "next_morning"]


class OrganizationNotificationSettingsResponse(BaseModel):
    show_informational_notifications: bool
    attendance_checkpoint_time: time | None
    schedule_missing_alert_enabled: bool


class OrganizationNotificationSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    show_informational_notifications: bool | None = None
    attendance_checkpoint_time: time | None = None
    schedule_missing_alert_enabled: bool | None = None

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("A nonempty patch is required")
        if self.show_informational_notifications is None and "show_informational_notifications" in self.model_fields_set:
            raise ValueError("Informational visibility must be boolean")
        if self.schedule_missing_alert_enabled is None and "schedule_missing_alert_enabled" in self.model_fields_set:
            raise ValueError("Schedule visibility must be boolean")
        return self


class SecurityStatus(BaseModel):
    blocked_accounts: int
    failed_or_expired_parent_invites: int

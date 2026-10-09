"""Stage 6 DIRECTOR/ADMIN management transport; tenant and actor fields stay server-owned."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.core.organization_time import validate_iana_timezone


def _trim(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


class ManagementAttentionItem(BaseModel):
    kind: str
    entity_type: str | None = None
    entity_id: UUID | None = None
    count: int | None = None


class ManagementTodayGroup(BaseModel):
    group_id: UUID
    group_name: str
    active_children: int
    present: int
    on_site: int
    departed: int
    absent: int
    unknown: int
    needs_arrival: int
    has_active_teacher: bool
    has_active_weekly_schedule: bool


class ManagementToday(BaseModel):
    date: date
    active_children: int
    present: int
    on_site: int
    departed: int
    absent: int
    unknown: int
    needs_arrival: int
    active_groups: int
    active_employees: int
    groups_without_active_teacher_assignment: int
    open_tasks: int
    overdue_tasks: int
    open_incidents: int
    unread_notifications: int
    groups: list[ManagementTodayGroup]
    attention_items: list[ManagementAttentionItem]


class TeacherAccountView(BaseModel):
    user_id: UUID
    username: str
    status: Literal["active", "blocked"]
    must_change_password: bool


class TeacherAssignmentView(BaseModel):
    id: UUID
    group_id: UUID
    group_name: str
    status: Literal["active", "archived"]


class TeacherProjection(BaseModel):
    employee_id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    position: str
    employee_status: Literal["active", "archived"]
    account: TeacherAccountView | None
    assignments: list[TeacherAssignmentView]
    eligible_for_teacher_account: bool


class TeacherProjectionList(BaseModel):
    items: list[TeacherProjection]


class ScheduleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: UUID
    weekday: int = Field(ge=0, le=6)
    start_time: time
    end_time: time
    title: str = Field(min_length=1, max_length=160)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: str) -> str:
        return str(value).strip()


class SchedulePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: UUID | None = None
    weekday: int | None = Field(default=None, ge=0, le=6)
    start_time: time | None = None
    end_time: time | None = None
    title: str | None = Field(default=None, min_length=1, max_length=160)

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        return _trim(value)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("A nonempty patch is required")
        return self


class ScheduleItemResponse(BaseModel):
    id: UUID
    group_id: UUID
    weekday: int
    start_time: time
    end_time: time
    title: str
    status: Literal["active", "archived"]
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime


class ScheduleList(BaseModel):
    items: list[ScheduleItemResponse]


class ManagementMessageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    body: str = Field(min_length=1, max_length=4000)
    audience: Literal["all", "parents", "teachers"] = "all"

    @field_validator("body", mode="before")
    @classmethod
    def trim_body(cls, value: str) -> str:
        return str(value).strip()


class ManagementMessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    group_id: UUID
    sender_user_id: UUID
    sender_role: Literal["DIRECTOR", "ADMIN", "TEACHER", "PARENT"]
    sender_name: str
    audience: Literal["all", "parents", "teachers"]
    body: str
    created_at: datetime


class ManagementMessageList(BaseModel):
    items: list[ManagementMessageResponse]


class DiaryEntryResponse(BaseModel):
    id: UUID
    child_id: UUID
    group_id: UUID
    date: date
    author_user_id: UUID
    note: str
    created_at: datetime
    updated_at: datetime


class DiaryEntryList(BaseModel):
    items: list[DiaryEntryResponse]


class PollCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: UUID
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=10)
    closes_at: datetime | None = None

    @field_validator("question", mode="before")
    @classmethod
    def trim_question(cls, value: str) -> str:
        return str(value).strip()

    @field_validator("options")
    @classmethod
    def validate_options(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 240 for value in cleaned):
            raise ValueError("Poll options must be nonempty and at most 240 characters")
        if len({value.casefold() for value in cleaned}) != len(cleaned):
            raise ValueError("Poll options must be unique")
        return cleaned


class PollOptionResult(BaseModel):
    id: UUID
    label: str
    sort_order: int
    vote_count: int


class PollResponse(BaseModel):
    id: UUID
    group_id: UUID
    question: str
    status: Literal["active", "closed", "archived"]
    closes_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
    options: list[PollOptionResult]
    total_votes: int


class PollList(BaseModel):
    items: list[PollResponse]


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: UUID
    child_id: UUID | None = None
    occurred_at: datetime
    category: Literal["safety", "behavior", "operational", "other"]
    description: str = Field(min_length=1, max_length=4000)

    @field_validator("description", mode="before")
    @classmethod
    def trim_description(cls, value: str) -> str:
        return str(value).strip()


class IncidentPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    occurred_at: datetime | None = None
    category: Literal["safety", "behavior", "operational", "other"] | None = None
    description: str | None = Field(default=None, min_length=1, max_length=4000)
    status: Literal["open", "resolved"] | None = None

    @field_validator("description", mode="before")
    @classmethod
    def trim_description(cls, value: str | None) -> str | None:
        return _trim(value)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("A nonempty patch is required")
        return self


class IncidentResponse(BaseModel):
    id: UUID
    group_id: UUID
    child_id: UUID | None
    occurred_at: datetime
    category: Literal["safety", "behavior", "operational", "other"]
    description: str
    status: Literal["open", "resolved"]
    reported_by: UUID
    resolved_by: UUID | None
    created_at: datetime
    updated_at: datetime


class IncidentList(BaseModel):
    items: list[IncidentResponse]


class TeacherTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignee_employee_id: UUID
    group_id: UUID | None = None
    title: str = Field(min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: str) -> str:
        return str(value).strip()

    @field_validator("description", mode="before")
    @classmethod
    def trim_description(cls, value: str | None) -> str | None:
        return _trim(value) or None


class TeacherTaskPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    assignee_employee_id: UUID | None = None
    group_id: UUID | None = None
    title: str | None = Field(default=None, min_length=1, max_length=240)
    description: str | None = Field(default=None, max_length=4000)
    due_at: datetime | None = None
    status: Literal["open", "in_progress", "done"] | None = None

    @field_validator("title", mode="before")
    @classmethod
    def trim_title(cls, value: str | None) -> str | None:
        return _trim(value)

    @field_validator("description", mode="before")
    @classmethod
    def trim_description(cls, value: str | None) -> str | None:
        return _trim(value)

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("A nonempty patch is required")
        return self


class TeacherTaskResponse(BaseModel):
    id: UUID
    assignee_employee_id: UUID
    group_id: UUID | None
    title: str
    description: str | None
    due_at: datetime | None
    status: Literal["open", "in_progress", "done", "cancelled"]
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class TeacherTaskList(BaseModel):
    items: list[TeacherTaskResponse]


class NotificationResponse(BaseModel):
    id: UUID
    kind: str
    entity_type: str
    entity_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationResponse]


class DocumentNoticeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    recipient_user_id: UUID
    title: str = Field(min_length=1, max_length=240)
    kind: str = Field(min_length=1, max_length=64)
    requires_ack: bool = False

    @field_validator("title", "kind", mode="before")
    @classmethod
    def trim_required(cls, value: str) -> str:
        return str(value).strip()


class DocumentNoticeResponse(BaseModel):
    id: UUID
    recipient_user_id: UUID
    title: str
    kind: str
    requires_ack: bool
    issued_by: UUID
    acknowledged_at: datetime | None
    created_at: datetime


class DocumentNoticeList(BaseModel):
    items: list[DocumentNoticeResponse]


class PhotoConsentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    child_id: UUID
    effective_from: datetime
    effective_to: datetime | None = None

    @model_validator(mode="after")
    def ordered_period(self):
        if self.effective_to is not None and self.effective_to < self.effective_from:
            raise ValueError("effective_to must not precede effective_from")
        return self


class PhotoConsentResponse(BaseModel):
    id: UUID
    child_id: UUID
    status: Literal["granted", "withdrawn"]
    scope: Literal["group_photo_report"]
    effective_from: datetime
    effective_to: datetime | None
    recorded_by: UUID
    created_at: datetime
    updated_at: datetime


class PhotoConsentList(BaseModel):
    items: list[PhotoConsentResponse]


class ManagementSettingsResponse(BaseModel):
    id: UUID
    name: str
    timezone: str


class ManagementSettingsPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None, min_length=1, max_length=200)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        return _trim(value)

    @field_validator("timezone")
    @classmethod
    def validate_timezone(cls, value: str | None) -> str | None:
        return validate_iana_timezone(value) if value is not None else None

    @model_validator(mode="after")
    def nonempty(self):
        if not self.model_fields_set:
            raise ValueError("A nonempty patch is required")
        return self

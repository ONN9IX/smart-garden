"""Minimized TEACHER/PARENT Stage 6 request and response contracts."""

from __future__ import annotations

from datetime import date as Date
from datetime import datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GroupSummary(BaseModel):
    id: UUID
    name: str


class ChildSummary(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None


class GuardianContext(BaseModel):
    id: UUID
    child_id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    relation_type: Literal["mother", "father", "legal_guardian", "other"]
    phone: str | None
    email: str | None
    can_message: bool


class ScheduleItemResponse(BaseModel):
    id: UUID
    group_id: UUID
    weekday: int
    start_time: time
    end_time: time
    title: str


class ParentAttendanceSummary(BaseModel):
    status: Literal["present", "absent", "unknown"]
    arrival_time: time | None
    departure_time: time | None


class ParentTodayResponse(BaseModel):
    date: Date
    child: ChildSummary
    group: GroupSummary
    attendance: ParentAttendanceSummary
    schedule: list[ScheduleItemResponse]


class ThreadResponse(BaseModel):
    id: UUID
    thread_type: Literal["group", "direct"]
    group_id: UUID
    audience: Literal["all", "parents", "teachers"]
    child_id: UUID | None
    guardian_id: UUID | None
    created_at: datetime


class MessageResponse(BaseModel):
    id: UUID
    thread_id: UUID
    sender_user_id: UUID
    sender_role: Literal["DIRECTOR", "ADMIN", "TEACHER", "PARENT"]
    sender_name: str
    body: str
    created_at: datetime


class MessageCreate(StrictModel):
    body: str = Field(min_length=1, max_length=4000)

    @field_validator("body")
    @classmethod
    def trim_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message body is required")
        return value


class TeacherDirectThreadCreate(StrictModel):
    child_id: UUID
    guardian_id: UUID


class ParentDirectThreadCreate(StrictModel):
    child_id: UUID


class DiaryCreate(StrictModel):
    child_id: UUID
    date: Date
    note: str = Field(min_length=1, max_length=4000)

    @field_validator("note")
    @classmethod
    def trim_note(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Diary note is required")
        return value


class DiaryPatch(StrictModel):
    date: Date | None = None
    note: str | None = Field(None, min_length=1, max_length=4000)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set or any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("At least one non-null change is required")
        return self

    @field_validator("note")
    @classmethod
    def trim_optional_note(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Diary note is required")
        return value


class DiaryResponse(BaseModel):
    id: UUID
    child_id: UUID
    group_id: UUID
    date: Date
    author_user_id: UUID
    note: str
    created_at: datetime
    updated_at: datetime


class TeacherAnnouncementCreate(StrictModel):
    group_id: UUID
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("title", "body")
    @classmethod
    def trim_announcement(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Announcement text is required")
        return value


class TeacherAnnouncementPatch(StrictModel):
    title: str | None = Field(None, min_length=1, max_length=120)
    body: str | None = Field(None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set or any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("At least one non-null change is required")
        return self

    @field_validator("title", "body")
    @classmethod
    def trim_optional_announcement(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Announcement text is required")
        return value


class AnnouncementResponse(BaseModel):
    id: UUID
    target_type: Literal["all", "group"]
    group_id: UUID | None
    title: str
    body: str
    status: Literal["active", "archived"]
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class PollCreate(StrictModel):
    group_id: UUID
    question: str = Field(min_length=1, max_length=500)
    options: list[str] = Field(min_length=2, max_length=12)
    closes_at: datetime | None = None

    @field_validator("question")
    @classmethod
    def trim_question(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Poll question is required")
        return value

    @field_validator("options")
    @classmethod
    def validate_options(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]
        if any(not value or len(value) > 240 for value in cleaned) or len(set(cleaned)) != len(cleaned):
            raise ValueError("Poll options must be unique nonempty labels")
        return cleaned


class PollOptionResponse(BaseModel):
    id: UUID
    label: str
    sort_order: int


class PollResponse(BaseModel):
    id: UUID
    group_id: UUID
    question: str
    status: Literal["active", "closed", "archived"]
    closes_at: datetime | None
    created_by: UUID
    options: list[PollOptionResponse]
    selected_option_id: UUID | None = None
    created_at: datetime


class PollVoteCreate(StrictModel):
    option_id: UUID


class IncidentCreate(StrictModel):
    group_id: UUID
    child_id: UUID | None = None
    occurred_at: datetime
    category: Literal["safety", "behavior", "operational", "other"]
    description: str = Field(min_length=1, max_length=4000)

    @field_validator("description")
    @classmethod
    def trim_description(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Incident description is required")
        return value


class IncidentPatch(StrictModel):
    occurred_at: datetime | None = None
    category: Literal["safety", "behavior", "operational", "other"] | None = None
    description: str | None = Field(None, min_length=1, max_length=4000)
    status: Literal["open", "resolved"] | None = None

    @model_validator(mode="after")
    def require_change(self):
        if not self.model_fields_set or any(getattr(self, field) is None for field in self.model_fields_set):
            raise ValueError("At least one non-null change is required")
        return self

    @field_validator("description")
    @classmethod
    def trim_optional_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Incident description is required")
        return value


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


class TaskStatusPatch(StrictModel):
    status: Literal["open", "in_progress", "done"]


class TaskResponse(BaseModel):
    id: UUID
    group_id: UUID | None
    title: str
    description: str | None
    due_at: datetime | None
    status: Literal["open", "in_progress", "done", "cancelled"]
    created_at: datetime
    updated_at: datetime


class NotificationResponse(BaseModel):
    id: UUID
    kind: str
    entity_type: str
    entity_id: UUID | None
    read_at: datetime | None
    created_at: datetime


class DocumentNoticeResponse(BaseModel):
    id: UUID
    title: str
    kind: str
    requires_ack: bool
    acknowledged_at: datetime | None
    created_at: datetime


class PhotoConsentResponse(BaseModel):
    id: UUID
    child_id: UUID
    status: Literal["granted", "withdrawn"]
    scope: Literal["group_photo_report"]
    effective_from: datetime
    effective_to: datetime | None


class PhotoResponse(BaseModel):
    id: UUID
    group_id: UUID
    child_ids: list[UUID]
    mime_type: str
    size_bytes: int
    captured_at: datetime | None
    status: Literal["active", "restricted", "removed"]
    created_at: datetime


class AttendanceSummary(BaseModel):
    group_id: UUID
    present: int
    on_site: int
    departed: int
    absent: int
    unknown: int
    needs_arrival: int


class TodayResponse(BaseModel):
    date: Date
    groups: list[GroupSummary]
    schedule: list[ScheduleItemResponse]
    attendance: list[AttendanceSummary]
    tasks: list[TaskResponse]
    notifications: list[NotificationResponse]
    unread_communication_count: int

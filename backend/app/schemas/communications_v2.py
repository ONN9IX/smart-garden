"""Strict, minimized Communications v2 contracts."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MessageCreateV2(StrictModel):
    body: str = Field(min_length=1, max_length=4000)
    client_message_id: UUID

    @field_validator("body")
    @classmethod
    def trim_body(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message body is required")
        return value


class DirectThreadCreateV2(StrictModel):
    child_id: UUID
    teacher_employee_id: UUID | None = None
    guardian_id: UUID | None = None


class ReadCursorCreate(StrictModel):
    last_read_message_id: UUID


class ThreadSummaryV2(BaseModel):
    id: UUID
    thread_type: Literal["group", "direct"]
    audience: Literal["all", "parents", "teachers"]
    group_id: UUID
    group_name: str
    child_id: UUID | None
    child_name: str | None
    guardian_id: UUID | None
    teacher_employee_id: UUID | None
    teacher_name: str | None
    last_message_id: UUID | None
    last_message_at: datetime | None
    preview: str | None
    unread_count: int


class TeacherOption(BaseModel):
    employee_id: UUID
    display_name: str
    group_id: UUID
    group_name: str


class ReadStateResponse(BaseModel):
    thread_id: UUID
    last_read_message_id: UUID
    last_read_at: datetime


class AnnouncementSummaryV2(BaseModel):
    id: UUID
    target_type: Literal["all", "group"]
    audience: Literal["all", "parents", "staff"]
    group_id: UUID | None
    group_name: str | None
    title: str
    body: str
    published_at: datetime
    status: Literal["active", "archived"]
    archived_at: datetime | None
    unread: bool
    recipient_count: int = 0
    can_manage: bool = False


class AnnouncementCreateV2(StrictModel):
    target_type: Literal["all", "group"]
    group_id: UUID | None = None
    audience: Literal["all", "parents", "staff"] = "all"
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=2000)

    @field_validator("title", "body")
    @classmethod
    def trim_announcement(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Announcement text is required")
        return value

    @model_validator(mode="after")
    def check_target_group(self):
        if (self.target_type == "group") != (self.group_id is not None):
            raise ValueError("Announcement target is invalid")
        return self


class AnnouncementPatchV2(StrictModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, min_length=1, max_length=2000)

    @field_validator("title", "body")
    @classmethod
    def trim_optional_announcement(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Announcement text is required")
        return value


class AnnouncementReadResponse(BaseModel):
    announcement_id: UUID
    read_at: datetime

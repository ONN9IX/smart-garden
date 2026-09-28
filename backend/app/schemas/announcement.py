"""Announcement input/output without client-controlled tenant or actor fields."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

AnnouncementTarget = Literal["all", "group"]
AnnouncementStatus = Literal["active", "archived"]


class AnnouncementText(BaseModel):
    @field_validator("title", "body", check_fields=False, mode="before")
    @classmethod
    def trim_nonempty_text(cls, value: object) -> object:
        if value is None or not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("Announcement text must be nonempty")
        return value


class AnnouncementCreate(AnnouncementText):
    model_config = ConfigDict(extra="forbid")
    target_type: AnnouncementTarget
    group_id: UUID | None = None
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=2000)

    @model_validator(mode="after")
    def valid_target(self):
        if (self.target_type == "all" and self.group_id is not None) or (
            self.target_type == "group" and self.group_id is None
        ):
            raise ValueError("Announcement target is invalid")
        return self


class AnnouncementPatch(AnnouncementText):
    model_config = ConfigDict(extra="forbid")
    target_type: AnnouncementTarget | None = None
    group_id: UUID | None = None
    title: str | None = Field(None, min_length=1, max_length=120)
    body: str | None = Field(None, min_length=1, max_length=2000)

    @model_validator(mode="after")
    def valid_patch(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if any(
            field in self.model_fields_set and getattr(self, field) is None
            for field in ("target_type", "title", "body")
        ):
            raise ValueError("Required announcement fields cannot be null")
        return self


class AnnouncementGroup(BaseModel):
    id: UUID
    name: str


class AnnouncementResponse(BaseModel):
    id: UUID
    target_type: AnnouncementTarget
    group: AnnouncementGroup | None
    title: str
    body: str
    status: AnnouncementStatus
    created_by: UUID
    updated_by: UUID
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AnnouncementList(BaseModel):
    items: list[AnnouncementResponse]

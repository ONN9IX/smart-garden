"""Minimal manual attendance transport with no free-form personal data."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

AttendanceStatus = Literal["present", "absent", "unknown"]


class LocalTimes(BaseModel):
    @field_validator("arrival_time", "departure_time", check_fields=False)
    @classmethod
    def no_timezone(cls, value: time | None) -> time | None:
        if value is not None and value.tzinfo is not None:
            raise ValueError("A local wall time without timezone is required")
        return value


class AttendanceCreate(LocalTimes):
    model_config = ConfigDict(extra="forbid")
    child_id: UUID
    date: date
    status: AttendanceStatus
    arrival_time: time | None = None
    departure_time: time | None = None


class AttendancePatch(LocalTimes):
    model_config = ConfigDict(extra="forbid")
    status: AttendanceStatus | None = None
    arrival_time: time | None = None
    departure_time: time | None = None

    @model_validator(mode="after")
    def require_changes(self):
        if not self.model_fields_set or ("status" in self.model_fields_set and self.status is None):
            raise ValueError("At least one valid field is required")
        return self


class AttendanceChild(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    status: Literal["active", "archived"]


class AttendanceGroup(BaseModel):
    id: UUID
    name: str


class AttendanceRow(BaseModel):
    record_id: UUID | None
    date: date
    child: AttendanceChild
    group: AttendanceGroup
    status: AttendanceStatus
    arrival_time: time | None
    departure_time: time | None


class AttendanceDetail(AttendanceRow):
    created_at: datetime
    updated_at: datetime
    created_by: UUID
    updated_by: UUID


class AttendanceList(BaseModel):
    items: list[AttendanceRow]

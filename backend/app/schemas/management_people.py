"""Tenant-scoped People / Group read models and atomic family-create contracts."""

from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.child import ChildCreate
from app.schemas.group import GroupResponse
from app.schemas.guardian import GuardianCreate


class FamilyGuardianInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guardian_id: UUID | None = None
    new_guardian: GuardianCreate | None = None
    relation_type: Literal["mother", "father", "legal_guardian", "other"]

    @model_validator(mode="after")
    def exactly_one_source(self):
        if (self.guardian_id is None) == (self.new_guardian is None):
            raise ValueError("Choose an existing or new representative")
        return self


class FamilyCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    child: ChildCreate
    guardians: list[FamilyGuardianInput] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_existing_guardians(self):
        ids = [item.guardian_id for item in self.guardians if item.guardian_id is not None]
        if len(ids) != len(set(ids)):
            raise ValueError("A representative can be linked only once")
        return self


class DuplicateCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Literal["child", "guardian", "employee"]
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("first_name", "last_name", "middle_name", "phone", mode="before")
    @classmethod
    def trim_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        return value.strip().lower() if isinstance(value, str) and value.strip() else None

    @model_validator(mode="after")
    def check_minimum_duplicate_keys(self):
        if self.kind == "child" and self.birth_date is None:
            raise ValueError("Birth date is required for a Child duplicate check")
        if self.kind != "child" and not (self.phone or self.email or self.first_name or self.last_name):
            raise ValueError("A name or contact value is required")
        return self


class DuplicateMatch(BaseModel):
    id: UUID
    full_name: str
    context: str | None = None


class DuplicateCheckResponse(BaseModel):
    matches: list[DuplicateMatch]


class GuardianSearchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=2, max_length=100)

    @field_validator("query", mode="before")
    @classmethod
    def trim_query(cls, value: str) -> str:
        return value.strip()


class GuardianSearchMatch(BaseModel):
    id: UUID
    full_name: str
    phone: str | None
    email: str | None
    account_status: Literal["active", "blocked"] | None


class GuardianSearchResponse(BaseModel):
    matches: list[GuardianSearchMatch]


class GroupProfileChild(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    status: Literal["active", "archived"]
    today_attendance: Literal["present", "absent", "unknown"] | None
    active_guardian_count: int


class GroupProfileEmployee(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    position: str
    category: Literal["teacher", "administrator", "other"]
    account_status: Literal["active", "blocked"] | None


class GroupProfileParent(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    phone: str | None
    email: str | None
    account_status: Literal["active", "blocked"] | None
    child_id: UUID
    child_name: str
    relation_type: Literal["mother", "father", "legal_guardian", "other"]


class GroupProfileScheduleItem(BaseModel):
    id: UUID
    weekday: int
    start_time: time
    end_time: time
    title: str


class GroupProfile(BaseModel):
    group: GroupResponse
    local_date: date
    active_children: int
    present: int
    absent: int
    unknown: int
    active_teacher_count: int
    parent_count: int
    active_schedule_count: int
    open_tasks: int
    overdue_tasks: int
    children: list[GroupProfileChild]
    employees: list[GroupProfileEmployee]
    parents: list[GroupProfileParent]
    schedule: list[GroupProfileScheduleItem]


class GroupOverviewItem(BaseModel):
    group: GroupResponse
    active_children: int
    present: int
    absent: int
    unknown: int
    active_teacher_names: list[str]
    has_active_weekly_schedule: bool
    open_tasks: int
    overdue_tasks: int


class GroupOverviewList(BaseModel):
    items: list[GroupOverviewItem]


class EmployeeAssignmentProfile(BaseModel):
    group_id: UUID
    group_name: str
    status: Literal["active", "archived"]
    archived_at: datetime | None


class EmployeeProfile(BaseModel):
    employee_id: UUID
    assignments: list[EmployeeAssignmentProfile]
    open_tasks: int
    overdue_tasks: int

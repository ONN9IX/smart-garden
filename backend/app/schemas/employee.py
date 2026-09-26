"""Minimal staff transport; tenant, password and User linkage are server-owned."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _trim(value: str | None) -> str | None:
    return value.strip() if isinstance(value, str) else value


class EmployeeCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    position: str = Field(min_length=1, max_length=100)

    @field_validator("first_name", "last_name", "position", mode="before")
    @classmethod
    def required_text(cls, value: str) -> str:
        return _trim(value)

    @field_validator("middle_name", mode="before")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _trim(value) or None


class EmployeePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    position: str | None = Field(default=None, min_length=1, max_length=100)

    @field_validator("first_name", "last_name", "position", mode="before")
    @classmethod
    def required_text(cls, value: str | None) -> str | None:
        return _trim(value)

    @field_validator("middle_name", mode="before")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _trim(value) or None

    @model_validator(mode="after")
    def nonempty_patch(self):
        if not self.model_fields_set or any(
            getattr(self, field) is None for field in ("first_name", "last_name", "position") if field in self.model_fields_set
        ):
            raise ValueError("A nonempty patch with required fields is expected")
        return self


class EmployeeAccountSummary(BaseModel):
    id: UUID
    username: str
    role: Literal["ADMIN"]
    status: Literal["active", "blocked"]
    must_change_password: bool


class EmployeeListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    position: str
    status: Literal["active", "archived"]
    account: EmployeeAccountSummary | None


class EmployeeResponse(EmployeeListItem):
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class EmployeeList(BaseModel):
    items: list[EmployeeListItem]

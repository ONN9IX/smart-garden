"""Minimal child transport schema; no health, documents, notes or tenant ID."""

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ChildCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: UUID
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    birth_date: date

    @field_validator("first_name", "last_name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("middle_name")
    @classmethod
    def trim_middle(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class ChildPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    group_id: UUID | None = None
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    birth_date: date | None = None

    @model_validator(mode="after")
    def require_fields(self):
        if not self.model_fields_set:
            raise ValueError("At least one field is required")
        if any(getattr(self, name) is None for name in ("group_id", "first_name", "last_name", "birth_date") if name in self.model_fields_set):
            raise ValueError("Required fields cannot be null")
        return self

    @field_validator("first_name", "last_name")
    @classmethod
    def trim_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("middle_name")
    @classmethod
    def trim_middle(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class GroupSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: Literal["active", "archived"]


class GuardianSummary(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    phone: str | None
    email: str | None
    status: Literal["active", "archived"]


class ChildGuardianResponse(BaseModel):
    id: UUID
    relation_type: Literal["mother", "father", "legal_guardian", "other"]
    status: Literal["active", "archived"]
    guardian: GuardianSummary
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChildSummary(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    birth_date: date
    status: Literal["active", "archived"]
    group: GroupSummary


class ChildResponse(ChildSummary):
    guardians: list[ChildGuardianResponse]
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ChildList(BaseModel):
    items: list[ChildSummary]

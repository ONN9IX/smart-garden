"""Minimal guardian transport schema. Passwords, tenant IDs and notes are absent."""

import re
from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.child import ChildSummary


def _name(value: str | None) -> str | None:
    return value.strip() if value is not None else None


def _optional(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


def _email(value: str | None) -> str | None:
    value = _optional(value)
    if value is not None:
        value = value.lower()
        if len(value) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
            raise ValueError("Invalid email")
    return value


class GuardianCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)

    @field_validator("first_name", "last_name")
    @classmethod
    def required_name(cls, value: str) -> str:
        value = _name(value)
        if not value:
            raise ValueError("Name is required")
        return value

    @field_validator("middle_name", "phone")
    @classmethod
    def optional_value(cls, value: str | None) -> str | None:
        return _optional(value)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value: str | None) -> str | None:
        return _email(value)


class GuardianPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str | None = Field(default=None, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    middle_name: str | None = Field(default=None, max_length=100)
    phone: str | None = Field(default=None, max_length=32)
    email: str | None = Field(default=None, max_length=254)

    @model_validator(mode="after")
    def require_fields(self):
        if not self.model_fields_set or any(getattr(self, field) is None for field in ("first_name", "last_name") if field in self.model_fields_set):
            raise ValueError("At least one field and nonnull required names")
        return self

    @field_validator("first_name", "last_name")
    @classmethod
    def required_name(cls, value: str | None) -> str | None:
        value = _name(value)
        if value is not None and not value:
            raise ValueError("Name is required")
        return value

    @field_validator("middle_name", "phone")
    @classmethod
    def optional_value(cls, value: str | None) -> str | None:
        return _optional(value)

    @field_validator("email")
    @classmethod
    def normalized_email(cls, value: str | None) -> str | None:
        return _email(value)


class ParentAccountSummary(BaseModel):
    id: UUID
    username: str
    status: Literal["active", "blocked"]
    must_change_password: bool


class GuardianChildRelation(BaseModel):
    relation_id: UUID
    relation_type: Literal["mother", "father", "legal_guardian", "other"]
    relation_status: Literal["active", "archived"]
    child: ChildSummary


class GuardianListItem(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    middle_name: str | None
    phone: str | None
    email: str | None
    status: Literal["active", "archived"]
    account: ParentAccountSummary | None


class GuardianResponse(GuardianListItem):
    children: list[GuardianChildRelation]
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GuardianList(BaseModel):
    items: list[GuardianListItem]

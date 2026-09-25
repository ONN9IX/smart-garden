"""Stage 2 group input/output; tenant ID is never accepted from the client."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class GroupWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=100)

    @field_validator("name")
    @classmethod
    def trim_nonempty_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Group name must be nonempty")
        return value


class GroupResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    status: Literal["active", "archived"]
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class GroupList(BaseModel):
    items: list[GroupResponse]

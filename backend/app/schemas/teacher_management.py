"""Teacher account assignment transport; tenant and audit identity stay server-owned."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TeacherAssignmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employee_id: UUID
    group_id: UUID


class TeacherAssignmentResponse(BaseModel):
    id: UUID
    employee_id: UUID
    group_id: UUID
    status: Literal["active", "archived"]
    assigned_by: UUID
    created_at: datetime
    archived_at: datetime | None


class TeacherAssignmentList(BaseModel):
    items: list[TeacherAssignmentResponse]

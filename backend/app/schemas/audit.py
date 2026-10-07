"""Read-only Audit transport; tenant identity is deliberately absent."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel


class AuditActor(BaseModel):
    id: UUID
    username: str
    role: Literal["DIRECTOR", "ADMIN", "TEACHER", "PARENT"]


class AuditEventResponse(BaseModel):
    id: UUID
    action: str
    entity_type: str
    entity_id: UUID | None
    actor: AuditActor
    details: dict[str, Any]
    created_at: datetime


class AuditEventList(BaseModel):
    items: list[AuditEventResponse]
    limit: int
    offset: int

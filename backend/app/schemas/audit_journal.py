"""Human, privacy-minimized projection of immutable Audit events."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

JournalCategory = Literal[
    "access", "people", "groups", "operations", "communications", "documents", "integrations", "organization",
]


class JournalActor(BaseModel):
    id: UUID
    display_name: str
    role: Literal["DIRECTOR", "ADMIN", "TEACHER", "PARENT"]


class JournalTarget(BaseModel):
    type: str
    display_name: str


class JournalItem(BaseModel):
    id: UUID
    created_at: datetime
    category: JournalCategory
    actor: JournalActor
    summary: str
    target: JournalTarget
    safe_changes: list[str]


class JournalList(BaseModel):
    items: list[JournalItem]
    actors: list[JournalActor]
    limit: int
    offset: int

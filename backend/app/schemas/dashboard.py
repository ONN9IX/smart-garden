"""Privacy-minimal current operational Dashboard response."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class DashboardGroup(BaseModel):
    id: UUID
    name: str
    active_children: int
    present: int
    absent: int
    unknown: int


class DashboardSummary(BaseModel):
    date: date
    active_children: int
    present: int
    absent: int
    unknown: int
    active_groups: int
    active_employees: int
    groups: list[DashboardGroup]

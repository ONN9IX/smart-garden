"""Privacy-minimal current operational Dashboard response."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel


class DashboardGroup(BaseModel):
    id: UUID
    name: str
    active_children: int
    present: int
    on_site: int
    departed: int
    absent: int
    unknown: int
    needs_arrival: int


class DashboardSummary(BaseModel):
    date: date
    active_children: int
    present: int
    on_site: int
    departed: int
    absent: int
    unknown: int
    needs_arrival: int
    active_groups: int
    active_employees: int
    groups: list[DashboardGroup]

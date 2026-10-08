"""Shared read-only attendance classification for active group rosters."""

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.attendance import Attendance
from app.models.child import Child
from app.models.group import Group


@dataclass(frozen=True)
class AttendanceCounts:
    active_children: int = 0
    present: int = 0
    on_site: int = 0
    departed: int = 0
    absent: int = 0
    unknown: int = 0
    needs_arrival: int = 0


def attendance_state(status: str | None, arrival_time, departure_time) -> str:
    if status == "absent":
        return "absent"
    if status != "present":
        return "unknown"
    if departure_time is not None:
        return "departed"
    if arrival_time is None:
        return "needs_arrival"
    return "on_site"


def count_group_attendance(
    db: Session, organization_id: UUID, group_ids: list[UUID], day,
) -> dict[UUID, AttendanceCounts]:
    """Count only each active child in their current group; old group snapshots do not follow transfers."""
    result: dict[UUID, AttendanceCounts] = {group_id: AttendanceCounts() for group_id in group_ids}
    if not group_ids:
        return result
    rows = db.execute(
        select(Child.group_id, Attendance.status, Attendance.arrival_time, Attendance.departure_time)
        .join(Group, and_(Group.id == Child.group_id, Group.organization_id == organization_id))
        .outerjoin(Attendance, and_(
            Attendance.organization_id == organization_id,
            Attendance.child_id == Child.id,
            Attendance.group_id == Group.id,
            Attendance.date == day,
        ))
        .where(
            Child.organization_id == organization_id,
            Child.group_id.in_(group_ids),
            Child.status == "active",
        )
    ).all()
    mutable = {group_id: {key: 0 for key in ("active_children", "present", "on_site", "departed", "absent", "unknown", "needs_arrival")} for group_id in group_ids}
    for group_id, status, arrival_time, departure_time in rows:
        counts = mutable[group_id]
        counts["active_children"] += 1
        if status == "present":
            counts["present"] += 1
        counts[attendance_state(status, arrival_time, departure_time)] += 1
    return {group_id: AttendanceCounts(**counts) for group_id, counts in mutable.items()}

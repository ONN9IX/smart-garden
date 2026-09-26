"""Tenant-scoped manual attendance with stable group snapshots."""

from datetime import UTC, date, datetime, time
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.attendance import Attendance
from app.models.child import Child
from app.models.group import Group
from app.models.user import User
from app.schemas.attendance import (
    AttendanceChild,
    AttendanceCreate,
    AttendanceDetail,
    AttendanceGroup,
    AttendancePatch,
    AttendanceRow,
)


def _validate_day(day: date) -> None:
    if day > datetime.now(UTC).date():
        raise AppError(400, "INVALID_ATTENDANCE_DATE", "date")


def _validate_times(status: str, arrival: time | None, departure: time | None) -> None:
    if (status != "present" and (arrival is not None or departure is not None)) or (
        status == "present" and departure is not None and (arrival is None or departure < arrival)
    ):
        raise AppError(400, "INVALID_ATTENDANCE_TIME")


def _child(db: Session, actor: User, child_id: UUID, *, lock: bool = False) -> Child:
    query = select(Child).where(Child.id == child_id, Child.organization_id == actor.organization_id)
    if lock:
        query = query.with_for_update()
    child = db.scalar(query)
    if child is None:
        raise AppError(404, "NOT_FOUND")
    return child


def _record(db: Session, actor: User, record_id: UUID, *, lock: bool = False) -> Attendance:
    query = select(Attendance).where(Attendance.id == record_id, Attendance.organization_id == actor.organization_id)
    if lock:
        query = query.with_for_update()
    record = db.scalar(query)
    if record is None:
        raise AppError(404, "NOT_FOUND")
    return record


def row(record: Attendance | None, child: Child, group: Group, day: date) -> AttendanceRow:
    return AttendanceRow(
        record_id=record.id if record else None, date=day,
        child=AttendanceChild(id=child.id, first_name=child.first_name, last_name=child.last_name,
                              middle_name=child.middle_name, status=child.status),
        group=AttendanceGroup(id=group.id, name=group.name),
        status=record.status if record else "unknown",
        arrival_time=record.arrival_time if record else None,
        departure_time=record.departure_time if record else None,
    )


def detail(record: Attendance) -> AttendanceDetail:
    return AttendanceDetail(
        **row(record, record.child, record.group, record.date).model_dump(),
        created_at=record.created_at, updated_at=record.updated_at,
        created_by=record.created_by, updated_by=record.updated_by,
    )


def list_day(db: Session, actor: User, day: date, group_id: UUID | None,
             status: str, child_id: UUID | None) -> list[AttendanceRow]:
    _validate_day(day)
    if group_id is not None and db.scalar(select(Group.id).where(
        Group.id == group_id, Group.organization_id == actor.organization_id,
    )) is None:
        raise AppError(404, "NOT_FOUND")
    if child_id is not None:
        _child(db, actor, child_id)
    records = list(db.scalars(select(Attendance).where(
        Attendance.organization_id == actor.organization_id, Attendance.date == day,
    )))
    by_child = {r.child_id: r for r in records}
    children = list(db.scalars(select(Child).join(Group, Child.group_id == Group.id).where(
        Child.organization_id == actor.organization_id, Child.status == "active", Group.status == "active",
    )))
    seen = {c.id for c in children}
    children.extend(r.child for r in records if r.child_id not in seen)
    items = [row(by_child.get(c.id), c, by_child[c.id].group if c.id in by_child else c.group, day) for c in children]
    if group_id is not None:
        items = [item for item in items if item.group.id == group_id]
    if child_id is not None:
        items = [item for item in items if item.child.id == child_id]
    if status != "all":
        items = [item for item in items if item.status == status]
    return sorted(items, key=lambda item: (item.group.name, item.child.last_name, item.child.first_name, str(item.child.id)))


def upsert(db: Session, actor: User, payload: AttendanceCreate) -> tuple[AttendanceDetail, bool]:
    _validate_day(payload.date)
    _validate_times(payload.status, payload.arrival_time, payload.departure_time)
    child = _child(db, actor, payload.child_id, lock=True)
    if child.status != "active":
        raise AppError(409, "CHILD_ARCHIVED")
    existing = db.scalar(select(Attendance).where(Attendance.child_id == child.id, Attendance.date == payload.date))
    if existing is None and child.group.status != "active":
        raise AppError(409, "GROUP_ARCHIVED")
    values = {
        "organization_id": actor.organization_id, "child_id": child.id, "group_id": child.group_id,
        "date": payload.date, "status": payload.status, "arrival_time": payload.arrival_time,
        "departure_time": payload.departure_time, "created_by": actor.id, "updated_by": actor.id,
    }
    statement = insert(Attendance).values(**values)
    statement = statement.on_conflict_do_update(
        constraint="uq_attendance_child_date",
        set_={"status": payload.status, "arrival_time": payload.arrival_time,
              "departure_time": payload.departure_time, "updated_by": actor.id,
              "updated_at": func.now()},
    ).returning(Attendance.id)
    record_id = db.scalar(statement)
    db.commit()
    # Core upsert bypasses the ORM identity map; reload the saved values.
    db.expire_all()
    record = _record(db, actor, record_id)
    return detail(record), existing is None


def update(db: Session, actor: User, record_id: UUID, payload: AttendancePatch) -> AttendanceDetail:
    record = _record(db, actor, record_id, lock=True)
    status = payload.status if payload.status is not None else record.status
    if status != "present":
        arrival = departure = None
        if any(getattr(payload, field) is not None for field in ("arrival_time", "departure_time")):
            raise AppError(400, "INVALID_ATTENDANCE_TIME")
    else:
        arrival = payload.arrival_time if "arrival_time" in payload.model_fields_set else record.arrival_time
        departure = payload.departure_time if "departure_time" in payload.model_fields_set else record.departure_time
    _validate_times(status, arrival, departure)
    record.status, record.arrival_time, record.departure_time = status, arrival, departure
    record.updated_by = actor.id
    db.commit()
    db.refresh(record)
    return detail(record)


def get(db: Session, actor: User, record_id: UUID) -> AttendanceDetail:
    return detail(_record(db, actor, record_id))

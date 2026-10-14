"""Assigned Groups, roster, attendance, schedule and Today aggregation."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.organization_time import organization_today
from app.models.attendance import Attendance
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.schemas.attendance import (
    AttendanceCreate,
    AttendanceDetail,
    AttendancePatch,
    AttendanceRow,
    GroupDayAttendanceSave,
)
from app.schemas.teacher.contracts import (
    AttendanceSummary,
    ChildSummary,
    GroupSummary,
    GuardianContext,
    NotificationResponse,
    ParentAttendanceSummary,
    ParentTodayResponse,
    ScheduleItemResponse,
    TaskResponse,
    TodayResponse,
)
from app.services import attendance, audit
from app.services.attendance_counts import count_group_attendance
from app.services.teacher import access


def groups(db: Session, actor: User) -> list[GroupSummary]:
    group_ids = access.teacher_group_ids(db, actor)
    if not group_ids:
        return []
    items = db.scalars(select(Group).where(Group.id.in_(group_ids)).order_by(Group.name, Group.id))
    return [GroupSummary(id=item.id, name=item.name) for item in items]


def group(db: Session, actor: User, group_id: UUID) -> GroupSummary:
    item = access.teacher_group(db, actor, group_id)
    return GroupSummary(id=item.id, name=item.name)


def children(db: Session, actor: User, group_id: UUID) -> list[ChildSummary]:
    access.teacher_group(db, actor, group_id)
    items = db.scalars(select(Child).where(
        Child.organization_id == actor.organization_id,
        Child.group_id == group_id,
        Child.status == "active",
    ).order_by(Child.last_name, Child.first_name, Child.id))
    return [ChildSummary(
        id=item.id, first_name=item.first_name, last_name=item.last_name, middle_name=item.middle_name,
    ) for item in items]


def parent_children(db: Session, actor: User) -> list[ChildSummary]:
    guardian = access.parent_guardian(db, actor)
    items = db.scalars(
        select(Child)
        .join(Group, Group.id == Child.group_id)
        .join(ChildGuardian, ChildGuardian.child_id == Child.id)
        .where(
            Child.organization_id == actor.organization_id,
            Child.status == "active",
            Group.organization_id == actor.organization_id,
            Group.status == "active",
            ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.guardian_id == guardian.id,
            ChildGuardian.status == "active",
        )
        .distinct()
        .order_by(Child.last_name, Child.first_name, Child.id)
    )
    return [
        ChildSummary(
            id=item.id,
            first_name=item.first_name,
            last_name=item.last_name,
            middle_name=item.middle_name,
        )
        for item in items
    ]


def parent_today(db: Session, actor: User, child_id: UUID) -> ParentTodayResponse:
    _, child = access.parent_child(db, actor, child_id)
    group = db.scalar(select(Group).where(
        Group.id == child.group_id,
        Group.organization_id == actor.organization_id,
        Group.status == "active",
    ))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    day = organization_today(actor.organization)
    record = db.scalar(select(Attendance).where(
        Attendance.organization_id == actor.organization_id,
        Attendance.child_id == child.id,
        Attendance.date == day,
    ))
    schedule_items = db.scalars(select(GroupScheduleItem).where(
        GroupScheduleItem.organization_id == actor.organization_id,
        GroupScheduleItem.group_id == group.id,
        GroupScheduleItem.weekday == day.weekday(),
        GroupScheduleItem.status == "active",
    ).order_by(GroupScheduleItem.start_time, GroupScheduleItem.id))
    return ParentTodayResponse(
        date=day,
        child=ChildSummary(
            id=child.id, first_name=child.first_name, last_name=child.last_name,
            middle_name=child.middle_name,
        ),
        group=GroupSummary(id=group.id, name=group.name),
        attendance=ParentAttendanceSummary(
            status=record.status if record is not None else "unknown",
            arrival_time=(record.arrival_time if record is not None and actor.organization.operating_profile != "GYMNASTICS" else None),
            departure_time=(record.departure_time if record is not None and actor.organization.operating_profile != "GYMNASTICS" else None),
        ),
        schedule=[
            ScheduleItemResponse(
                id=item.id, group_id=item.group_id, weekday=item.weekday,
                start_time=item.start_time, end_time=item.end_time, title=item.title,
            )
            for item in schedule_items
        ],
    )


def guardians(db: Session, actor: User, group_id: UUID) -> list[GuardianContext]:
    access.teacher_group(db, actor, group_id)
    rows = db.execute(
        select(Guardian, ChildGuardian.child_id, ChildGuardian.relation_type, User.status)
        .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
        .join(Child, Child.id == ChildGuardian.child_id)
        .outerjoin(User, User.id == Guardian.user_id)
        .where(
            Guardian.organization_id == actor.organization_id,
            Guardian.status == "active",
            ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.status == "active",
            Child.organization_id == actor.organization_id,
            Child.group_id == group_id,
            Child.status == "active",
        ).order_by(Guardian.last_name, Guardian.first_name, ChildGuardian.child_id)
    )
    return [GuardianContext(
        id=guardian.id, child_id=child_id, first_name=guardian.first_name,
        last_name=guardian.last_name, middle_name=guardian.middle_name,
        relation_type=relation_type, phone=guardian.phone, email=guardian.email,
        can_message=guardian.user_id is not None and user_status == "active",
    ) for guardian, child_id, relation_type, user_status in rows]


def list_attendance(db: Session, actor: User, day: date, group_id: UUID) -> list[AttendanceRow]:
    assigned_group = access.teacher_group(db, actor, group_id)
    if day > organization_today(actor.organization):
        raise AppError(400, "INVALID_ATTENDANCE_DATE", "date")
    active_children = list(db.scalars(select(Child).where(
        Child.organization_id == actor.organization_id,
        Child.group_id == group_id,
        Child.status == "active",
    ).order_by(Child.last_name, Child.first_name, Child.id)))
    records = list(db.scalars(select(Attendance).where(
        Attendance.organization_id == actor.organization_id,
        Attendance.group_id == group_id,
        Attendance.date == day,
        Attendance.child_id.in_([child.id for child in active_children]),
    ))) if active_children else []
    by_child = {record.child_id: record for record in records}
    rows = [attendance.row(by_child.get(child.id), child, assigned_group, day) for child in active_children]
    if actor.organization.operating_profile == "GYMNASTICS":
        return [row.model_copy(update={"arrival_time": None, "departure_time": None}) for row in rows]
    return rows


def save_attendance(
    db: Session, actor: User, payload: AttendanceCreate,
) -> tuple[AttendanceDetail, bool]:
    child = access.teacher_child(db, actor, payload.child_id, lock=True)
    access.teacher_group(db, actor, child.group_id)
    if (
        actor.organization.operating_profile == "GYMNASTICS"
        and payload.group_id is not None
        and payload.group_id != child.group_id
    ):
        raise AppError(409, "ROSTER_CHANGED")
    if actor.organization.operating_profile == "GYMNASTICS":
        historical_group_id = db.scalar(select(Attendance.group_id).where(
            Attendance.organization_id == actor.organization_id,
            Attendance.child_id == child.id,
            Attendance.date == payload.date,
        ).with_for_update())
        if historical_group_id is not None and historical_group_id != child.group_id:
            raise AppError(409, "ATTENDANCE_GROUP_CONFLICT")
    return attendance.upsert(db, actor, payload)


def save_group_day_attendance(
    db: Session, actor: User, payload: GroupDayAttendanceSave,
) -> list[AttendanceDetail]:
    profile = db.scalar(select(Organization.operating_profile).where(
        Organization.id == actor.organization_id,
    ))
    if profile != "GYMNASTICS":
        raise AppError(403, "FORBIDDEN")
    assigned = access.teacher_group(db, actor, payload.group_id)
    if payload.date > organization_today(actor.organization):
        raise AppError(400, "INVALID_ATTENDANCE_DATE", "date")
    group = db.scalar(select(Group).where(
        Group.id == assigned.id,
        Group.organization_id == actor.organization_id,
        Group.status == "active",
    ).with_for_update())
    if group is None:
        raise AppError(404, "NOT_FOUND")

    children = list(db.scalars(select(Child).where(
        Child.organization_id == actor.organization_id,
        Child.group_id == group.id,
        Child.status == "active",
    ).order_by(Child.id).with_for_update()))
    requested = {item.child_id: item.status for item in payload.items}
    if len(requested) != len(payload.items):
        raise AppError(400, "VALIDATION_ERROR", "items")
    if not children or set(requested) != {child.id for child in children}:
        raise AppError(409, "ROSTER_CHANGED")

    saved_ids = []
    for child in children:
        status = requested[child.id]
        existing = db.scalar(select(Attendance).where(
            Attendance.organization_id == actor.organization_id,
            Attendance.child_id == child.id,
            Attendance.date == payload.date,
        ).with_for_update())
        if existing is not None and existing.group_id != group.id:
            # Existing day records keep their original group snapshot after transfer.
            raise AppError(409, "ATTENDANCE_GROUP_CONFLICT")
        before = None if existing is None else {
            "status": existing.status,
            "arrival_time": existing.arrival_time.isoformat(timespec="minutes") if existing.arrival_time else None,
            "departure_time": existing.departure_time.isoformat(timespec="minutes") if existing.departure_time else None,
        }
        after = {"status": status, "arrival_time": None, "departure_time": None}
        if before is not None and before == after:
            saved_ids.append(existing.id)
            continue
        statement = insert(Attendance).values(
            organization_id=actor.organization_id,
            child_id=child.id,
            group_id=group.id,
            date=payload.date,
            status=status,
            arrival_time=None,
            departure_time=None,
            created_by=actor.id,
            updated_by=actor.id,
        ).on_conflict_do_update(
            constraint="uq_attendance_child_date",
            set_={
                "status": status,
                "arrival_time": None,
                "departure_time": None,
                "updated_by": actor.id,
                "updated_at": func.now(),
            },
        ).returning(Attendance.id)
        record_id = db.scalar(statement)
        details = {"after": after}
        if before is not None:
            details["before"] = before
            details["changed_fields"] = audit.changed_fields(before, after)
        audit.write(
            db, actor, "attendance.create" if existing is None else "attendance.update",
            "attendance", record_id, details,
        )
        saved_ids.append(record_id)
    db.commit()
    db.expire_all()
    return [attendance.get(db, actor, record_id) for record_id in saved_ids]


def patch_attendance(
    db: Session, actor: User, record_id: UUID, payload: AttendancePatch,
) -> AttendanceDetail:
    record = db.scalar(select(Attendance).where(
        Attendance.id == record_id, Attendance.organization_id == actor.organization_id,
    ))
    if record is None:
        raise AppError(404, "NOT_FOUND")
    child = access.teacher_child(db, actor, record.child_id)
    if child.group_id != record.group_id:
        raise AppError(404, "NOT_FOUND")
    access.teacher_group(db, actor, record.group_id)
    return attendance.update(db, actor, record_id, payload)


def mark_arrival(db: Session, actor: User, child_id: UUID) -> AttendanceDetail:
    child = access.teacher_child(db, actor, child_id)
    access.teacher_group(db, actor, child.group_id)
    return attendance.mark_arrival(db, actor, child_id)


def mark_departure(db: Session, actor: User, child_id: UUID) -> AttendanceDetail:
    child = access.teacher_child(db, actor, child_id)
    access.teacher_group(db, actor, child.group_id)
    return attendance.mark_departure(db, actor, child_id)


def schedule(db: Session, actor: User, group_id: UUID) -> list[ScheduleItemResponse]:
    access.teacher_group(db, actor, group_id)
    items = db.scalars(select(GroupScheduleItem).where(
        GroupScheduleItem.organization_id == actor.organization_id,
        GroupScheduleItem.group_id == group_id,
        GroupScheduleItem.status == "active",
    ).order_by(GroupScheduleItem.weekday, GroupScheduleItem.start_time, GroupScheduleItem.id))
    return [ScheduleItemResponse(
        id=item.id, group_id=item.group_id, weekday=item.weekday,
        start_time=item.start_time, end_time=item.end_time, title=item.title,
    ) for item in items]


def _task(item: TeacherTask) -> TaskResponse:
    return TaskResponse(
        id=item.id, group_id=item.group_id, title=item.title, description=item.description,
        due_at=item.due_at, status=item.status, created_at=item.created_at, updated_at=item.updated_at,
    )


def _notification(item: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=item.id, kind=item.kind, entity_type=item.entity_type, entity_id=item.entity_id,
        read_at=item.read_at, created_at=item.created_at,
    )


def today(db: Session, actor: User) -> TodayResponse:
    employee = access.teacher_employee(db, actor)
    day = organization_today(actor.organization)
    assigned_groups = groups(db, actor)
    group_ids = [item.id for item in assigned_groups]
    schedule_items: list[ScheduleItemResponse] = []
    attendance_items: list[AttendanceSummary] = []
    if group_ids:
        raw_schedule = db.scalars(select(GroupScheduleItem).where(
            GroupScheduleItem.organization_id == actor.organization_id,
            GroupScheduleItem.group_id.in_(group_ids),
            GroupScheduleItem.weekday == day.weekday(),
            GroupScheduleItem.status == "active",
        ).order_by(GroupScheduleItem.start_time, GroupScheduleItem.id))
        schedule_items = [ScheduleItemResponse(
            id=item.id, group_id=item.group_id, weekday=item.weekday,
            start_time=item.start_time, end_time=item.end_time, title=item.title,
        ) for item in raw_schedule]
        counts_by_group = count_group_attendance(db, actor.organization_id, group_ids, day)
        for item in assigned_groups:
            counts = counts_by_group[item.id].__dict__.copy()
            if actor.organization.operating_profile == "GYMNASTICS":
                counts.update(on_site=0, departed=0, needs_arrival=0)
            attendance_items.append(AttendanceSummary(group_id=item.id, **counts))
    tasks = db.scalars(select(TeacherTask).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.assignee_employee_id == employee.id,
        TeacherTask.status.in_(("open", "in_progress")),
    ).order_by(TeacherTask.due_at.asc().nulls_last(), TeacherTask.created_at, TeacherTask.id))
    notifications = list(db.scalars(select(Notification).where(
        Notification.organization_id == actor.organization_id,
        Notification.recipient_user_id == actor.id,
        Notification.read_at.is_(None),
    ).order_by(Notification.created_at.desc(), Notification.id.desc()).limit(20)))
    unread_communications = sum(
        item.entity_type in {"communication_thread", "communication_message"} for item in notifications
    )
    return TodayResponse(
        date=day, groups=assigned_groups, schedule=schedule_items, attendance=attendance_items,
        tasks=[_task(item) for item in tasks], notifications=[_notification(item) for item in notifications],
        unread_communication_count=unread_communications,
    )

"""Stage 6 DIRECTOR/ADMIN services over the frozen Foundation schema."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.child import Child
from app.models.child_diary_entry import ChildDiaryEntry
from app.models.communication import CommunicationMessage, CommunicationThread
from app.models.document_notice import DocumentNotice
from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.incident import Incident
from app.models.notification import Notification
from app.models.photo import PhotoConsent
from app.models.poll import Poll, PollOption, PollVote
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.schemas.management_cabinet import (
    DiaryEntryList,
    DiaryEntryResponse,
    DocumentNoticeCreate,
    DocumentNoticeList,
    DocumentNoticeResponse,
    IncidentCreate,
    IncidentList,
    IncidentPatch,
    IncidentResponse,
    ManagementAttentionItem,
    ManagementMessageCreate,
    ManagementMessageList,
    ManagementMessageResponse,
    ManagementSettingsPatch,
    ManagementSettingsResponse,
    ManagementToday,
    NotificationList,
    NotificationResponse,
    PhotoConsentCreate,
    PhotoConsentList,
    PhotoConsentResponse,
    PollCreate,
    PollList,
    PollOptionResult,
    PollResponse,
    ScheduleCreate,
    ScheduleItemResponse,
    ScheduleList,
    SchedulePatch,
    TeacherAccountView,
    TeacherAssignmentView,
    TeacherProjection,
    TeacherProjectionList,
    TeacherTaskCreate,
    TeacherTaskList,
    TeacherTaskPatch,
    TeacherTaskResponse,
)
from app.services import audit, dashboard
from app.services.auth import utc_now


def _group(db: Session, actor: User, group_id: UUID, *, active: bool = False) -> Group:
    group = db.scalar(select(Group).where(
        Group.id == group_id,
        Group.organization_id == actor.organization_id,
    ))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    if active and group.status != "active":
        raise AppError(409, "GROUP_ARCHIVED")
    return group


def _child(db: Session, actor: User, child_id: UUID, *, active: bool = False) -> Child:
    child = db.scalar(select(Child).where(
        Child.id == child_id,
        Child.organization_id == actor.organization_id,
    ))
    if child is None:
        raise AppError(404, "NOT_FOUND")
    if active and child.status != "active":
        raise AppError(409, "CHILD_ARCHIVED")
    return child


def _teacher_user(db: Session, actor: User, employee: Employee, *, active: bool = False) -> User | None:
    if employee.user_id is None:
        return None
    user = db.scalar(select(User).where(
        User.id == employee.user_id,
        User.organization_id == actor.organization_id,
    ))
    if user is None or user.role != "TEACHER":
        return None
    if active and user.status != "active":
        raise AppError(409, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    return user


def _teacher_employee(db: Session, actor: User, employee_id: UUID, *, active: bool = True) -> tuple[Employee, User]:
    employee = db.scalar(select(Employee).where(
        Employee.id == employee_id,
        Employee.organization_id == actor.organization_id,
    ))
    if employee is None:
        raise AppError(404, "NOT_FOUND")
    if active and employee.status != "active":
        raise AppError(409, "EMPLOYEE_ARCHIVED")
    user = _teacher_user(db, actor, employee, active=active)
    if user is None:
        raise AppError(409, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    return employee, user


def _active_assignment(db: Session, actor: User, employee_id: UUID, group_id: UUID) -> TeacherGroupAssignment:
    assignment = db.scalar(select(TeacherGroupAssignment).where(
        TeacherGroupAssignment.organization_id == actor.organization_id,
        TeacherGroupAssignment.employee_id == employee_id,
        TeacherGroupAssignment.group_id == group_id,
        TeacherGroupAssignment.status == "active",
    ))
    if assignment is None:
        raise AppError(409, "VALIDATION_ERROR", "group_id")
    return assignment


def management_today(db: Session, actor: User) -> ManagementToday:
    base = dashboard.summary(db, actor)
    active_group_ids = list(db.scalars(select(Group.id).where(
        Group.organization_id == actor.organization_id,
        Group.status == "active",
    )))
    assigned_group_ids = set(db.scalars(
        select(TeacherGroupAssignment.group_id)
        .join(Employee, Employee.id == TeacherGroupAssignment.employee_id)
        .join(User, User.id == Employee.user_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.status == "active",
            Employee.organization_id == actor.organization_id,
            Employee.status == "active",
            User.organization_id == actor.organization_id,
            User.role == "TEACHER",
            User.status == "active",
        )
    ))
    without_teacher = [group_id for group_id in active_group_ids if group_id not in assigned_group_ids]
    open_tasks = db.scalar(select(func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.status.in_(("open", "in_progress")),
    )) or 0
    now = datetime.now(UTC)
    overdue_tasks = db.scalar(select(func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.status.in_(("open", "in_progress")),
        TeacherTask.due_at.is_not(None),
        TeacherTask.due_at < now,
    )) or 0
    open_incidents = db.scalar(select(func.count(Incident.id)).where(
        Incident.organization_id == actor.organization_id,
        Incident.status == "open",
    )) or 0
    unread = db.scalar(select(func.count(Notification.id)).where(
        Notification.organization_id == actor.organization_id,
        Notification.recipient_user_id == actor.id,
        Notification.read_at.is_(None),
    )) or 0

    attention: list[ManagementAttentionItem] = []
    if base.unknown:
        attention.append(ManagementAttentionItem(kind="attendance_missing", entity_type="attendance", count=base.unknown))
    if overdue_tasks:
        attention.append(ManagementAttentionItem(kind="tasks_overdue", entity_type="teacher_task", count=overdue_tasks))
    if open_incidents:
        attention.append(ManagementAttentionItem(kind="incidents_open", entity_type="incident", count=open_incidents))
    if unread:
        attention.append(ManagementAttentionItem(kind="notifications_unread", entity_type="notification", count=unread))
    attention.extend(
        ManagementAttentionItem(kind="group_without_teacher", entity_type="group", entity_id=group_id)
        for group_id in without_teacher
    )
    return ManagementToday(
        date=base.date,
        active_children=base.active_children,
        present=base.present,
        absent=base.absent,
        unknown=base.unknown,
        active_groups=base.active_groups,
        active_employees=base.active_employees,
        groups_without_active_teacher_assignment=len(without_teacher),
        open_tasks=open_tasks,
        overdue_tasks=overdue_tasks,
        open_incidents=open_incidents,
        unread_notifications=unread,
        attention_items=attention,
    )


def _teacher_projection(db: Session, actor: User, employee: Employee) -> TeacherProjection:
    account = _teacher_user(db, actor, employee)
    if employee.user_id is not None and account is None:
        raise AppError(404, "NOT_FOUND")
    rows = db.execute(
        select(TeacherGroupAssignment, Group.name)
        .join(Group, Group.id == TeacherGroupAssignment.group_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.employee_id == employee.id,
            Group.organization_id == actor.organization_id,
        )
        .order_by(Group.name, TeacherGroupAssignment.created_at)
    ).all()
    assignments = [
        TeacherAssignmentView(
            id=assignment.id,
            group_id=assignment.group_id,
            group_name=group_name,
            status=assignment.status,
        )
        for assignment, group_name in rows
    ]
    account_view = None if account is None else TeacherAccountView(
        user_id=account.id,
        username=account.username,
        status=account.status,
        must_change_password=account.must_change_password,
    )
    return TeacherProjection(
        employee_id=employee.id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        middle_name=employee.middle_name,
        position=employee.position,
        employee_status=employee.status,
        account=account_view,
        assignments=assignments,
        eligible_for_teacher_account=employee.status == "active" and employee.user_id is None,
    )


def list_teachers(
    db: Session,
    actor: User,
    *,
    status: str,
    account_status: str,
    group_id: UUID | None,
    q: str | None,
) -> TeacherProjectionList:
    if group_id is not None:
        _group(db, actor, group_id)
    query = select(Employee).where(Employee.organization_id == actor.organization_id)
    if status != "all":
        query = query.where(Employee.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(
            Employee.first_name.ilike(pattern),
            Employee.last_name.ilike(pattern),
            Employee.middle_name.ilike(pattern),
            Employee.position.ilike(pattern),
        ))
    employees = list(db.scalars(query.order_by(Employee.last_name, Employee.first_name, Employee.id)))
    items: list[TeacherProjection] = []
    for employee in employees:
        if employee.user_id is not None:
            linked = db.scalar(select(User).where(
                User.id == employee.user_id,
                User.organization_id == actor.organization_id,
            ))
            if linked is None or linked.role != "TEACHER":
                continue
        item = _teacher_projection(db, actor, employee)
        if account_status == "none" and item.account is not None:
            continue
        if account_status in {"active", "blocked"} and (item.account is None or item.account.status != account_status):
            continue
        if group_id is not None and not any(
            assignment.group_id == group_id and assignment.status == "active"
            for assignment in item.assignments
        ):
            continue
        items.append(item)
    return TeacherProjectionList(items=items)


def get_teacher(db: Session, actor: User, employee_id: UUID) -> TeacherProjection:
    employee = db.scalar(select(Employee).where(
        Employee.id == employee_id,
        Employee.organization_id == actor.organization_id,
    ))
    if employee is None:
        raise AppError(404, "NOT_FOUND")
    return _teacher_projection(db, actor, employee)


def _schedule_response(item: GroupScheduleItem) -> ScheduleItemResponse:
    return ScheduleItemResponse(
        id=item.id,
        group_id=item.group_id,
        weekday=item.weekday,
        start_time=item.start_time,
        end_time=item.end_time,
        title=item.title,
        status=item.status,
        created_by=item.created_by,
        updated_by=item.updated_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _schedule_item(db: Session, actor: User, item_id: UUID, *, lock: bool = False) -> GroupScheduleItem:
    query = select(GroupScheduleItem).where(
        GroupScheduleItem.id == item_id,
        GroupScheduleItem.organization_id == actor.organization_id,
    )
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise AppError(404, "NOT_FOUND")
    return item


def list_schedule(db: Session, actor: User, group_id: UUID | None, status: str) -> ScheduleList:
    query = select(GroupScheduleItem).where(GroupScheduleItem.organization_id == actor.organization_id)
    if group_id is not None:
        _group(db, actor, group_id)
        query = query.where(GroupScheduleItem.group_id == group_id)
    if status != "all":
        query = query.where(GroupScheduleItem.status == status)
    items = db.scalars(query.order_by(
        GroupScheduleItem.weekday,
        GroupScheduleItem.start_time,
        GroupScheduleItem.id,
    ))
    return ScheduleList(items=[_schedule_response(item) for item in items])


def create_schedule(db: Session, actor: User, payload: ScheduleCreate) -> ScheduleItemResponse:
    _group(db, actor, payload.group_id, active=True)
    if payload.end_time <= payload.start_time:
        raise AppError(400, "VALIDATION_ERROR", "end_time")
    item = GroupScheduleItem(
        organization_id=actor.organization_id,
        group_id=payload.group_id,
        weekday=payload.weekday,
        start_time=payload.start_time,
        end_time=payload.end_time,
        title=payload.title,
        status="active",
        created_by=actor.id,
        updated_by=actor.id,
    )
    db.add(item)
    db.flush()
    audit.write(db, actor, "schedule.create", "group_schedule_item", item.id, {
        "group_id": str(item.group_id),
    })
    db.commit()
    db.refresh(item)
    return _schedule_response(item)


def update_schedule(db: Session, actor: User, item_id: UUID, payload: SchedulePatch) -> ScheduleItemResponse:
    item = _schedule_item(db, actor, item_id, lock=True)
    if item.status != "active":
        raise AppError(409, "VALIDATION_ERROR")
    data = payload.model_dump(exclude_unset=True)
    if "group_id" in data:
        if data["group_id"] is None:
            raise AppError(400, "VALIDATION_ERROR", "group_id")
        _group(db, actor, data["group_id"], active=True)
    start_time = data.get("start_time", item.start_time)
    end_time = data.get("end_time", item.end_time)
    if start_time is None or end_time is None or end_time <= start_time:
        raise AppError(400, "INVALID_SCHEDULE_TIME")
    changed = []
    for field, value in data.items():
        if getattr(item, field) != value:
            setattr(item, field, value)
            changed.append(field)
    item.updated_by = actor.id
    if changed:
        audit.write(db, actor, "schedule.update", "group_schedule_item", item.id, {
            "changed_fields": sorted(changed),
        })
        db.commit()
        db.refresh(item)
    return _schedule_response(item)


def archive_schedule(db: Session, actor: User, item_id: UUID) -> ScheduleItemResponse:
    item = _schedule_item(db, actor, item_id, lock=True)
    if item.status != "archived":
        item.status = "archived"
        item.updated_by = actor.id
        audit.write(db, actor, "schedule.archive", "group_schedule_item", item.id, {
            "status_before": "active", "status_after": "archived",
        })
        db.commit()
        db.refresh(item)
    return _schedule_response(item)


def _group_thread(db: Session, actor: User, group_id: UUID, *, create: bool) -> CommunicationThread | None:
    _group(db, actor, group_id, active=True)
    thread = db.scalar(select(CommunicationThread).where(
        CommunicationThread.organization_id == actor.organization_id,
        CommunicationThread.thread_type == "group",
        CommunicationThread.group_id == group_id,
    ))
    if thread is None and create:
        thread = CommunicationThread(
            organization_id=actor.organization_id,
            thread_type="group",
            group_id=group_id,
        )
        db.add(thread)
        db.flush()
    return thread


def list_group_messages(db: Session, actor: User, group_id: UUID) -> ManagementMessageList:
    thread = _group_thread(db, actor, group_id, create=False)
    if thread is None:
        return ManagementMessageList(items=[])
    messages = db.scalars(select(CommunicationMessage).where(
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread.id,
    ).order_by(CommunicationMessage.created_at, CommunicationMessage.id))
    return ManagementMessageList(items=[
        ManagementMessageResponse(
            id=message.id,
            thread_id=message.thread_id,
            group_id=group_id,
            sender_user_id=message.sender_user_id,
            body=message.body,
            created_at=message.created_at,
        )
        for message in messages
    ])


def create_group_message(
    db: Session,
    actor: User,
    group_id: UUID,
    payload: ManagementMessageCreate,
) -> ManagementMessageResponse:
    thread = _group_thread(db, actor, group_id, create=True)
    assert thread is not None
    message = CommunicationMessage(
        organization_id=actor.organization_id,
        thread_id=thread.id,
        sender_user_id=actor.id,
        body=payload.body,
    )
    db.add(message)
    db.flush()
    audit.write(db, actor, "teacher_message.create", "communication_message", message.id, {
        "group_id": str(group_id),
        "thread_id": str(thread.id),
    })
    db.commit()
    db.refresh(message)
    return ManagementMessageResponse(
        id=message.id,
        thread_id=thread.id,
        group_id=group_id,
        sender_user_id=actor.id,
        body=message.body,
        created_at=message.created_at,
    )


def list_diary(
    db: Session,
    actor: User,
    child_id: UUID,
    date_from: date | None,
    date_to: date | None,
) -> DiaryEntryList:
    _child(db, actor, child_id)
    if date_from and date_to and date_from > date_to:
        raise AppError(400, "VALIDATION_ERROR")
    query = select(ChildDiaryEntry).where(
        ChildDiaryEntry.organization_id == actor.organization_id,
        ChildDiaryEntry.child_id == child_id,
    )
    if date_from:
        query = query.where(ChildDiaryEntry.date >= date_from)
    if date_to:
        query = query.where(ChildDiaryEntry.date <= date_to)
    entries = db.scalars(query.order_by(ChildDiaryEntry.date.desc(), ChildDiaryEntry.id.desc()))
    return DiaryEntryList(items=[_diary_response(entry) for entry in entries])


def _diary_response(entry: ChildDiaryEntry) -> DiaryEntryResponse:
    return DiaryEntryResponse(
        id=entry.id,
        child_id=entry.child_id,
        group_id=entry.group_id,
        date=entry.date,
        author_user_id=entry.author_user_id,
        note=entry.note,
        created_at=entry.created_at,
        updated_at=entry.updated_at,
    )


def get_diary_entry(db: Session, actor: User, entry_id: UUID) -> DiaryEntryResponse:
    entry = db.scalar(select(ChildDiaryEntry).where(
        ChildDiaryEntry.id == entry_id,
        ChildDiaryEntry.organization_id == actor.organization_id,
    ))
    if entry is None:
        raise AppError(404, "NOT_FOUND")
    return _diary_response(entry)


def _poll(db: Session, actor: User, poll_id: UUID, *, lock: bool = False) -> Poll:
    query = select(Poll).where(Poll.id == poll_id, Poll.organization_id == actor.organization_id)
    if lock:
        query = query.with_for_update()
    poll = db.scalar(query)
    if poll is None:
        raise AppError(404, "NOT_FOUND")
    return poll


def _poll_response(db: Session, poll: Poll) -> PollResponse:
    rows = db.execute(
        select(
            PollOption.id,
            PollOption.label,
            PollOption.sort_order,
            func.count(PollVote.id).label("vote_count"),
        )
        .outerjoin(PollVote, and_(
            PollVote.option_id == PollOption.id,
            PollVote.organization_id == poll.organization_id,
        ))
        .where(PollOption.poll_id == poll.id)
        .group_by(PollOption.id, PollOption.label, PollOption.sort_order)
        .order_by(PollOption.sort_order, PollOption.id)
    ).all()
    options = [
        PollOptionResult(
            id=row.id,
            label=row.label,
            sort_order=row.sort_order,
            vote_count=row.vote_count,
        )
        for row in rows
    ]
    return PollResponse(
        id=poll.id,
        group_id=poll.group_id,
        question=poll.question,
        status=poll.status,
        closes_at=poll.closes_at,
        created_by=poll.created_by,
        created_at=poll.created_at,
        updated_at=poll.updated_at,
        options=options,
        total_votes=sum(option.vote_count for option in options),
    )


def list_polls(db: Session, actor: User, group_id: UUID | None, status: str) -> PollList:
    query = select(Poll).where(Poll.organization_id == actor.organization_id)
    if group_id is not None:
        _group(db, actor, group_id)
        query = query.where(Poll.group_id == group_id)
    if status != "all":
        query = query.where(Poll.status == status)
    polls = db.scalars(query.order_by(Poll.created_at.desc(), Poll.id.desc()))
    return PollList(items=[_poll_response(db, poll) for poll in polls])


def get_poll(db: Session, actor: User, poll_id: UUID) -> PollResponse:
    return _poll_response(db, _poll(db, actor, poll_id))


def create_poll(db: Session, actor: User, payload: PollCreate) -> PollResponse:
    _group(db, actor, payload.group_id, active=True)
    poll = Poll(
        organization_id=actor.organization_id,
        group_id=payload.group_id,
        question=payload.question,
        status="active",
        closes_at=payload.closes_at,
        created_by=actor.id,
    )
    db.add(poll)
    db.flush()
    db.add_all([
        PollOption(poll_id=poll.id, label=label, sort_order=index)
        for index, label in enumerate(payload.options)
    ])
    audit.write(db, actor, "poll.create", "poll", poll.id, {"group_id": str(poll.group_id)})
    db.commit()
    db.refresh(poll)
    return _poll_response(db, poll)


def close_poll(db: Session, actor: User, poll_id: UUID) -> PollResponse:
    poll = _poll(db, actor, poll_id, lock=True)
    if poll.status == "archived":
        raise AppError(409, "VALIDATION_ERROR")
    if poll.status != "closed":
        poll.status = "closed"
        audit.write(db, actor, "poll.close", "poll", poll.id, {
            "status_before": "active", "status_after": "closed",
        })
        db.commit()
        db.refresh(poll)
    return _poll_response(db, poll)


def _incident_response(item: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=item.id,
        group_id=item.group_id,
        child_id=item.child_id,
        occurred_at=item.occurred_at,
        category=item.category,
        description=item.description,
        status=item.status,
        reported_by=item.reported_by,
        resolved_by=item.resolved_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _incident(db: Session, actor: User, incident_id: UUID, *, lock: bool = False) -> Incident:
    query = select(Incident).where(
        Incident.id == incident_id,
        Incident.organization_id == actor.organization_id,
    )
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise AppError(404, "NOT_FOUND")
    return item


def _incident_context(db: Session, actor: User, group_id: UUID, child_id: UUID | None) -> None:
    _group(db, actor, group_id, active=True)
    if child_id is not None:
        child = _child(db, actor, child_id, active=True)
        if child.group_id != group_id:
            raise AppError(400, "VALIDATION_ERROR", "child_id")


def list_incidents(db: Session, actor: User, group_id: UUID | None, status: str) -> IncidentList:
    query = select(Incident).where(Incident.organization_id == actor.organization_id)
    if group_id is not None:
        _group(db, actor, group_id)
        query = query.where(Incident.group_id == group_id)
    if status != "all":
        query = query.where(Incident.status == status)
    rows = db.scalars(query.order_by(Incident.occurred_at.desc(), Incident.id.desc()))
    return IncidentList(items=[_incident_response(item) for item in rows])


def get_incident(db: Session, actor: User, incident_id: UUID) -> IncidentResponse:
    return _incident_response(_incident(db, actor, incident_id))


def create_incident(db: Session, actor: User, payload: IncidentCreate) -> IncidentResponse:
    _incident_context(db, actor, payload.group_id, payload.child_id)
    item = Incident(
        organization_id=actor.organization_id,
        group_id=payload.group_id,
        child_id=payload.child_id,
        occurred_at=payload.occurred_at,
        category=payload.category,
        description=payload.description,
        status="open",
        reported_by=actor.id,
    )
    db.add(item)
    db.flush()
    details = {"group_id": str(item.group_id), "category": item.category}
    if item.child_id:
        details["child_id"] = str(item.child_id)
    audit.write(db, actor, "incident.create", "incident", item.id, details)
    db.commit()
    db.refresh(item)
    return _incident_response(item)


def update_incident(db: Session, actor: User, incident_id: UUID, payload: IncidentPatch) -> IncidentResponse:
    item = _incident(db, actor, incident_id, lock=True)
    data = payload.model_dump(exclude_unset=True)
    _incident_context(db, actor, item.group_id, item.child_id)

    before_status = item.status
    changed: list[str] = []
    for field, value in data.items():
        if getattr(item, field) != value:
            setattr(item, field, value)
            changed.append(field)
    if "status" in changed:
        item.resolved_by = actor.id if item.status == "resolved" else None
    if changed:
        if before_status != "resolved" and item.status == "resolved":
            audit.write(db, actor, "incident.resolve", "incident", item.id, {
                "status_before": before_status,
                "status_after": "resolved",
            })
            non_status = sorted(field for field in changed if field != "status")
            if non_status:
                audit.write(db, actor, "incident.update", "incident", item.id, {
                    "changed_fields": non_status,
                })
        else:
            audit.write(db, actor, "incident.update", "incident", item.id, {
                "changed_fields": sorted(changed),
            })
        db.commit()
        db.refresh(item)
    return _incident_response(item)


def _task_response(item: TeacherTask) -> TeacherTaskResponse:
    return TeacherTaskResponse(
        id=item.id,
        assignee_employee_id=item.assignee_employee_id,
        group_id=item.group_id,
        title=item.title,
        description=item.description,
        due_at=item.due_at,
        status=item.status,
        created_by=item.created_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _task(db: Session, actor: User, task_id: UUID, *, lock: bool = False) -> TeacherTask:
    query = select(TeacherTask).where(
        TeacherTask.id == task_id,
        TeacherTask.organization_id == actor.organization_id,
    )
    if lock:
        query = query.with_for_update()
    item = db.scalar(query)
    if item is None:
        raise AppError(404, "NOT_FOUND")
    return item


def _task_context(db: Session, actor: User, employee_id: UUID, group_id: UUID | None) -> None:
    _teacher_employee(db, actor, employee_id, active=True)
    if group_id is not None:
        _group(db, actor, group_id, active=True)
        _active_assignment(db, actor, employee_id, group_id)


def list_tasks(
    db: Session,
    actor: User,
    employee_id: UUID | None,
    group_id: UUID | None,
    status: str,
) -> TeacherTaskList:
    query = select(TeacherTask).where(TeacherTask.organization_id == actor.organization_id)
    if employee_id is not None:
        employee = db.scalar(select(Employee.id).where(
            Employee.id == employee_id,
            Employee.organization_id == actor.organization_id,
        ))
        if employee is None:
            raise AppError(404, "NOT_FOUND")
        query = query.where(TeacherTask.assignee_employee_id == employee_id)
    if group_id is not None:
        _group(db, actor, group_id)
        query = query.where(TeacherTask.group_id == group_id)
    if status != "all":
        query = query.where(TeacherTask.status == status)
    rows = db.scalars(query.order_by(TeacherTask.due_at.asc().nullslast(), TeacherTask.created_at.desc()))
    return TeacherTaskList(items=[_task_response(item) for item in rows])


def create_task(db: Session, actor: User, payload: TeacherTaskCreate) -> TeacherTaskResponse:
    _task_context(db, actor, payload.assignee_employee_id, payload.group_id)
    item = TeacherTask(
        organization_id=actor.organization_id,
        assignee_employee_id=payload.assignee_employee_id,
        group_id=payload.group_id,
        title=payload.title,
        description=payload.description,
        due_at=payload.due_at,
        status="open",
        created_by=actor.id,
    )
    db.add(item)
    db.flush()
    details = {"assignee_employee_id": str(item.assignee_employee_id)}
    if item.group_id is not None:
        details["group_id"] = str(item.group_id)
    audit.write(db, actor, "teacher_task.create", "teacher_task", item.id, details)
    db.commit()
    db.refresh(item)
    return _task_response(item)


def update_task(db: Session, actor: User, task_id: UUID, payload: TeacherTaskPatch) -> TeacherTaskResponse:
    item = _task(db, actor, task_id, lock=True)
    if item.status == "cancelled":
        raise AppError(409, "VALIDATION_ERROR")
    data = payload.model_dump(exclude_unset=True)
    target_employee = data.get("assignee_employee_id", item.assignee_employee_id)
    target_group = data.get("group_id", item.group_id)
    if target_employee is None:
        raise AppError(400, "VALIDATION_ERROR", "assignee_employee_id")
    _task_context(db, actor, target_employee, target_group)
    changed = []
    for field, value in data.items():
        if getattr(item, field) != value:
            setattr(item, field, value)
            changed.append(field)
    if changed:
        audit.write(db, actor, "teacher_task.update", "teacher_task", item.id, {
            "changed_fields": sorted(changed),
        })
        db.commit()
        db.refresh(item)
    return _task_response(item)


def cancel_task(db: Session, actor: User, task_id: UUID) -> TeacherTaskResponse:
    item = _task(db, actor, task_id, lock=True)
    if item.status != "cancelled":
        before = item.status
        item.status = "cancelled"
        audit.write(db, actor, "teacher_task.cancel", "teacher_task", item.id, {
            "status_before": before,
            "status_after": "cancelled",
        })
        db.commit()
        db.refresh(item)
    return _task_response(item)


def list_notifications(db: Session, actor: User, status: str) -> NotificationList:
    query = select(Notification).where(
        Notification.organization_id == actor.organization_id,
        Notification.recipient_user_id == actor.id,
    )
    if status == "unread":
        query = query.where(Notification.read_at.is_(None))
    elif status == "read":
        query = query.where(Notification.read_at.is_not(None))
    rows = db.scalars(query.order_by(Notification.created_at.desc(), Notification.id.desc()))
    return NotificationList(items=[_notification_response(item) for item in rows])


def _notification_response(item: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=item.id,
        kind=item.kind,
        entity_type=item.entity_type,
        entity_id=item.entity_id,
        read_at=item.read_at,
        created_at=item.created_at,
    )


def read_notification(db: Session, actor: User, notification_id: UUID) -> NotificationResponse:
    item = db.scalar(select(Notification).where(
        Notification.id == notification_id,
        Notification.organization_id == actor.organization_id,
        Notification.recipient_user_id == actor.id,
    ).with_for_update())
    if item is None:
        raise AppError(404, "NOT_FOUND")
    if item.read_at is None:
        item.read_at = utc_now()
        audit.write(db, actor, "notification.read", "notification", item.id, {
            "changed_fields": ["read_at"],
        })
        db.commit()
        db.refresh(item)
    return _notification_response(item)


def _notice_response(item: DocumentNotice) -> DocumentNoticeResponse:
    return DocumentNoticeResponse(
        id=item.id,
        recipient_user_id=item.recipient_user_id,
        title=item.title,
        kind=item.kind,
        requires_ack=item.requires_ack,
        issued_by=item.issued_by,
        acknowledged_at=item.acknowledged_at,
        created_at=item.created_at,
    )


def list_document_notices(
    db: Session,
    actor: User,
    recipient_user_id: UUID | None,
) -> DocumentNoticeList:
    query = select(DocumentNotice).where(DocumentNotice.organization_id == actor.organization_id)
    if recipient_user_id is not None:
        target = db.scalar(select(User.id).where(
            User.id == recipient_user_id,
            User.organization_id == actor.organization_id,
            User.role == "TEACHER",
        ))
        if target is None:
            raise AppError(404, "NOT_FOUND")
        query = query.where(DocumentNotice.recipient_user_id == recipient_user_id)
    rows = db.scalars(query.order_by(DocumentNotice.created_at.desc(), DocumentNotice.id.desc()))
    return DocumentNoticeList(items=[_notice_response(item) for item in rows])


def create_document_notice(
    db: Session,
    actor: User,
    payload: DocumentNoticeCreate,
) -> DocumentNoticeResponse:
    user = db.scalar(select(User).where(
        User.id == payload.recipient_user_id,
        User.organization_id == actor.organization_id,
        User.role == "TEACHER",
        User.status == "active",
    ))
    if user is None:
        raise AppError(404, "NOT_FOUND")
    employee = db.scalar(select(Employee.id).where(
        Employee.organization_id == actor.organization_id,
        Employee.user_id == user.id,
        Employee.status == "active",
    ))
    if employee is None:
        raise AppError(409, "EMPLOYEE_ARCHIVED")
    item = DocumentNotice(
        organization_id=actor.organization_id,
        recipient_user_id=user.id,
        title=payload.title,
        kind=payload.kind,
        requires_ack=payload.requires_ack,
        issued_by=actor.id,
    )
    db.add(item)
    db.flush()
    audit.write(db, actor, "document_notice.issue", "document_notice", item.id, {
        "recipient_user_id": str(user.id),
        "requires_ack": item.requires_ack,
    })
    db.commit()
    db.refresh(item)
    return _notice_response(item)


def _consent_response(item: PhotoConsent) -> PhotoConsentResponse:
    return PhotoConsentResponse(
        id=item.id,
        child_id=item.child_id,
        status=item.status,
        scope=item.scope,
        effective_from=item.effective_from,
        effective_to=item.effective_to,
        recorded_by=item.recorded_by,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def list_photo_consents(
    db: Session,
    actor: User,
    child_id: UUID | None,
    group_id: UUID | None,
) -> PhotoConsentList:
    query = select(PhotoConsent).where(PhotoConsent.organization_id == actor.organization_id)
    if child_id is not None:
        _child(db, actor, child_id)
        query = query.where(PhotoConsent.child_id == child_id)
    if group_id is not None:
        _group(db, actor, group_id)
        query = query.join(Child, Child.id == PhotoConsent.child_id).where(
            Child.organization_id == actor.organization_id,
            Child.group_id == group_id,
        )
    rows = db.scalars(query.order_by(PhotoConsent.updated_at.desc(), PhotoConsent.id.desc()))
    return PhotoConsentList(items=[_consent_response(item) for item in rows])


def record_photo_consent(
    db: Session,
    actor: User,
    payload: PhotoConsentCreate,
) -> PhotoConsentResponse:
    _child(db, actor, payload.child_id, active=True)
    item = db.scalar(select(PhotoConsent).where(
        PhotoConsent.organization_id == actor.organization_id,
        PhotoConsent.child_id == payload.child_id,
        PhotoConsent.scope == "group_photo_report",
    ).with_for_update())
    if item is None:
        item = PhotoConsent(
            organization_id=actor.organization_id,
            child_id=payload.child_id,
            status="granted",
            scope="group_photo_report",
            effective_from=payload.effective_from,
            effective_to=payload.effective_to,
            recorded_by=actor.id,
        )
        db.add(item)
        db.flush()
        details = {"child_id": str(item.child_id), "scope": item.scope}
    else:
        changed = []
        values = {
            "status": "granted",
            "effective_from": payload.effective_from,
            "effective_to": payload.effective_to,
            "recorded_by": actor.id,
        }
        for field, value in values.items():
            if getattr(item, field) != value:
                setattr(item, field, value)
                if field != "recorded_by":
                    changed.append(field)
        details = {
            "child_id": str(item.child_id),
            "scope": item.scope,
            "changed_fields": sorted(changed),
        }
    audit.write(db, actor, "photo_consent.record", "photo_consent", item.id, details)
    db.commit()
    db.refresh(item)
    return _consent_response(item)


def withdraw_photo_consent(db: Session, actor: User, consent_id: UUID) -> PhotoConsentResponse:
    item = db.scalar(select(PhotoConsent).where(
        PhotoConsent.id == consent_id,
        PhotoConsent.organization_id == actor.organization_id,
    ).with_for_update())
    if item is None:
        raise AppError(404, "NOT_FOUND")
    if item.status != "withdrawn":
        item.status = "withdrawn"
        item.effective_to = utc_now()
        item.recorded_by = actor.id
        audit.write(db, actor, "photo_consent.withdraw", "photo_consent", item.id, {
            "child_id": str(item.child_id),
            "scope": item.scope,
            "status_before": "granted",
            "status_after": "withdrawn",
            "changed_fields": ["effective_to", "status"],
        })
        db.commit()
        db.refresh(item)
    return _consent_response(item)


def get_settings(actor: User) -> ManagementSettingsResponse:
    return ManagementSettingsResponse(
        id=actor.organization.id,
        name=actor.organization.name,
        timezone=actor.organization.timezone,
    )


def update_settings(
    db: Session,
    actor: User,
    payload: ManagementSettingsPatch,
) -> ManagementSettingsResponse:
    organization = actor.organization
    data = payload.model_dump(exclude_unset=True)
    changed = []
    for field, value in data.items():
        if value is None:
            raise AppError(400, "VALIDATION_ERROR", field)
        if getattr(organization, field) != value:
            setattr(organization, field, value)
            changed.append(field)
    if changed:
        audit.write(
            db,
            actor,
            "organization.settings_update",
            "organization",
            organization.id,
            {"changed_fields": sorted(changed)},
        )
        db.commit()
        db.refresh(organization)
    return ManagementSettingsResponse(
        id=organization.id,
        name=organization.name,
        timezone=organization.timezone,
    )

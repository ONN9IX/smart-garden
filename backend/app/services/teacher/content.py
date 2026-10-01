"""Diary, announcements, polls, incidents, tasks, notifications and notices."""

from datetime import date
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.announcement import Announcement
from app.models.child_diary_entry import ChildDiaryEntry
from app.models.document_notice import DocumentNotice
from app.models.incident import Incident
from app.models.notification import Notification
from app.models.poll import Poll, PollOption, PollVote
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.schemas.teacher.contracts import (
    AnnouncementResponse,
    DiaryCreate,
    DiaryPatch,
    DiaryResponse,
    DocumentNoticeResponse,
    IncidentCreate,
    IncidentPatch,
    IncidentResponse,
    NotificationResponse,
    PollCreate,
    PollOptionResponse,
    PollResponse,
    TaskResponse,
    TeacherAnnouncementCreate,
    TeacherAnnouncementPatch,
)
from app.services import audit
from app.services.auth import utc_now
from app.services.teacher import access


def _diary(item: ChildDiaryEntry) -> DiaryResponse:
    return DiaryResponse(
        id=item.id, child_id=item.child_id, group_id=item.group_id, date=item.date,
        author_user_id=item.author_user_id, note=item.note,
        created_at=item.created_at, updated_at=item.updated_at,
    )


def teacher_diary(
    db: Session, actor: User, child_id: UUID, date_from: date | None, date_to: date | None,
) -> list[DiaryResponse]:
    child = access.teacher_child(db, actor, child_id)
    query = select(ChildDiaryEntry).where(
        ChildDiaryEntry.organization_id == actor.organization_id,
        ChildDiaryEntry.child_id == child.id,
    )
    if date_from is not None:
        query = query.where(ChildDiaryEntry.date >= date_from)
    if date_to is not None:
        query = query.where(ChildDiaryEntry.date <= date_to)
    items = db.scalars(query.order_by(ChildDiaryEntry.date.desc(), ChildDiaryEntry.created_at.desc()))
    return [_diary(item) for item in items]


def parent_diary(db: Session, actor: User, child_id: UUID) -> list[DiaryResponse]:
    _, child = access.parent_child(db, actor, child_id)
    items = db.scalars(select(ChildDiaryEntry).where(
        ChildDiaryEntry.organization_id == actor.organization_id,
        ChildDiaryEntry.child_id == child.id,
    ).order_by(ChildDiaryEntry.date.desc(), ChildDiaryEntry.created_at.desc()))
    return [_diary(item) for item in items]


def create_diary(db: Session, actor: User, payload: DiaryCreate) -> DiaryResponse:
    child = access.teacher_child(db, actor, payload.child_id)
    item = ChildDiaryEntry(
        organization_id=actor.organization_id, child_id=child.id, group_id=child.group_id,
        date=payload.date, author_user_id=actor.id, note=payload.note,
    )
    db.add(item)
    db.flush()
    audit.write(db, actor, "diary.create", "child_diary_entry", item.id, {
        "child_id": str(child.id), "group_id": str(child.group_id),
    })
    db.commit()
    db.refresh(item)
    return _diary(item)


def update_diary(db: Session, actor: User, entry_id: UUID, payload: DiaryPatch) -> DiaryResponse:
    item = db.scalar(select(ChildDiaryEntry).where(
        ChildDiaryEntry.id == entry_id,
        ChildDiaryEntry.organization_id == actor.organization_id,
    ).with_for_update(of=ChildDiaryEntry))
    if item is None:
        raise AppError(404, "NOT_FOUND")
    child = access.teacher_child(db, actor, item.child_id)
    if child.group_id != item.group_id:
        raise AppError(404, "NOT_FOUND")
    changed: list[str] = []
    for field in payload.model_fields_set:
        if getattr(item, field) != getattr(payload, field):
            setattr(item, field, getattr(payload, field))
            changed.append(field)
    audit.write(db, actor, "diary.update", "child_diary_entry", item.id, {
        "child_id": str(item.child_id), "group_id": str(item.group_id), "changed_fields": sorted(changed),
    })
    db.commit()
    db.refresh(item)
    return _diary(item)


def _announcement(item: Announcement) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=item.id, target_type=item.target_type, group_id=item.group_id,
        title=item.title, body=item.body, status=item.status,
        created_by=item.created_by, created_at=item.created_at, updated_at=item.updated_at,
    )


def teacher_announcements(db: Session, actor: User, group_id: UUID) -> list[AnnouncementResponse]:
    access.teacher_group(db, actor, group_id)
    items = db.scalars(select(Announcement).where(
        Announcement.organization_id == actor.organization_id,
        Announcement.group_id == group_id,
    ).order_by(Announcement.created_at.desc(), Announcement.id.desc()))
    return [_announcement(item) for item in items]


def parent_announcements(db: Session, actor: User) -> list[AnnouncementResponse]:
    group_ids = access.parent_group_ids(db, actor)
    eligibility = Announcement.target_type == "all"
    if group_ids:
        eligibility = or_(eligibility, Announcement.group_id.in_(group_ids))
    items = db.scalars(select(Announcement).where(
        Announcement.organization_id == actor.organization_id,
        Announcement.status == "active",
        eligibility,
    ).order_by(Announcement.created_at.desc(), Announcement.id.desc()))
    return [_announcement(item) for item in items.unique()]


def create_announcement(
    db: Session, actor: User, payload: TeacherAnnouncementCreate,
) -> AnnouncementResponse:
    access.teacher_group(db, actor, payload.group_id)
    item = Announcement(
        organization_id=actor.organization_id, target_type="group", group_id=payload.group_id,
        title=payload.title, body=payload.body, status="active",
        created_by=actor.id, updated_by=actor.id,
    )
    db.add(item)
    db.flush()
    audit.write(db, actor, "teacher_announcement.create", "announcement", item.id, {
        "target_type": "group", "group_id": str(payload.group_id),
    })
    db.commit()
    db.refresh(item)
    return _announcement(item)


def _owned_announcement(db: Session, actor: User, announcement_id: UUID) -> Announcement:
    item = db.scalar(select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.organization_id == actor.organization_id,
        Announcement.target_type == "group",
        Announcement.created_by == actor.id,
    ).with_for_update(of=Announcement))
    if item is None or item.group_id is None:
        raise AppError(404, "NOT_FOUND")
    access.teacher_group(db, actor, item.group_id)
    return item


def update_announcement(
    db: Session, actor: User, announcement_id: UUID, payload: TeacherAnnouncementPatch,
) -> AnnouncementResponse:
    item = _owned_announcement(db, actor, announcement_id)
    if item.status != "active":
        raise AppError(409, "ANNOUNCEMENT_ARCHIVED")
    for field in payload.model_fields_set:
        setattr(item, field, getattr(payload, field))
    item.updated_by = actor.id
    audit.write(db, actor, "teacher_announcement.update", "announcement", item.id, {
        "target_type": "group", "group_id": str(item.group_id),
    })
    db.commit()
    db.refresh(item)
    return _announcement(item)


def archive_announcement(db: Session, actor: User, announcement_id: UUID) -> AnnouncementResponse:
    item = _owned_announcement(db, actor, announcement_id)
    if item.status == "active":
        item.status = "archived"
        item.archived_at = utc_now()
        item.updated_by = actor.id
        audit.write(db, actor, "teacher_announcement.archive", "announcement", item.id, {
            "target_type": "group", "group_id": str(item.group_id),
        })
        db.commit()
        db.refresh(item)
    return _announcement(item)


def _poll(db: Session, item: Poll, voter_id: UUID | None = None) -> PollResponse:
    options = list(db.scalars(select(PollOption).where(
        PollOption.poll_id == item.id,
    ).order_by(PollOption.sort_order, PollOption.id)))
    selected = None
    if voter_id is not None:
        selected = db.scalar(select(PollVote.option_id).where(
            PollVote.poll_id == item.id, PollVote.voter_user_id == voter_id,
        ))
    return PollResponse(
        id=item.id, group_id=item.group_id, question=item.question, status=item.status,
        closes_at=item.closes_at, created_by=item.created_by,
        options=[PollOptionResponse(id=option.id, label=option.label, sort_order=option.sort_order) for option in options],
        selected_option_id=selected, created_at=item.created_at,
    )


def teacher_polls(db: Session, actor: User, group_id: UUID) -> list[PollResponse]:
    access.teacher_group(db, actor, group_id)
    items = db.scalars(select(Poll).where(
        Poll.organization_id == actor.organization_id, Poll.group_id == group_id,
    ).order_by(Poll.created_at.desc(), Poll.id.desc()))
    return [_poll(db, item) for item in items]


def parent_polls(db: Session, actor: User) -> list[PollResponse]:
    group_ids = access.parent_group_ids(db, actor)
    if not group_ids:
        return []
    items = db.scalars(select(Poll).where(
        Poll.organization_id == actor.organization_id,
        Poll.group_id.in_(group_ids),
        Poll.status.in_(("active", "closed")),
    ).order_by(Poll.created_at.desc(), Poll.id.desc()))
    return [_poll(db, item, actor.id) for item in items]


def create_poll(db: Session, actor: User, payload: PollCreate) -> PollResponse:
    access.teacher_group(db, actor, payload.group_id)
    item = Poll(
        organization_id=actor.organization_id, group_id=payload.group_id,
        question=payload.question, status="active", closes_at=payload.closes_at, created_by=actor.id,
    )
    db.add(item)
    db.flush()
    db.add_all([PollOption(poll_id=item.id, label=label, sort_order=index) for index, label in enumerate(payload.options)])
    audit.write(db, actor, "poll.create", "poll", item.id, {"group_id": str(item.group_id)})
    db.commit()
    db.refresh(item)
    return _poll(db, item)


def close_poll(db: Session, actor: User, poll_id: UUID) -> PollResponse:
    item = db.scalar(select(Poll).where(
        Poll.id == poll_id, Poll.organization_id == actor.organization_id,
    ).with_for_update())
    if item is None:
        raise AppError(404, "NOT_FOUND")
    access.teacher_group(db, actor, item.group_id)
    if item.status == "active":
        item.status = "closed"
        audit.write(db, actor, "poll.close", "poll", item.id, {
            "group_id": str(item.group_id), "status_before": "active", "status_after": "closed",
        })
        db.commit()
        db.refresh(item)
    return _poll(db, item)


def vote_poll(db: Session, actor: User, poll_id: UUID, option_id: UUID) -> PollResponse:
    item = db.scalar(select(Poll).where(
        Poll.id == poll_id, Poll.organization_id == actor.organization_id,
    ).with_for_update())
    if item is None or item.status != "active" or item.group_id not in access.parent_group_ids(db, actor):
        raise AppError(404, "NOT_FOUND")
    if item.closes_at is not None and item.closes_at <= utc_now():
        raise AppError(404, "NOT_FOUND")
    option = db.scalar(select(PollOption).where(PollOption.id == option_id, PollOption.poll_id == item.id))
    if option is None:
        raise AppError(404, "NOT_FOUND")
    if db.scalar(select(PollVote.id).where(
        PollVote.poll_id == item.id, PollVote.voter_user_id == actor.id,
    )) is not None:
        raise AppError(409, "RELATION_ALREADY_EXISTS")
    vote = PollVote(
        organization_id=actor.organization_id, poll_id=item.id,
        option_id=option.id, voter_user_id=actor.id,
    )
    db.add(vote)
    db.flush()
    audit.write(db, actor, "poll.vote", "poll_vote", vote.id, {
        "poll_id": str(item.id), "option_id": str(option.id), "group_id": str(item.group_id),
    })
    db.commit()
    return _poll(db, item, actor.id)


def _incident(item: Incident) -> IncidentResponse:
    return IncidentResponse(
        id=item.id, group_id=item.group_id, child_id=item.child_id,
        occurred_at=item.occurred_at, category=item.category, description=item.description,
        status=item.status, reported_by=item.reported_by, resolved_by=item.resolved_by,
        created_at=item.created_at, updated_at=item.updated_at,
    )


def incidents(db: Session, actor: User, group_id: UUID, status: str | None) -> list[IncidentResponse]:
    access.teacher_group(db, actor, group_id)
    query = select(Incident).where(
        Incident.organization_id == actor.organization_id, Incident.group_id == group_id,
    )
    if status is not None:
        query = query.where(Incident.status == status)
    items = db.scalars(query.order_by(Incident.occurred_at.desc(), Incident.id.desc()))
    return [_incident(item) for item in items]


def create_incident(db: Session, actor: User, payload: IncidentCreate) -> IncidentResponse:
    access.teacher_group(db, actor, payload.group_id)
    if payload.child_id is not None:
        child = access.teacher_child(db, actor, payload.child_id)
        if child.group_id != payload.group_id:
            raise AppError(404, "NOT_FOUND")
    item = Incident(
        organization_id=actor.organization_id, group_id=payload.group_id, child_id=payload.child_id,
        occurred_at=payload.occurred_at, category=payload.category, description=payload.description,
        status="open", reported_by=actor.id,
    )
    db.add(item)
    db.flush()
    audit.write(db, actor, "incident.create", "incident", item.id, {
        "group_id": str(item.group_id), "child_id": str(item.child_id) if item.child_id else None,
        "category": item.category,
    })
    db.commit()
    db.refresh(item)
    return _incident(item)


def update_incident(
    db: Session, actor: User, incident_id: UUID, payload: IncidentPatch,
) -> IncidentResponse:
    item = db.scalar(select(Incident).where(
        Incident.id == incident_id, Incident.organization_id == actor.organization_id,
    ).with_for_update())
    if item is None:
        raise AppError(404, "NOT_FOUND")
    access.teacher_group(db, actor, item.group_id)
    before_status = item.status
    changed: list[str] = []
    for field in payload.model_fields_set:
        if getattr(item, field) != getattr(payload, field):
            setattr(item, field, getattr(payload, field))
            changed.append(field)
    if item.status == "resolved":
        item.resolved_by = actor.id
    elif "status" in changed:
        item.resolved_by = None
    action = "incident.resolve" if before_status != "resolved" and item.status == "resolved" else "incident.update"
    details: dict = {
        "group_id": str(item.group_id), "child_id": str(item.child_id) if item.child_id else None,
        "category": item.category,
    }
    safe_changed = [field for field in changed if field != "description"]
    if safe_changed:
        details["changed_fields"] = safe_changed
    if before_status != item.status:
        details.update(status_before=before_status, status_after=item.status)
    audit.write(db, actor, action, "incident", item.id, details)
    db.commit()
    db.refresh(item)
    return _incident(item)


def _task(item: TeacherTask) -> TaskResponse:
    return TaskResponse(
        id=item.id, group_id=item.group_id, title=item.title, description=item.description,
        due_at=item.due_at, status=item.status, created_at=item.created_at, updated_at=item.updated_at,
    )


def tasks(db: Session, actor: User) -> list[TaskResponse]:
    employee = access.teacher_employee(db, actor)
    items = db.scalars(select(TeacherTask).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.assignee_employee_id == employee.id,
    ).order_by(TeacherTask.due_at.asc().nulls_last(), TeacherTask.created_at.desc()))
    return [_task(item) for item in items]


def update_task(db: Session, actor: User, task_id: UUID, status: str) -> TaskResponse:
    employee = access.teacher_employee(db, actor)
    item = db.scalar(select(TeacherTask).where(
        TeacherTask.id == task_id,
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.assignee_employee_id == employee.id,
    ).with_for_update())
    if item is None:
        raise AppError(404, "NOT_FOUND")
    before = item.status
    item.status = status
    if before != status:
        audit.write(db, actor, "teacher_task.status", "teacher_task", item.id, {
            "assignee_employee_id": str(employee.id),
            "group_id": str(item.group_id) if item.group_id else None,
            "status_before": before, "status_after": status,
        })
        db.commit()
        db.refresh(item)
    return _task(item)


def _notification(item: Notification) -> NotificationResponse:
    return NotificationResponse(
        id=item.id, kind=item.kind, entity_type=item.entity_type, entity_id=item.entity_id,
        read_at=item.read_at, created_at=item.created_at,
    )


def notifications(db: Session, actor: User) -> list[NotificationResponse]:
    items = db.scalars(select(Notification).where(
        Notification.organization_id == actor.organization_id,
        Notification.recipient_user_id == actor.id,
    ).order_by(Notification.created_at.desc(), Notification.id.desc()))
    return [_notification(item) for item in items]


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
            "recipient_user_id": str(actor.id), "status_before": "unread", "status_after": "read",
        })
        db.commit()
        db.refresh(item)
    return _notification(item)


def _notice(item: DocumentNotice) -> DocumentNoticeResponse:
    return DocumentNoticeResponse(
        id=item.id, title=item.title, kind=item.kind, requires_ack=item.requires_ack,
        acknowledged_at=item.acknowledged_at, created_at=item.created_at,
    )


def notices(db: Session, actor: User) -> list[DocumentNoticeResponse]:
    items = db.scalars(select(DocumentNotice).where(
        DocumentNotice.organization_id == actor.organization_id,
        DocumentNotice.recipient_user_id == actor.id,
    ).order_by(DocumentNotice.created_at.desc(), DocumentNotice.id.desc()))
    return [_notice(item) for item in items]


def acknowledge_notice(db: Session, actor: User, notice_id: UUID) -> DocumentNoticeResponse:
    item = db.scalar(select(DocumentNotice).where(
        DocumentNotice.id == notice_id,
        DocumentNotice.organization_id == actor.organization_id,
        DocumentNotice.recipient_user_id == actor.id,
    ).with_for_update())
    if item is None:
        raise AppError(404, "NOT_FOUND")
    if item.acknowledged_at is None:
        item.acknowledged_at = utc_now()
        audit.write(db, actor, "document_notice.ack", "document_notice", item.id, {
            "recipient_user_id": str(actor.id), "requires_ack": item.requires_ack,
        })
        db.commit()
        db.refresh(item)
    return _notice(item)

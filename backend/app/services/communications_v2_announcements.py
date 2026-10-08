"""Audience-scoped, privacy-minimized announcement v2 lifecycle."""

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.announcement import Announcement
from app.models.announcement_read_state import AnnouncementReadState
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.notification import Notification
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from app.schemas.communications_v2 import (
    AnnouncementCreateV2,
    AnnouncementPatchV2,
    AnnouncementReadResponse,
    AnnouncementSummaryV2,
)
from app.services import audit
from app.services.teacher import access


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _group(db: Session, actor: User, group_id: UUID) -> Group:
    group = db.scalar(select(Group).where(
        Group.id == group_id, Group.organization_id == actor.organization_id, Group.status == "active",
    ))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    return group


def _eligible_recipients(
    db: Session, organization_id: UUID, target_type: str, group_id: UUID | None, audience: str,
) -> set[UUID]:
    parents = set(db.scalars(
        select(User.id).join(Guardian, Guardian.user_id == User.id)
        .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
        .join(Child, Child.id == ChildGuardian.child_id)
        .join(Group, Group.id == Child.group_id)
        .where(
            User.organization_id == organization_id, User.role == "PARENT", User.status == "active",
            Guardian.organization_id == organization_id, Guardian.status == "active",
            ChildGuardian.organization_id == organization_id, ChildGuardian.status == "active",
            Child.organization_id == organization_id, Child.status == "active",
            Group.organization_id == organization_id, Group.status == "active",
            *(([Child.group_id == group_id]) if target_type == "group" and group_id else []),
        ).distinct()
    ))
    teachers = set(db.scalars(
        select(User.id).join(Employee, Employee.user_id == User.id)
        .join(TeacherGroupAssignment, TeacherGroupAssignment.employee_id == Employee.id)
        .join(Group, Group.id == TeacherGroupAssignment.group_id)
        .where(
            User.organization_id == organization_id, User.role == "TEACHER", User.status == "active",
            Employee.organization_id == organization_id, Employee.status == "active", Employee.category == "teacher",
            TeacherGroupAssignment.organization_id == organization_id, TeacherGroupAssignment.status == "active",
            Group.organization_id == organization_id, Group.status == "active",
            *(([TeacherGroupAssignment.group_id == group_id]) if target_type == "group" and group_id else []),
        ).distinct()
    ))
    managers = set(db.scalars(select(User.id).where(
        User.organization_id == organization_id, User.role.in_(("DIRECTOR", "ADMIN")), User.status == "active",
    )))
    if audience == "parents":
        return parents
    if audience == "staff":
        return teachers | managers
    return parents | teachers | managers


def _can_read(db: Session, actor: User, item: Announcement) -> bool:
    if actor.organization_id != item.organization_id:
        return False
    if actor.role in {"DIRECTOR", "ADMIN"}:
        return True
    if actor.role == "TEACHER" and item.created_by == actor.id and item.group_id is not None:
        try:
            access.teacher_group(db, actor, item.group_id)
            return True
        except AppError:
            return False
    if item.status != "active":
        return False
    recipients = _eligible_recipients(db, actor.organization_id, item.target_type, item.group_id, item.audience)
    return actor.id in recipients


def _summary(db: Session, actor: User, item: Announcement) -> AnnouncementSummaryV2:
    group = db.scalar(select(Group).where(
        Group.id == item.group_id, Group.organization_id == actor.organization_id,
    )) if item.group_id else None
    state = db.scalar(select(AnnouncementReadState).where(
        AnnouncementReadState.organization_id == actor.organization_id,
        AnnouncementReadState.announcement_id == item.id,
        AnnouncementReadState.user_id == actor.id,
    ))
    recipients = _eligible_recipients(db, actor.organization_id, item.target_type, item.group_id, item.audience)
    recipients.discard(item.created_by)
    return AnnouncementSummaryV2(
        id=item.id, target_type=item.target_type, audience=item.audience, group_id=item.group_id,
        group_name=group.name if group else None, title=item.title, body=item.body,
        published_at=item.created_at, status=item.status, archived_at=item.archived_at,
        unread=state is None or state.read_at is None,
        recipient_count=len(recipients),
        can_manage=actor.role in {"DIRECTOR", "ADMIN"} or (actor.role == "TEACHER" and item.created_by == actor.id),
    )


def list_for_actor(db: Session, actor: User, status: str = "active") -> list[AnnouncementSummaryV2]:
    if status not in {"active", "archived", "all"}:
        raise AppError(400, "VALIDATION_ERROR", "status")
    query = select(Announcement).where(Announcement.organization_id == actor.organization_id)
    if actor.role == "PARENT":
        query = query.where(Announcement.status == "active")
    elif actor.role == "TEACHER":
        if status != "all":
            query = query.where(Announcement.status == status)
    elif status != "all":
        query = query.where(Announcement.status == status)
    rows = db.scalars(query.order_by(Announcement.created_at.desc(), Announcement.id.desc()))
    result = []
    for item in rows:
        if _can_read(db, actor, item):
            result.append(_summary(db, actor, item))
    return result


def get_for_actor(db: Session, actor: User, item_id: UUID) -> AnnouncementSummaryV2:
    item = db.scalar(select(Announcement).where(
        Announcement.id == item_id, Announcement.organization_id == actor.organization_id,
    ))
    if item is None or not _can_read(db, actor, item):
        raise AppError(404, "NOT_FOUND")
    return _summary(db, actor, item)


def create(
    db: Session, actor: User, payload: AnnouncementCreateV2, idempotency_key: str | None = None,
) -> AnnouncementSummaryV2:
    if actor.role == "TEACHER":
        if payload.target_type != "group" or payload.group_id is None:
            raise AppError(404, "NOT_FOUND")
        access.teacher_group(db, actor, payload.group_id)
    elif actor.role in {"DIRECTOR", "ADMIN"}:
        if payload.group_id is not None:
            _group(db, actor, payload.group_id)
    else:
        raise AppError(403, "FORBIDDEN")
    if idempotency_key:
        existing = db.scalar(select(Announcement).where(
            Announcement.organization_id == actor.organization_id,
            Announcement.created_by == actor.id,
            Announcement.idempotency_key == idempotency_key,
        ))
        if existing is not None:
            return _summary(db, actor, existing)
    item = Announcement(
        organization_id=actor.organization_id, target_type=payload.target_type,
        audience=payload.audience, group_id=payload.group_id, title=payload.title, body=payload.body,
        status="active", created_by=actor.id, updated_by=actor.id,
        idempotency_key=idempotency_key,
    )
    db.add(item)
    db.flush()
    recipients = _eligible_recipients(db, actor.organization_id, item.target_type, item.group_id, item.audience)
    recipients.discard(actor.id)
    # Payload text and recipient identities never enter the audit trail or notifications.
    audit.write(db, actor, "communications.announcement.publish", "announcement", item.id, {
        "target_type": item.target_type, "group_id": str(item.group_id) if item.group_id else None,
        "audience": item.audience, "recipient_count": len(recipients),
    })
    predicate = text(
        "read_at IS NULL AND kind = 'announcement.published' AND "
        "entity_type = 'announcement' AND entity_id IS NOT NULL"
    )
    for recipient_id in recipients:
        db.execute(insert(Notification).values(
            organization_id=actor.organization_id, recipient_user_id=recipient_id,
            kind="announcement.published", entity_type="announcement", entity_id=item.id,
        ).on_conflict_do_nothing(
            index_elements=[Notification.organization_id, Notification.recipient_user_id, Notification.entity_id],
            index_where=predicate,
        ))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        if not idempotency_key:
            raise
        existing = db.scalar(select(Announcement).where(
            Announcement.organization_id == actor.organization_id,
            Announcement.created_by == actor.id,
            Announcement.idempotency_key == idempotency_key,
        ))
        if existing is None:
            raise
        return _summary(db, actor, existing)
    db.refresh(item)
    return _summary(db, actor, item)


def update_content(db: Session, actor: User, item_id: UUID, payload: AnnouncementPatchV2) -> AnnouncementSummaryV2:
    item = db.scalar(select(Announcement).where(
        Announcement.id == item_id, Announcement.organization_id == actor.organization_id,
    ).with_for_update(of=Announcement))
    if item is None:
        raise AppError(404, "NOT_FOUND")
    if item.status != "active":
        raise AppError(409, "ANNOUNCEMENT_ARCHIVED")
    if actor.role == "TEACHER":
        if item.target_type != "group" or item.created_by != actor.id or item.group_id is None:
            raise AppError(404, "NOT_FOUND")
        access.teacher_group(db, actor, item.group_id)
    elif actor.role not in {"DIRECTOR", "ADMIN"}:
        raise AppError(403, "FORBIDDEN")
    if not payload.model_fields_set:
        raise AppError(400, "VALIDATION_ERROR")
    if "title" in payload.model_fields_set:
        item.title = payload.title
    if "body" in payload.model_fields_set:
        item.body = payload.body
    item.updated_by = actor.id
    audit.write(db, actor, "communications.announcement.update", "announcement", item.id, {
        "target_type": item.target_type, "group_id": str(item.group_id) if item.group_id else None,
        "audience": item.audience, "changed_fields": sorted(payload.model_fields_set),
    })
    db.commit()
    db.refresh(item)
    return _summary(db, actor, item)


def archive(db: Session, actor: User, item_id: UUID) -> AnnouncementSummaryV2:
    item = db.scalar(select(Announcement).where(
        Announcement.id == item_id, Announcement.organization_id == actor.organization_id,
    ).with_for_update(of=Announcement))
    if item is None:
        raise AppError(404, "NOT_FOUND")
    if actor.role == "TEACHER":
        if item.created_by != actor.id or item.target_type != "group" or item.group_id is None:
            raise AppError(404, "NOT_FOUND")
        access.teacher_group(db, actor, item.group_id)
    elif actor.role not in {"DIRECTOR", "ADMIN"}:
        raise AppError(403, "FORBIDDEN")
    if item.status == "active":
        item.status = "archived"
        item.archived_at = _now()
        item.updated_by = actor.id
        audit.write(db, actor, "communications.announcement.archive", "announcement", item.id, {
            "target_type": item.target_type, "group_id": str(item.group_id) if item.group_id else None,
            "audience": item.audience,
        })
        db.commit()
        db.refresh(item)
    return _summary(db, actor, item)


def mark_read(db: Session, actor: User, item_id: UUID) -> AnnouncementReadResponse:
    item = db.scalar(select(Announcement).where(
        Announcement.id == item_id, Announcement.organization_id == actor.organization_id,
    ))
    if item is None or not _can_read(db, actor, item):
        raise AppError(404, "NOT_FOUND")
    now = _now()
    state = db.scalar(select(AnnouncementReadState).where(
        AnnouncementReadState.organization_id == actor.organization_id,
        AnnouncementReadState.announcement_id == item.id,
        AnnouncementReadState.user_id == actor.id,
    ).with_for_update())
    if state is None:
        db.execute(insert(AnnouncementReadState).values(
            organization_id=actor.organization_id, announcement_id=item.id, user_id=actor.id,
            read_at=now, updated_at=now,
        ).on_conflict_do_nothing(index_elements=[
            AnnouncementReadState.organization_id,
            AnnouncementReadState.announcement_id,
            AnnouncementReadState.user_id,
        ]))
        state = db.scalar(select(AnnouncementReadState).where(
            AnnouncementReadState.organization_id == actor.organization_id,
            AnnouncementReadState.announcement_id == item.id,
            AnnouncementReadState.user_id == actor.id,
        ).with_for_update())
    elif state.read_at is None:
        state.read_at = now
        state.updated_at = now
    notifications = db.scalars(select(Notification).where(
        Notification.organization_id == actor.organization_id,
        Notification.recipient_user_id == actor.id,
        Notification.kind == "announcement.published",
        Notification.entity_type == "announcement",
        Notification.entity_id == item.id,
        Notification.read_at.is_(None),
    ))
    for notification in notifications:
        notification.read_at = now
    db.commit()
    return AnnouncementReadResponse(announcement_id=item.id, read_at=state.read_at or now)

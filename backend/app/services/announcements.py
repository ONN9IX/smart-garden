"""Tenant-scoped Announcement lifecycle with atomic privacy-safe Audit writes."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.announcement import Announcement
from app.models.group import Group
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementGroup,
    AnnouncementList,
    AnnouncementPatch,
    AnnouncementResponse,
)
from app.services import audit
from app.services.auth import utc_now


def _announcement(db: Session, actor: User, announcement_id: UUID, *, lock: bool = False) -> Announcement:
    query = select(Announcement).where(
        Announcement.id == announcement_id,
        Announcement.organization_id == actor.organization_id,
    )
    if lock:
        # The optional group is eager-loaded with a LEFT JOIN; lock only the
        # announcement row so PostgreSQL never tries to lock the nullable side.
        query = query.with_for_update(of=Announcement)
    item = db.scalar(query)
    if item is None:
        raise AppError(404, "NOT_FOUND")
    return item


def _group(db: Session, actor: User, group_id: UUID, *, active: bool) -> Group:
    query = select(Group).where(Group.id == group_id, Group.organization_id == actor.organization_id)
    group = db.scalar(query)
    if group is None:
        raise AppError(404, "NOT_FOUND")
    if active and group.status != "active":
        raise AppError(409, "GROUP_ARCHIVED", "group_id")
    return group


def _response(item: Announcement) -> AnnouncementResponse:
    return AnnouncementResponse(
        id=item.id,
        target_type=item.target_type,
        group=AnnouncementGroup(id=item.group.id, name=item.group.name) if item.group else None,
        title=item.title,
        body=item.body,
        status=item.status,
        created_by=item.created_by,
        updated_by=item.updated_by,
        archived_at=item.archived_at,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _audit_details(target_type: str, group_id: UUID | None, changed: list[str] | None = None) -> dict:
    # Announcement free text and even its field names are deliberately excluded.
    details: dict = {"target_type": target_type, "group_id": str(group_id) if group_id else None}
    safe_changed = [field for field in (changed or []) if field in {"target_type", "group_id"}]
    if safe_changed:
        details["changed_fields"] = safe_changed
    return details


def list_announcements(
    db: Session,
    actor: User,
    *,
    status: str,
    target_type: str | None,
    group_id: UUID | None,
) -> AnnouncementList:
    if group_id is not None:
        _group(db, actor, group_id, active=False)
    query = select(Announcement).where(Announcement.organization_id == actor.organization_id)
    if status != "all":
        query = query.where(Announcement.status == status)
    if target_type is not None:
        query = query.where(Announcement.target_type == target_type)
    if group_id is not None:
        query = query.where(Announcement.group_id == group_id)
    items = db.scalars(query.order_by(Announcement.created_at.desc(), Announcement.id.desc())).unique()
    return AnnouncementList(items=[_response(item) for item in items])


def create_announcement(
    db: Session,
    actor: User,
    payload: AnnouncementCreate,
    *,
    idempotency_key: str | None = None,
) -> AnnouncementResponse:
    if idempotency_key:
        existing = db.scalar(select(Announcement).where(
            Announcement.organization_id == actor.organization_id,
            Announcement.created_by == actor.id,
            Announcement.idempotency_key == idempotency_key,
        ))
        if existing is not None:
            return _response(existing)
    if payload.group_id is not None:
        _group(db, actor, payload.group_id, active=True)
    item = Announcement(
        organization_id=actor.organization_id,
        target_type=payload.target_type,
        group_id=payload.group_id,
        title=payload.title,
        body=payload.body,
        status="active",
        created_by=actor.id,
        updated_by=actor.id,
        idempotency_key=idempotency_key,
    )
    db.add(item)
    try:
        db.flush()
        audit.write(
            db, actor, "announcement.create", "announcement", item.id,
            _audit_details(item.target_type, item.group_id),
        )
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
        return _response(existing)
    db.refresh(item)
    return _response(item)


def get_announcement(db: Session, actor: User, announcement_id: UUID) -> AnnouncementResponse:
    return _response(_announcement(db, actor, announcement_id))


def update_announcement(
    db: Session,
    actor: User,
    announcement_id: UUID,
    payload: AnnouncementPatch,
) -> AnnouncementResponse:
    item = _announcement(db, actor, announcement_id, lock=True)
    if item.status == "archived":
        raise AppError(409, "ANNOUNCEMENT_ARCHIVED")
    before = {
        "target_type": item.target_type,
        "group_id": item.group_id,
        "title": item.title,
        "body": item.body,
    }
    target_type = payload.target_type if "target_type" in payload.model_fields_set else item.target_type
    if "group_id" in payload.model_fields_set and payload.group_id is not None:
        _group(db, actor, payload.group_id, active=True)
    if target_type == "all":
        if "group_id" in payload.model_fields_set and payload.group_id is not None:
            raise AppError(400, "VALIDATION_ERROR", "group_id")
        group_id = None
    else:
        group_id = payload.group_id if "group_id" in payload.model_fields_set else item.group_id
        if group_id is None:
            raise AppError(400, "VALIDATION_ERROR", "group_id")
        if "group_id" not in payload.model_fields_set:
            _group(db, actor, group_id, active=True)
    item.target_type = target_type
    item.group_id = group_id
    if "title" in payload.model_fields_set:
        item.title = payload.title
    if "body" in payload.model_fields_set:
        item.body = payload.body
    item.updated_by = actor.id
    after = {
        "target_type": item.target_type,
        "group_id": item.group_id,
        "title": item.title,
        "body": item.body,
    }
    audit.write(
        db, actor, "announcement.update", "announcement", item.id,
        _audit_details(item.target_type, item.group_id, audit.changed_fields(before, after)),
    )
    db.commit()
    db.refresh(item)
    return _response(item)


def archive_announcement(db: Session, actor: User, announcement_id: UUID) -> AnnouncementResponse:
    item = _announcement(db, actor, announcement_id, lock=True)
    if item.status == "archived":
        return _response(item)
    item.status = "archived"
    item.archived_at = utc_now()
    item.updated_by = actor.id
    audit.write(
        db, actor, "announcement.archive", "announcement", item.id,
        _audit_details(item.target_type, item.group_id),
    )
    db.commit()
    db.refresh(item)
    return _response(item)

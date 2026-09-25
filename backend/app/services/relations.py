"""Tenant-scoped child ↔ guardian lifecycle with retained archived pairs."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.guardian import Guardian
from app.models.user import User
from app.schemas.child import ChildGuardianResponse, GuardianSummary
from app.schemas.relation import RelationType
from app.services.auth import utc_now


def _entities(db: Session, user: User, child_id: UUID, guardian_id: UUID, *, lock: bool = False) -> tuple[Child, Guardian]:
    # Lock Child then Guardian to serialize links with archiving.
    child_query = select(Child).where(Child.id == child_id, Child.organization_id == user.organization_id)
    guardian_query = select(Guardian).where(Guardian.id == guardian_id, Guardian.organization_id == user.organization_id)
    if lock:
        child_query = child_query.with_for_update()
        guardian_query = guardian_query.with_for_update()
    child = db.scalar(child_query)
    guardian = db.scalar(guardian_query)
    if child is None or guardian is None:
        raise AppError(404, "NOT_FOUND")
    return child, guardian


def _active(child: Child, guardian: Guardian) -> None:
    if child.status != "active":
        raise AppError(409, "CHILD_ARCHIVED")
    if guardian.status != "active":
        raise AppError(409, "GUARDIAN_ARCHIVED")


def _relation(db: Session, user: User, child_id: UUID, guardian_id: UUID) -> ChildGuardian:
    _entities(db, user, child_id, guardian_id)
    record = db.scalar(select(ChildGuardian).where(
        ChildGuardian.child_id == child_id, ChildGuardian.guardian_id == guardian_id,
        ChildGuardian.organization_id == user.organization_id,
    ))
    if record is None:
        raise AppError(404, "RELATION_NOT_FOUND")
    return record


def response(record: ChildGuardian) -> ChildGuardianResponse:
    guardian = record.guardian
    return ChildGuardianResponse(
        id=record.id, relation_type=record.relation_type, status=record.status,
        guardian=GuardianSummary(
            id=guardian.id, first_name=guardian.first_name, last_name=guardian.last_name,
            middle_name=guardian.middle_name, phone=guardian.phone, email=guardian.email,
            status=guardian.status,
        ),
        archived_at=record.archived_at, created_at=record.created_at, updated_at=record.updated_at,
    )


def link(db: Session, user: User, child_id: UUID, guardian_id: UUID, relation_type: RelationType) -> tuple[ChildGuardianResponse, bool]:
    child, guardian = _entities(db, user, child_id, guardian_id, lock=True)
    _active(child, guardian)
    existing = db.scalar(select(ChildGuardian).where(
        ChildGuardian.child_id == child.id, ChildGuardian.guardian_id == guardian.id,
        ChildGuardian.organization_id == user.organization_id,
    ))
    if existing and existing.status == "active":
        raise AppError(409, "RELATION_ALREADY_EXISTS")
    created = existing is None
    if existing:
        existing.status = "active"
        existing.archived_at = None
        existing.relation_type = relation_type
        record = existing
    else:
        record = ChildGuardian(
            organization_id=user.organization_id, child_id=child.id, guardian_id=guardian.id,
            relation_type=relation_type, status="active",
        )
        db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "RELATION_ALREADY_EXISTS") from None
    db.refresh(record)
    db.expire(child, ["guardian_links"])
    db.expire(guardian, ["child_links"])
    return response(record), created


def update_relation(db: Session, user: User, child_id: UUID, guardian_id: UUID, relation_type: RelationType) -> ChildGuardianResponse:
    record = _relation(db, user, child_id, guardian_id)
    if record.status != "active":
        raise AppError(404, "RELATION_NOT_FOUND")
    record.relation_type = relation_type
    db.commit()
    db.refresh(record)
    return response(record)


def archive_relation(db: Session, user: User, child_id: UUID, guardian_id: UUID) -> ChildGuardianResponse:
    record = _relation(db, user, child_id, guardian_id)
    if record.status == "active":
        record.status = "archived"
        record.archived_at = utc_now()
        db.commit()
        db.refresh(record)
    return response(record)


def restore_relation(db: Session, user: User, child_id: UUID, guardian_id: UUID) -> ChildGuardianResponse:
    child, guardian = _entities(db, user, child_id, guardian_id, lock=True)
    _active(child, guardian)
    record = _relation(db, user, child_id, guardian_id)
    if record.status == "archived":
        record.status = "active"
        record.archived_at = None
        db.commit()
        db.refresh(record)
    return response(record)

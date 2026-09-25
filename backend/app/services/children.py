"""Tenant-scoped child business rules and projections; never log child attributes."""

from datetime import date
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.child import Child
from app.models.group import Group
from app.models.user import User
from app.schemas.child import (
    ChildCreate,
    ChildPatch,
    ChildResponse,
    ChildSummary,
    GroupSummary,
)
from app.services.auth import utc_now


def get_child(db: Session, user: User, child_id: UUID) -> Child:
    child = db.scalar(select(Child).where(Child.id == child_id, Child.organization_id == user.organization_id))
    if child is None:
        raise AppError(404, "NOT_FOUND")
    return child


def active_group(db: Session, user: User, group_id: UUID) -> Group:
    # Serialize creation/transfer/restore against Group archive.
    group = db.scalar(select(Group).where(Group.id == group_id, Group.organization_id == user.organization_id).with_for_update())
    if group is None:
        raise AppError(404, "NOT_FOUND")
    if group.status != "active":
        raise AppError(409, "GROUP_ARCHIVED", "group_id")
    return group


def group_for_filter(db: Session, user: User, group_id: UUID) -> None:
    if db.scalar(select(Group.id).where(Group.id == group_id, Group.organization_id == user.organization_id)) is None:
        raise AppError(404, "NOT_FOUND")


def validate_birth_date(value: date) -> None:
    if value > utc_now().date():
        raise AppError(400, "INVALID_BIRTH_DATE", "birth_date")


def summary(child: Child) -> ChildSummary:
    return ChildSummary(
        id=child.id, first_name=child.first_name, last_name=child.last_name,
        middle_name=child.middle_name, birth_date=child.birth_date,
        status=child.status, group=GroupSummary.model_validate(child.group),
    )


def detail(child: Child) -> ChildResponse:
    # Child ↔ Guardian details are populated when BACK2-05 adds relation endpoints.
    return ChildResponse(
        **summary(child).model_dump(), guardians=[], archived_at=child.archived_at,
        created_at=child.created_at, updated_at=child.updated_at,
    )


def list_children(db: Session, user: User, status: str, group_id: UUID | None, q: str | None) -> list[ChildSummary]:
    if group_id:
        group_for_filter(db, user, group_id)
    stmt = select(Child).where(Child.organization_id == user.organization_id)
    if status != "all":
        stmt = stmt.where(Child.status == status)
    if group_id:
        stmt = stmt.where(Child.group_id == group_id)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            Child.first_name.ilike(pattern),
            Child.last_name.ilike(pattern),
            Child.middle_name.ilike(pattern),
            func.concat(Child.last_name, " ", Child.first_name, " ", func.coalesce(Child.middle_name, "")).ilike(pattern),
        ))
    return [summary(child) for child in db.scalars(stmt.order_by(Child.last_name, Child.first_name, Child.id))]


def create_child(db: Session, user: User, payload: ChildCreate) -> ChildResponse:
    validate_birth_date(payload.birth_date)
    group = active_group(db, user, payload.group_id)
    child = Child(organization_id=user.organization_id, group_id=group.id, **payload.model_dump(exclude={"group_id"}), status="active")
    db.add(child)
    db.commit()
    db.refresh(child)
    return detail(child)


def update_child(db: Session, user: User, child_id: UUID, payload: ChildPatch) -> ChildResponse:
    child = get_child(db, user, child_id)
    data = payload.model_dump(exclude_unset=True)
    if "birth_date" in data:
        validate_birth_date(data["birth_date"])
    if "group_id" in data:
        active_group(db, user, data["group_id"])
    for field, value in data.items():
        setattr(child, field, value)
    db.commit()
    db.refresh(child)
    return detail(child)


def archive_child(db: Session, user: User, child_id: UUID) -> ChildResponse:
    child = get_child(db, user, child_id)
    if child.status != "archived":
        child.status = "archived"
        child.archived_at = utc_now()
        db.commit()
        db.refresh(child)
    return detail(child)


def restore_child(db: Session, user: User, child_id: UUID) -> ChildResponse:
    child = get_child(db, user, child_id)
    if child.status != "active":
        active_group(db, user, child.group_id)
        child.status = "active"
        child.archived_at = None
        db.commit()
        db.refresh(child)
    return detail(child)

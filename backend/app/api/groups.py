"""Group CRUD/archive endpoints. All queries use the authenticated tenant."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.child import Child
from app.models.group import Group
from app.models.user import User
from app.schemas.group import GroupList, GroupResponse, GroupWrite
from app.services.auth import utc_now

router = APIRouter(prefix="/groups", tags=["Группы"])
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


def _group(db: Session, user: User, group_id: UUID) -> Group:
    group = db.scalar(select(Group).where(Group.id == group_id, Group.organization_id == user.organization_id))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    return group


def _name_available(db: Session, user: User, name: str, excluding: UUID | None = None) -> None:
    stmt = select(Group.id).where(
        Group.organization_id == user.organization_id,
        Group.status == "active",
        func.lower(func.btrim(Group.name)) == name.lower(),
    )
    if excluding:
        stmt = stmt.where(Group.id != excluding)
    if db.scalar(stmt):
        raise AppError(409, "GROUP_NAME_CONFLICT", "name")


def _save(db: Session, group: Group) -> GroupResponse:
    try:
        db.add(group)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise AppError(409, "GROUP_NAME_CONFLICT", "name") from None
    db.refresh(group)
    return GroupResponse.model_validate(group)


@router.get("", response_model=GroupList)
def list_groups(user: Manager, db: Database, status: Literal["active", "archived", "all"] = Query("active")) -> GroupList:
    stmt = select(Group).where(Group.organization_id == user.organization_id)
    if status != "all":
        stmt = stmt.where(Group.status == status)
    return GroupList(items=[GroupResponse.model_validate(group) for group in db.scalars(stmt.order_by(Group.name, Group.id))])


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(payload: GroupWrite, user: Manager, db: Database) -> GroupResponse:
    _name_available(db, user, payload.name)
    return _save(db, Group(organization_id=user.organization_id, name=payload.name, status="active"))


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: UUID, user: Manager, db: Database) -> GroupResponse:
    return GroupResponse.model_validate(_group(db, user, group_id))


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(group_id: UUID, payload: GroupWrite, user: Manager, db: Database) -> GroupResponse:
    group = _group(db, user, group_id)
    if group.status == "active":
        _name_available(db, user, payload.name, group.id)
    group.name = payload.name
    return _save(db, group)


@router.post("/{group_id}/archive", response_model=GroupResponse)
def archive_group(group_id: UUID, user: Manager, db: Database) -> GroupResponse:
    group = _group(db, user, group_id)
    if group.status == "active":
        # Locking the group serializes archive with child creation in later endpoints.
        db.execute(select(Group).where(Group.id == group.id).with_for_update()).scalar_one()
        if db.scalar(select(Child.id).where(Child.group_id == group.id, Child.status == "active").limit(1)):
            raise AppError(409, "GROUP_NOT_EMPTY")
        group.status = "archived"
        group.archived_at = utc_now()
    return _save(db, group)


@router.post("/{group_id}/restore", response_model=GroupResponse)
def restore_group(group_id: UUID, user: Manager, db: Database) -> GroupResponse:
    group = _group(db, user, group_id)
    if group.status == "archived":
        _name_available(db, user, group.name, group.id)
        group.status = "active"
        group.archived_at = None
    return _save(db, group)

"""Thin Group HTTP handlers; tenant and roles come from the session."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.group import GroupList, GroupResponse, GroupWrite
from app.services import groups

router = APIRouter(prefix="/groups", tags=["Группы"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=GroupList)
def list_groups(user: Manager, db: Database, status: Literal["active", "archived", "all"] = Query("active")) -> GroupList:
    return groups.list_groups(db, user, status)


@router.post("", response_model=GroupResponse, status_code=201)
def create_group(payload: GroupWrite, user: Manager, db: Database) -> GroupResponse:
    return groups.create_group(db, user, payload)


@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: UUID, user: Manager, db: Database) -> GroupResponse:
    return groups.get_group(db, user, group_id)


@router.patch("/{group_id}", response_model=GroupResponse)
def update_group(group_id: UUID, payload: GroupWrite, user: Manager, db: Database) -> GroupResponse:
    return groups.update_group(db, user, group_id, payload)


@router.post("/{group_id}/archive", response_model=GroupResponse)
def archive_group(group_id: UUID, user: Manager, db: Database) -> GroupResponse:
    return groups.archive_group(db, user, group_id)


@router.post("/{group_id}/restore", response_model=GroupResponse)
def restore_group(group_id: UUID, user: Manager, db: Database) -> GroupResponse:
    return groups.restore_group(db, user, group_id)

"""Announcement API for authenticated DIRECTOR and ADMIN users."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementList,
    AnnouncementPatch,
    AnnouncementResponse,
)
from app.services import announcements

router = APIRouter(prefix="/announcements", tags=["Объявления"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=AnnouncementList)
def list_announcements(
    user: Manager,
    db: Database,
    status: Literal["active", "archived", "all"] = Query("active"),
    target_type: Literal["all", "group"] | None = None,
    group_id: UUID | None = None,
) -> AnnouncementList:
    return announcements.list_announcements(
        db, user, status=status, target_type=target_type, group_id=group_id,
    )


@router.post("", response_model=AnnouncementResponse, status_code=201)
def create_announcement(
    payload: AnnouncementCreate,
    user: Manager,
    db: Database,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=64)] = None,
) -> AnnouncementResponse:
    return announcements.create_announcement(db, user, payload, idempotency_key=idempotency_key)


@router.get("/{announcement_id}", response_model=AnnouncementResponse)
def get_announcement(announcement_id: UUID, user: Manager, db: Database) -> AnnouncementResponse:
    return announcements.get_announcement(db, user, announcement_id)


@router.patch("/{announcement_id}", response_model=AnnouncementResponse)
def update_announcement(
    announcement_id: UUID,
    payload: AnnouncementPatch,
    user: Manager,
    db: Database,
) -> AnnouncementResponse:
    return announcements.update_announcement(db, user, announcement_id, payload)


@router.post("/{announcement_id}/archive", response_model=AnnouncementResponse)
def archive_announcement(announcement_id: UUID, user: Manager, db: Database) -> AnnouncementResponse:
    return announcements.archive_announcement(db, user, announcement_id)

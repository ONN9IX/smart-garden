"""Role-checked Communications v2 announcement endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.communications_v2 import (
    AnnouncementCreateV2,
    AnnouncementPatchV2,
    AnnouncementReadResponse,
    AnnouncementSummaryV2,
)
from app.services import communications_v2_announcements

router = APIRouter(prefix="/communications/v2/announcements", tags=["Communications v2"])
Actor = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN", "TEACHER", "PARENT"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=list[AnnouncementSummaryV2])
def list_announcements(
    user: Actor, db: Database, status: str = Query("active", pattern="^(active|archived|all)$"),
) -> list[AnnouncementSummaryV2]:
    return communications_v2_announcements.list_for_actor(db, user, status)


@router.post("", response_model=AnnouncementSummaryV2, status_code=201)
def create_announcement(
    payload: AnnouncementCreateV2,
    user: Actor,
    db: Database,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=64)] = None,
) -> AnnouncementSummaryV2:
    return communications_v2_announcements.create(db, user, payload, idempotency_key)


@router.get("/{announcement_id}", response_model=AnnouncementSummaryV2)
def get_announcement(announcement_id: UUID, user: Actor, db: Database) -> AnnouncementSummaryV2:
    return communications_v2_announcements.get_for_actor(db, user, announcement_id)


@router.patch("/{announcement_id}", response_model=AnnouncementSummaryV2)
def update_announcement(
    announcement_id: UUID, payload: AnnouncementPatchV2, user: Actor, db: Database,
) -> AnnouncementSummaryV2:
    return communications_v2_announcements.update_content(db, user, announcement_id, payload)


@router.post("/{announcement_id}/archive", response_model=AnnouncementSummaryV2)
def archive_announcement(announcement_id: UUID, user: Actor, db: Database) -> AnnouncementSummaryV2:
    return communications_v2_announcements.archive(db, user, announcement_id)


@router.post("/{announcement_id}/read", response_model=AnnouncementReadResponse)
def mark_announcement_read(announcement_id: UUID, user: Actor, db: Database) -> AnnouncementReadResponse:
    return communications_v2_announcements.mark_read(db, user, announcement_id)

"""Eligible PARENT Stage 6 communication, announcement, diary, poll and photo API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.teacher.contracts import (
    AnnouncementResponse,
    ChildSummary,
    DiaryResponse,
    MessageCreate,
    MessageResponse,
    ParentDirectThreadCreate,
    PhotoResponse,
    PollResponse,
    PollVoteCreate,
    ThreadResponse,
)
from app.services.teacher import cabinet, communications, content, photos

router = APIRouter(prefix="/parent", tags=["Stage 6 кабинет родителя"])
Parent = Annotated[User, Depends(require_role("PARENT"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("/children", response_model=list[ChildSummary])
def list_children(user: Parent, db: Database) -> list[ChildSummary]:
    return cabinet.parent_children(db, user)


@router.get("/communications/threads", response_model=list[ThreadResponse])
def list_threads(user: Parent, db: Database) -> list[ThreadResponse]:
    return communications.parent_threads(db, user)


@router.get("/communications/threads/{thread_id}/messages", response_model=list[MessageResponse])
def list_messages(thread_id: UUID, user: Parent, db: Database) -> list[MessageResponse]:
    return communications.parent_messages(db, user, thread_id)


@router.post("/communications/threads/{thread_id}/messages", response_model=MessageResponse, status_code=201)
def send_message(
    thread_id: UUID, payload: MessageCreate, user: Parent, db: Database,
) -> MessageResponse:
    return communications.parent_send(db, user, thread_id, payload.body)


@router.post("/communications/direct", response_model=ThreadResponse, status_code=201)
def create_direct_thread(
    payload: ParentDirectThreadCreate, user: Parent, db: Database,
) -> ThreadResponse:
    return communications.parent_direct(db, user, payload.child_id)


@router.get("/announcements", response_model=list[AnnouncementResponse])
def list_announcements(user: Parent, db: Database) -> list[AnnouncementResponse]:
    return content.parent_announcements(db, user)


@router.get("/children/{child_id}/diary", response_model=list[DiaryResponse])
def list_diary(child_id: UUID, user: Parent, db: Database) -> list[DiaryResponse]:
    return content.parent_diary(db, user, child_id)


@router.get("/polls", response_model=list[PollResponse])
def list_polls(user: Parent, db: Database) -> list[PollResponse]:
    return content.parent_polls(db, user)


@router.post("/polls/{poll_id}/vote", response_model=PollResponse)
def vote_poll(poll_id: UUID, payload: PollVoteCreate, user: Parent, db: Database) -> PollResponse:
    return content.vote_poll(db, user, poll_id, payload.option_id)


@router.get("/photos", response_model=list[PhotoResponse])
def list_photos(child_id: UUID, user: Parent, db: Database) -> list[PhotoResponse]:
    return photos.parent_photos(db, user, child_id)


@router.get("/photos/{photo_id}/content")
def get_photo_content(photo_id: UUID, user: Parent, db: Database) -> Response:
    data, mime_type = photos.parent_content(db, user, photo_id)
    return Response(content=data, media_type=mime_type, headers={"Cache-Control": "private, no-store"})

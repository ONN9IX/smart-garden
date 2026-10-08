"""Eligible PARENT Stage 6 communication, announcement, diary, poll and photo API."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.communications_v2 import (
    DirectThreadCreateV2,
    MessageCreateV2,
    ReadCursorCreate,
    ReadStateResponse,
    TeacherOption,
    ThreadSummaryV2,
)
from app.schemas.teacher.contracts import (
    AnnouncementResponse,
    ChildSummary,
    DiaryResponse,
    MessageCreate,
    MessageResponse,
    ParentDirectThreadCreate,
    ParentTodayResponse,
    PhotoResponse,
    PollResponse,
    PollVoteCreate,
    ThreadResponse,
)
from app.services import communications_v2
from app.services.teacher import cabinet, communications, content, photos

router = APIRouter(prefix="/parent", tags=["Stage 6 кабинет родителя"])
Parent = Annotated[User, Depends(require_role("PARENT"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("/children", response_model=list[ChildSummary])
def list_children(user: Parent, db: Database) -> list[ChildSummary]:
    return cabinet.parent_children(db, user)


@router.get("/children/{child_id}/today", response_model=ParentTodayResponse)
def get_child_today(child_id: UUID, user: Parent, db: Database) -> ParentTodayResponse:
    return cabinet.parent_today(db, user, child_id)


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


@router.get("/communications/v2/threads", response_model=list[ThreadSummaryV2])
def list_v2_threads(user: Parent, db: Database) -> list[ThreadSummaryV2]:
    return communications_v2.list_threads(db, user)


@router.get("/communications/v2/groups/{group_id}/thread", response_model=ThreadSummaryV2)
def get_v2_group_thread(group_id: UUID, user: Parent, db: Database) -> ThreadSummaryV2:
    thread = communications_v2.group_thread(db, user, group_id, "all")
    return next(item for item in communications_v2.list_threads(db, user) if item.id == thread.id)


@router.get("/communications/v2/threads/{thread_id}/messages", response_model=list[MessageResponse])
def list_v2_messages(thread_id: UUID, user: Parent, db: Database) -> list[MessageResponse]:
    return [communications._message_response(db, user, item) for item in communications_v2.messages(db, user, thread_id)]


@router.post("/communications/v2/threads/{thread_id}/messages", response_model=MessageResponse, status_code=201)
def send_v2_message(thread_id: UUID, payload: MessageCreateV2, user: Parent, db: Database) -> MessageResponse:
    item = communications_v2.send(db, user, thread_id, payload.body, payload.client_message_id)
    return communications._message_response(db, user, item)


@router.post("/communications/v2/threads/{thread_id}/read", response_model=ReadStateResponse)
def mark_v2_read(thread_id: UUID, payload: ReadCursorCreate, user: Parent, db: Database) -> ReadStateResponse:
    return communications_v2.mark_read(db, user, thread_id, payload.last_read_message_id)


@router.get("/children/{child_id}/teachers", response_model=list[TeacherOption])
def eligible_teachers(child_id: UUID, user: Parent, db: Database) -> list[TeacherOption]:
    return communications_v2.eligible_teachers(db, user, child_id)


@router.post("/communications/v2/direct", response_model=ThreadSummaryV2, status_code=201)
def create_v2_direct(payload: DirectThreadCreateV2, user: Parent, db: Database) -> ThreadSummaryV2:
    if payload.teacher_employee_id is None:
        from app.core.errors import AppError
        raise AppError(400, "VALIDATION_ERROR", "teacher_employee_id")
    thread = communications_v2.create_parent_direct(db, user, payload.child_id, payload.teacher_employee_id)
    return next(item for item in communications_v2.list_threads(db, user) if item.id == thread.id)


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

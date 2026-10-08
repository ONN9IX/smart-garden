"""Complete assigned-context TEACHER cabinet HTTP API."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.attendance import (
    AttendanceAction,
    AttendanceCreate,
    AttendanceDetail,
    AttendancePatch,
    AttendanceRow,
)
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
    DiaryCreate,
    DiaryPatch,
    DiaryResponse,
    DocumentNoticeResponse,
    GroupSummary,
    GuardianContext,
    IncidentCreate,
    IncidentPatch,
    IncidentResponse,
    MessageCreate,
    MessageResponse,
    NotificationResponse,
    PhotoConsentResponse,
    PhotoResponse,
    PollCreate,
    PollResponse,
    ScheduleItemResponse,
    TaskResponse,
    TaskStatusPatch,
    TeacherAnnouncementCreate,
    TeacherAnnouncementPatch,
    TeacherDirectThreadCreate,
    ThreadResponse,
    TodayResponse,
)
from app.services import communications_v2
from app.services.teacher import access, cabinet, communications, content, photos

router = APIRouter(prefix="/teacher", tags=["Кабинет воспитателя"])
Teacher = Annotated[User, Depends(require_role("TEACHER"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("/today", response_model=TodayResponse)
def get_today(user: Teacher, db: Database) -> TodayResponse:
    return cabinet.today(db, user)


@router.get("/groups", response_model=list[GroupSummary])
def list_groups(user: Teacher, db: Database) -> list[GroupSummary]:
    return cabinet.groups(db, user)


@router.get("/groups/{group_id}", response_model=GroupSummary)
def get_group(group_id: UUID, user: Teacher, db: Database) -> GroupSummary:
    return cabinet.group(db, user, group_id)


@router.get("/groups/{group_id}/children", response_model=list[ChildSummary])
def list_children(group_id: UUID, user: Teacher, db: Database) -> list[ChildSummary]:
    return cabinet.children(db, user, group_id)


@router.get("/groups/{group_id}/guardians", response_model=list[GuardianContext])
def list_guardians(group_id: UUID, user: Teacher, db: Database) -> list[GuardianContext]:
    return cabinet.guardians(db, user, group_id)


@router.get("/groups/{group_id}/communication-thread", response_model=ThreadResponse)
def get_group_thread(
    group_id: UUID,
    user: Teacher,
    db: Database,
    audience: Literal["all", "teachers"] = "all",
) -> ThreadResponse:
    return communications.group_thread(db, user, group_id, audience)


@router.get("/attendance", response_model=list[AttendanceRow])
def list_attendance(user: Teacher, db: Database, date: date, group_id: UUID) -> list[AttendanceRow]:
    return cabinet.list_attendance(db, user, date, group_id)


@router.post("/attendance", response_model=AttendanceDetail, status_code=201)
def save_attendance(
    payload: AttendanceCreate, user: Teacher, db: Database, response: Response,
) -> AttendanceDetail:
    result, created = cabinet.save_attendance(db, user, payload)
    if not created:
        response.status_code = 200
    return result


@router.patch("/attendance/{record_id}", response_model=AttendanceDetail)
def patch_attendance(
    record_id: UUID, payload: AttendancePatch, user: Teacher, db: Database,
) -> AttendanceDetail:
    return cabinet.patch_attendance(db, user, record_id, payload)


@router.post("/attendance/arrival", response_model=AttendanceDetail)
def mark_arrival(payload: AttendanceAction, user: Teacher, db: Database) -> AttendanceDetail:
    return cabinet.mark_arrival(db, user, payload.child_id)


@router.post("/attendance/departure", response_model=AttendanceDetail)
def mark_departure(payload: AttendanceAction, user: Teacher, db: Database) -> AttendanceDetail:
    return cabinet.mark_departure(db, user, payload.child_id)


@router.get("/schedule", response_model=list[ScheduleItemResponse])
def get_schedule(user: Teacher, db: Database, group_id: UUID) -> list[ScheduleItemResponse]:
    return cabinet.schedule(db, user, group_id)


@router.get("/communications/threads", response_model=list[ThreadResponse])
def list_threads(user: Teacher, db: Database) -> list[ThreadResponse]:
    return communications.teacher_threads(db, user)


@router.get("/communications/threads/{thread_id}/messages", response_model=list[MessageResponse])
def list_messages(thread_id: UUID, user: Teacher, db: Database) -> list[MessageResponse]:
    return communications.teacher_messages(db, user, thread_id)


@router.post("/communications/threads/{thread_id}/messages", response_model=MessageResponse, status_code=201)
def send_message(
    thread_id: UUID, payload: MessageCreate, user: Teacher, db: Database,
) -> MessageResponse:
    return communications.teacher_send(db, user, thread_id, payload.body)


@router.post("/communications/direct", response_model=ThreadResponse, status_code=201)
def create_direct_thread(
    payload: TeacherDirectThreadCreate, user: Teacher, db: Database,
) -> ThreadResponse:
    return communications.teacher_direct(db, user, payload.child_id, payload.guardian_id)


@router.get("/communications/v2/threads", response_model=list[ThreadSummaryV2])
def list_v2_threads(user: Teacher, db: Database) -> list[ThreadSummaryV2]:
    return communications_v2.list_threads(db, user)


@router.get("/communications/v2/groups/{group_id}/thread", response_model=ThreadSummaryV2)
def get_v2_group_thread(
    group_id: UUID, user: Teacher, db: Database, audience: Literal["all", "teachers"] = "all",
) -> ThreadSummaryV2:
    thread = communications_v2.group_thread(db, user, group_id, audience)
    return next(item for item in communications_v2.list_threads(db, user) if item.id == thread.id)


@router.get("/communications/v2/threads/{thread_id}/messages", response_model=list[MessageResponse])
def list_v2_messages(thread_id: UUID, user: Teacher, db: Database) -> list[MessageResponse]:
    return [communications._message_response(db, user, item) for item in communications_v2.messages(db, user, thread_id)]


@router.post("/communications/v2/threads/{thread_id}/messages", response_model=MessageResponse, status_code=201)
def send_v2_message(thread_id: UUID, payload: MessageCreateV2, user: Teacher, db: Database) -> MessageResponse:
    item = communications_v2.send(db, user, thread_id, payload.body, payload.client_message_id)
    return communications._message_response(db, user, item)


@router.post("/communications/v2/threads/{thread_id}/read", response_model=ReadStateResponse)
def mark_v2_read(thread_id: UUID, payload: ReadCursorCreate, user: Teacher, db: Database) -> ReadStateResponse:
    return communications_v2.mark_read(db, user, thread_id, payload.last_read_message_id)


@router.get("/communications/v2/children/{child_id}/teachers", response_model=list[TeacherOption])
def list_v2_eligible_teachers(child_id: UUID, user: Teacher, db: Database) -> list[TeacherOption]:
    access.teacher_child(db, user, child_id)
    # Keep this endpoint minimal; the service performs the same active assignment filter.
    return communications_v2.eligible_teachers(db, user, child_id)


@router.post("/communications/v2/direct", response_model=ThreadSummaryV2, status_code=201)
def create_v2_direct(payload: DirectThreadCreateV2, user: Teacher, db: Database) -> ThreadSummaryV2:
    if payload.guardian_id is None:
        from app.core.errors import AppError
        raise AppError(400, "VALIDATION_ERROR", "guardian_id")
    thread = communications_v2.create_teacher_direct(db, user, payload.child_id, payload.guardian_id)
    return next(item for item in communications_v2.list_threads(db, user) if item.id == thread.id)


@router.get("/diary", response_model=list[DiaryResponse])
def list_diary(
    user: Teacher, db: Database, child_id: UUID,
    date_from: date | None = None, date_to: date | None = None,
) -> list[DiaryResponse]:
    return content.teacher_diary(db, user, child_id, date_from, date_to)


@router.post("/diary", response_model=DiaryResponse, status_code=201)
def create_diary(payload: DiaryCreate, user: Teacher, db: Database) -> DiaryResponse:
    return content.create_diary(db, user, payload)


@router.patch("/diary/{entry_id}", response_model=DiaryResponse)
def patch_diary(entry_id: UUID, payload: DiaryPatch, user: Teacher, db: Database) -> DiaryResponse:
    return content.update_diary(db, user, entry_id, payload)


@router.get("/announcements", response_model=list[AnnouncementResponse])
def list_announcements(user: Teacher, db: Database, group_id: UUID) -> list[AnnouncementResponse]:
    return content.teacher_announcements(db, user, group_id)


@router.post("/announcements", response_model=AnnouncementResponse, status_code=201)
def create_announcement(
    payload: TeacherAnnouncementCreate, user: Teacher, db: Database,
) -> AnnouncementResponse:
    return content.create_announcement(db, user, payload)


@router.patch("/announcements/{announcement_id}", response_model=AnnouncementResponse)
def patch_announcement(
    announcement_id: UUID, payload: TeacherAnnouncementPatch, user: Teacher, db: Database,
) -> AnnouncementResponse:
    return content.update_announcement(db, user, announcement_id, payload)


@router.post("/announcements/{announcement_id}/archive", response_model=AnnouncementResponse)
def archive_announcement(announcement_id: UUID, user: Teacher, db: Database) -> AnnouncementResponse:
    return content.archive_announcement(db, user, announcement_id)


@router.get("/polls", response_model=list[PollResponse])
def list_polls(user: Teacher, db: Database, group_id: UUID) -> list[PollResponse]:
    return content.teacher_polls(db, user, group_id)


@router.post("/polls", response_model=PollResponse, status_code=201)
def create_poll(payload: PollCreate, user: Teacher, db: Database) -> PollResponse:
    return content.create_poll(db, user, payload)


@router.post("/polls/{poll_id}/close", response_model=PollResponse)
def close_poll(poll_id: UUID, user: Teacher, db: Database) -> PollResponse:
    return content.close_poll(db, user, poll_id)


@router.get("/incidents", response_model=list[IncidentResponse])
def list_incidents(
    user: Teacher, db: Database, group_id: UUID,
    status: Literal["open", "resolved"] | None = Query(None),
) -> list[IncidentResponse]:
    return content.incidents(db, user, group_id, status)


@router.post("/incidents", response_model=IncidentResponse, status_code=201)
def create_incident(payload: IncidentCreate, user: Teacher, db: Database) -> IncidentResponse:
    return content.create_incident(db, user, payload)


@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
def patch_incident(
    incident_id: UUID, payload: IncidentPatch, user: Teacher, db: Database,
) -> IncidentResponse:
    return content.update_incident(db, user, incident_id, payload)


@router.get("/tasks", response_model=list[TaskResponse])
def list_tasks(user: Teacher, db: Database) -> list[TaskResponse]:
    return content.tasks(db, user)


@router.patch("/tasks/{task_id}", response_model=TaskResponse)
def patch_task(task_id: UUID, payload: TaskStatusPatch, user: Teacher, db: Database) -> TaskResponse:
    return content.update_task(db, user, task_id, payload.status)


@router.get("/notifications", response_model=list[NotificationResponse])
def list_notifications(user: Teacher, db: Database) -> list[NotificationResponse]:
    return content.notifications(db, user)


@router.post("/notifications/{notification_id}/read", response_model=NotificationResponse)
def read_notification(notification_id: UUID, user: Teacher, db: Database) -> NotificationResponse:
    return content.read_notification(db, user, notification_id)


@router.get("/document-notices", response_model=list[DocumentNoticeResponse])
def list_notices(user: Teacher, db: Database) -> list[DocumentNoticeResponse]:
    return content.notices(db, user)


@router.post("/document-notices/{notice_id}/ack", response_model=DocumentNoticeResponse)
def acknowledge_notice(notice_id: UUID, user: Teacher, db: Database) -> DocumentNoticeResponse:
    return content.acknowledge_notice(db, user, notice_id)


@router.get("/photo-consents", response_model=list[PhotoConsentResponse])
def list_photo_consents(user: Teacher, db: Database, group_id: UUID) -> list[PhotoConsentResponse]:
    return photos.teacher_consents(db, user, group_id)


@router.post("/photos", response_model=PhotoResponse, status_code=201)
async def upload_photo(
    user: Teacher,
    db: Database,
    group_id: Annotated[UUID, Form()],
    child_ids: Annotated[list[UUID], Form()],
    file: Annotated[UploadFile, File()],
) -> PhotoResponse:
    raw = await file.read(photos.MAX_PHOTO_BYTES + 1)
    return photos.upload(db, user, group_id, child_ids, file.content_type or "", raw)


@router.get("/photos", response_model=list[PhotoResponse])
def list_photos(user: Teacher, db: Database, group_id: UUID) -> list[PhotoResponse]:
    return photos.teacher_photos(db, user, group_id)


@router.get("/photos/{photo_id}/content")
def get_photo_content(photo_id: UUID, user: Teacher, db: Database) -> Response:
    data, mime_type = photos.teacher_content(db, user, photo_id)
    return Response(content=data, media_type=mime_type, headers={"Cache-Control": "private, no-store"})

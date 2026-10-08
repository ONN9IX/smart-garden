"""Stage 6 DIRECTOR/ADMIN management endpoints over the frozen Foundation schema."""

from datetime import date
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.communications_v2 import (
    MessageCreateV2,
    ReadCursorCreate,
    ReadStateResponse,
    ThreadSummaryV2,
)
from app.schemas.management_cabinet import (
    DiaryEntryList,
    DiaryEntryResponse,
    DocumentNoticeCreate,
    DocumentNoticeList,
    DocumentNoticeResponse,
    IncidentCreate,
    IncidentList,
    IncidentPatch,
    IncidentResponse,
    ManagementMessageCreate,
    ManagementMessageList,
    ManagementMessageResponse,
    ManagementSettingsPatch,
    ManagementSettingsResponse,
    ManagementToday,
    NotificationList,
    NotificationResponse,
    PhotoConsentCreate,
    PhotoConsentList,
    PhotoConsentResponse,
    PollCreate,
    PollList,
    PollResponse,
    ScheduleCreate,
    ScheduleItemResponse,
    ScheduleList,
    SchedulePatch,
    TeacherProjection,
    TeacherProjectionList,
    TeacherTaskCreate,
    TeacherTaskList,
    TeacherTaskPatch,
    TeacherTaskResponse,
)
from app.services import communications_v2, management_cabinet
from app.services.teacher import communications as teacher_communications

router = APIRouter(tags=["Stage 6 — управление"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Director = Annotated[User, Depends(require_role("DIRECTOR"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("/management/today", response_model=ManagementToday)
def today(user: Manager, db: Database) -> ManagementToday:
    return management_cabinet.management_today(db, user)


@router.get("/management/notifications", response_model=NotificationList)
def notifications(
    user: Manager,
    db: Database,
    status: Literal["unread", "read", "all"] = "unread",
) -> NotificationList:
    return management_cabinet.list_notifications(db, user, status)


@router.post("/management/notifications/{notification_id}/read", response_model=NotificationResponse)
def read_notification(notification_id: UUID, user: Manager, db: Database) -> NotificationResponse:
    return management_cabinet.read_notification(db, user, notification_id)


@router.get("/management/settings", response_model=ManagementSettingsResponse)
def settings(user: Director) -> ManagementSettingsResponse:
    return management_cabinet.get_settings(user)


@router.patch("/management/settings", response_model=ManagementSettingsResponse)
def patch_settings(
    payload: ManagementSettingsPatch,
    user: Director,
    db: Database,
) -> ManagementSettingsResponse:
    return management_cabinet.update_settings(db, user, payload)


@router.get("/teacher-management/teachers", response_model=TeacherProjectionList)
def teachers(
    user: Manager,
    db: Database,
    status: Literal["active", "archived", "all"] = "active",
    account_status: Literal["active", "blocked", "none", "all"] = "all",
    group_id: UUID | None = None,
    q: str | None = Query(default=None, max_length=160),
) -> TeacherProjectionList:
    return management_cabinet.list_teachers(
        db,
        user,
        status=status,
        account_status=account_status,
        group_id=group_id,
        q=q,
    )


@router.get("/teacher-management/teachers/{employee_id}", response_model=TeacherProjection)
def teacher(employee_id: UUID, user: Manager, db: Database) -> TeacherProjection:
    return management_cabinet.get_teacher(db, user, employee_id)


@router.get("/teacher-management/schedule", response_model=ScheduleList)
def schedule(
    user: Manager,
    db: Database,
    group_id: UUID | None = None,
    status: Literal["active", "archived", "all"] = "active",
) -> ScheduleList:
    return management_cabinet.list_schedule(db, user, group_id, status)


@router.post("/teacher-management/schedule", response_model=ScheduleItemResponse, status_code=201)
def create_schedule(payload: ScheduleCreate, user: Manager, db: Database) -> ScheduleItemResponse:
    return management_cabinet.create_schedule(db, user, payload)


@router.patch("/teacher-management/schedule/{item_id}", response_model=ScheduleItemResponse)
def patch_schedule(
    item_id: UUID,
    payload: SchedulePatch,
    user: Manager,
    db: Database,
) -> ScheduleItemResponse:
    return management_cabinet.update_schedule(db, user, item_id, payload)


@router.post("/teacher-management/schedule/{item_id}/archive", response_model=ScheduleItemResponse)
def archive_schedule(item_id: UUID, user: Manager, db: Database) -> ScheduleItemResponse:
    return management_cabinet.archive_schedule(db, user, item_id)


@router.get(
    "/teacher-management/communications/groups/{group_id}/messages",
    response_model=ManagementMessageList,
)
def group_messages(
    group_id: UUID,
    user: Manager,
    db: Database,
    audience: Literal["all", "parents", "teachers"] = "all",
) -> ManagementMessageList:
    return management_cabinet.list_group_messages(db, user, group_id, audience)


@router.post(
    "/teacher-management/communications/groups/{group_id}/messages",
    response_model=ManagementMessageResponse,
    status_code=201,
)
def create_group_message(
    group_id: UUID,
    payload: ManagementMessageCreate,
    user: Manager,
    db: Database,
) -> ManagementMessageResponse:
    return management_cabinet.create_group_message(db, user, group_id, payload)


@router.get("/teacher-management/communications/v2/threads", response_model=list[ThreadSummaryV2])
def list_v2_group_threads(user: Manager, db: Database) -> list[ThreadSummaryV2]:
    return communications_v2.list_threads(db, user)


@router.get("/teacher-management/communications/v2/groups/{group_id}/thread", response_model=ThreadSummaryV2)
def get_v2_group_thread(
    group_id: UUID, user: Manager, db: Database, audience: Literal["all", "teachers"] = "all",
) -> ThreadSummaryV2:
    thread = communications_v2.group_thread(db, user, group_id, audience)
    return next(item for item in communications_v2.list_threads(db, user) if item.id == thread.id)


@router.get("/teacher-management/communications/v2/threads/{thread_id}/messages", response_model=list[ManagementMessageResponse])
def list_v2_messages(thread_id: UUID, user: Manager, db: Database) -> list[ManagementMessageResponse]:
    result = []
    for item in communications_v2.messages(db, user, thread_id):
        role, name = teacher_communications._sender_presentation(db, user, item.sender_user_id)
        result.append(ManagementMessageResponse(
            id=item.id, thread_id=item.thread_id, sender_user_id=item.sender_user_id,
            group_id=communications_v2._eligible_thread(db, user, thread_id).group_id,
            sender_role=role, sender_name=name, audience=communications_v2._eligible_thread(db, user, thread_id).audience,
            body=item.body, created_at=item.created_at,
        ))
    return result


@router.post("/teacher-management/communications/v2/threads/{thread_id}/messages", response_model=ManagementMessageResponse, status_code=201)
def send_v2_message(thread_id: UUID, payload: MessageCreateV2, user: Manager, db: Database) -> ManagementMessageResponse:
    item = communications_v2.send(db, user, thread_id, payload.body, payload.client_message_id)
    role, name = teacher_communications._sender_presentation(db, user, item.sender_user_id)
    return ManagementMessageResponse(
        id=item.id, thread_id=item.thread_id, sender_user_id=item.sender_user_id,
        group_id=thread.group_id if (thread := communications_v2._eligible_thread(db, user, thread_id)) else None,
        sender_role=role, sender_name=name, audience=thread.audience,
        body=item.body, created_at=item.created_at,
    )


@router.post("/teacher-management/communications/v2/threads/{thread_id}/read", response_model=ReadStateResponse)
def mark_v2_read(thread_id: UUID, payload: ReadCursorCreate, user: Manager, db: Database) -> ReadStateResponse:
    return communications_v2.mark_read(db, user, thread_id, payload.last_read_message_id)


@router.get("/teacher-management/diary", response_model=DiaryEntryList)
def diary(
    user: Manager,
    db: Database,
    child_id: UUID,
    date_from: date | None = None,
    date_to: date | None = None,
) -> DiaryEntryList:
    return management_cabinet.list_diary(db, user, child_id, date_from, date_to)


@router.get("/teacher-management/diary/{entry_id}", response_model=DiaryEntryResponse)
def diary_entry(entry_id: UUID, user: Manager, db: Database) -> DiaryEntryResponse:
    return management_cabinet.get_diary_entry(db, user, entry_id)


@router.get("/teacher-management/polls", response_model=PollList)
def polls(
    user: Manager,
    db: Database,
    group_id: UUID | None = None,
    status: Literal["active", "closed", "archived", "all"] = "all",
) -> PollList:
    return management_cabinet.list_polls(db, user, group_id, status)


@router.get("/teacher-management/polls/{poll_id}", response_model=PollResponse)
def poll(poll_id: UUID, user: Manager, db: Database) -> PollResponse:
    return management_cabinet.get_poll(db, user, poll_id)


@router.post("/teacher-management/polls", response_model=PollResponse, status_code=201)
def create_poll(payload: PollCreate, user: Manager, db: Database) -> PollResponse:
    return management_cabinet.create_poll(db, user, payload)


@router.post("/teacher-management/polls/{poll_id}/close", response_model=PollResponse)
def close_poll(poll_id: UUID, user: Manager, db: Database) -> PollResponse:
    return management_cabinet.close_poll(db, user, poll_id)


@router.get("/teacher-management/incidents", response_model=IncidentList)
def incidents(
    user: Manager,
    db: Database,
    group_id: UUID | None = None,
    status: Literal["open", "resolved", "all"] = "all",
) -> IncidentList:
    return management_cabinet.list_incidents(db, user, group_id, status)


@router.get("/teacher-management/incidents/{incident_id}", response_model=IncidentResponse)
def incident(incident_id: UUID, user: Manager, db: Database) -> IncidentResponse:
    return management_cabinet.get_incident(db, user, incident_id)


@router.post("/teacher-management/incidents", response_model=IncidentResponse, status_code=201)
def create_incident(payload: IncidentCreate, user: Manager, db: Database) -> IncidentResponse:
    return management_cabinet.create_incident(db, user, payload)


@router.patch("/teacher-management/incidents/{incident_id}", response_model=IncidentResponse)
def patch_incident(
    incident_id: UUID,
    payload: IncidentPatch,
    user: Manager,
    db: Database,
) -> IncidentResponse:
    return management_cabinet.update_incident(db, user, incident_id, payload)


@router.get("/teacher-management/tasks", response_model=TeacherTaskList)
def tasks(
    user: Manager,
    db: Database,
    employee_id: UUID | None = None,
    group_id: UUID | None = None,
    status: Literal["open", "in_progress", "done", "cancelled", "all"] = "all",
) -> TeacherTaskList:
    return management_cabinet.list_tasks(db, user, employee_id, group_id, status)


@router.post("/teacher-management/tasks", response_model=TeacherTaskResponse, status_code=201)
def create_task(payload: TeacherTaskCreate, user: Manager, db: Database) -> TeacherTaskResponse:
    return management_cabinet.create_task(db, user, payload)


@router.patch("/teacher-management/tasks/{task_id}", response_model=TeacherTaskResponse)
def patch_task(
    task_id: UUID,
    payload: TeacherTaskPatch,
    user: Manager,
    db: Database,
) -> TeacherTaskResponse:
    return management_cabinet.update_task(db, user, task_id, payload)


@router.post("/teacher-management/tasks/{task_id}/cancel", response_model=TeacherTaskResponse)
def cancel_task(task_id: UUID, user: Manager, db: Database) -> TeacherTaskResponse:
    return management_cabinet.cancel_task(db, user, task_id)


@router.get("/teacher-management/document-notices", response_model=DocumentNoticeList)
def document_notices(
    user: Manager,
    db: Database,
    recipient_user_id: UUID | None = None,
) -> DocumentNoticeList:
    return management_cabinet.list_document_notices(db, user, recipient_user_id)


@router.post(
    "/teacher-management/document-notices",
    response_model=DocumentNoticeResponse,
    status_code=201,
)
def create_document_notice(
    payload: DocumentNoticeCreate,
    user: Manager,
    db: Database,
) -> DocumentNoticeResponse:
    return management_cabinet.create_document_notice(db, user, payload)


@router.get("/teacher-management/photo-consents", response_model=PhotoConsentList)
def photo_consents(
    user: Manager,
    db: Database,
    child_id: UUID | None = None,
    group_id: UUID | None = None,
) -> PhotoConsentList:
    return management_cabinet.list_photo_consents(db, user, child_id, group_id)


@router.post("/teacher-management/photo-consents", response_model=PhotoConsentResponse)
def record_photo_consent(
    payload: PhotoConsentCreate,
    user: Manager,
    db: Database,
) -> PhotoConsentResponse:
    return management_cabinet.record_photo_consent(db, user, payload)


@router.post(
    "/teacher-management/photo-consents/{consent_id}/withdraw",
    response_model=PhotoConsentResponse,
)
def withdraw_photo_consent(consent_id: UUID, user: Manager, db: Database) -> PhotoConsentResponse:
    return management_cabinet.withdraw_photo_consent(db, user, consent_id)

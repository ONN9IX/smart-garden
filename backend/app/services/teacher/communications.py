"""Participant-derived immutable Group and direct communication."""

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.communication import CommunicationMessage, CommunicationThread
from app.models.employee import Employee
from app.models.guardian import Guardian
from app.models.notification import Notification
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from app.schemas.teacher.contracts import MessageResponse, ThreadResponse
from app.services import audit
from app.services.teacher import access


def _thread_response(item: CommunicationThread) -> ThreadResponse:
    return ThreadResponse(
        id=item.id, thread_type=item.thread_type, group_id=item.group_id, audience=item.audience,
        child_id=item.child_id, guardian_id=item.guardian_id, created_at=item.created_at,
    )


def _sender_presentation(db: Session, actor: User, sender_user_id: UUID) -> tuple[str, str]:
    sender = db.scalar(select(User).where(
        User.id == sender_user_id, User.organization_id == actor.organization_id,
    ))
    if sender is None:
        raise AppError(404, "NOT_FOUND")
    if sender.role == "TEACHER":
        profile = db.scalar(select(Employee).where(
            Employee.user_id == sender.id, Employee.organization_id == actor.organization_id,
        ))
    elif sender.role == "PARENT":
        profile = db.scalar(select(Guardian).where(
            Guardian.user_id == sender.id, Guardian.organization_id == actor.organization_id,
        ))
    else:
        profile = None
    if profile is not None:
        return sender.role, f"{profile.last_name} {profile.first_name}"
    return sender.role, {"DIRECTOR": "Директор", "ADMIN": "Администратор"}.get(sender.role, "Пользователь")


def _message_response(db: Session, actor: User, item: CommunicationMessage) -> MessageResponse:
    sender_role, sender_name = _sender_presentation(db, actor, item.sender_user_id)
    return MessageResponse(
        id=item.id, thread_id=item.thread_id, sender_user_id=item.sender_user_id,
        sender_role=sender_role, sender_name=sender_name,
        body=item.body, created_at=item.created_at,
    )


def teacher_threads(db: Session, actor: User) -> list[ThreadResponse]:
    group_ids = access.teacher_group_ids(db, actor)
    if not group_ids:
        return []
    candidates = db.scalars(select(CommunicationThread).where(
        CommunicationThread.organization_id == actor.organization_id,
        CommunicationThread.group_id.in_(group_ids),
    ).order_by(CommunicationThread.created_at.desc(), CommunicationThread.id.desc()))
    result = []
    for item in candidates:
        try:
            access.teacher_thread(db, actor, item.id)
        except AppError:
            continue
        result.append(_thread_response(item))
    return result


def parent_threads(db: Session, actor: User) -> list[ThreadResponse]:
    group_ids = access.parent_group_ids(db, actor)
    if not group_ids:
        return []
    candidates = db.scalars(select(CommunicationThread).where(
        CommunicationThread.organization_id == actor.organization_id,
        CommunicationThread.group_id.in_(group_ids),
    ).order_by(CommunicationThread.created_at.desc(), CommunicationThread.id.desc()))
    result = []
    for item in candidates:
        try:
            access.parent_thread(db, actor, item.id)
        except AppError:
            continue
        result.append(_thread_response(item))
    return result


def group_thread(db: Session, actor: User, group_id: UUID, audience: str = "all") -> ThreadResponse:
    access.teacher_group(db, actor, group_id)
    if audience not in {"all", "teachers"}:
        raise AppError(404, "NOT_FOUND")
    thread = db.scalar(select(CommunicationThread).where(
        CommunicationThread.organization_id == actor.organization_id,
        CommunicationThread.thread_type == "group",
        CommunicationThread.group_id == group_id,
        CommunicationThread.audience == audience,
    ))
    if thread is None:
        thread = CommunicationThread(
            organization_id=actor.organization_id, thread_type="group", group_id=group_id, audience=audience,
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
    return _thread_response(thread)


def teacher_direct(db: Session, actor: User, child_id: UUID, guardian_id: UUID) -> ThreadResponse:
    child = access.teacher_child(db, actor, child_id)
    guardian = db.scalar(
        select(Guardian)
        .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
        .where(
            Guardian.id == guardian_id,
            Guardian.organization_id == actor.organization_id,
            Guardian.status == "active",
            ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.child_id == child.id,
            ChildGuardian.status == "active",
        )
    )
    if guardian is None:
        raise AppError(404, "NOT_FOUND")
    parent_user = db.scalar(select(User).where(
        User.id == guardian.user_id,
        User.organization_id == actor.organization_id,
        User.role == "PARENT",
        User.status == "active",
    ))
    if parent_user is None:
        raise AppError(409, "PARENT_ACCOUNT_UNAVAILABLE")
    return _direct(db, actor, child, guardian)


def parent_direct(db: Session, actor: User, child_id: UUID) -> ThreadResponse:
    guardian, child = access.parent_child(db, actor, child_id)
    return _direct(db, actor, child, guardian)


def _direct(db: Session, actor: User, child: Child, guardian: Guardian) -> ThreadResponse:
    thread = db.scalar(select(CommunicationThread).where(
        CommunicationThread.organization_id == actor.organization_id,
        CommunicationThread.thread_type == "direct",
        CommunicationThread.group_id == child.group_id,
        CommunicationThread.child_id == child.id,
        CommunicationThread.guardian_id == guardian.id,
        CommunicationThread.teacher_employee_id.is_(None),
    ))
    if thread is None:
        thread = CommunicationThread(
            organization_id=actor.organization_id, thread_type="direct", group_id=child.group_id,
            child_id=child.id, guardian_id=guardian.id, audience="all",
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)
    return _thread_response(thread)


def teacher_messages(db: Session, actor: User, thread_id: UUID) -> list[MessageResponse]:
    access.teacher_thread(db, actor, thread_id)
    return _messages(db, actor, thread_id)


def parent_messages(db: Session, actor: User, thread_id: UUID) -> list[MessageResponse]:
    access.parent_thread(db, actor, thread_id)
    return _messages(db, actor, thread_id)


def _messages(db: Session, actor: User, thread_id: UUID) -> list[MessageResponse]:
    items = db.scalars(select(CommunicationMessage).where(
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread_id,
    ).order_by(CommunicationMessage.created_at, CommunicationMessage.id))
    return [_message_response(db, actor, item) for item in items]


def teacher_send(db: Session, actor: User, thread_id: UUID, body: str) -> MessageResponse:
    thread = access.teacher_thread(db, actor, thread_id)
    return _send(db, actor, thread, body)


def parent_send(db: Session, actor: User, thread_id: UUID, body: str) -> MessageResponse:
    thread = access.parent_thread(db, actor, thread_id)
    return _send(db, actor, thread, body)


def _send(db: Session, actor: User, thread: CommunicationThread, body: str) -> MessageResponse:
    message = CommunicationMessage(
        organization_id=actor.organization_id, thread_id=thread.id,
        sender_user_id=actor.id, body=body,
    )
    db.add(message)
    db.flush()
    audit.write(db, actor, "teacher_message.create", "communication_message", message.id, {
        "thread_id": str(thread.id), "group_id": str(thread.group_id), "thread_type": thread.thread_type,
    })
    for recipient_id in _recipient_ids(db, actor, thread):
        db.execute(insert(Notification).values(
            organization_id=actor.organization_id, recipient_user_id=recipient_id,
            kind="communication.message", entity_type="communication_thread", entity_id=thread.id,
        ).on_conflict_do_nothing(
            index_elements=[Notification.organization_id, Notification.recipient_user_id, Notification.entity_id],
            index_where=text(
                "read_at IS NULL AND kind = 'communication.message' AND "
                "entity_type = 'communication_thread' AND entity_id IS NOT NULL"
            ),
        ))
    db.commit()
    db.refresh(message)
    return _message_response(db, actor, message)


def _recipient_ids(db: Session, actor: User, thread: CommunicationThread) -> set[UUID]:
    recipients = set(db.scalars(
        select(User.id)
        .join(Employee, Employee.user_id == User.id)
        .join(TeacherGroupAssignment, TeacherGroupAssignment.employee_id == Employee.id)
        .where(
            User.organization_id == actor.organization_id,
            User.role == "TEACHER", User.status == "active",
            Employee.organization_id == actor.organization_id, Employee.status == "active",
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.group_id == thread.group_id,
            TeacherGroupAssignment.status == "active",
        )
    ))
    if thread.thread_type == "group":
        if thread.audience in {"all", "parents"}:
            recipients.update(db.scalars(
                select(User.id)
                .join(Guardian, Guardian.user_id == User.id)
                .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
                .join(Child, Child.id == ChildGuardian.child_id)
                .where(
                    User.organization_id == actor.organization_id,
                    User.role == "PARENT", User.status == "active",
                    Guardian.organization_id == actor.organization_id, Guardian.status == "active",
                    ChildGuardian.organization_id == actor.organization_id, ChildGuardian.status == "active",
                    Child.organization_id == actor.organization_id,
                    Child.group_id == thread.group_id, Child.status == "active",
                )
            ))
        if thread.audience == "parents":
            recipients = {recipient for recipient in recipients if db.scalar(
                select(User.role).where(User.id == recipient)
            ) == "PARENT"}
        elif thread.audience == "teachers":
            recipients = {recipient for recipient in recipients if db.scalar(
                select(User.role).where(User.id == recipient)
            ) == "TEACHER"}
    elif thread.guardian_id is not None:
        parent_id = db.scalar(
            select(User.id)
            .join(Guardian, Guardian.user_id == User.id)
            .where(
                Guardian.id == thread.guardian_id,
                Guardian.organization_id == actor.organization_id,
                Guardian.status == "active",
                User.organization_id == actor.organization_id,
                User.role == "PARENT",
                User.status == "active",
            )
        )
        if parent_id is not None:
            recipients.add(parent_id)
    recipients.discard(actor.id)
    return recipients

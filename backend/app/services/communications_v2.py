"""Participant-checked Communications v2 operations.

Every entry point derives tenant, role and participant scope from the authenticated User.
Legacy direct threads (without teacher_employee_id) are intentionally not exposed here.
"""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import and_, or_, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.communication import (
    CommunicationMessage,
    CommunicationReadState,
    CommunicationThread,
)
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from app.schemas.communications_v2 import (
    ReadStateResponse,
    TeacherMessageResponseV2,
    TeacherOption,
    TeacherSenderChildContext,
    ThreadSummaryV2,
)
from app.services import audit
from app.services.teacher import access, communications


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_coach_actor(db: Session, actor: User) -> bool:
    if actor.role == "TEACHER":
        return True
    return actor.role == "DIRECTOR" and db.scalar(select(Organization.operating_profile).where(
        Organization.id == actor.organization_id,
    )) == "GYMNASTICS"


@dataclass(frozen=True)
class ManagementScope:
    organization_id: UUID


def management_scope(actor: User) -> ManagementScope:
    if actor.role not in {"DIRECTOR", "ADMIN"} or actor.status != "active":
        raise AppError(403, "FORBIDDEN")
    return ManagementScope(organization_id=actor.organization_id)


def _management_group(db: Session, actor: User, scope: ManagementScope, group_id: UUID) -> Group:
    if (
        scope.organization_id != actor.organization_id
        or actor.role not in {"DIRECTOR", "ADMIN"}
        or actor.status != "active"
    ):
        raise AppError(403, "FORBIDDEN")
    group = db.scalar(select(Group).where(
        Group.id == group_id, Group.organization_id == scope.organization_id, Group.status == "active",
    ))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    return group


def _active_teacher_assignment(db: Session, actor: User, employee_id: UUID, group_id: UUID) -> Employee:
    employee = db.scalar(
        select(Employee)
        .join(User, User.id == Employee.user_id)
        .join(Organization, Organization.id == Employee.organization_id)
        .join(TeacherGroupAssignment, TeacherGroupAssignment.employee_id == Employee.id)
        .where(
            Employee.id == employee_id,
            Employee.organization_id == actor.organization_id,
            Employee.status == "active",
            Employee.category == "teacher",
            User.organization_id == actor.organization_id,
            or_(
                User.role == "TEACHER",
                and_(User.role == "DIRECTOR", Organization.operating_profile == "GYMNASTICS"),
            ),
            User.status == "active",
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.group_id == group_id,
            TeacherGroupAssignment.status == "active",
        )
    )
    if employee is None:
        raise AppError(404, "NOT_FOUND")
    return employee


def eligible_teachers(db: Session, actor: User, child_id: UUID) -> list[TeacherOption]:
    if actor.role == "PARENT":
        _, child = access.parent_child(db, actor, child_id)
    elif _is_coach_actor(db, actor):
        child = access.teacher_child(db, actor, child_id)
    else:
        raise AppError(403, "FORBIDDEN")
    rows = db.execute(
        select(Employee, Group)
        .join(User, User.id == Employee.user_id)
        .join(Organization, Organization.id == Employee.organization_id)
        .join(TeacherGroupAssignment, TeacherGroupAssignment.employee_id == Employee.id)
        .join(Group, Group.id == TeacherGroupAssignment.group_id)
        .where(
            Employee.organization_id == actor.organization_id,
            Employee.status == "active", Employee.category == "teacher",
            User.organization_id == actor.organization_id,
            or_(
                User.role == "TEACHER",
                and_(User.role == "DIRECTOR", Organization.operating_profile == "GYMNASTICS"),
            ),
            User.status == "active",
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.group_id == child.group_id, TeacherGroupAssignment.status == "active",
            Group.organization_id == actor.organization_id, Group.status == "active",
        )
        .order_by(Employee.last_name, Employee.first_name, Employee.id)
    )
    return [TeacherOption(
        employee_id=employee.id,
        display_name=f"{employee.last_name} {employee.first_name}".strip(),
        group_id=group.id,
        group_name=group.name,
    ) for employee, group in rows]


def create_teacher_direct(db: Session, actor: User, child_id: UUID, guardian_id: UUID) -> CommunicationThread:
    child = access.teacher_child(db, actor, child_id)
    employee = access.teacher_employee(db, actor)
    _active_teacher_assignment(db, actor, employee.id, child.group_id)
    guardian = db.scalar(
        select(Guardian)
        .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
        .join(User, User.id == Guardian.user_id)
        .where(
            Guardian.id == guardian_id, Guardian.organization_id == actor.organization_id,
            Guardian.status == "active", ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.child_id == child.id, ChildGuardian.status == "active",
            User.organization_id == actor.organization_id, User.role == "PARENT", User.status == "active",
        )
    )
    if guardian is None:
        raise AppError(404, "NOT_FOUND")
    return _get_or_create_direct(db, actor, child, guardian, employee.id)


def create_parent_direct(db: Session, actor: User, child_id: UUID, teacher_employee_id: UUID) -> CommunicationThread:
    guardian, child = access.parent_child(db, actor, child_id)
    _active_teacher_assignment(db, actor, teacher_employee_id, child.group_id)
    return _get_or_create_direct(db, actor, child, guardian, teacher_employee_id)


def _get_or_create_direct(
    db: Session, actor: User, child: Child, guardian: Guardian, teacher_employee_id: UUID,
) -> CommunicationThread:
    query = select(CommunicationThread).where(
        CommunicationThread.organization_id == actor.organization_id,
        CommunicationThread.thread_type == "direct",
        CommunicationThread.group_id == child.group_id,
        CommunicationThread.child_id == child.id,
        CommunicationThread.guardian_id == guardian.id,
        CommunicationThread.teacher_employee_id == teacher_employee_id,
    )
    thread = db.scalar(query)
    if thread is None:
        thread = CommunicationThread(
            organization_id=actor.organization_id, thread_type="direct", audience="all",
            group_id=child.group_id, child_id=child.id, guardian_id=guardian.id,
            teacher_employee_id=teacher_employee_id,
        )
        db.add(thread)
        try:
            db.commit()
            db.refresh(thread)
        except IntegrityError:
            db.rollback()
            thread = db.scalar(query)
            if thread is None:
                raise
    return thread


def group_thread(
    db: Session, actor: User, group_id: UUID, audience: str, scope: ManagementScope | None = None,
) -> CommunicationThread:
    if scope is not None:
        _management_group(db, actor, scope, group_id)
        if audience not in {"all", "teachers"}:
            raise AppError(404, "NOT_FOUND")
    elif _is_coach_actor(db, actor):
        access.teacher_group(db, actor, group_id)
        if audience not in {"all", "teachers"}:
            raise AppError(404, "NOT_FOUND")
    elif actor.role == "PARENT":
        if group_id not in access.parent_group_ids(db, actor) or audience != "all":
            raise AppError(404, "NOT_FOUND")
        _group = db.scalar(select(Group.id).where(
            Group.id == group_id, Group.organization_id == actor.organization_id, Group.status == "active",
        ))
        if _group is None:
            raise AppError(404, "NOT_FOUND")
    else:
        raise AppError(403, "FORBIDDEN")
    query = select(CommunicationThread).where(
        CommunicationThread.organization_id == actor.organization_id,
        CommunicationThread.thread_type == "group", CommunicationThread.group_id == group_id,
        CommunicationThread.audience == audience,
    )
    thread = db.scalar(query)
    if thread is None:
        thread = CommunicationThread(
            organization_id=actor.organization_id, thread_type="group", group_id=group_id, audience=audience,
        )
        db.add(thread)
        try:
            db.commit()
            db.refresh(thread)
        except IntegrityError:
            db.rollback()
            thread = db.scalar(query)
            if thread is None:
                raise
    return thread


def _eligible_thread(
    db: Session, actor: User, thread_id: UUID, scope: ManagementScope | None = None,
) -> CommunicationThread:
    if scope is not None:
        if (
            scope.organization_id != actor.organization_id
            or actor.role not in {"DIRECTOR", "ADMIN"}
            or actor.status != "active"
        ):
            raise AppError(403, "FORBIDDEN")
        thread = db.scalar(select(CommunicationThread).where(
            CommunicationThread.id == thread_id,
            CommunicationThread.organization_id == scope.organization_id,
            CommunicationThread.thread_type == "group",
            CommunicationThread.audience.in_(("all", "teachers")),
        ).join(Group, Group.id == CommunicationThread.group_id).where(
            Group.organization_id == scope.organization_id, Group.status == "active",
        ))
        if thread is None:
            raise AppError(404, "NOT_FOUND")
        return thread
    if _is_coach_actor(db, actor):
        thread = access.teacher_thread(db, actor, thread_id)
        if thread.thread_type == "direct":
            employee = access.teacher_employee(db, actor)
            if thread.teacher_employee_id is None or thread.teacher_employee_id != employee.id:
                raise AppError(404, "NOT_FOUND")
            child = access.teacher_child(db, actor, thread.child_id)
            if child.group_id != thread.group_id:
                raise AppError(404, "NOT_FOUND")
        return thread
    if actor.role == "PARENT":
        thread = access.parent_thread(db, actor, thread_id)
        # The legacy Parent API still exposes historical `parents` Group threads,
        # but v2 only permits the currently approved shared `all` channel.
        if thread.thread_type == "group" and thread.audience != "all":
            raise AppError(404, "NOT_FOUND")
        if thread.thread_type == "direct":
            if thread.teacher_employee_id is None:
                raise AppError(404, "NOT_FOUND")
            _, child = access.parent_child(db, actor, thread.child_id)
            if child.group_id != thread.group_id:
                raise AppError(404, "NOT_FOUND")
            _active_teacher_assignment(db, actor, thread.teacher_employee_id, thread.group_id)
        return thread
    raise AppError(403, "FORBIDDEN")


def _summary(db: Session, actor: User, thread: CommunicationThread) -> ThreadSummaryV2:
    group = db.scalar(select(Group).where(
        Group.id == thread.group_id, Group.organization_id == actor.organization_id,
    ))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    child = db.scalar(select(Child).where(
        Child.id == thread.child_id, Child.organization_id == actor.organization_id,
    )) if thread.child_id else None
    employee = db.scalar(select(Employee).where(
        Employee.id == thread.teacher_employee_id, Employee.organization_id == actor.organization_id,
    )) if thread.teacher_employee_id else None
    last = db.scalar(select(CommunicationMessage).where(
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread.id,
    ).order_by(CommunicationMessage.created_at.desc(), CommunicationMessage.id.desc()).limit(1))
    state = db.scalar(select(CommunicationReadState).where(
        CommunicationReadState.organization_id == actor.organization_id,
        CommunicationReadState.thread_id == thread.id,
        CommunicationReadState.user_id == actor.id,
    ))
    unread_query = select(CommunicationMessage.id).where(
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread.id,
        CommunicationMessage.sender_user_id != actor.id,
    )
    if state and state.last_read_message_id:
        cursor = db.scalar(select(CommunicationMessage).where(
            CommunicationMessage.id == state.last_read_message_id,
            CommunicationMessage.organization_id == actor.organization_id,
            CommunicationMessage.thread_id == thread.id,
        ))
        if cursor:
            unread_query = unread_query.where(or_(
                CommunicationMessage.created_at > cursor.created_at,
                and_(CommunicationMessage.created_at == cursor.created_at, CommunicationMessage.id > cursor.id),
            ))
    unread_count = len(list(db.scalars(unread_query)))
    preview = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", last.body).strip()[:160] if last else None
    child_name = f"{child.last_name} {child.first_name}".strip() if child else None
    teacher_name = f"{employee.last_name} {employee.first_name}".strip() if employee else None
    return ThreadSummaryV2(
        id=thread.id, thread_type=thread.thread_type, audience=thread.audience,
        group_id=group.id, group_name=group.name, child_id=thread.child_id, child_name=child_name,
        guardian_id=thread.guardian_id, teacher_employee_id=thread.teacher_employee_id,
        teacher_name=teacher_name, last_message_id=last.id if last else None,
        last_message_at=last.created_at if last else None, preview=preview, unread_count=unread_count,
    )


def list_threads(db: Session, actor: User, scope: ManagementScope | None = None) -> list[ThreadSummaryV2]:
    if scope is not None:
        if (
            scope.organization_id != actor.organization_id
            or actor.role not in {"DIRECTOR", "ADMIN"}
            or actor.status != "active"
        ):
            raise AppError(403, "FORBIDDEN")
        query = select(CommunicationThread).where(
            CommunicationThread.organization_id == scope.organization_id,
            CommunicationThread.thread_type == "group", CommunicationThread.audience.in_(("all", "teachers")),
        )
    elif _is_coach_actor(db, actor):
        group_ids = access.teacher_group_ids(db, actor)
        if not group_ids:
            return []
        employee = access.teacher_employee(db, actor)
        query = select(CommunicationThread).where(
            CommunicationThread.organization_id == actor.organization_id,
            CommunicationThread.group_id.in_(group_ids),
            or_(CommunicationThread.thread_type == "group", CommunicationThread.teacher_employee_id == employee.id),
        )
    elif actor.role == "PARENT":
        group_ids = access.parent_group_ids(db, actor)
        if not group_ids:
            return []
        query = select(CommunicationThread).where(
            CommunicationThread.organization_id == actor.organization_id,
            CommunicationThread.group_id.in_(group_ids),
            or_(
                and_(CommunicationThread.thread_type == "group", CommunicationThread.audience == "all"),
                and_(CommunicationThread.thread_type == "direct", CommunicationThread.guardian_id == access.parent_guardian(db, actor).id,
                     CommunicationThread.teacher_employee_id.is_not(None)),
            ),
        )
    else:
        raise AppError(403, "FORBIDDEN")
    candidates = db.scalars(query.order_by(CommunicationThread.created_at.desc(), CommunicationThread.id.desc()))
    result = []
    for item in candidates:
        try:
            _eligible_thread(db, actor, item.id, scope)
        except AppError:
            continue
        result.append(_summary(db, actor, item))
    return result


def messages(
    db: Session, actor: User, thread_id: UUID, scope: ManagementScope | None = None,
) -> list[CommunicationMessage]:
    thread = _eligible_thread(db, actor, thread_id, scope)
    return list(db.scalars(select(CommunicationMessage).where(
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread.id,
    ).order_by(CommunicationMessage.created_at, CommunicationMessage.id)))


def teacher_message_responses(
    db: Session, actor: User, thread_id: UUID, items: list[CommunicationMessage],
) -> list[TeacherMessageResponseV2]:
    """Resolve current relationships in one tenant/group-scoped query, never persist them."""
    if actor.status != "active" or not _is_coach_actor(db, actor):
        raise AppError(403, "FORBIDDEN")
    thread = _eligible_thread(db, actor, thread_id)
    employee = access.teacher_employee(db, actor)
    _active_teacher_assignment(db, actor, employee.id, thread.group_id)
    if any(item.organization_id != actor.organization_id or item.thread_id != thread.id for item in items):
        raise AppError(404, "NOT_FOUND")
    contexts: dict[UUID, TeacherSenderChildContext] = {}
    if items and (thread.thread_type == "direct" or thread.audience == "all"):
        query = (
            select(User.id, Child.first_name, Child.last_name, ChildGuardian.relation_type)
            .join(Guardian, Guardian.user_id == User.id)
            .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
            .join(Child, Child.id == ChildGuardian.child_id)
            .where(
                User.id.in_({item.sender_user_id for item in items}),
                User.organization_id == actor.organization_id, User.role == "PARENT", User.status == "active",
                Guardian.organization_id == actor.organization_id, Guardian.status == "active",
                ChildGuardian.organization_id == actor.organization_id, ChildGuardian.status == "active",
                Child.organization_id == actor.organization_id, Child.status == "active",
                Child.group_id == thread.group_id,
            )
            .order_by(User.id, Child.id)
        )
        if thread.thread_type == "direct":
            query = query.where(Child.id == thread.child_id, Guardian.id == thread.guardian_id)
        for sender_id, first_name, last_name, relation_type in db.execute(query):
            # Multiple current links reveal only ambiguity, not a list of children.
            if sender_id in contexts:
                contexts[sender_id] = TeacherSenderChildContext(multiple_children=True)
            else:
                contexts[sender_id] = TeacherSenderChildContext(
                    child_name=f"{last_name} {first_name}".strip(), relation_type=relation_type,
                )
    return [TeacherMessageResponseV2(
        **communications._message_response(db, actor, item).model_dump(),
        sender_child_context=contexts.get(item.sender_user_id),
    ) for item in items]


def send(
    db: Session, actor: User, thread_id: UUID, body: str, client_message_id: UUID,
    scope: ManagementScope | None = None,
) -> CommunicationMessage:
    thread = _eligible_thread(db, actor, thread_id, scope)
    prior = db.scalar(select(CommunicationMessage).where(
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.sender_user_id == actor.id,
        CommunicationMessage.client_message_id == client_message_id,
    ))
    if prior:
        if prior.thread_id != thread.id:
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED")
        return prior
    message = CommunicationMessage(
        organization_id=actor.organization_id, thread_id=thread.id,
        sender_user_id=actor.id, body=body, client_message_id=client_message_id, created_at=_now(),
    )
    db.add(message)
    try:
        db.flush()
        audit.write(db, actor, "communication.message.create", "communication_message", message.id, {
            "thread_id": str(thread.id), "group_id": str(thread.group_id),
            "thread_type": thread.thread_type, "client_message_id": str(client_message_id),
        })
        for recipient_id in _recipient_ids(db, actor, thread):
            _upsert_unread_notification(db, actor.organization_id, recipient_id, "communication.message", "communication_thread", thread.id)
        db.commit()
        db.refresh(message)
        return message
    except IntegrityError:
        db.rollback()
        prior = db.scalar(select(CommunicationMessage).where(
            CommunicationMessage.organization_id == actor.organization_id,
            CommunicationMessage.sender_user_id == actor.id,
            CommunicationMessage.client_message_id == client_message_id,
        ))
        if prior is None:
            raise
        if prior.thread_id != thread.id:
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED")
        return prior


def _upsert_unread_notification(db: Session, organization_id: UUID, recipient_id: UUID, kind: str, entity_type: str, entity_id: UUID) -> None:
    predicate = f"read_at IS NULL AND kind = '{kind}' AND entity_type = '{entity_type}' AND entity_id IS NOT NULL"
    db.execute(insert(Notification).values(
        organization_id=organization_id, recipient_user_id=recipient_id,
        kind=kind, entity_type=entity_type, entity_id=entity_id,
    ).on_conflict_do_nothing(
        index_elements=[Notification.organization_id, Notification.recipient_user_id, Notification.entity_id],
        index_where=text(predicate),
    ))


def _recipient_ids(db: Session, actor: User, thread: CommunicationThread) -> set[UUID]:
    recipients: set[UUID] = set()
    if thread.thread_type == "direct":
        parent_id = db.scalar(select(User.id).join(Guardian, Guardian.user_id == User.id).where(
            Guardian.id == thread.guardian_id, Guardian.organization_id == actor.organization_id,
            Guardian.status == "active", User.organization_id == actor.organization_id,
            User.role == "PARENT", User.status == "active",
        ))
        teacher_id = db.scalar(select(User.id).join(Employee, Employee.user_id == User.id)
            .join(Organization, Organization.id == User.organization_id).where(
            Employee.id == thread.teacher_employee_id, Employee.organization_id == actor.organization_id,
            Employee.status == "active", Employee.category == "teacher",
            User.organization_id == actor.organization_id,
            or_(
                User.role == "TEACHER",
                and_(User.role == "DIRECTOR", Organization.operating_profile == "GYMNASTICS"),
            ),
            User.status == "active",
        ))
        recipients.update(user_id for user_id in (parent_id, teacher_id) if user_id)
    else:
        teacher_ids = db.scalars(
            select(User.id).join(Employee, Employee.user_id == User.id)
            .join(Organization, Organization.id == User.organization_id)
            .join(TeacherGroupAssignment, TeacherGroupAssignment.employee_id == Employee.id)
            .where(
                User.organization_id == actor.organization_id,
                or_(
                    User.role == "TEACHER",
                    and_(User.role == "DIRECTOR", Organization.operating_profile == "GYMNASTICS"),
                ),
                User.status == "active",
                Employee.organization_id == actor.organization_id, Employee.status == "active", Employee.category == "teacher",
                TeacherGroupAssignment.organization_id == actor.organization_id,
                TeacherGroupAssignment.group_id == thread.group_id, TeacherGroupAssignment.status == "active",
            )
        )
        recipients.update(teacher_ids)
        if thread.audience == "all":
            recipients.update(db.scalars(
                select(User.id).join(Guardian, Guardian.user_id == User.id)
                .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
                .join(Child, Child.id == ChildGuardian.child_id)
                .where(
                    User.organization_id == actor.organization_id, User.role == "PARENT", User.status == "active",
                    Guardian.organization_id == actor.organization_id, Guardian.status == "active",
                    ChildGuardian.organization_id == actor.organization_id, ChildGuardian.status == "active",
                    Child.organization_id == actor.organization_id, Child.group_id == thread.group_id, Child.status == "active",
                )
            ))
    recipients.discard(actor.id)
    return recipients


def mark_read(
    db: Session, actor: User, thread_id: UUID, message_id: UUID, scope: ManagementScope | None = None,
) -> ReadStateResponse:
    thread = _eligible_thread(db, actor, thread_id, scope)
    message = db.scalar(select(CommunicationMessage).where(
        CommunicationMessage.id == message_id,
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread.id,
    ))
    if message is None:
        raise AppError(404, "NOT_FOUND")
    state = db.scalar(select(CommunicationReadState).where(
        CommunicationReadState.organization_id == actor.organization_id,
        CommunicationReadState.thread_id == thread.id,
        CommunicationReadState.user_id == actor.id,
    ).with_for_update())
    if state is None:
        db.execute(insert(CommunicationReadState).values(
            organization_id=actor.organization_id, thread_id=thread.id, user_id=actor.id,
            last_read_message_id=message.id, last_read_at=message.created_at,
        ).on_conflict_do_nothing(
            index_elements=[
                CommunicationReadState.organization_id,
                CommunicationReadState.thread_id,
                CommunicationReadState.user_id,
            ],
        ))
        state = db.scalar(select(CommunicationReadState).where(
            CommunicationReadState.organization_id == actor.organization_id,
            CommunicationReadState.thread_id == thread.id,
            CommunicationReadState.user_id == actor.id,
        ).with_for_update())
    if state is not None:
        current = db.scalar(select(CommunicationMessage).where(
            CommunicationMessage.id == state.last_read_message_id,
            CommunicationMessage.organization_id == actor.organization_id,
            CommunicationMessage.thread_id == thread.id,
        )) if state.last_read_message_id else None
        if current is None or (message.created_at, message.id.int) > (current.created_at, current.id.int):
            state.last_read_message_id = message.id
            state.last_read_at = message.created_at
            state.updated_at = _now()
    read_through = state.last_read_at
    cursor_message = db.scalar(select(CommunicationMessage).where(
        CommunicationMessage.id == state.last_read_message_id,
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread.id,
    ))
    unread_remains = db.scalar(select(CommunicationMessage.id).where(
        CommunicationMessage.organization_id == actor.organization_id,
        CommunicationMessage.thread_id == thread.id,
        CommunicationMessage.sender_user_id != actor.id,
        or_(
            CommunicationMessage.created_at > cursor_message.created_at,
            and_(CommunicationMessage.created_at == cursor_message.created_at, CommunicationMessage.id > cursor_message.id),
        ),
    ).limit(1)) if cursor_message else None
    if unread_remains is None:
        notifications = db.scalars(select(Notification).where(
            Notification.organization_id == actor.organization_id,
            Notification.recipient_user_id == actor.id,
            Notification.kind == "communication.message",
            Notification.entity_type == "communication_thread",
            Notification.entity_id == thread.id,
            Notification.read_at.is_(None),
        ))
        for notification in notifications:
            notification.read_at = _now()
    db.commit()
    return ReadStateResponse(thread_id=thread.id, last_read_message_id=state.last_read_message_id, last_read_at=read_through)


"""Current-request TEACHER/PARENT tenant, assignment and participant guards."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.permissions import require_teacher_group_access
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.communication import CommunicationThread
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User


def teacher_employee(db: Session, actor: User) -> Employee:
    employee = db.scalar(select(Employee).where(
        Employee.user_id == actor.id,
        Employee.organization_id == actor.organization_id,
        Employee.status == "active",
    ))
    if actor.role != "TEACHER" or employee is None:
        raise AppError(403, "FORBIDDEN")
    return employee


def teacher_group_ids(db: Session, actor: User) -> list[UUID]:
    employee = teacher_employee(db, actor)
    return list(db.scalars(
        select(TeacherGroupAssignment.group_id)
        .join(Group, Group.id == TeacherGroupAssignment.group_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.employee_id == employee.id,
            TeacherGroupAssignment.status == "active",
            Group.organization_id == actor.organization_id,
            Group.status == "active",
        )
    ))


def teacher_group(db: Session, actor: User, group_id: UUID) -> Group:
    require_teacher_group_access(db, actor, group_id)
    group = db.scalar(select(Group).where(
        Group.id == group_id, Group.organization_id == actor.organization_id, Group.status == "active",
    ))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    return group


def teacher_child(db: Session, actor: User, child_id: UUID, *, lock: bool = False) -> Child:
    query = select(Child).where(
        Child.id == child_id,
        Child.organization_id == actor.organization_id,
        Child.status == "active",
    )
    if lock:
        query = query.with_for_update()
    child = db.scalar(query)
    if child is None:
        raise AppError(404, "NOT_FOUND")
    teacher_group(db, actor, child.group_id)
    return child


def parent_guardian(db: Session, actor: User) -> Guardian:
    guardian = db.scalar(select(Guardian).where(
        Guardian.user_id == actor.id,
        Guardian.organization_id == actor.organization_id,
        Guardian.status == "active",
    ))
    if actor.role != "PARENT" or guardian is None:
        raise AppError(403, "FORBIDDEN")
    return guardian


def parent_child(db: Session, actor: User, child_id: UUID) -> tuple[Guardian, Child]:
    guardian = parent_guardian(db, actor)
    child = db.scalar(
        select(Child)
        .join(Group, Group.id == Child.group_id)
        .join(ChildGuardian, ChildGuardian.child_id == Child.id)
        .where(
            Child.id == child_id,
            Child.organization_id == actor.organization_id,
            Child.status == "active",
            Group.organization_id == actor.organization_id,
            Group.status == "active",
            ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.guardian_id == guardian.id,
            ChildGuardian.status == "active",
        )
    )
    if child is None:
        raise AppError(404, "NOT_FOUND")
    return guardian, child


def parent_group_ids(db: Session, actor: User) -> list[UUID]:
    guardian = parent_guardian(db, actor)
    return list(db.scalars(
        select(Child.group_id)
        .join(Group, Group.id == Child.group_id)
        .join(ChildGuardian, ChildGuardian.child_id == Child.id)
        .where(
            Child.organization_id == actor.organization_id,
            Child.status == "active",
            Group.organization_id == actor.organization_id,
            Group.status == "active",
            ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.guardian_id == guardian.id,
            ChildGuardian.status == "active",
        ).distinct()
    ))


def teacher_thread(db: Session, actor: User, thread_id: UUID) -> CommunicationThread:
    thread = db.scalar(select(CommunicationThread).where(
        CommunicationThread.id == thread_id,
        CommunicationThread.organization_id == actor.organization_id,
    ))
    if thread is None:
        raise AppError(404, "NOT_FOUND")
    teacher_group(db, actor, thread.group_id)
    if thread.thread_type == "group" and thread.audience not in {"all", "teachers"}:
        raise AppError(404, "NOT_FOUND")
    if thread.thread_type == "direct":
        if thread.child_id is None or thread.guardian_id is None:
            raise AppError(404, "NOT_FOUND")
        child = teacher_child(db, actor, thread.child_id)
        relation = db.scalar(select(ChildGuardian.id).join(Guardian, Guardian.id == ChildGuardian.guardian_id).where(
            ChildGuardian.organization_id == actor.organization_id,
            ChildGuardian.child_id == child.id,
            ChildGuardian.guardian_id == thread.guardian_id,
            ChildGuardian.status == "active",
            Guardian.organization_id == actor.organization_id,
            Guardian.status == "active",
            Guardian.user_id.is_not(None),
        ))
        if relation is None:
            raise AppError(404, "NOT_FOUND")
    return thread


def parent_thread(db: Session, actor: User, thread_id: UUID) -> CommunicationThread:
    guardian = parent_guardian(db, actor)
    thread = db.scalar(select(CommunicationThread).where(
        CommunicationThread.id == thread_id,
        CommunicationThread.organization_id == actor.organization_id,
    ))
    if thread is None or thread.group_id not in parent_group_ids(db, actor):
        raise AppError(404, "NOT_FOUND")
    if thread.thread_type == "group" and thread.audience not in {"all", "parents"}:
        raise AppError(404, "NOT_FOUND")
    if thread.thread_type == "direct":
        if thread.guardian_id != guardian.id or thread.child_id is None:
            raise AppError(404, "NOT_FOUND")
        parent_child(db, actor, thread.child_id)
    return thread

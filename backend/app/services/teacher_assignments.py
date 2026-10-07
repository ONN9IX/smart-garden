"""Director writes and management reads for explicit TEACHER-to-Group assignments."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.employee import Employee
from app.models.group import Group
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from app.schemas.teacher_management import (
    TeacherAssignmentCreate,
    TeacherAssignmentResponse,
)
from app.services import audit
from app.services.auth import utc_now


def _response(assignment: TeacherGroupAssignment) -> TeacherAssignmentResponse:
    return TeacherAssignmentResponse(
        id=assignment.id, employee_id=assignment.employee_id, group_id=assignment.group_id,
        status=assignment.status, assigned_by=assignment.assigned_by,
        created_at=assignment.created_at, archived_at=assignment.archived_at,
    )


def _audit(db: Session, actor: User, action: str, assignment: TeacherGroupAssignment, details: dict) -> None:
    audit.write(db, actor, action, "teacher_assignment", assignment.id, details)


def _eligible_employee(db: Session, actor: User, employee_id: UUID) -> Employee:
    employee = db.scalar(select(Employee).where(
        Employee.id == employee_id, Employee.organization_id == actor.organization_id,
    ))
    if employee is None:
        raise AppError(404, "NOT_FOUND")
    if employee.status != "active":
        raise AppError(409, "EMPLOYEE_ARCHIVED")
    if employee.category != "teacher":
        raise AppError(409, "EMPLOYEE_CATEGORY_CONFLICT", "employee_id")
    account = db.scalar(select(User.id).where(
        User.id == employee.user_id, User.organization_id == actor.organization_id,
        User.role == "TEACHER", User.status == "active",
    ))
    if account is None:
        raise AppError(409, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    return employee


def _active_group(db: Session, actor: User, group_id: UUID) -> Group:
    group = db.scalar(select(Group).where(Group.id == group_id, Group.organization_id == actor.organization_id))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    if group.status != "active":
        raise AppError(409, "GROUP_ARCHIVED")
    return group


def _get(db: Session, actor: User, assignment_id: UUID, *, lock: bool = False) -> TeacherGroupAssignment:
    query = select(TeacherGroupAssignment).where(
        TeacherGroupAssignment.id == assignment_id,
        TeacherGroupAssignment.organization_id == actor.organization_id,
    )
    if lock:
        query = query.with_for_update()
    assignment = db.scalar(query)
    if assignment is None:
        raise AppError(404, "NOT_FOUND")
    return assignment


def create(db: Session, actor: User, payload: TeacherAssignmentCreate) -> TeacherAssignmentResponse:
    _eligible_employee(db, actor, payload.employee_id)
    _active_group(db, actor, payload.group_id)
    existing = db.scalar(select(TeacherGroupAssignment).where(
        TeacherGroupAssignment.employee_id == payload.employee_id,
        TeacherGroupAssignment.group_id == payload.group_id,
    ))
    if existing is not None:
        raise AppError(409, "RELATION_ALREADY_EXISTS")
    assignment = TeacherGroupAssignment(
        organization_id=actor.organization_id, employee_id=payload.employee_id,
        group_id=payload.group_id, status="active", assigned_by=actor.id,
    )
    db.add(assignment)
    db.flush()
    _audit(db, actor, "teacher_assignment.create", assignment, {
        "employee_id": str(assignment.employee_id), "group_id": str(assignment.group_id),
    })
    db.commit()
    db.refresh(assignment)
    return _response(assignment)


def list_assignments(db: Session, actor: User) -> list[TeacherAssignmentResponse]:
    assignments = db.scalars(
        select(TeacherGroupAssignment).where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
        ).order_by(TeacherGroupAssignment.created_at, TeacherGroupAssignment.id)
    )
    return [_response(assignment) for assignment in assignments]


def archive(db: Session, actor: User, assignment_id: UUID) -> TeacherAssignmentResponse:
    assignment = _get(db, actor, assignment_id, lock=True)
    if assignment.status != "archived":
        assignment.status = "archived"
        assignment.archived_at = utc_now()
        _audit(db, actor, "teacher_assignment.archive", assignment, {
            "status_before": "active", "status_after": "archived",
        })
        db.commit()
        db.refresh(assignment)
    return _response(assignment)


def restore(db: Session, actor: User, assignment_id: UUID) -> TeacherAssignmentResponse:
    assignment = _get(db, actor, assignment_id, lock=True)
    if assignment.status != "active":
        _eligible_employee(db, actor, assignment.employee_id)
        _active_group(db, actor, assignment.group_id)
        assignment.status = "active"
        assignment.archived_at = None
        _audit(db, actor, "teacher_assignment.restore", assignment, {
            "status_before": "archived", "status_after": "active",
        })
        db.commit()
        db.refresh(assignment)
    return _response(assignment)

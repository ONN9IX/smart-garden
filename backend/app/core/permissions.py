"""Server-side role and tenant guards for current and future business endpoints.

Security: organization IDs from a client never select an authenticated tenant.
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.employee import Employee
from app.models.group import Group
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from app.services.auth import current_user


def require_role(*roles: str) -> Callable:
    def dependency(user: Annotated[User, Depends(current_user)]) -> User:
        if user.role not in roles:
            raise AppError(403, "FORBIDDEN")
        return user

    return dependency


def require_tenant(user: User, resource_organization_id: UUID) -> None:
    if user.organization_id != resource_organization_id:
        # Hidden tenant resources get 404; never leak existence or payload.
        raise AppError(404, "NOT_FOUND")


def require_teacher_group_access(db: Session, actor: User, group_id: UUID) -> TeacherGroupAssignment:
    """Return the active assignment after revalidating the complete teacher context."""
    if actor.role != "TEACHER":
        raise AppError(403, "FORBIDDEN")
    employee_id = db.scalar(select(Employee.id).where(
        Employee.user_id == actor.id,
        Employee.organization_id == actor.organization_id,
        Employee.status == "active",
    ))
    if employee_id is None:
        raise AppError(403, "FORBIDDEN")
    assignment = db.scalar(
        select(TeacherGroupAssignment)
        .join(Group, Group.id == TeacherGroupAssignment.group_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.employee_id == employee_id,
            TeacherGroupAssignment.group_id == group_id,
            TeacherGroupAssignment.status == "active",
            Group.organization_id == actor.organization_id,
            Group.status == "active",
        )
    )
    if assignment is None:
        raise AppError(404, "NOT_FOUND")
    return assignment

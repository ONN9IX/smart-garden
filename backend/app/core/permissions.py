"""Server-side role and tenant guards for current and future business endpoints.

Security: organization IDs from a client never select an authenticated tenant.
"""

from collections.abc import Callable
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.db.session import get_db
from app.models.employee import Employee
from app.models.group import Group
from app.models.organization import Organization
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


def require_coach_employee(db: Session, actor: User) -> Employee:
    """Resolve a current coach profile without broadening the user's RBAC role."""
    allowed = actor.role == "TEACHER"
    if actor.role == "DIRECTOR":
        profile = db.scalar(select(Organization.operating_profile).where(
            Organization.id == actor.organization_id,
        ))
        allowed = profile == "GYMNASTICS"
    if not allowed:
        raise AppError(403, "FORBIDDEN")
    employee = db.scalar(select(Employee).where(
        Employee.user_id == actor.id,
        Employee.organization_id == actor.organization_id,
        Employee.status == "active",
        Employee.category == "teacher",
    ))
    if employee is None:
        raise AppError(403, "FORBIDDEN")
    return employee


def require_coach_context(
    request: Request,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(current_user)],
) -> User:
    require_coach_employee(db, user)
    # The existing TEACHER account keeps its established product surface. A
    # director using the constrained Gymnastics coach context gets only the
    # explicitly requested daily workflow; OFF/STOP modules remain closed.
    profile = db.scalar(select(Organization.operating_profile).where(
        Organization.id == user.organization_id,
    ))
    if profile == "GYMNASTICS" and user.role == "DIRECTOR":
        route = request.scope.get("route")
        route_path = getattr(route, "path", request.url.path).removeprefix("/api/v1")
        allowed_routes = {
            ("GET", "/teacher/today"),
            ("GET", "/teacher/groups"),
            ("GET", "/teacher/groups/{group_id}"),
            ("GET", "/teacher/groups/{group_id}/children"),
            ("GET", "/teacher/groups/{group_id}/guardians"),
            ("GET", "/teacher/groups/{group_id}/communication-thread"),
            ("GET", "/teacher/attendance"),
            ("POST", "/teacher/attendance/group-day"),
            ("GET", "/teacher/schedule"),
            ("GET", "/teacher/communications/threads"),
            ("GET", "/teacher/communications/threads/{thread_id}/messages"),
            ("POST", "/teacher/communications/threads/{thread_id}/messages"),
            ("POST", "/teacher/communications/direct"),
            ("GET", "/teacher/communications/v2/threads"),
            ("GET", "/teacher/communications/v2/groups/{group_id}/thread"),
            ("GET", "/teacher/communications/v2/threads/{thread_id}/messages"),
            ("POST", "/teacher/communications/v2/threads/{thread_id}/messages"),
            ("POST", "/teacher/communications/v2/threads/{thread_id}/read"),
            ("GET", "/teacher/communications/v2/children/{child_id}/teachers"),
            ("POST", "/teacher/communications/v2/direct"),
        }
        if (request.method, route_path) not in allowed_routes:
            raise AppError(403, "FORBIDDEN")
    return user


def require_teacher_group_access(db: Session, actor: User, group_id: UUID) -> TeacherGroupAssignment:
    """Return the active assignment after revalidating the complete teacher context."""
    employee = require_coach_employee(db, actor)
    assignment = db.scalar(
        select(TeacherGroupAssignment)
        .join(Group, Group.id == TeacherGroupAssignment.group_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.employee_id == employee.id,
            TeacherGroupAssignment.group_id == group_id,
            TeacherGroupAssignment.status == "active",
            Group.organization_id == actor.organization_id,
            Group.status == "active",
        )
    )
    if assignment is None:
        raise AppError(404, "NOT_FOUND")
    return assignment

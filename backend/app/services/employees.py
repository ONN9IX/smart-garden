"""Tenant-scoped staff cards; archiving an account also blocks and revokes access."""

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.auth_session import AuthSession
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import (
    EmployeeAccountSummary,
    EmployeeCreate,
    EmployeeListItem,
    EmployeePatch,
    EmployeeResponse,
)
from app.services.auth import utc_now


def get_employee(db: Session, actor: User, employee_id: UUID, *, lock: bool = False) -> Employee:
    query = select(Employee).where(Employee.id == employee_id, Employee.organization_id == actor.organization_id)
    if lock:
        query = query.with_for_update()
    employee = db.scalar(query)
    if employee is None:
        raise AppError(404, "NOT_FOUND")
    return employee


def account_summary(employee: Employee) -> EmployeeAccountSummary | None:
    if employee.user is None:
        return None
    return EmployeeAccountSummary(
        id=employee.user.id, username=employee.user.username,
        role=employee.user.role, status=employee.user.status,
        must_change_password=employee.user.must_change_password,
    )


def summary(employee: Employee) -> EmployeeListItem:
    return EmployeeListItem(
        id=employee.id, first_name=employee.first_name, last_name=employee.last_name,
        middle_name=employee.middle_name, position=employee.position,
        status=employee.status, account=account_summary(employee),
    )


def detail(employee: Employee) -> EmployeeResponse:
    return EmployeeResponse(
        **summary(employee).model_dump(), archived_at=employee.archived_at,
        created_at=employee.created_at, updated_at=employee.updated_at,
    )


def list_employees(db: Session, actor: User, status: str, q: str | None) -> list[EmployeeListItem]:
    query = select(Employee).where(Employee.organization_id == actor.organization_id)
    if status != "all":
        query = query.where(Employee.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(
            Employee.first_name.ilike(pattern), Employee.last_name.ilike(pattern),
            Employee.middle_name.ilike(pattern),
            func.concat(Employee.last_name, " ", Employee.first_name, " ", func.coalesce(Employee.middle_name, "")).ilike(pattern),
        ))
    return [summary(item) for item in db.scalars(query.order_by(Employee.last_name, Employee.first_name, Employee.id))]


def create_employee(db: Session, actor: User, payload: EmployeeCreate) -> EmployeeResponse:
    employee = Employee(organization_id=actor.organization_id, **payload.model_dump(), status="active")
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return detail(employee)


def update_employee(db: Session, actor: User, employee_id: UUID, payload: EmployeePatch) -> EmployeeResponse:
    employee = get_employee(db, actor, employee_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(employee, field, value)
    db.commit()
    db.refresh(employee)
    return detail(employee)


def archive_employee(db: Session, actor: User, employee_id: UUID) -> EmployeeResponse:
    employee = get_employee(db, actor, employee_id, lock=True)
    if employee.user_id is not None:
        if actor.role != "DIRECTOR":
            raise AppError(403, "FORBIDDEN")
        linked = employee.user
        if linked is None or linked.organization_id != actor.organization_id or linked.role != "ADMIN":
            raise AppError(403, "FORBIDDEN")
        linked.status = "blocked"
        db.execute(update(AuthSession).where(
            AuthSession.user_id == linked.id, AuthSession.revoked_at.is_(None),
        ).values(revoked_at=utc_now()))
    if employee.status != "archived":
        employee.status = "archived"
        employee.archived_at = utc_now()
    db.commit()
    db.refresh(employee)
    return detail(employee)


def restore_employee(db: Session, actor: User, employee_id: UUID) -> EmployeeResponse:
    employee = get_employee(db, actor, employee_id)
    if employee.status == "archived":
        employee.status = "active"
        employee.archived_at = None
        db.commit()
        db.refresh(employee)
    return detail(employee)

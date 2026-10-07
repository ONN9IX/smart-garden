"""Director-managed TEACHER account lifecycle bound to an active Employee."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.auth_session import AuthSession
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeAccountSummary
from app.services import audit
from app.services.auth import utc_now
from app.services.employees import get_employee


def _account(db: Session, employee: Employee, actor: User) -> User:
    if employee.user_id is None:
        raise AppError(404, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    account = db.scalar(select(User).where(
        User.id == employee.user_id, User.organization_id == actor.organization_id, User.role == "TEACHER",
    ))
    if account is None:
        raise AppError(404, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    return account


def _summary(account: User) -> EmployeeAccountSummary:
    return EmployeeAccountSummary(
        id=account.id, username=account.username, role="TEACHER",
        status=account.status, must_change_password=account.must_change_password,
    )


def _revoke(db: Session, account: User) -> None:
    db.execute(update(AuthSession).where(
        AuthSession.user_id == account.id, AuthSession.revoked_at.is_(None),
    ).values(revoked_at=utc_now()))


def block(db: Session, actor: User, employee_id: UUID) -> EmployeeAccountSummary:
    employee = get_employee(db, actor, employee_id, lock=True)
    account = _account(db, employee, actor)
    if account.status != "blocked":
        account.status = "blocked"
        _revoke(db, account)
        audit.write(db, actor, "teacher_account.block", "user_account", account.id, {
            "account_role": "TEACHER", "status_before": "active", "status_after": "blocked",
        })
    db.commit()
    return _summary(account)


def unblock(db: Session, actor: User, employee_id: UUID) -> EmployeeAccountSummary:
    employee = get_employee(db, actor, employee_id, lock=True)
    if employee.status != "active":
        raise AppError(409, "EMPLOYEE_ARCHIVED")
    account = _account(db, employee, actor)
    if account.status != "active":
        account.status = "active"
        audit.write(db, actor, "teacher_account.unblock", "user_account", account.id, {
            "account_role": "TEACHER", "status_before": "blocked", "status_after": "active",
        })
    db.commit()
    return _summary(account)

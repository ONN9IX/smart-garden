"""Director-managed ADMIN account lifecycle bound to a tenant employee card."""

import secrets
import string
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import generate_temporary_password, hash_password
from app.models.auth_session import AuthSession
from app.models.employee import Employee
from app.models.user import User
from app.schemas.employee import EmployeeAccountSummary, EmployeeTemporaryCredentials
from app.services.auth import utc_now
from app.services.employees import get_employee

ALPHABET = string.ascii_lowercase + string.digits


def _account(db: Session, employee: Employee, actor: User) -> User:
    if employee.user_id is None:
        raise AppError(404, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    account = db.scalar(select(User).where(
        User.id == employee.user_id,
        User.organization_id == actor.organization_id,
        User.role == "ADMIN",
    ))
    if account is None:
        raise AppError(404, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    return account


def _summary(account: User) -> EmployeeAccountSummary:
    return EmployeeAccountSummary(
        id=account.id, username=account.username, role="ADMIN",
        status=account.status, must_change_password=account.must_change_password,
    )


def _revoke(db: Session, account: User) -> None:
    db.execute(update(AuthSession).where(
        AuthSession.user_id == account.id, AuthSession.revoked_at.is_(None),
    ).values(revoked_at=utc_now()))


def create(db: Session, actor: User, employee_id: UUID) -> EmployeeTemporaryCredentials:
    employee = get_employee(db, actor, employee_id, lock=True)
    if employee.status != "active":
        raise AppError(409, "EMPLOYEE_ARCHIVED")
    if employee.user_id is not None:
        raise AppError(409, "EMPLOYEE_ACCOUNT_ALREADY_EXISTS")
    temporary = generate_temporary_password()
    account = None
    for _attempt in range(10):
        username = "staff-" + "".join(secrets.choice(ALPHABET) for _ in range(8))
        if db.scalar(select(User.id).where(User.username == username)):
            continue
        try:
            with db.begin_nested():
                candidate = User(
                    organization_id=actor.organization_id, username=username,
                    password_hash=hash_password(temporary), role="ADMIN",
                    status="active", must_change_password=True,
                )
                db.add(candidate)
                db.flush()
                account = candidate
        except IntegrityError:
            continue
        break
    if account is None:
        raise AppError(409, "USERNAME_ALREADY_EXISTS")
    employee.user_id = account.id
    db.commit()
    db.expire(employee, ["user"])
    return EmployeeTemporaryCredentials(account=_summary(account), temporary_password=temporary)


def reset_password(db: Session, actor: User, employee_id: UUID) -> EmployeeTemporaryCredentials:
    employee = get_employee(db, actor, employee_id, lock=True)
    account = _account(db, employee, actor)
    temporary = generate_temporary_password()
    account.password_hash = hash_password(temporary)
    account.must_change_password = True
    _revoke(db, account)
    db.commit()
    return EmployeeTemporaryCredentials(account=_summary(account), temporary_password=temporary)


def block(db: Session, actor: User, employee_id: UUID) -> EmployeeAccountSummary:
    employee = get_employee(db, actor, employee_id, lock=True)
    account = _account(db, employee, actor)
    account.status = "blocked"
    _revoke(db, account)
    db.commit()
    return _summary(account)


def unblock(db: Session, actor: User, employee_id: UUID) -> EmployeeAccountSummary:
    employee = get_employee(db, actor, employee_id, lock=True)
    if employee.status != "active":
        raise AppError(409, "EMPLOYEE_ARCHIVED")
    account = _account(db, employee, actor)
    account.status = "active"
    db.commit()
    return _summary(account)

"""Staff management routes; tenant and role derive only from authenticated session."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.errors import AppError
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.account_access import (
    AccountActionResponse,
    InviteRequest,
    InviteResponse,
    RoleChangeRequest,
)
from app.schemas.employee import (
    EmployeeAccountSummary,
    EmployeeCreate,
    EmployeeList,
    EmployeePatch,
    EmployeeResponse,
)
from app.services import account_access, employee_accounts, employees

router = APIRouter(prefix="/employees", tags=["Сотрудники"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Director = Annotated[User, Depends(require_role("DIRECTOR"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=EmployeeList)
def list_employees(
    user: Manager, db: Database,
    status: Literal["active", "archived", "all"] = Query("active"),
    category: Literal["teacher", "administrator", "other"] | None = Query(None),
    q: str | None = Query(None, max_length=100),
) -> EmployeeList:
    return EmployeeList(items=employees.list_employees(db, user, status, q, category))


@router.post("", response_model=EmployeeResponse, status_code=201)
def create_employee(payload: EmployeeCreate, user: Manager, db: Database) -> EmployeeResponse:
    return employees.create_employee(db, user, payload)


@router.get("/{employee_id}", response_model=EmployeeResponse)
def get_employee(employee_id: UUID, user: Manager, db: Database) -> EmployeeResponse:
    return employees.detail(employees.get_employee(db, user, employee_id))


@router.patch("/{employee_id}", response_model=EmployeeResponse)
def update_employee(employee_id: UUID, payload: EmployeePatch, user: Manager, db: Database) -> EmployeeResponse:
    return employees.update_employee(db, user, employee_id, payload)


@router.post("/{employee_id}/archive", response_model=EmployeeResponse)
def archive_employee(employee_id: UUID, user: Manager, db: Database) -> EmployeeResponse:
    return employees.archive_employee(db, user, employee_id)


@router.post("/{employee_id}/restore", response_model=EmployeeResponse)
def restore_employee(employee_id: UUID, user: Manager, db: Database) -> EmployeeResponse:
    return employees.restore_employee(db, user, employee_id)


@router.post("/{employee_id}/account", response_model=InviteResponse, status_code=201)
def create_account(employee_id: UUID, payload: InviteRequest, user: Director, db: Database) -> InviteResponse:
    if payload.role is None:
        raise AppError(400, "VALIDATION_ERROR", "role")
    return account_access.invite_employee(db, user, employee_id, payload.role)


@router.post("/{employee_id}/account/resend", response_model=InviteResponse)
def resend_account_invite(employee_id: UUID, payload: InviteRequest, user: Director, db: Database) -> InviteResponse:
    if payload.role is None:
        raise AppError(400, "VALIDATION_ERROR", "role")
    return account_access.invite_employee(db, user, employee_id, payload.role)


@router.post("/{employee_id}/account/role", response_model=AccountActionResponse)
def change_account_role(employee_id: UUID, payload: RoleChangeRequest, user: Director, db: Database) -> AccountActionResponse:
    account_access.change_employee_role(db, user, employee_id, payload.role)
    return AccountActionResponse()


@router.post("/{employee_id}/account/block", response_model=EmployeeAccountSummary)
def block_account(employee_id: UUID, user: Director, db: Database) -> EmployeeAccountSummary:
    return employee_accounts.block(db, user, employee_id)


@router.post("/{employee_id}/account/unblock", response_model=EmployeeAccountSummary)
def unblock_account(employee_id: UUID, user: Director, db: Database) -> EmployeeAccountSummary:
    return employee_accounts.unblock(db, user, employee_id)

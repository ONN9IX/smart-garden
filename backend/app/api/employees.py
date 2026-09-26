"""Staff management routes; tenant and role derive only from authenticated session."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeList,
    EmployeePatch,
    EmployeeResponse,
)
from app.services import employees

router = APIRouter(prefix="/employees", tags=["Сотрудники"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=EmployeeList)
def list_employees(
    user: Manager, db: Database,
    status: Literal["active", "archived", "all"] = Query("active"),
    q: str | None = Query(None, max_length=100),
) -> EmployeeList:
    return EmployeeList(items=employees.list_employees(db, user, status, q))


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

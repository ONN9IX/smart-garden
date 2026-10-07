"""Teacher account and Group assignment management surfaces."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.account_access import InviteResponse
from app.schemas.employee import EmployeeAccountSummary
from app.schemas.teacher_management import (
    TeacherAssignmentCreate,
    TeacherAssignmentList,
    TeacherAssignmentResponse,
)
from app.services import account_access, teacher_accounts, teacher_assignments

router = APIRouter(prefix="/teacher-management", tags=["Кабинет воспитателя — управление"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Director = Annotated[User, Depends(require_role("DIRECTOR"))]
Database = Annotated[Session, Depends(get_db)]


@router.post("/employees/{employee_id}/account", response_model=InviteResponse, status_code=201)
def create_account(employee_id: UUID, user: Director, db: Database) -> InviteResponse:
    return account_access.invite_employee(db, user, employee_id, "TEACHER")


@router.post("/employees/{employee_id}/account/resend", response_model=InviteResponse)
def resend_account_invite(employee_id: UUID, user: Director, db: Database) -> InviteResponse:
    return account_access.invite_employee(db, user, employee_id, "TEACHER")


@router.post("/employees/{employee_id}/account/block", response_model=EmployeeAccountSummary)
def block_account(employee_id: UUID, user: Director, db: Database) -> EmployeeAccountSummary:
    return teacher_accounts.block(db, user, employee_id)


@router.post("/employees/{employee_id}/account/unblock", response_model=EmployeeAccountSummary)
def unblock_account(employee_id: UUID, user: Director, db: Database) -> EmployeeAccountSummary:
    return teacher_accounts.unblock(db, user, employee_id)


@router.post("/assignments", response_model=TeacherAssignmentResponse, status_code=201)
def create_assignment(payload: TeacherAssignmentCreate, user: Director, db: Database) -> TeacherAssignmentResponse:
    return teacher_assignments.create(db, user, payload)


@router.get("/assignments", response_model=TeacherAssignmentList)
def list_assignments(user: Manager, db: Database) -> TeacherAssignmentList:
    return TeacherAssignmentList(items=teacher_assignments.list_assignments(db, user))


@router.post("/assignments/{assignment_id}/archive", response_model=TeacherAssignmentResponse)
def archive_assignment(assignment_id: UUID, user: Director, db: Database) -> TeacherAssignmentResponse:
    return teacher_assignments.archive(db, user, assignment_id)


@router.post("/assignments/{assignment_id}/restore", response_model=TeacherAssignmentResponse)
def restore_assignment(assignment_id: UUID, user: Director, db: Database) -> TeacherAssignmentResponse:
    return teacher_assignments.restore(db, user, assignment_id)

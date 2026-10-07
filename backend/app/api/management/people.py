"""Management People / Group profile reads and atomic family orchestration."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.child import ChildResponse
from app.schemas.management_people import (
    DuplicateCheck,
    DuplicateCheckResponse,
    EmployeeProfile,
    FamilyCreate,
    GuardianSearchRequest,
    GuardianSearchResponse,
    GroupOverviewList,
    GroupProfile,
)
from app.services import management_people

router = APIRouter(tags=["Люди и группы"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


@router.post("/management/people/duplicates", response_model=DuplicateCheckResponse)
def check_duplicates(payload: DuplicateCheck, user: Manager, db: Database) -> DuplicateCheckResponse:
    return management_people.duplicate_matches(db, user, payload)


@router.post("/management/people/guardian-search", response_model=GuardianSearchResponse)
def search_guardians(payload: GuardianSearchRequest, user: Manager, db: Database) -> GuardianSearchResponse:
    return management_people.search_guardians(db, user, payload)


@router.post("/management/families", response_model=ChildResponse, status_code=201)
def create_family(payload: FamilyCreate, user: Manager, db: Database) -> ChildResponse:
    return management_people.create_family(db, user, payload)


@router.get("/management/groups/{group_id}/profile", response_model=GroupProfile)
def group_profile(group_id: UUID, user: Manager, db: Database) -> GroupProfile:
    return management_people.group_profile(db, user, group_id)


@router.get("/management/groups/overview", response_model=GroupOverviewList)
def group_overviews(
    user: Manager, db: Database,
    status: Literal["active", "archived", "all"] = "active",
) -> GroupOverviewList:
    return management_people.group_overviews(db, user, status)


@router.get("/management/employees/{employee_id}/profile", response_model=EmployeeProfile)
def employee_profile(employee_id: UUID, user: Manager, db: Database) -> EmployeeProfile:
    return management_people.employee_profile(db, user, employee_id)

"""Guardian HTTP handlers; identity and tenant always come from the session."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.guardian import (
    GuardianCreate,
    GuardianList,
    GuardianPatch,
    GuardianResponse,
    ParentAccountSummary,
)
from app.schemas.parent_account import TemporaryCredentials
from app.services import guardians, parent_accounts

router = APIRouter(prefix="/guardians", tags=["Представители"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=GuardianList)
def list_guardians(user: Manager, db: Database, status: Literal["active", "archived", "all"] = Query("active"), q: str | None = Query(None, max_length=100)) -> GuardianList:
    return GuardianList(items=guardians.list_guardians(db, user, status, q))


@router.post("", response_model=GuardianResponse, status_code=201)
def create_guardian(payload: GuardianCreate, user: Manager, db: Database) -> GuardianResponse:
    return guardians.create_guardian(db, user, payload)


@router.get("/{guardian_id}", response_model=GuardianResponse)
def get_guardian(guardian_id: UUID, user: Manager, db: Database) -> GuardianResponse:
    return guardians.detail(guardians.get_guardian(db, user, guardian_id))


@router.patch("/{guardian_id}", response_model=GuardianResponse)
def update_guardian(guardian_id: UUID, payload: GuardianPatch, user: Manager, db: Database) -> GuardianResponse:
    return guardians.update_guardian(db, user, guardian_id, payload)


@router.post("/{guardian_id}/archive", response_model=GuardianResponse)
def archive_guardian(guardian_id: UUID, user: Manager, db: Database) -> GuardianResponse:
    return guardians.archive_guardian(db, user, guardian_id)


@router.post("/{guardian_id}/restore", response_model=GuardianResponse)
def restore_guardian(guardian_id: UUID, user: Manager, db: Database) -> GuardianResponse:
    return guardians.restore_guardian(db, user, guardian_id)


@router.post("/{guardian_id}/account", response_model=TemporaryCredentials, status_code=201)
def create_parent_account(guardian_id: UUID, user: Manager, db: Database) -> TemporaryCredentials:
    return parent_accounts.create(db, user, guardian_id)


@router.post("/{guardian_id}/account/reset-password", response_model=TemporaryCredentials)
def reset_parent_password(guardian_id: UUID, user: Manager, db: Database) -> TemporaryCredentials:
    return parent_accounts.reset_password(db, user, guardian_id)


@router.post("/{guardian_id}/account/block", response_model=ParentAccountSummary)
def block_parent_account(guardian_id: UUID, user: Manager, db: Database) -> ParentAccountSummary:
    return parent_accounts.block(db, user, guardian_id)


@router.post("/{guardian_id}/account/unblock", response_model=ParentAccountSummary)
def unblock_parent_account(guardian_id: UUID, user: Manager, db: Database) -> ParentAccountSummary:
    return parent_accounts.unblock(db, user, guardian_id)

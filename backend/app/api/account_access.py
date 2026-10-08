"""Aggregate Access & Accounts management endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.account_access import (
    AccessAccountSections,
    AccountActionResponse,
    BulkParentRequest,
    BulkParentResponse,
    RevokeSessionsRequest,
)
from app.services import account_access

router = APIRouter(prefix="/access-accounts", tags=["Доступ и аккаунты"], responses=MANAGEMENT_ERRORS)
Manager = Annotated[User, Depends(require_role("DIRECTOR", "ADMIN"))]
Database = Annotated[Session, Depends(get_db)]
Director = Annotated[User, Depends(require_role("DIRECTOR"))]


@router.get("", response_model=AccessAccountSections)
def list_access_accounts(user: Manager, db: Database) -> AccessAccountSections:
    return account_access.access_sections(db, user)


@router.post("/parents/bulk-invite", response_model=BulkParentResponse)
def bulk_parent_invite(payload: BulkParentRequest, user: Manager, db: Database) -> BulkParentResponse:
    return account_access.bulk_parent_invites(db, user, payload.guardian_ids, payload.confirm)


@router.post("/revoke-sessions", response_model=AccountActionResponse)
def revoke_all_sessions(payload: RevokeSessionsRequest, user: Director, db: Database) -> AccountActionResponse:
    account_access.revoke_profile_sessions(db, user, payload.profile_type, payload.profile_id)
    return AccountActionResponse()

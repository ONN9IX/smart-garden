"""Guardian HTTP handlers; identity and tenant always come from the session."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.guardian import (
    GuardianCreate,
    GuardianList,
    GuardianPatch,
    GuardianResponse,
)
from app.services import guardians

router = APIRouter(prefix="/guardians", tags=["Представители"])
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

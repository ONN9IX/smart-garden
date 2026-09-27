"""DIRECTOR-only, read-only tenant Audit API."""

from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.error_responses import MANAGEMENT_ERRORS
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.audit import AuditEventList, AuditEventResponse
from app.services import audit

router = APIRouter(prefix="/audit", tags=["Аудит"], responses=MANAGEMENT_ERRORS)
Director = Annotated[User, Depends(require_role("DIRECTOR"))]
Database = Annotated[Session, Depends(get_db)]


@router.get("", response_model=AuditEventList)
def list_audit_events(
    user: Director,
    db: Database,
    entity_type: str | None = Query(None, max_length=32),
    action: str | None = Query(None, max_length=64),
    actor_user_id: UUID | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> AuditEventList:
    return audit.list_events(
        db,
        user,
        entity_type=entity_type,
        action=action,
        actor_user_id=actor_user_id,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}", response_model=AuditEventResponse)
def get_audit_event(event_id: UUID, user: Director, db: Database) -> AuditEventResponse:
    return audit.get_event(db, user, event_id)

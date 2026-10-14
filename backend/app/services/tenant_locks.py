"""Coarse tenant row locks for operations that must serialize across writers."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.organization import Organization


def lock_tenant(db: Session, organization_id: UUID) -> None:
    locked_id = db.scalar(
        select(Organization.id)
        .where(Organization.id == organization_id)
        .with_for_update()
    )
    if locked_id is None:
        raise AppError(404, "NOT_FOUND")

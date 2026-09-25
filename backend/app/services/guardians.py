"""Tenant-scoped guardian records and atomic archive/account blocking."""

from uuid import UUID

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.auth_session import AuthSession
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.guardian import Guardian
from app.models.user import User
from app.schemas.guardian import (
    GuardianCreate,
    GuardianListItem,
    GuardianPatch,
    GuardianResponse,
    ParentAccountSummary,
)
from app.services.auth import utc_now


def get_guardian(db: Session, user: User, guardian_id: UUID) -> Guardian:
    guardian = db.scalar(select(Guardian).where(Guardian.id == guardian_id, Guardian.organization_id == user.organization_id))
    if guardian is None:
        raise AppError(404, "NOT_FOUND")
    return guardian


def account_summary(guardian: Guardian) -> ParentAccountSummary | None:
    if guardian.user is None:
        return None
    return ParentAccountSummary(
        id=guardian.user.id, username=guardian.user.username, status=guardian.user.status,
        must_change_password=guardian.user.must_change_password,
    )


def summary(guardian: Guardian) -> GuardianListItem:
    return GuardianListItem(
        id=guardian.id, first_name=guardian.first_name, last_name=guardian.last_name,
        middle_name=guardian.middle_name, phone=guardian.phone, email=guardian.email,
        status=guardian.status, account=account_summary(guardian),
    )


def detail(guardian: Guardian) -> GuardianResponse:
    # Child relation projection is added with BACK2-05.
    return GuardianResponse(
        **summary(guardian).model_dump(), children=[], archived_at=guardian.archived_at,
        created_at=guardian.created_at, updated_at=guardian.updated_at,
    )


def list_guardians(db: Session, user: User, status: str, q: str | None) -> list[GuardianListItem]:
    stmt = select(Guardian).where(Guardian.organization_id == user.organization_id)
    if status != "all":
        stmt = stmt.where(Guardian.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        stmt = stmt.where(or_(
            Guardian.first_name.ilike(pattern), Guardian.last_name.ilike(pattern),
            Guardian.middle_name.ilike(pattern),
            func.concat(Guardian.last_name, " ", Guardian.first_name, " ", func.coalesce(Guardian.middle_name, "")).ilike(pattern),
        ))
    return [summary(guardian) for guardian in db.scalars(stmt.order_by(Guardian.last_name, Guardian.first_name, Guardian.id))]


def create_guardian(db: Session, user: User, payload: GuardianCreate) -> GuardianResponse:
    guardian = Guardian(organization_id=user.organization_id, **payload.model_dump(), status="active")
    db.add(guardian)
    db.commit()
    db.refresh(guardian)
    return detail(guardian)


def update_guardian(db: Session, user: User, guardian_id: UUID, payload: GuardianPatch) -> GuardianResponse:
    guardian = get_guardian(db, user, guardian_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(guardian, field, value)
    db.commit()
    db.refresh(guardian)
    return detail(guardian)


def archive_guardian(db: Session, user: User, guardian_id: UUID) -> GuardianResponse:
    guardian = get_guardian(db, user, guardian_id)
    db.execute(select(Guardian).where(Guardian.id == guardian.id).with_for_update()).scalar_one()
    active_link = db.scalar(
        select(ChildGuardian.id).join(Child, Child.id == ChildGuardian.child_id).where(
            ChildGuardian.guardian_id == guardian.id, ChildGuardian.organization_id == user.organization_id,
            ChildGuardian.status == "active", Child.status == "active",
        ).limit(1),
    )
    if active_link:
        raise AppError(409, "GUARDIAN_HAS_ACTIVE_CHILDREN")
    if guardian.status != "archived":
        guardian.status = "archived"
        guardian.archived_at = utc_now()
    if guardian.user_id:
        parent = guardian.user
        if parent is None or parent.organization_id != user.organization_id or parent.role != "PARENT":
            raise AppError(409, "FORBIDDEN")
        parent.status = "blocked"
        db.execute(update(AuthSession).where(AuthSession.user_id == parent.id, AuthSession.revoked_at.is_(None)).values(revoked_at=utc_now()))
    db.commit()
    db.refresh(guardian)
    return detail(guardian)


def restore_guardian(db: Session, user: User, guardian_id: UUID) -> GuardianResponse:
    guardian = get_guardian(db, user, guardian_id)
    if guardian.status == "archived":
        guardian.status = "active"
        guardian.archived_at = None
        db.commit()
        db.refresh(guardian)
    return detail(guardian)

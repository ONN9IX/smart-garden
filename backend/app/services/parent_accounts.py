"""PARENT lifecycle with tenant locks, hashed passwords and atomic session revocation."""

from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.auth_session import AuthSession
from app.models.guardian import Guardian
from app.models.user import User
from app.schemas.guardian import ParentAccountSummary
from app.services import audit
from app.services.auth import utc_now


def _guardian(db: Session, actor: User, guardian_id: UUID) -> Guardian:
    guardian = db.scalar(select(Guardian).where(
        Guardian.id == guardian_id, Guardian.organization_id == actor.organization_id,
    ).with_for_update())
    if guardian is None:
        raise AppError(404, "NOT_FOUND")
    return guardian


def _parent(db: Session, guardian: Guardian, actor: User) -> User:
    if guardian.user_id is None:
        raise AppError(404, "PARENT_ACCOUNT_NOT_FOUND")
    parent = db.scalar(select(User).where(
        User.id == guardian.user_id, User.organization_id == actor.organization_id, User.role == "PARENT",
    ))
    if parent is None:
        raise AppError(404, "PARENT_ACCOUNT_NOT_FOUND")
    return parent


def _summary(parent: User) -> ParentAccountSummary:
    return ParentAccountSummary(
        id=parent.id, username=parent.username,
        status=parent.status, must_change_password=parent.must_change_password,
    )


def _revoke(db: Session, parent: User) -> None:
    db.execute(update(AuthSession).where(
        AuthSession.user_id == parent.id, AuthSession.revoked_at.is_(None),
    ).values(revoked_at=utc_now()))


def block(db: Session, actor: User, guardian_id: UUID) -> ParentAccountSummary:
    guardian = _guardian(db, actor, guardian_id)
    parent = _parent(db, guardian, actor)
    if parent.status != "blocked":
        parent.status = "blocked"
        _revoke(db, parent)
        audit.write(db, actor, "account.block", "user_account", parent.id, {
            "account_role": "PARENT", "status_before": "active", "status_after": "blocked",
        })
    db.commit()
    return _summary(parent)


def unblock(db: Session, actor: User, guardian_id: UUID) -> ParentAccountSummary:
    guardian = _guardian(db, actor, guardian_id)
    if guardian.status != "active":
        raise AppError(409, "GUARDIAN_ARCHIVED")
    parent = _parent(db, guardian, actor)
    if parent.status != "active":
        parent.status = "active"
        audit.write(db, actor, "account.unblock", "user_account", parent.id, {
            "account_role": "PARENT", "status_before": "blocked", "status_after": "active",
        })
    db.commit()
    return _summary(parent)

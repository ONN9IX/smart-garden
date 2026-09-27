"""PARENT lifecycle with tenant locks, hashed passwords and atomic session revocation."""

import secrets
import string
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.security import generate_temporary_password, hash_password
from app.models.auth_session import AuthSession
from app.models.guardian import Guardian
from app.models.user import User
from app.schemas.guardian import ParentAccountSummary
from app.schemas.parent_account import TemporaryCredentials
from app.services import audit
from app.services.auth import utc_now

ALPHABET = string.ascii_lowercase + string.digits


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


def create(db: Session, actor: User, guardian_id: UUID) -> TemporaryCredentials:
    guardian = _guardian(db, actor, guardian_id)
    if guardian.status != "active":
        raise AppError(409, "GUARDIAN_ARCHIVED")
    if guardian.user_id is not None:
        raise AppError(409, "PARENT_ACCOUNT_ALREADY_EXISTS")
    temporary = generate_temporary_password()
    # Savepoint preserves the guardian lock when a globally unique username collides.
    parent = None
    for _attempt in range(10):
        username = "parent-" + "".join(secrets.choice(ALPHABET) for _ in range(8))
        if db.scalar(select(User.id).where(User.username == username)):
            continue
        try:
            with db.begin_nested():
                candidate = User(
                    organization_id=actor.organization_id, username=username,
                    password_hash=hash_password(temporary), role="PARENT",
                    status="active", must_change_password=True,
                )
                db.add(candidate)
                db.flush()
                parent = candidate
        except IntegrityError:
            continue
        break
    if parent is None:
        raise AppError(409, "USERNAME_ALREADY_EXISTS")
    guardian.user_id = parent.id
    audit.write(db, actor, "account.create", "user_account", parent.id, {"account_role": "PARENT"})
    db.commit()
    db.expire(guardian, ["user"])
    return TemporaryCredentials(account=_summary(parent), temporary_password=temporary)


def reset_password(db: Session, actor: User, guardian_id: UUID) -> TemporaryCredentials:
    guardian = _guardian(db, actor, guardian_id)
    parent = _parent(db, guardian, actor)
    temporary = generate_temporary_password()
    parent.password_hash = hash_password(temporary)
    parent.must_change_password = True
    _revoke(db, parent)
    audit.write(db, actor, "account.reset_password", "user_account", parent.id, {"account_role": "PARENT"})
    db.commit()
    return TemporaryCredentials(account=_summary(parent), temporary_password=temporary)


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

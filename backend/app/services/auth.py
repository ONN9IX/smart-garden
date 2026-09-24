"""Server-owned auth sessions and current identity.

Purpose: issue/revoke sessions and resolve tenant from the authenticated user.
Security: only a SHA-256 token digest is stored; temporary users cannot enter protected business APIs.
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, Security
from fastapi.security import APIKeyCookie
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    generate_session_token,
    hash_session_token,
    verify_password,
)
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User

COOKIE_NAME = "smart_garden_session"
session_cookie = APIKeyCookie(name=COOKIE_NAME, auto_error=False, description="HttpOnly server-side session cookie")


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def issue_session(db: Session, user: User) -> str:
    token = generate_session_token()
    db.add(AuthSession(user_id=user.id, token_hash=hash_session_token(token), expires_at=utc_now() + timedelta(seconds=get_settings().auth_session_ttl_seconds)))
    return token


def authenticate_credentials(db: Session, username: str, password: str) -> User:
    from app.core.security import normalize_username

    try:
        normalized = normalize_username(username)
    except ValueError:
        raise AppError(401, "INVALID_CREDENTIALS") from None
    user = db.scalar(select(User).where(User.username == normalized))
    if user is None or not verify_password(user.password_hash, password):
        raise AppError(401, "INVALID_CREDENTIALS")
    if user.status != "active":
        raise AppError(403, "USER_BLOCKED")
    if user.organization.status != "active":
        raise AppError(403, "ORGANIZATION_BLOCKED")
    if user.role not in {"DIRECTOR", "ADMIN"}:
        raise AppError(403, "FORBIDDEN")
    return user


def session_from_token(db: Session, token: str | None) -> AuthSession:
    if not token:
        raise AppError(401, "UNAUTHORIZED")
    try:
        digest = hash_session_token(token)
    except UnicodeEncodeError:
        raise AppError(401, "UNAUTHORIZED") from None
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == digest))
    if session is None or session.revoked_at is not None or session.expires_at <= utc_now():
        raise AppError(401, "UNAUTHORIZED")
    return session


def current_identity(
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Security(session_cookie)],
) -> User:
    session = session_from_token(db, token)
    user = db.get(User, session.user_id)
    if user is None:
        raise AppError(401, "UNAUTHORIZED")
    if user.status != "active":
        raise AppError(403, "USER_BLOCKED")
    if user.organization.status != "active":
        raise AppError(403, "ORGANIZATION_BLOCKED")
    if user.role not in {"DIRECTOR", "ADMIN"}:
        raise AppError(403, "FORBIDDEN")
    return user


def current_user(user: Annotated[User, Depends(current_identity)]) -> User:
    if user.must_change_password:
        raise AppError(403, "PASSWORD_CHANGE_REQUIRED")
    return user

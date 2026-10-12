"""Independent password + replay-resistant TOTP sessions. No tenant auth fallback."""

import hmac
import re
from datetime import timedelta

import pyotp
from sqlalchemy import func, select

from app.core import platform_security as security
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import (
    generate_session_token,
    hash_password,
    hash_session_token,
    normalize_username,
    verify_password,
)
from app.models.platform_operator import PlatformOperator
from app.models.platform_session import PlatformSession
from app.schemas.platform import IdentityView
from app.services import platform_audit

DUMMY_HASH = hash_password("platform-dummy-password-only")


def password_login(db, username: str, password: str, client_address: str) -> str:
    now = security.utc_now()
    ip_hash = security.digest_context("platform-login-ip:" + client_address)
    security.advisory_lock(db, "platform-login-rate:" + ip_hash)
    recent = db.scalar(
        select(func.count(PlatformSession.id)).where(
            PlatformSession.purpose == "login_attempt",
            PlatformSession.ip_hash == ip_hash,
            PlatformSession.created_at > now - timedelta(minutes=15),
        )
    )
    if recent >= 20:
        db.commit()
        raise AppError(429, "FORBIDDEN")
    db.add(
        PlatformSession(
            token_hash=hash_session_token(generate_session_token()),
            purpose="login_attempt",
            ip_hash=ip_hash,
            created_at=now,
            expires_at=now + timedelta(minutes=15),
        )
    )
    try:
        username = normalize_username(username)
    except ValueError:
        username = ""
    operator = db.scalar(
        select(PlatformOperator)
        .where(PlatformOperator.username == username)
        .with_for_update()
    )
    valid = verify_password(
        operator.password_hash if operator else DUMMY_HASH, password
    )
    if operator and operator.locked_until and operator.locked_until <= now:
        operator.locked_until = None
        operator.failed_attempts = 0
    if (
        not operator
        or operator.status != "active"
        or (operator.locked_until and operator.locked_until > now)
        or not valid
    ):
        if operator and operator.status == "active" and not operator.locked_until:
            failed_attempt(db, operator)
        db.commit()
        raise AppError(401, "INVALID_CREDENTIALS")
    token = generate_session_token()
    db.add(
        PlatformSession(
            operator_id=operator.id,
            token_hash=hash_session_token(token),
            ip_hash=ip_hash,
            created_at=now,
            expires_at=now + timedelta(minutes=5),
        )
    )
    db.commit()
    return token


def failed_attempt(db, operator) -> None:
    operator.failed_attempts += 1
    if operator.failed_attempts >= 5:
        operator.locked_until = security.utc_now() + timedelta(minutes=15)
    platform_audit.write(db, operator.id, "auth.failure")


def session_identity(db, token: str | None, *, allow_challenge: bool = False):
    security.cipher()
    if not token or not re.fullmatch(r"[A-Za-z0-9_-]{50,128}", token):
        raise AppError(401, "UNAUTHORIZED")
    session = db.scalar(
        select(PlatformSession).where(
            PlatformSession.token_hash == hash_session_token(token),
            PlatformSession.purpose == "session",
        )
    )
    if session is None:
        raise AppError(401, "UNAUTHORIZED")
    # Consistent operator -> session lock order also serializes offline recovery.
    operator = db.scalar(
        select(PlatformOperator)
        .where(PlatformOperator.id == session.operator_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    session = db.scalar(
        select(PlatformSession)
        .where(PlatformSession.id == session.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        operator is None
        or operator.status != "active"
        or session.revoked_at is not None
        or session.expires_at <= security.utc_now()
    ):
        raise AppError(401, "UNAUTHORIZED")
    if not allow_challenge and session.mfa_verified_at is None:
        raise AppError(401, "UNAUTHORIZED")
    return session, operator


def verify_mfa(db, token: str | None, code: str, *, step_up: bool = False):
    session, operator = session_identity(db, token, allow_challenge=not step_up)
    now = security.utc_now()
    if operator.locked_until and operator.locked_until > now:
        raise AppError(401, "INVALID_CREDENTIALS")
    if not step_up and session.mfa_verified_at is not None:
        raise AppError(401, "INVALID_CREDENTIALS")
    totp = pyotp.TOTP(security.decrypt_secret(operator.totp_secret_ciphertext))
    current = int(now.timestamp()) // 30
    matching = next(
        (
            counter
            for counter in (current - 1, current, current + 1)
            if hmac.compare_digest(totp.at(counter * 30), code)
        ),
        None,
    )
    if matching is None or matching <= operator.last_totp_counter:
        failed_attempt(db, operator)
        db.commit()
        raise AppError(401, "INVALID_CREDENTIALS")
    operator.last_totp_counter = matching
    operator.failed_attempts = 0
    operator.locked_until = None
    session.mfa_verified_at = now
    if not step_up:
        session.expires_at = now + timedelta(
            seconds=get_settings().platform_session_ttl_seconds
        )
    platform_audit.write(db, operator.id, "auth.step_up" if step_up else "auth.login")
    db.commit()
    return session, operator


def require_fresh(session) -> None:
    if (
        session.mfa_verified_at is None
        or session.mfa_verified_at
        < security.utc_now()
        - timedelta(seconds=get_settings().platform_step_up_seconds)
    ):
        raise AppError(403, "FORBIDDEN")


def identity_view(session, operator, token: str) -> IdentityView:
    return IdentityView(
        username=operator.username,
        csrf_token=security.csrf_token(token),
        credential_handoff_enabled=get_settings().platform_credential_handoff_enabled,
        step_up_required=session.mfa_verified_at
        < security.utc_now()
        - timedelta(seconds=get_settings().platform_step_up_seconds),
    )


def logout(db, token: str) -> None:
    session, operator = session_identity(db, token)
    session.revoked_at = security.utc_now()
    platform_audit.write(db, operator.id, "auth.logout")
    db.commit()

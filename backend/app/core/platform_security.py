"""Platform-only cryptography and request defenses. No tenant cookie is consumed."""

import hashlib
import hmac
from datetime import UTC, datetime

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request

from app.core.config import get_settings
from app.core.errors import AppError

COOKIE_NAME = "promax_platform_session"
COOKIE_PATH = "/api/v1/platform"


def utc_now() -> datetime:
    return datetime.now(UTC)


def cipher() -> Fernet:
    key = get_settings().platform_encryption_key
    if not key:
        raise AppError(503, "FORBIDDEN")
    return Fernet(key.encode("ascii"))


def encrypt_secret(secret: str) -> str:
    return cipher().encrypt(secret.encode("ascii")).decode("ascii")


def decrypt_secret(value: str) -> str:
    try:
        return cipher().decrypt(value.encode("ascii")).decode("ascii")
    except (InvalidToken, UnicodeError):
        raise AppError(503, "FORBIDDEN") from None


def digest_context(context: str) -> str:
    cipher()  # Fail closed before any platform action if key custody is absent.
    return hmac.new(
        get_settings().platform_encryption_key.encode("ascii"),
        context.encode(),
        hashlib.sha256,
    ).hexdigest()


def csrf_token(token: str) -> str:
    return digest_context("platform-csrf:" + token)


def enforce_write(request: Request, token: str | None = None) -> None:
    if request.headers.get("origin") not in get_settings().allowed_origins:
        raise AppError(403, "FORBIDDEN")
    if (
        request.headers.get("content-type", "").split(";")[0].strip().lower()
        != "application/json"
    ):
        raise AppError(403, "FORBIDDEN")
    expected = csrf_token(token) if token else "login"
    if not hmac.compare_digest(request.headers.get("x-platform-csrf", ""), expected):
        raise AppError(403, "FORBIDDEN")


def advisory_lock(db, context: str) -> None:
    from sqlalchemy import func, select

    key = int.from_bytes(
        hashlib.sha256(context.encode()).digest()[:8], "big", signed=True
    )
    db.execute(select(func.pg_advisory_xact_lock(key)))

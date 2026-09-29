"""Operator-invoked cleanup limited to expired authentication sessions."""

from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models.auth_session import AuthSession


def cleanup_expired_sessions(db: Session, *, cutoff: datetime | None = None) -> int:
    """Delete AuthSession rows expired at ``cutoff`` and return only their count.

    The caller owns the transaction. An exception therefore propagates to the
    operator and lets the surrounding transaction roll back instead of
    reporting a failed cleanup as successful.
    """
    effective_cutoff = cutoff or datetime.now(timezone.utc)
    if effective_cutoff.tzinfo is None or effective_cutoff.utcoffset() is None:
        raise ValueError("session cleanup cutoff must be timezone-aware")
    effective_cutoff = effective_cutoff.astimezone(timezone.utc)

    result = db.execute(delete(AuthSession).where(AuthSession.expires_at <= effective_cutoff))
    deleted_count = result.rowcount
    if deleted_count is None or deleted_count < 0:
        raise RuntimeError("session cleanup did not return a deleted-row count")
    return deleted_count

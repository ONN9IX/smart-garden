"""PostgreSQL checks for bounded Stage 5 authentication-session cleanup."""

from datetime import timedelta

import pytest
from sqlalchemy import func, select, text

from app.core.errors import AppError
from app.core.security import hash_session_token
from app.models.auth_session import AuthSession
from app.models.user import User
from app.services.auth import session_from_token, utc_now
from app.services.session_cleanup import cleanup_expired_sessions


def test_cleanup_deletes_only_expired_sessions_and_preserves_business_data(db, users, caplog):
    _, _, director, _ = users
    cutoff = utc_now()
    sessions = {
        "expired_active": AuthSession(
            user_id=director.id,
            token_hash="a" * 64,
            expires_at=cutoff - timedelta(seconds=1),
        ),
        "expired_revoked": AuthSession(
            user_id=director.id,
            token_hash="b" * 64,
            expires_at=cutoff,
            revoked_at=cutoff - timedelta(minutes=1),
        ),
        "revoked_not_expired": AuthSession(
            user_id=director.id,
            token_hash="c" * 64,
            expires_at=cutoff + timedelta(hours=1),
            revoked_at=cutoff - timedelta(minutes=1),
        ),
        "active_not_expired": AuthSession(
            user_id=director.id,
            token_hash="d" * 64,
            expires_at=cutoff + timedelta(hours=1),
        ),
    }
    db.add_all(sessions.values())
    db.flush()

    user_count = db.scalar(select(func.count()).select_from(User))
    audit_count = db.execute(text("SELECT count(*) FROM audit_events")).scalar_one()

    deleted_count = cleanup_expired_sessions(db, cutoff=cutoff)
    db.flush()

    remaining_hashes = set(
        db.scalars(
            select(AuthSession.token_hash).where(
                AuthSession.token_hash.in_(session.token_hash for session in sessions.values())
            )
        )
    )
    assert deleted_count == 2
    assert sessions["expired_active"].token_hash not in remaining_hashes
    assert sessions["expired_revoked"].token_hash not in remaining_hashes
    assert sessions["revoked_not_expired"].token_hash in remaining_hashes
    assert sessions["active_not_expired"].token_hash in remaining_hashes

    assert db.scalar(select(func.count()).select_from(User)) == user_count
    assert db.execute(text("SELECT count(*) FROM audit_events")).scalar_one() == audit_count

    operator_evidence = f"deleted_auth_sessions={deleted_count}\n{caplog.text}"
    assert str(director.id) not in operator_evidence
    for session in sessions.values():
        assert session.token_hash not in operator_evidence


def test_revoked_unexpired_session_remains_invalid_after_cleanup(db, users):
    _, _, director, _ = users
    cutoff = utc_now()
    token = "revoked-session-token"
    revoked = AuthSession(
        user_id=director.id,
        token_hash=hash_session_token(token),
        expires_at=cutoff + timedelta(hours=1),
        revoked_at=cutoff,
    )
    db.add(revoked)
    db.flush()

    assert cleanup_expired_sessions(db, cutoff=cutoff) == 0
    assert db.get(AuthSession, revoked.id) is revoked
    with pytest.raises(AppError) as error:
        session_from_token(db, token)
    assert error.value.status == 401


def test_cleanup_rejects_naive_cutoff_without_deleting(db, users):
    _, _, director, _ = users
    session = AuthSession(
        user_id=director.id,
        token_hash="f" * 64,
        expires_at=utc_now() - timedelta(seconds=1),
    )
    db.add(session)
    db.flush()

    with pytest.raises(ValueError, match="timezone-aware"):
        cleanup_expired_sessions(db, cutoff=utc_now().replace(tzinfo=None))
    assert db.get(AuthSession, session.id) is session

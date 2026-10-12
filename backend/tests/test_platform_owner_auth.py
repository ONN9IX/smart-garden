"""Synthetic PostgreSQL checks for the independent platform authentication boundary."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from alembic.config import Config
from cryptography.fernet import Fernet
from sqlalchemy import select, text

from alembic import command
from app.core import platform_security as security
from app.core.config import get_settings
from app.db.session import engine
from app.models.platform_session import PlatformSession
from app.services.platform_bootstrap import configure_operator
from tests.conftest import TEST_PASSWORD

PASSWORD = "synthetic-owner-password-221"
ROOT = "/api/v1/platform"


class SyntheticOwner(tuple):
    def __repr__(self):
        return "SyntheticOwner(credentials redacted)"


@pytest.fixture(autouse=True)
def platform_schema(migrations):
    # Historical #177 round-trip intentionally ends at 0018. Our tests own
    # restoring their required schema without changing frozen tests/conftest.
    with engine.connect() as connection:
        revision = connection.scalar(text("SELECT version_num FROM alembic_version"))
    if revision != "0019":
        command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def platform_owner(db, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(
        settings, "platform_encryption_key", Fernet.generate_key().decode()
    )
    monkeypatch.setattr(settings, "platform_credential_handoff_enabled", True)
    clock = [datetime.now(UTC).replace(microsecond=0)]
    monkeypatch.setattr(security, "utc_now", lambda: clock[0])
    operator, secret = configure_operator(db, "synthetic-owner", PASSWORD)
    db.commit()
    return SyntheticOwner((operator, secret, clock))


def headers(csrf="login"):
    return {"Origin": get_settings().allowed_origins[0], "X-Platform-CSRF": csrf}


def challenge(client):
    response = client.post(
        ROOT + "/auth/login",
        json={"username": "synthetic-owner", "password": PASSWORD},
        headers=headers(),
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def authenticate(client, platform_owner):
    csrf = challenge(client)
    response = client.post(
        ROOT + "/auth/mfa/verify",
        json={"code": pyotp.TOTP(platform_owner[1]).at(platform_owner[2][0])},
        headers=headers(csrf),
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_password_only_denied_and_cookie_separated(client, platform_owner, users):
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": "director-test", "password": TEST_PASSWORD},
        ).status_code
        == 200
    )
    assert client.get(ROOT + "/overview").status_code == 401
    response = client.post(
        ROOT + "/auth/login",
        json={"username": "synthetic-owner", "password": PASSWORD},
        headers=headers(),
    )
    cookie = response.headers["set-cookie"].lower()
    assert (
        "httponly" in cookie
        and "samesite=strict" in cookie
        and "path=/api/v1/platform" in cookie
    )
    for path in ("/auth/me", "/overview", "/organizations", "/audit"):
        assert client.get(ROOT + path).status_code == 401
    csrf = response.json()["csrf_token"]
    assert (
        client.post(ROOT + "/organizations", json={}, headers=headers(csrf)).status_code
        == 401
    )
    assert (
        client.post(
            ROOT + "/auth/mfa/verify",
            json={"code": pyotp.TOTP(platform_owner[1]).at(platform_owner[2][0])},
            headers=headers(csrf),
        ).status_code
        == 200
    )
    client.cookies.delete(
        "smart_garden_session", domain="testserver.local", path="/api/v1"
    )
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.get(ROOT + "/auth/me").json()["role"] == "PLATFORM_OWNER"


def test_csrf_origin_content_type_and_session_binding(client, platform_owner):
    payload = {"username": "synthetic-owner", "password": PASSWORD}
    for request_headers in (
        {},
        {"Origin": "https://foreign.invalid", "X-Platform-CSRF": "login"},
        headers("wrong"),
    ):
        assert (
            client.post(
                ROOT + "/auth/login", json=payload, headers=request_headers
            ).status_code
            == 403
        )
    assert (
        client.post(ROOT + "/auth/login", data=payload, headers=headers()).status_code
        == 400
    )
    old_csrf = challenge(client)
    csrf = authenticate(client, platform_owner)
    for value in ("", "wrong", old_csrf):
        assert (
            client.post(
                ROOT + "/auth/logout", json={}, headers=headers(value)
            ).status_code
            == 403
        )
    assert client.get(ROOT + "/auth/me").headers["cache-control"] == "no-store"
    assert (
        client.post(ROOT + "/auth/logout", json={}, headers=headers(csrf)).status_code
        == 200
    )
    assert client.get(ROOT + "/auth/me").status_code == 401


def test_otp_replay_lockout_not_reset_by_password(client, platform_owner):
    authenticate(client, platform_owner)
    for _ in range(5):
        csrf = challenge(client)
        assert (
            client.post(
                ROOT + "/auth/mfa/verify",
                json={"code": pyotp.TOTP(platform_owner[1]).at(platform_owner[2][0])},
                headers=headers(csrf),
            ).status_code
            == 401
        )
    assert (
        client.post(
            ROOT + "/auth/login",
            json={"username": "synthetic-owner", "password": PASSWORD},
            headers=headers(),
        ).status_code
        == 401
    )
    assert platform_owner[0].failed_attempts == 5


def test_ip_rate_limit_for_unknown_accounts(client, platform_owner):
    for _ in range(20):
        assert (
            client.post(
                ROOT + "/auth/login",
                json={"username": "absent-owner", "password": PASSWORD},
                headers=headers(),
            ).status_code
            == 401
        )
    assert (
        client.post(
            ROOT + "/auth/login",
            json={"username": "absent-owner", "password": PASSWORD},
            headers=headers(),
        ).status_code
        == 429
    )


def test_expiry_recovery_and_encryption(client, platform_owner, db):
    operator, secret, clock = platform_owner
    csrf = authenticate(client, platform_owner)
    assert secret not in operator.totp_secret_ciphertext
    _, rotated = configure_operator(db, operator.username, PASSWORD, recover=True)
    db.commit()
    assert rotated != secret
    assert client.get(ROOT + "/overview").status_code == 401
    assert (
        db.scalar(
            select(PlatformSession).where(PlatformSession.revoked_at.is_not(None))
        )
        is not None
    )
    csrf = challenge(client)
    assert (
        client.post(
            ROOT + "/auth/mfa/verify",
            json={"code": pyotp.TOTP(rotated).at(clock[0])},
            headers=headers(csrf),
        ).status_code
        == 200
    )
    clock[0] += timedelta(seconds=get_settings().platform_session_ttl_seconds + 1)
    assert client.get(ROOT + "/overview").status_code == 401


def test_missing_key_fails_closed(client, monkeypatch):
    monkeypatch.setattr(get_settings(), "platform_encryption_key", None)
    assert client.get(ROOT + "/overview").status_code == 503
    assert (
        client.post(
            ROOT + "/auth/login",
            json={"username": "synthetic-owner", "password": PASSWORD},
            headers=headers(),
        ).status_code
        == 503
    )


def test_challenge_expiry_blocked_operator_and_secure_cookie(
    client, platform_owner, db, monkeypatch
):
    csrf = challenge(client)
    platform_owner[2][0] += timedelta(minutes=6)
    assert (
        client.post(
            ROOT + "/auth/mfa/verify",
            json={"code": pyotp.TOTP(platform_owner[1]).at(platform_owner[2][0])},
            headers=headers(csrf),
        ).status_code
        == 401
    )
    authenticate(client, platform_owner)
    platform_owner[0].status = "blocked"
    db.flush()
    assert client.get(ROOT + "/overview").status_code == 401
    platform_owner[0].status = "active"
    db.flush()
    monkeypatch.setattr(get_settings(), "app_env", "production")
    response = client.post(
        ROOT + "/auth/login",
        json={"username": "synthetic-owner", "password": PASSWORD},
        headers=headers(),
    )
    assert "secure" in response.headers["set-cookie"].lower()


def test_one_time_handoff_absent_from_public_tenant_docs(client, platform_owner):
    specification = client.get("/openapi.json").json()
    assert "temporary_password" not in str(specification)
    assert "post" not in specification["paths"][ROOT + "/organizations"]


def test_bounded_retention_preserves_live_rate_sessions_tenant_auth_and_audit(
    client, platform_owner, db, users
):
    from app.core.security import generate_session_token, hash_session_token
    from app.models.auth_session import AuthSession
    from app.models.platform_audit_event import PlatformAuditEvent
    from app.services.platform_auth import cleanup_expired_sessions

    now = platform_owner[2][0]
    operator_id = platform_owner[0].id
    stale = [
        PlatformSession(purpose="login_attempt", expires_at=now - timedelta(seconds=1)),
        PlatformSession(operator_id=operator_id, expires_at=now - timedelta(seconds=1)),
        PlatformSession(
            operator_id=operator_id,
            expires_at=now - timedelta(seconds=1),
            mfa_verified_at=now - timedelta(hours=2),
        ),
        PlatformSession(
            operator_id=operator_id, expires_at=now + timedelta(hours=1), revoked_at=now
        ),
    ]
    live = [
        PlatformSession(
            purpose="login_attempt", expires_at=now + timedelta(minutes=15)
        ),
        PlatformSession(operator_id=operator_id, expires_at=now + timedelta(minutes=5)),
        PlatformSession(
            operator_id=operator_id,
            expires_at=now + timedelta(hours=1),
            mfa_verified_at=now,
        ),
    ]
    for row in stale + live:
        row.token_hash = hash_session_token(generate_session_token())
        row.ip_hash = "synthetic-ip-hash"
        row.created_at = now
        db.add(row)
    tenant_session = AuthSession(
        user_id=users[2].id,
        token_hash=hash_session_token(generate_session_token()),
        expires_at=now - timedelta(hours=1),
    )
    db.add(tenant_session)
    db.commit()
    stale_ids = [row.id for row in stale]
    live_ids = [row.id for row in live]
    audit_ids = list(db.scalars(select(PlatformAuditEvent.id)))
    assert cleanup_expired_sessions(db, batch_size=2) == 2
    db.commit()
    assert sum(db.get(PlatformSession, row_id) is not None for row_id in stale_ids) == 2
    assert cleanup_expired_sessions(db, batch_size=2) == 2
    db.commit()
    assert cleanup_expired_sessions(db, batch_size=2) == 0
    assert all(db.get(PlatformSession, row_id) is not None for row_id in live_ids)
    assert db.get(AuthSession, tenant_session.id) is not None
    assert list(db.scalars(select(PlatformAuditEvent.id))) == audit_ids
    # Login automatically sweeps stale rows even if a scheduler is absent.
    expired = PlatformSession(
        purpose="login_attempt",
        token_hash=hash_session_token(generate_session_token()),
        ip_hash="synthetic-ip-hash",
        created_at=now - timedelta(hours=1),
        expires_at=now - timedelta(minutes=45),
    )
    db.add(expired)
    db.commit()
    expired_id = expired.id
    challenge(client)
    assert db.get(PlatformSession, expired_id) is None


def test_session_removed_between_identity_reads_returns_unauthorized(
    platform_owner, db, monkeypatch
):
    from uuid import uuid4

    from app.core.errors import AppError
    from app.services.platform_auth import session_identity

    row = PlatformSession(id=uuid4(), operator_id=platform_owner[0].id)
    results = iter([row, platform_owner[0], None])
    monkeypatch.setattr(db, "scalar", lambda _query: next(results))
    with pytest.raises(AppError) as error:
        session_identity(db, "a" * 64)
    assert error.value.status == 401


def test_cleanup_and_expired_authenticate_do_not_deadlock(platform_owner):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from sqlalchemy import delete, event
    from sqlalchemy.orm import Session

    from app.core.errors import AppError
    from app.core.security import generate_session_token, hash_session_token
    from app.models.platform_audit_event import PlatformAuditEvent
    from app.models.platform_operator import PlatformOperator
    from app.services import platform_auth

    raw = generate_session_token()
    now = platform_owner[2][0]
    with Session(engine) as seed:
        operator, _ = configure_operator(seed, "retention-race-owner", PASSWORD)
        operator_id = operator.id
        seed.add(
            PlatformSession(
                operator_id=operator_id,
                token_hash=hash_session_token(raw),
                ip_hash="synthetic-race",
                expires_at=now - timedelta(seconds=1),
            )
        )
        seed.commit()
    removed, operator_locked = Event(), Event()

    def interleave(
        _connection, _cursor, statement, _parameters, _context, _executemany
    ):
        if statement.startswith("DELETE FROM platform_sessions"):
            removed.set()
            assert operator_locked.wait(10)
        elif "FROM platform_operators" in statement and "FOR UPDATE" in statement:
            operator_locked.set()

    event.listen(engine, "after_cursor_execute", interleave)
    try:

        def expired_identity():
            assert removed.wait(10)
            with Session(engine) as db:
                with pytest.raises(AppError) as error:
                    platform_auth.session_identity(db, raw)
                assert error.value.status == 401

        def password_login():
            with Session(engine) as db:
                return platform_auth.password_login(
                    db, "retention-race-owner", PASSWORD, "synthetic-race-address"
                )

        with ThreadPoolExecutor(max_workers=2) as pool:
            identity = pool.submit(expired_identity)
            login = pool.submit(password_login)
            identity.result(timeout=15)
            assert login.result(timeout=15)
    finally:
        event.remove(engine, "after_cursor_execute", interleave)
        with Session(engine) as cleanup:
            cleanup.execute(
                delete(PlatformSession).where(
                    (PlatformSession.operator_id == operator_id)
                    | (
                        PlatformSession.ip_hash
                        == security.digest_context(
                            "platform-login-ip:synthetic-race-address"
                        )
                    )
                )
            )
            cleanup.execute(
                delete(PlatformAuditEvent).where(
                    PlatformAuditEvent.operator_id == operator_id
                )
            )
            cleanup.execute(
                delete(PlatformOperator).where(PlatformOperator.id == operator_id)
            )
            cleanup.commit()

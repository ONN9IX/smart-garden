"""Synthetic PostgreSQL checks for the independent platform authentication boundary."""

from datetime import UTC, datetime, timedelta

import pyotp
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from app.core import platform_security as security
from app.core.config import get_settings
from app.models.platform_session import PlatformSession
from app.services.platform_bootstrap import configure_operator
from tests.conftest import TEST_PASSWORD

PASSWORD = "synthetic-owner-password-221"
ROOT = "/api/v1/platform"


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
    return operator, secret, clock


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
    assert (
        db.scalar(
            select(PlatformSession).where(PlatformSession.revoked_at.is_not(None))
        )
        is not None
    )


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

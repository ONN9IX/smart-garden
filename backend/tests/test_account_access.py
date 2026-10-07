"""Delivery C secure account access integration coverage."""

from datetime import timedelta
from threading import Barrier, Thread

import pytest
from sqlalchemy import select

from app.core.errors import AppError
from app.core.security import hash_password, verify_password
from app.db.session import SessionLocal
from app.models.account_access_token import AccountAccessToken
from app.models.auth_session import AuthSession
from app.models.employee import Employee
from app.models.guardian import Guardian
from app.models.organization import Organization
from app.models.user import User
from app.services import account_access, email_delivery
from app.services.auth import utc_now
from tests.conftest import TEST_PASSWORD


def _director(client, users):
    users[2].must_change_password = False
    response = client.post("/api/v1/auth/login", json={"username": "director-test", "password": TEST_PASSWORD})
    assert response.status_code == 200


def _fake(monkeypatch):
    sender = email_delivery.InMemoryEmailSender([])
    monkeypatch.setattr(email_delivery, "get_email_sender", lambda: sender)
    return sender


def _raw(sender):
    return sender.messages[-1]["text"].split("#token=", 1)[1].splitlines()[0]


def test_parent_invite_is_digest_only_one_time_and_resend_revokes(client, db, users, monkeypatch):
    sender = _fake(monkeypatch)
    _director(client, users)
    guardian = client.post("/api/v1/guardians", json={
        "first_name": "Ирина", "last_name": "Тестова", "email": "parent@example.test",
    }).json()
    created = client.post(f"/api/v1/guardians/{guardian['id']}/account")
    assert created.status_code == 201 and created.json()["status"] == "sent"
    assert "password" not in str(created.json()).lower()
    raw = _raw(sender)
    grant = db.scalar(select(AccountAccessToken).where(AccountAccessToken.user_id == db.get(Guardian, guardian["id"]).user_id))
    assert grant.token_digest != raw and raw not in grant.token_digest
    assert grant.guardian_id is not None and grant.employee_id is None
    old_hash = db.get(User, grant.user_id).password_hash

    resent = client.post(f"/api/v1/guardians/{guardian['id']}/account/resend")
    assert resent.status_code == 200 and len(sender.messages) == 2
    assert grant.revoked_at is not None
    assert db.get(User, grant.user_id).password_hash != old_hash
    assert client.post("/api/v1/auth/activate", json={"token": raw, "new_password": "safe-parent-password-1"}).json()["error"]["code"] == "ACCESS_LINK_INVALID"
    current = _raw(sender)
    assert client.post("/api/v1/auth/activate", json={"token": current, "new_password": "safe-parent-password-1"}).status_code == 200
    assert client.post("/api/v1/auth/activate", json={"token": current, "new_password": "another-safe-password-1"}).json()["error"]["code"] == "ACCESS_LINK_INVALID"
    parent = db.get(User, grant.user_id)
    assert not parent.must_change_password and verify_password(parent.password_hash, "safe-parent-password-1")


def test_wrong_expired_revoked_purpose_and_cross_tenant_tokens_fail(client, db, users, monkeypatch):
    sender = _fake(monkeypatch)
    _director(client, users)
    guardian_id = client.post("/api/v1/guardians", json={"first_name": "А", "last_name": "Б", "email": "a@example.test"}).json()["id"]
    client.post(f"/api/v1/guardians/{guardian_id}/account")
    raw = _raw(sender)
    grant = db.scalar(select(AccountAccessToken).order_by(AccountAccessToken.created_at.desc()))
    assert client.post("/api/v1/auth/reset-password", json={"token": raw, "new_password": "valid-password-123"}).status_code == 400
    assert client.post("/api/v1/auth/activate", json={"token": "x" * 48, "new_password": "valid-password-123"}).status_code == 400
    grant.expires_at = utc_now() - timedelta(seconds=1); db.flush()
    assert client.post("/api/v1/auth/activate", json={"token": raw, "new_password": "valid-password-123"}).status_code == 400
    grant.expires_at = utc_now() + timedelta(hours=1); grant.revoked_at = utc_now(); db.flush()
    assert client.post("/api/v1/auth/activate", json={"token": raw, "new_password": "valid-password-123"}).status_code == 400
    grant.revoked_at = None; grant.organization_id = users[1].id; db.flush()
    assert client.post("/api/v1/auth/activate", json={"token": raw, "new_password": "valid-password-123"}).status_code == 400


def test_email_login_ambiguity_and_generic_forgot_response(client, db, users, monkeypatch):
    sender = _fake(monkeypatch)
    organization = users[0]
    accounts = []
    for suffix in ("one", "two"):
        account = User(organization_id=organization.id, username=f"parent-{suffix}", password_hash=hash_password("shared-password-123"), role="PARENT", status="active", must_change_password=False)
        db.add(account); db.flush()
        db.add(Guardian(organization_id=organization.id, user_id=account.id, first_name=suffix, last_name="Тест", email="same@example.test", status="active"))
        accounts.append(account)
    db.flush()
    ambiguous = client.post("/api/v1/auth/login", json={"username": "same@example.test", "password": "shared-password-123"})
    assert ambiguous.status_code == 401 and ambiguous.json()["error"]["code"] == "INVALID_CREDENTIALS"
    for identifier in ("missing@example.test", "same@example.test", "director-test"):
        response = client.post("/api/v1/auth/forgot-password", json={"identifier": identifier})
        assert response.status_code == 200
        assert response.json()["message"] == "Если аккаунт найден и для него доступно восстановление, мы отправили ссылку на email."
    assert sender.messages == []


def test_reset_revokes_sessions_and_blocked_remains_blocked(client, db, users, monkeypatch):
    sender = _fake(monkeypatch)
    organization = users[0]
    account = User(organization_id=organization.id, username="blocked-parent", password_hash=hash_password("old-password-12345"), role="PARENT", status="blocked", must_change_password=False)
    db.add(account); db.flush()
    guardian = Guardian(organization_id=organization.id, user_id=account.id, first_name="И", last_name="Б", email="blocked@example.test", status="active")
    db.add(guardian); db.flush()
    active_session = AuthSession(user_id=account.id, token_hash="1" * 64, expires_at=utc_now() + timedelta(hours=1))
    db.add(active_session); db.flush()
    response = client.post("/api/v1/auth/forgot-password", json={"identifier": "blocked-parent"})
    assert response.status_code == 200 and sender.messages
    raw = _raw(sender)
    assert client.post("/api/v1/auth/reset-password", json={"token": raw, "new_password": "new-password-12345"}).status_code == 200
    db.refresh(active_session)
    assert account.status == "blocked" and active_session.revoked_at is not None
    login = client.post("/api/v1/auth/login", json={"username": account.username, "password": "new-password-12345"})
    assert login.status_code == 403 and login.json()["error"]["code"] == "USER_BLOCKED"


def test_employee_invite_category_director_only_and_role_change_archives(client, db, users, monkeypatch):
    _fake(monkeypatch)
    _director(client, users)
    employee_id = client.post("/api/v1/employees", json={
        "first_name": "Пётр", "last_name": "Тестов", "position": "Воспитатель",
        "category": "teacher", "email": "teacher@example.test",
    }).json()["id"]
    invite = client.post(f"/api/v1/employees/{employee_id}/account", json={"role": "TEACHER"})
    assert invite.status_code == 201 and invite.json()["role"] == "TEACHER"
    employee = db.get(Employee, employee_id)
    assert employee.user_id and db.get(User, employee.user_id).role == "TEACHER"
    assert client.post(f"/api/v1/employees/{employee_id}/account", json={"role": "TEACHER"}).status_code == 201
    changed = client.post(f"/api/v1/employees/{employee_id}/account/role", json={"role": "ADMIN"})
    assert changed.status_code == 200 and db.get(User, employee.user_id).role == "ADMIN"
    assert employee.category == "teacher"


def test_competing_token_replacements_leave_only_newest_effective(migrations):
    """Real PostgreSQL row locking serializes competing writers across sessions."""
    with SessionLocal() as setup:
        organization = Organization(name="Конкурентный тест", status="active", timezone="Europe/Moscow")
        setup.add(organization); setup.flush()
        user = User(organization_id=organization.id, username=f"race-{organization.id}", password_hash=hash_password("old-password-12345"), role="PARENT", status="active", must_change_password=False)
        setup.add(user); setup.flush()
        guardian = Guardian(organization_id=organization.id, user_id=user.id, first_name="Тест", last_name="Конкуренция", email="race@example.test", status="active")
        setup.add(guardian); setup.commit()
        user_id, guardian_id = user.id, guardian.id

    barrier = Barrier(2)
    issued: list[str] = []
    def replace() -> None:
        with SessionLocal() as session:
            target = session.get(User, user_id)
            barrier.wait()
            _, raw = account_access._create_token(session, target, "password_reset", guardian_id=guardian_id)
            session.commit()
            issued.append(raw)

    threads = [Thread(target=replace), Thread(target=replace)]
    for thread in threads: thread.start()
    for thread in threads: thread.join(timeout=10)
    assert all(not thread.is_alive() for thread in threads) and len(issued) == 2

    with SessionLocal() as verify:
        grants = verify.scalars(select(AccountAccessToken).where(
            AccountAccessToken.user_id == user_id,
            AccountAccessToken.purpose == "password_reset",
        )).all()
        effective = [grant for grant in grants if grant.used_at is None and grant.revoked_at is None]
        assert len(grants) == 2 and len(effective) == 1
        effective_raw = next(raw for raw in issued if account_access.token_digest(raw) == effective[0].token_digest)
        stale_raw = next(raw for raw in issued if raw != effective_raw)
        account_access.complete_password_action(verify, effective_raw, "new-password-12345", "password_reset")
        with pytest.raises(AppError) as error:
            account_access.complete_password_action(verify, stale_raw, "other-password-12345", "password_reset")
        assert getattr(error.value, "code", None) == "ACCESS_LINK_INVALID"

"""Parent lifecycle and tenant isolation with synthetic PostgreSQL records."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import verify_password
from app.main import app
from app.models.auth_session import AuthSession
from app.models.guardian import Guardian
from app.models.user import User
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/guardians"


def _admin(client):
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200


def _guardian(client):
    response = client.post(ROOT, json={"first_name": "Ирина", "last_name": "Пример"})
    assert response.status_code == 201
    return response.json()["id"]


def _login(client, username, password):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_create_login_change_reset_and_block(client, db, users):
    _admin(client)
    guardian_id = _guardian(client)
    path = f"{ROOT}/{guardian_id}/account"
    created = client.post(path)
    assert created.status_code == 201
    credentials = created.json()
    account = credentials["account"]
    username, temporary = account["username"], credentials["temporary_password"]
    assert username.startswith("parent-") and "ирина" not in username.lower()
    assert account["must_change_password"] is True
    assert client.post(path).json()["error"]["code"] == "PARENT_ACCOUNT_ALREADY_EXISTS"
    detail = client.get(f"{ROOT}/{guardian_id}").json()
    assert detail["account"] == account and "temporary_password" not in str(detail)
    parent = db.scalar(select(User).where(User.username == username))
    assert parent is not None and parent.role == "PARENT"
    assert parent.password_hash != temporary and verify_password(parent.password_hash, temporary)

    with TestClient(app) as parent_client:
        response = _login(parent_client, username, temporary)
        assert response.status_code == 200 and response.json()["user"]["role"] == "PARENT"
        assert parent_client.get("/api/v1/auth/me").status_code == 200
        assert parent_client.get("/api/v1/groups").status_code == 403
        assert parent_client.get("/api/v1/children").status_code == 403
        assert parent_client.post(path).status_code == 403
        assert parent_client.get("/api/v1/guardians").status_code == 403
        assert parent_client.post("/api/v1/auth/change-password", json={"new_password": "parent-new-secure-1234"}).status_code == 200
        assert parent_client.get("/api/v1/auth/me").json()["user"]["must_change_password"] is False
        session_token = parent_client.cookies.get("smart_garden_session")
        assert parent_client.post("/api/v1/auth/logout").status_code == 200
        assert parent_client.get("/api/v1/auth/me").status_code == 401
        assert _login(parent_client, username, "parent-new-secure-1234").status_code == 200
        active_token = parent_client.cookies.get("smart_garden_session")

        reset = client.post(f"{path}/reset-password")
        assert reset.status_code == 200
        second_temporary = reset.json()["temporary_password"]
        assert second_temporary != temporary and reset.json()["account"]["must_change_password"]
        assert parent_client.get("/api/v1/auth/me").status_code == 401
        for token in (session_token, active_token):
            parent_client.cookies.set("smart_garden_session", token, path="/api/v1")
            assert parent_client.get("/api/v1/auth/me").status_code == 401
        assert _login(parent_client, username, "parent-new-secure-1234").status_code == 401
        assert _login(parent_client, username, second_temporary).status_code == 200
        assert client.post(f"{path}/block").json()["status"] == "blocked"
        assert client.post(f"{path}/block").status_code == 200
        assert parent_client.get("/api/v1/auth/me").status_code in (401, 403)
        assert _login(parent_client, username, second_temporary).json()["error"]["code"] == "USER_BLOCKED"
        assert client.post(f"{path}/reset-password").json()["account"]["status"] == "blocked"
        assert client.post(f"{path}/unblock").json()["status"] == "active"
        assert client.post(f"{path}/unblock").status_code == 200
        assert _login(parent_client, username, second_temporary).status_code == 401

    assert db.scalar(select(AuthSession).where(AuthSession.user_id == parent.id, AuthSession.revoked_at.is_(None))) is None


def test_archived_and_foreign_guardian_accounts(client, db, users):
    _, other, _, _ = users
    _admin(client)
    guardian_id = _guardian(client)
    path = f"{ROOT}/{guardian_id}/account"
    assert client.post(f"{ROOT}/{guardian_id}/archive").status_code == 200
    assert client.post(path).json()["error"]["code"] == "GUARDIAN_ARCHIVED"
    assert client.post(f"{ROOT}/{guardian_id}/restore").status_code == 200
    assert client.post(f"{path}/reset-password").json()["error"]["code"] == "PARENT_ACCOUNT_NOT_FOUND"
    username = client.post(path).json()["account"]["username"]
    assert client.post(f"{ROOT}/{guardian_id}/archive").json()["account"]["status"] == "blocked"
    assert client.post(f"{path}/unblock").json()["error"]["code"] == "GUARDIAN_ARCHIVED"
    assert client.post(f"{ROOT}/{guardian_id}/restore").json()["account"]["status"] == "blocked"
    assert client.post(f"{path}/unblock").json()["status"] == "active"
    assert db.scalar(select(User).where(User.username == username)).status == "active"

    foreign = Guardian(organization_id=other.id, first_name="Другой", last_name="Представитель", status="active")
    db.add(foreign)
    db.flush()
    for suffix in ("", "/reset-password", "/block", "/unblock"):
        response = client.post(f"{ROOT}/{foreign.id}/account{suffix}")
        assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"

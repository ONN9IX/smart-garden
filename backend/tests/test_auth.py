"""Real PostgreSQL checks for the frontend-facing Stage 1 auth contract."""

from datetime import timedelta
from typing import Annotated
from uuid import UUID

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.errors import AppError, app_error_handler
from app.core.permissions import require_role, require_tenant
from app.core.security import verify_password
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.services.auth import current_user, utc_now
from tests.conftest import TEST_PASSWORD


def login(client, username="director-test", password=TEST_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_health_and_openapi(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}
    spec = client.get("/openapi.json").json()
    for route in ("/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/auth/change-password", "/api/v1/auth/logout"):
        assert route in spec["paths"]


def test_login_cookie_and_me_match_frontend(client, users, db):
    organization, _, director, _ = users
    response = login(client)
    assert response.status_code == 200
    assert response.json() == {
        "user": {"id": str(director.id), "username": "director-test", "role": "DIRECTOR", "status": "active", "must_change_password": True},
        "organization": {"id": str(organization.id), "name": organization.name},
    }
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie
    assert client.get("/api/v1/auth/me").json() == response.json()
    session = db.scalar(select(AuthSession).where(AuthSession.user_id == director.id))
    assert session and session.token_hash != client.cookies.get("smart_garden_session")
    assert "password_hash" not in str(response.json())


def test_wrong_and_unknown_credentials_indistinguishable(client, users):
    wrong = login(client, password="not-the-password")
    unknown = login(client, username="absent-test")
    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json() == unknown.json()
    assert wrong.json()["error"]["code"] == "INVALID_CREDENTIALS"


def test_user_and_organization_blocking(client, users, db):
    organization, _, director, _ = users
    director.status = "blocked"
    db.flush()
    assert login(client).json()["error"]["code"] == "USER_BLOCKED"
    director.status = "active"
    organization.status = "blocked"
    db.flush()
    assert login(client).json()["error"]["code"] == "ORGANIZATION_BLOCKED"
    organization.status = "active"
    db.flush()
    assert login(client).status_code == 200
    organization.status = "blocked"
    db.flush()
    assert client.get("/api/v1/auth/me").status_code == 403


def test_mandatory_password_change_rotates_all_sessions(client, users, db):
    _, _, director, _ = users
    assert login(client).status_code == 200
    old_token = client.cookies.get("smart_garden_session")
    assert login(client).status_code == 200
    second_token = client.cookies.get("smart_garden_session")
    assert old_token != second_token
    new_password = "new-secure-password-456"
    changed = client.post("/api/v1/auth/change-password", json={"new_password": new_password})
    assert changed.status_code == 200
    assert changed.json() == {"success": True, "must_change_password": False}
    new_token = client.cookies.get("smart_garden_session")
    assert new_token not in {old_token, second_token}
    assert client.get("/api/v1/auth/me").json()["user"]["must_change_password"] is False
    assert not verify_password(director.password_hash, TEST_PASSWORD)
    assert login(client, password=TEST_PASSWORD).status_code == 401
    assert login(client, password=new_password).status_code == 200
    client.cookies.set("smart_garden_session", old_token, path="/api/v1")
    assert client.get("/api/v1/auth/me").status_code == 401
    client.cookies.set("smart_garden_session", second_token, path="/api/v1")
    assert client.get("/api/v1/auth/me").status_code == 401
    assert db.scalar(select(AuthSession).where(AuthSession.user_id == director.id, AuthSession.revoked_at.is_(None))) is not None


def test_change_password_validation_and_regular_user_forbidden(client, users):
    assert login(client).status_code == 200
    for password in ("short", TEST_PASSWORD):
        result = client.post("/api/v1/auth/change-password", json={"new_password": password})
        assert result.status_code == 400
        assert result.json()["error"]["code"] == "INVALID_PASSWORD"
    assert login(client, "admin-test").status_code == 200
    result = client.post("/api/v1/auth/change-password", json={"new_password": "new-password-12345"})
    assert result.status_code == 403


def test_logout_and_expired_or_revoked_session(client, users, db):
    assert login(client).status_code == 200
    token = client.cookies.get("smart_garden_session")
    response = client.post("/api/v1/auth/logout")
    assert response.json() == {"success": True}
    assert "max-age=0" in response.headers["set-cookie"].lower()
    client.cookies.set("smart_garden_session", token, path="/api/v1")
    assert client.get("/api/v1/auth/me").status_code == 401
    assert login(client).status_code == 200
    session = db.scalars(select(AuthSession).where(AuthSession.revoked_at.is_(None))).first()
    session.expires_at = utc_now() - timedelta(seconds=1)
    db.flush()
    assert client.get("/api/v1/auth/me").status_code == 401


def test_role_and_tenant_guards(client, users, db):
    organization, other, director, admin = users
    assert client.get("/api/v1/auth/me").status_code == 401
    assert require_role("DIRECTOR")(director) is director
    with pytest.raises(AppError) as forbidden:
        require_role("DIRECTOR")(admin)
    assert forbidden.value.status == 403
    require_tenant(director, organization.id)
    with pytest.raises(AppError) as hidden:
        require_tenant(director, other.id)
    assert hidden.value.status == 404
    assert hidden.value.code == "NOT_FOUND"

    # Exercise the guards through HTTP on temporary test-only routes.
    protected = FastAPI()
    protected.add_exception_handler(AppError, app_error_handler)
    protected.dependency_overrides[get_db] = lambda: db

    @protected.get("/organizations/{organization_id}")
    def tenant_resource(organization_id: UUID, user: Annotated[User, Depends(current_user)]):
        require_tenant(user, organization_id)
        return {"organization_id": str(organization_id)}

    @protected.get("/director")
    def director_resource(_user: Annotated[User, Depends(require_role("DIRECTOR"))]):
        return {"ok": True}

    assert login(client).status_code == 200
    director_cookie = {"Cookie": f"smart_garden_session={client.cookies.get('smart_garden_session')}"}
    with TestClient(protected) as test_client:
        missing = test_client.get(f"/organizations/{other.id}", headers=director_cookie)
        assert missing.status_code == 403  # temporary password blocks all business endpoints
        assert missing.json()["error"]["code"] == "PASSWORD_CHANGE_REQUIRED"
        assert other.name not in str(missing.json())

    assert login(client, "admin-test").status_code == 200
    admin_cookie = {"Cookie": f"smart_garden_session={client.cookies.get('smart_garden_session')}"}
    with TestClient(protected) as test_client:
        forbidden_response = test_client.get("/director", headers=admin_cookie)
        assert forbidden_response.status_code == 403
        hidden_response = test_client.get(f"/organizations/{other.id}", headers=admin_cookie)
        assert hidden_response.status_code == 404
        assert other.name not in str(hidden_response.json())
        assert test_client.get(f"/organizations/{organization.id}", headers=admin_cookie).status_code == 200


def test_validation_origin_and_password_not_in_logs(client, users, caplog):
    assert client.post("/api/v1/auth/login", json={"password": TEST_PASSWORD}).status_code == 400
    response = client.post("/api/v1/auth/login", json={"username": "director-test", "password": TEST_PASSWORD}, headers={"Origin": "https://untrusted.example"})
    assert response.status_code == 403
    assert login(client).status_code == 200
    assert TEST_PASSWORD not in caplog.text


def test_password_hash_and_user_ids_are_isolated(client, users, db):
    _, other, director, _ = users
    assert director.password_hash.startswith("$argon2id$")
    assert TEST_PASSWORD not in director.password_hash
    assert login(client).status_code == 200
    assert str(other.id) not in str(client.get("/api/v1/auth/me").json())

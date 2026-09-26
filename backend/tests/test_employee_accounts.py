"""Director-only ADMIN access, one-time credentials and atomic revocation."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import verify_password
from app.main import app
from app.models.employee import Employee
from app.models.user import User
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/employees"


def _director(client, users):
    users[2].must_change_password = False
    assert client.post("/api/v1/auth/login", json={"username": "director-test", "password": TEST_PASSWORD}).status_code == 200


def _employee(client):
    response = client.post(ROOT, json={"first_name": "Ирина", "last_name": "Пример", "position": "Администратор"})
    assert response.status_code == 201
    return response.json()["id"]


def test_account_lifecycle(client, db, users):
    _director(client, users)
    employee_id = _employee(client)
    path = f"{ROOT}/{employee_id}/account"
    created = client.post(path)
    assert created.status_code == 201
    username = created.json()["account"]["username"]
    temporary = created.json()["temporary_password"]
    assert username.startswith("staff-")
    assert created.json()["account"]["role"] == "ADMIN"
    assert client.post(path).json()["error"]["code"] == "EMPLOYEE_ACCOUNT_ALREADY_EXISTS"
    detail = client.get(f"{ROOT}/{employee_id}").json()
    assert detail["account"] == created.json()["account"]
    assert "temporary_password" not in str(detail)
    account = db.scalar(select(User).where(User.username == username))
    assert account.role == "ADMIN" and verify_password(account.password_hash, temporary)

    with TestClient(app) as staff:
        assert staff.post("/api/v1/auth/login", json={"username": username, "password": temporary}).status_code == 200
        assert staff.get(ROOT).status_code == 403
        assert staff.post(path).status_code == 403
        assert staff.post("/api/v1/auth/change-password", json={"new_password": "staff-new-secure-1234"}).status_code == 200
        assert staff.get(ROOT).status_code == 200
        assert staff.post(path + "/block").status_code == 403
        reset = client.post(path + "/reset-password")
        assert reset.status_code == 200
        second = reset.json()["temporary_password"]
        assert staff.get("/api/v1/auth/me").status_code == 401
        assert staff.post("/api/v1/auth/login", json={"username": username, "password": "staff-new-secure-1234"}).status_code == 401
        assert staff.post("/api/v1/auth/login", json={"username": username, "password": second}).status_code == 200
        assert client.post(path + "/block").json()["status"] == "blocked"
        assert staff.get("/api/v1/auth/me").status_code in (401, 403)
        assert staff.post("/api/v1/auth/login", json={"username": username, "password": second}).json()["error"]["code"] == "USER_BLOCKED"
        assert client.post(path + "/unblock").json()["status"] == "active"
        assert staff.post("/api/v1/auth/login", json={"username": username, "password": second}).status_code == 200
        assert client.post(f"{ROOT}/{employee_id}/archive").json()["account"]["status"] == "blocked"
        assert staff.get("/api/v1/auth/me").status_code in (401, 403)
    assert client.post(path + "/unblock").json()["error"]["code"] == "EMPLOYEE_ARCHIVED"
    assert client.post(f"{ROOT}/{employee_id}/restore").json()["account"]["status"] == "blocked"


def test_archived_missing_and_foreign_accounts(client, db, users):
    _, other, _, _ = users
    _director(client, users)
    employee_id = _employee(client)
    path = f"{ROOT}/{employee_id}/account"
    assert client.post(path + "/reset-password").json()["error"]["code"] == "EMPLOYEE_ACCOUNT_NOT_FOUND"
    assert client.post(f"{ROOT}/{employee_id}/archive").status_code == 200
    assert client.post(path).json()["error"]["code"] == "EMPLOYEE_ARCHIVED"
    foreign = Employee(organization_id=other.id, first_name="Другой", last_name="Работник", position="Сотрудник", status="active")
    db.add(foreign)
    db.flush()
    for suffix in ("", "/reset-password", "/block", "/unblock"):
        response = client.post(f"{ROOT}/{foreign.id}/account{suffix}")
        assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"

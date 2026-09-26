"""Employee HTTP lifecycle, account archiving rights and two-tenant isolation."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.security import hash_password
from app.main import app
from app.models.auth_session import AuthSession
from app.models.employee import Employee
from app.models.guardian import Guardian
from app.models.user import User
from app.services.auth import issue_session
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/employees"


def _login(client, username="admin-test"):
    assert client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}).status_code == 200


def test_employee_crud_archive_and_validation(client, users):
    _, other, _, _ = users
    _login(client)
    response = client.post(ROOT, json={
        "first_name": " Анна ", "last_name": " Тестовая ", "middle_name": " ", "position": " Воспитатель ",
    })
    assert response.status_code == 201
    employee = response.json()
    assert employee["first_name"] == "Анна" and employee["middle_name"] is None
    assert employee["position"] == "Воспитатель" and employee["account"] is None
    assert "organization_id" not in employee and "user_id" not in employee
    path = f"{ROOT}/{employee['id']}"
    assert client.post(ROOT, json={"first_name": "Тест", "last_name": "Тест", "position": "Сотрудник", "organization_id": str(other.id)}).status_code == 400
    assert client.patch(path, json={}).status_code == 400
    assert client.patch(path, json={"position": None}).status_code == 400
    assert client.patch(path, json={"position": " Помощник "}).json()["position"] == "Помощник"
    assert [item["id"] for item in client.get(f"{ROOT}?q=анна").json()["items"]] == [employee["id"]]
    assert client.post(f"{path}/archive").json()["status"] == "archived"
    assert client.post(f"{path}/archive").status_code == 200
    assert client.get(ROOT).json()["items"] == []
    assert len(client.get(f"{ROOT}?status=archived").json()["items"]) == 1
    assert client.post(f"{path}/restore").json()["status"] == "active"
    assert client.get(path).json()["status"] == "active"


def test_director_blocks_linked_admin_atomically_and_admin_cannot_archive(client, db, users):
    organization, _, director, admin = users
    director.must_change_password = False
    db.flush()
    _login(client)
    employee = Employee(
        organization_id=organization.id, user_id=admin.id,
        first_name="Тестовый", last_name="Администратор", position="Администратор", status="active",
    )
    db.add(employee)
    db.flush()
    token = issue_session(db, admin)
    db.flush()
    path = f"{ROOT}/{employee.id}"
    assert client.post(f"{path}/archive").status_code == 403
    assert employee.status == "active" and admin.status == "active"

    with TestClient(app) as director_client:
        _login(director_client, "director-test")
        archived = director_client.post(f"{path}/archive")
        assert archived.status_code == 200
        assert archived.json()["account"]["status"] == "blocked"
        assert admin.status == "blocked"
        session = db.scalar(select(AuthSession).where(AuthSession.user_id == admin.id, AuthSession.revoked_at.is_not(None)))
        assert session is not None and token
        restored = director_client.post(f"{path}/restore")
        assert restored.json()["account"]["status"] == "blocked"
        assert admin.status == "blocked"


def test_employee_foreign_tenant_and_parent_denied(client, db, users):
    organization, other, _, _ = users
    _login(client)
    foreign = Employee(
        organization_id=other.id, first_name="Чужой", last_name="Сотрудник", position="Помощник", status="active",
    )
    db.add(foreign)
    db.flush()
    for method, suffix, body in (("get", "", None), ("patch", "", {"position": "Чужой"}), ("post", "/archive", None)):
        response = getattr(client, method)(f"{ROOT}/{foreign.id}{suffix}", json=body) if body else getattr(client, method)(f"{ROOT}/{foreign.id}{suffix}")
        assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"
    assert client.get(ROOT).json()["items"] == []

    parent = User(
        organization_id=organization.id, username="parent-employee-test", role="PARENT",
        status="active", password_hash=hash_password(TEST_PASSWORD), must_change_password=False,
    )
    db.add(parent)
    db.flush()
    db.add(Guardian(
        organization_id=organization.id, user_id=parent.id,
        first_name="Тестовый", last_name="Представитель", status="active",
    ))
    db.flush()
    token = issue_session(db, parent)
    db.flush()
    client.cookies.set("smart_garden_session", token, path="/api/v1")
    assert client.get(ROOT).status_code == 403
    assert client.post(ROOT, json={"first_name": "Тест", "last_name": "Тест", "position": "Тест"}).status_code == 403


def test_employee_openapi_and_forbidden_fields(client):
    spec = client.get("/openapi.json").json()
    for route in ("/api/v1/employees", "/api/v1/employees/{employee_id}", "/api/v1/employees/{employee_id}/archive", "/api/v1/employees/{employee_id}/restore"):
        assert route in spec["paths"]
        for operation in spec["paths"][route].values():
            assert "403" in operation["responses"] and "404" in operation["responses"]
    for name in ("EmployeeCreate", "EmployeePatch"):
        assert {"organization_id", "user_id", "role", "password_hash"}.isdisjoint(spec["components"]["schemas"][name]["properties"])

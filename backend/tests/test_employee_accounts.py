"""Director-only secure employee account lifecycle."""

from app.models.employee import Employee
from app.models.user import User
from app.services import email_delivery
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/employees"


def _director(client, users):
    users[2].must_change_password = False
    assert client.post("/api/v1/auth/login", json={"username": "director-test", "password": TEST_PASSWORD}).status_code == 200


def test_employee_invite_no_duplicate_and_access_controls(client, db, users, monkeypatch):
    sender = email_delivery.InMemoryEmailSender([])
    monkeypatch.setattr(email_delivery, "get_email_sender", lambda: sender)
    _director(client, users)
    employee_id = client.post(ROOT, json={"first_name": "Ирина", "last_name": "Пример", "position": "Администратор", "category": "administrator", "email": "admin@example.test"}).json()["id"]
    path = f"{ROOT}/{employee_id}/account"
    created = client.post(path, json={"role": "ADMIN"})
    assert created.status_code == 201 and created.json()["status"] == "sent"
    account_id = db.get(Employee, employee_id).user_id
    assert account_id and db.get(User, account_id).role == "ADMIN"
    assert client.post(path + "/resend", json={"role": "ADMIN"}).status_code == 200
    assert db.get(Employee, employee_id).user_id == account_id and len(sender.messages) == 2
    assert client.post(path + "/block").json()["status"] == "blocked"
    assert client.post(path + "/unblock").json()["status"] == "active"


def test_category_archived_and_foreign_rejected(client, db, users):
    _director(client, users)
    employee_id = client.post(ROOT, json={"first_name": "И", "last_name": "П", "position": "Сотрудник", "category": "other", "email": "other@example.test"}).json()["id"]
    assert client.post(f"{ROOT}/{employee_id}/account", json={"role": "ADMIN"}).json()["error"]["code"] == "EMPLOYEE_CATEGORY_CONFLICT"
    assert client.post(f"{ROOT}/{employee_id}/archive").status_code == 200
    assert client.post(f"{ROOT}/{employee_id}/account", json={"role": "ADMIN"}).json()["error"]["code"] == "EMPLOYEE_ARCHIVED"
    foreign = Employee(organization_id=users[1].id, first_name="Другой", last_name="Работник", position="Админ", category="administrator", email="foreign@example.test", status="active")
    db.add(foreign); db.flush()
    assert client.post(f"{ROOT}/{foreign.id}/account", json={"role": "ADMIN"}).status_code == 404

"""Secure parent invitation lifecycle and tenant isolation."""

from sqlalchemy import select

from app.models.guardian import Guardian
from app.models.user import User
from app.services import email_delivery
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/guardians"


def _admin(client):
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200


def test_invite_resend_block_and_unblock(client, db, users, monkeypatch):
    sender = email_delivery.InMemoryEmailSender([])
    monkeypatch.setattr(email_delivery, "get_email_sender", lambda: sender)
    _admin(client)
    guardian_id = client.post(ROOT, json={"first_name": "Ирина", "last_name": "Пример", "email": "parent@example.test"}).json()["id"]
    path = f"{ROOT}/{guardian_id}/account"
    created = client.post(path)
    assert created.status_code == 201 and created.json()["status"] == "sent"
    assert "password" not in created.text.lower()
    username = created.json()["username"]
    parent = db.scalar(select(User).where(User.username == username))
    assert parent and db.get(Guardian, guardian_id).user_id == parent.id
    assert client.post(path + "/resend").status_code == 200
    assert len(sender.messages) == 2
    assert client.post(path + "/block").json()["status"] == "blocked"
    assert client.post(path + "/unblock").json()["status"] == "active"


def test_archived_missing_email_and_foreign_rejected(client, db, users):
    _admin(client)
    guardian_id = client.post(ROOT, json={"first_name": "И", "last_name": "П"}).json()["id"]
    assert client.post(f"{ROOT}/{guardian_id}/account").json()["error"]["code"] == "ACCOUNT_EMAIL_REQUIRED"
    assert client.post(f"{ROOT}/{guardian_id}/archive").status_code == 200
    assert client.post(f"{ROOT}/{guardian_id}/account").json()["error"]["code"] == "GUARDIAN_ARCHIVED"
    foreign = Guardian(organization_id=users[1].id, first_name="Другой", last_name="Представитель", email="foreign@example.test", status="active")
    db.add(foreign); db.flush()
    assert client.post(f"{ROOT}/{foreign.id}/account").status_code == 404

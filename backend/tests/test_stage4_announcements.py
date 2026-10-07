"""Stage 4 Announcement API, lifecycle, RBAC, tenant and Audit privacy."""

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.security import hash_password
from app.main import app
from app.models.announcement import Announcement
from app.models.audit_event import AuditEvent
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.user import User
from app.services import audit

from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/announcements"


def _login(client, username: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200


def _director(client, db, users) -> None:
    users[2].must_change_password = False
    db.flush()
    _login(client, users[2].username)


def test_announcement_lifecycle_filters_and_private_audit(client, db, users):
    _director(client, db, users)
    group = client.post("/api/v1/groups", json={"name": "Синтетическая группа объявлений"}).json()
    first_title, first_body = "  Синтетическое объявление  ", "  Только синтетический текст  "
    whole = client.post(ROOT, json={
        "target_type": "all", "group_id": None, "title": first_title, "body": first_body,
    })
    assert whole.status_code == 201, whole.text
    assert whole.json()["title"] == first_title.strip()
    assert whole.json()["body"] == first_body.strip()
    assert whole.json()["group"] is None and whole.json()["status"] == "active"
    assert "organization_id" not in whole.text

    group_item = client.post(ROOT, json={
        "target_type": "group", "group_id": group["id"],
        "title": "Групповое синтетическое", "body": "Синтетический текст для группы",
    })
    assert group_item.status_code == 201
    item_id = group_item.json()["id"]
    assert group_item.json()["group"] == {"id": group["id"], "name": group["name"]}

    assert len(client.get(ROOT).json()["items"]) == 2
    assert [item["id"] for item in client.get(ROOT, params={"target_type": "group"}).json()["items"]] == [item_id]
    assert [item["id"] for item in client.get(ROOT, params={"group_id": group["id"]}).json()["items"]] == [item_id]
    assert client.get(f"{ROOT}/{item_id}").status_code == 200

    changed_title, changed_body = "Новый закрытый заголовок", "Новый закрытый текст"
    updated = client.patch(f"{ROOT}/{item_id}", json={
        "target_type": "all", "title": changed_title, "body": changed_body,
    })
    assert updated.status_code == 200, updated.text
    assert updated.json()["group"] is None and updated.json()["target_type"] == "all"

    archived = client.post(f"{ROOT}/{item_id}/archive")
    assert archived.status_code == 200 and archived.json()["status"] == "archived"
    archived_at = archived.json()["archived_at"]
    repeated = client.post(f"{ROOT}/{item_id}/archive")
    assert repeated.status_code == 200 and repeated.json()["archived_at"] == archived_at
    denied = client.patch(f"{ROOT}/{item_id}", json={"title": "Запрещённое изменение"})
    assert denied.status_code == 409
    assert denied.json()["error"]["code"] == "ANNOUNCEMENT_ARCHIVED"
    assert item_id not in {item["id"] for item in client.get(ROOT).json()["items"]}
    assert item_id in {item["id"] for item in client.get(ROOT, params={"status": "archived"}).json()["items"]}

    events = list(db.scalars(select(AuditEvent).where(
        AuditEvent.entity_type == "announcement", AuditEvent.entity_id == group_item.json()["id"],
    ).order_by(AuditEvent.created_at)))
    assert [event.action for event in events] == [
        "announcement.create", "announcement.update", "announcement.archive",
    ]
    assert sum(event.action == "announcement.archive" for event in events) == 1
    rendered = repr([event.details for event in events])
    assert all(value not in rendered for value in (
        "title", "body", "Групповое синтетическое", "Синтетический текст для группы",
        changed_title, changed_body, "Запрещённое изменение",
    ))


def test_announcement_create_is_idempotent(client, db, users):
    _director(client, db, users)
    headers = {"Idempotency-Key": "synthetic-retry-key"}
    payload = {
        "target_type": "all", "group_id": None,
        "title": "Синтетическая повторная публикация", "body": "Один логический экземпляр",
    }
    first = client.post(ROOT, json=payload, headers=headers)
    retry = client.post(ROOT, json=payload, headers=headers)
    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert db.scalar(select(func.count()).select_from(Announcement).where(
        Announcement.idempotency_key == "synthetic-retry-key",
    )) == 1
    assert db.scalar(select(func.count()).select_from(AuditEvent).where(
        AuditEvent.entity_id == first.json()["id"],
        AuditEvent.action == "announcement.create",
    )) == 1


def test_announcement_validation_tenant_rbac_and_atomicity(client, db, users, monkeypatch):
    organization, other, _, admin = users
    _director(client, db, users)
    own_group = Group(organization_id=organization.id, name="Активная целевая", status="active")
    archived_group = Group(organization_id=organization.id, name="Архивная целевая", status="archived")
    foreign_group = Group(organization_id=other.id, name="Чужая целевая", status="active")
    foreign_user = User(
        organization_id=other.id, username="announcement-other-director",
        password_hash=hash_password(TEST_PASSWORD), role="DIRECTOR", status="active", must_change_password=False,
    )
    db.add_all([own_group, archived_group, foreign_group, foreign_user])
    db.flush()
    foreign_item = Announcement(
        organization_id=other.id, target_type="all", title="Foreign synthetic", body="Foreign synthetic body",
        status="active", created_by=foreign_user.id, updated_by=foreign_user.id,
    )
    db.add(foreign_item)
    db.commit()

    valid = {"target_type": "group", "group_id": str(own_group.id), "title": "Synthetic", "body": "Synthetic body"}
    assert client.post(ROOT, json={**valid, "organization_id": str(organization.id)}).status_code == 400
    assert client.post(ROOT, json={**valid, "title": " "}).status_code == 400
    assert client.post(ROOT, json={**valid, "group_id": None}).status_code == 400
    assert client.post(ROOT, json={**valid, "group_id": str(archived_group.id)}).status_code == 409
    assert client.post(ROOT, json={**valid, "group_id": str(foreign_group.id)}).status_code == 404
    assert client.get(ROOT, params={"group_id": str(foreign_group.id)}).status_code == 404
    assert client.get(f"{ROOT}/{foreign_item.id}").status_code == 404
    assert client.patch(f"{ROOT}/{foreign_item.id}", json={"title": "No"}).status_code == 404
    assert client.post(f"{ROOT}/{foreign_item.id}/archive").status_code == 404

    client.post("/api/v1/auth/logout")
    _login(client, admin.username)
    assert client.post(ROOT, json={
        "target_type": "all", "group_id": None, "title": "Admin synthetic", "body": "Admin body",
    }).status_code == 201
    client.post("/api/v1/auth/logout")

    parent = User(
        organization_id=organization.id, username="announcement-parent", password_hash=admin.password_hash,
        role="PARENT", status="active", must_change_password=False,
    )
    db.add(parent)
    db.flush()
    db.add(Guardian(
        organization_id=organization.id, user_id=parent.id,
        first_name="Синтетический", last_name="Родитель", status="active",
    ))
    db.commit()
    _login(client, parent.username)
    assert client.get(ROOT).status_code == 403
    assert client.post(ROOT, json={
        "target_type": "all", "group_id": None, "title": "Denied", "body": "Denied",
    }).status_code == 403
    with TestClient(app) as anonymous:
        assert anonymous.get(ROOT).status_code == 401

    client.post("/api/v1/auth/logout")
    _director(client, db, users)
    rollback_title = "Synthetic rollback announcement"

    def fail_writer(*_args, **_kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(audit, "write", fail_writer)
    with TestClient(app, raise_server_exceptions=False) as failure_client:
        _login(failure_client, users[2].username)
        response = failure_client.post(ROOT, json={
            "target_type": "all", "group_id": None, "title": rollback_title, "body": "Synthetic rollback body",
        })
    assert response.status_code == 500
    db.rollback()
    assert db.scalar(select(Announcement.id).where(Announcement.title == rollback_title)) is None
    assert db.scalar(select(func.count(AuditEvent.id)).where(AuditEvent.action == "announcement.create")) >= 1

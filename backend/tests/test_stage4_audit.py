"""Stage 4 immutable Audit API, instrumentation, privacy and atomicity."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.audit_event import AuditEvent
from app.models.guardian import Guardian
from app.models.user import User
from app.services import audit
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/audit"
DAY = "2025-09-20"


def _login(client, username: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200


def _director(client, db, users) -> None:
    users[2].must_change_password = False
    db.flush()
    _login(client, users[2].username)


def _post(client, path: str, payload: dict | None = None, status: int = 200) -> dict:
    response = client.post(path, json=payload) if payload is not None else client.post(path)
    assert response.status_code == status, response.text
    return response.json()


def _patch(client, path: str, payload: dict) -> dict:
    response = client.patch(path, json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def test_all_stage4_audit_actions_and_privacy(client, db, users):
    _director(client, db, users)

    group = _post(client, "/api/v1/groups", {"name": "Синтетическая аудит-группа"}, 201)
    _patch(client, f"/api/v1/groups/{group['id']}", {"name": "Изменённая аудит-группа"})
    child = _post(client, "/api/v1/children", {
        "group_id": group["id"], "first_name": "Аудит", "last_name": "Ребёнок",
        "middle_name": None, "birth_date": "2020-01-01",
    }, 201)
    _patch(client, f"/api/v1/children/{child['id']}", {"middle_name": "Синтетический"})
    guardian = _post(client, "/api/v1/guardians", {
        "first_name": "Аудит", "last_name": "Представитель", "middle_name": None,
        "phone": "+79990000000", "email": "audit@example.test",
    }, 201)
    _patch(client, f"/api/v1/guardians/{guardian['id']}", {"middle_name": "Синтетический"})
    relation = _post(client, f"/api/v1/children/{child['id']}/guardians", {
        "guardian_id": guardian["id"], "relation_type": "other",
    }, 201)
    _patch(client, f"/api/v1/children/{child['id']}/guardians/{guardian['id']}", {"relation_type": "father"})
    _post(client, f"/api/v1/children/{child['id']}/guardians/{guardian['id']}/archive")
    _post(client, f"/api/v1/children/{child['id']}/guardians/{guardian['id']}/restore")

    parent_credentials = _post(client, f"/api/v1/guardians/{guardian['id']}/account", status=201)
    _post(client, f"/api/v1/guardians/{guardian['id']}/account/resend")
    _post(client, f"/api/v1/guardians/{guardian['id']}/account/block")
    _post(client, f"/api/v1/guardians/{guardian['id']}/account/unblock")

    employee = _post(client, "/api/v1/employees", {
        "first_name": "Аудит", "last_name": "Сотрудник", "middle_name": None,
        "position": "Администратор", "category": "administrator", "email": "staff-audit@example.test",
    }, 201)
    _patch(client, f"/api/v1/employees/{employee['id']}", {"position": "Старший администратор"})
    admin_credentials = _post(client, f"/api/v1/employees/{employee['id']}/account", {"role": "ADMIN"}, 201)
    _post(client, f"/api/v1/employees/{employee['id']}/account/resend", {"role": "ADMIN"})
    _post(client, f"/api/v1/employees/{employee['id']}/account/block")
    _post(client, f"/api/v1/employees/{employee['id']}/account/unblock")

    attendance = _post(client, "/api/v1/attendance", {
        "child_id": child["id"], "date": DAY, "status": "present", "arrival_time": "08:30",
    }, 201)
    _post(client, "/api/v1/attendance", {
        "child_id": child["id"], "date": DAY, "status": "absent",
    })
    _patch(client, f"/api/v1/attendance/{attendance['record_id']}", {
        "status": "present", "arrival_time": "09:00", "departure_time": "16:00",
    })

    _post(client, f"/api/v1/children/{child['id']}/guardians/{guardian['id']}/archive")
    _post(client, f"/api/v1/guardians/{guardian['id']}/archive")
    _post(client, f"/api/v1/guardians/{guardian['id']}/restore")
    _post(client, f"/api/v1/children/{child['id']}/archive")
    _post(client, f"/api/v1/groups/{group['id']}/archive")
    _post(client, f"/api/v1/groups/{group['id']}/restore")
    _post(client, f"/api/v1/children/{child['id']}/restore")
    _post(client, f"/api/v1/employees/{employee['id']}/archive")
    _post(client, f"/api/v1/employees/{employee['id']}/restore")

    response = client.get(ROOT, params={"limit": 100})
    assert response.status_code == 200
    events = response.json()["items"]
    assert {
        "group.create", "group.update", "group.archive", "group.restore",
        "child.create", "child.update", "child.archive", "child.restore",
        "guardian.create", "guardian.update", "guardian.archive", "guardian.restore",
        "child_guardian.create", "child_guardian.update", "child_guardian.archive", "child_guardian.restore",
        "employee.create", "employee.update", "employee.archive", "employee.restore",
        "account.invite", "account.block", "account.unblock",
        "attendance.create", "attendance.update",
    } <= {event["action"] for event in events}
    assert relation["id"] in {event["entity_id"] for event in events if event["entity_type"] == "child_guardian"}

    rendered = response.text
    forbidden = [
        "Синтетическая аудит-группа", "Изменённая аудит-группа", "Ребёнок", "Представитель",
        "+79990000000", "audit@example.test", "Сотрудник", "Старший администратор",
        parent_credentials["username"], admin_credentials["username"],
        "password_hash", "temporary_password", "session_token",
    ]
    assert all(value not in rendered for value in forbidden)
    attendance_creates = [event for event in events if event["action"] == "attendance.create"]
    attendance_updates = [event for event in events if event["action"] == "attendance.update"]
    assert len(attendance_creates) == 1
    assert attendance_creates[0]["details"] == {
        "after": {"status": "present", "arrival_time": "08:30", "departure_time": None},
    }
    assert attendance_updates
    for event in attendance_updates:
        assert set(event["details"]) == {"before", "after", "changed_fields"}
        assert set(event["details"]["before"]) == {"status", "arrival_time", "departure_time"}
        assert set(event["details"]["after"]) == {"status", "arrival_time", "departure_time"}


def test_director_filters_pagination_tenant_and_append_only(client, db, users):
    organization, other, director, _ = users
    _director(client, db, users)
    own = AuditEvent(
        organization_id=organization.id, actor_user_id=director.id, action="group.create",
        entity_type="group", details={}, created_at=datetime(2026, 9, 26, 12, 0, tzinfo=UTC),
    )
    older = AuditEvent(
        organization_id=organization.id, actor_user_id=director.id, action="group.update",
        entity_type="group", details={"changed_fields": ["name"]},
        created_at=datetime(2026, 9, 26, 11, 0, tzinfo=UTC),
    )
    other_actor = User(
        organization_id=other.id, username="audit-other-director", password_hash=director.password_hash,
        role="DIRECTOR", status="active", must_change_password=False,
    )
    db.add(other_actor)
    db.flush()
    foreign = AuditEvent(
        organization_id=other.id, actor_user_id=other_actor.id, action="group.create",
        entity_type="group", details={}, created_at=datetime(2026, 9, 26, 13, 0, tzinfo=UTC),
    )
    db.add_all([own, older, foreign])
    teacher = User(
        organization_id=organization.id, username="audit-teacher-synthetic",
        password_hash=director.password_hash, role="TEACHER", status="active", must_change_password=False,
    )
    db.add(teacher)
    db.flush()
    teacher_event = AuditEvent(
        organization_id=organization.id, actor_user_id=teacher.id, action="attendance.update",
        entity_type="attendance", details={"before": {}, "after": {}, "changed_fields": []},
        created_at=datetime(2026, 9, 26, 12, 30, tzinfo=UTC),
    )
    db.add(teacher_event)
    db.commit()

    teacher_authored = client.get(ROOT, params={"actor_user_id": str(teacher.id)})
    assert teacher_authored.status_code == 200
    assert teacher_authored.json()["items"][0]["actor"]["role"] == "TEACHER"

    filtered = client.get(ROOT, params={
        "entity_type": "group", "action": "group.create", "actor_user_id": str(director.id),
        "date_from": "2026-09-26", "date_to": "2026-09-26", "limit": 1, "offset": 0,
    })
    assert filtered.status_code == 200
    assert filtered.json()["limit"] == 1 and filtered.json()["offset"] == 0
    assert len(filtered.json()["items"]) == 1
    assert filtered.json()["items"][0]["id"] == str(own.id)
    assert "organization_id" not in filtered.text
    assert client.get(f"{ROOT}/{own.id}").status_code == 200
    assert client.get(f"{ROOT}/{foreign.id}").status_code == 404
    first_page = client.get(ROOT, params={"limit": 1}).json()
    second_page = client.get(ROOT, params={"offset": 1, "limit": 1}).json()
    assert first_page["items"][0]["id"] == str(teacher_event.id)
    assert second_page["items"][0]["id"] == str(own.id)
    assert second_page["offset"] == 1
    assert str(foreign.id) not in client.get(ROOT, params={"limit": 100}).text
    assert client.get(ROOT, params={"limit": 101}).status_code == 400
    assert client.post(ROOT, json={}).status_code == 405
    assert client.patch(f"{ROOT}/{own.id}", json={}).status_code == 405
    assert client.delete(f"{ROOT}/{own.id}").status_code == 405


def test_admin_parent_and_anonymous_cannot_read_audit(client, db, users):
    organization, _, _, admin = users
    _login(client, admin.username)
    assert client.get(ROOT).status_code == 403
    client.post("/api/v1/auth/logout")

    parent = User(
        organization_id=organization.id, username="audit-parent", password_hash=admin.password_hash,
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
    with TestClient(app) as anonymous:
        assert anonymous.get(ROOT).status_code == 401


def test_writer_rejects_non_whitelisted_or_sensitive_details(db, users):
    actor = users[2]
    with pytest.raises(ValueError, match="non-whitelisted"):
        audit.write(db, actor, "child.update", "child", None, {"first_name": "Запрещённое значение"})
    with pytest.raises(ValueError, match="attendance state"):
        audit.write(db, actor, "attendance.update", "attendance", None, {
            "before": {"status": "present", "arrival_time": "08:30", "departure_time": None, "child_name": "Нет"},
        })
    with pytest.raises(ValueError, match="non-whitelisted"):
        audit.write(db, actor, "announcement.create", "announcement", None, {"title": "Запрещённое значение"})
    with pytest.raises(ValueError, match="action/entity"):
        audit.write(db, actor, "unknown.create", "unknown", None)


def test_audit_failure_rolls_back_business_mutation(client, db, users, monkeypatch):
    _director(client, db, users)
    name = "Группа rollback audit"

    def fail_writer(*_args, **_kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(audit, "write", fail_writer)
    with TestClient(app, raise_server_exceptions=False) as failure_client:
        _login(failure_client, users[2].username)
        response = failure_client.post("/api/v1/groups", json={"name": name})
    assert response.status_code == 500
    db.rollback()
    from app.models.group import Group
    assert db.scalar(select(Group.id).where(Group.name == name)) is None
    assert db.scalar(select(AuditEvent.id).where(AuditEvent.action == "group.create")) is None

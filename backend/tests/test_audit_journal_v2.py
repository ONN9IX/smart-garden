"""Synthetic DIRECTOR-only Journal read model and privacy regressions."""

from datetime import UTC, datetime
from uuid import uuid4

from app.models.audit_event import AuditEvent
from app.models.employee import Employee
from app.models.group import Group
from app.models.user import User
from tests.test_stage6_management_cabinet import _director, _login, _logout


def test_journal_projects_teacher_and_never_renders_raw_details(client, db, users):
    organization, other, director, admin = users
    teacher = User(organization_id=organization.id, username="journal-teacher",
                   password_hash=director.password_hash, role="TEACHER", status="active", must_change_password=False)
    db.add(teacher); db.flush()
    employee = Employee(organization_id=organization.id, user_id=teacher.id, first_name="Анна",
                        last_name="Синтетическая", position="Воспитатель", category="teacher", status="active")
    group = Group(organization_id=organization.id, name="Ромашка", status="active")
    foreign_group = Group(organization_id=other.id, name="Чужой сад", status="active")
    db.add_all([employee, group, foreign_group]); db.flush()
    malicious = "private-message-secret-should-never-render"
    event = AuditEvent(organization_id=organization.id, actor_user_id=teacher.id,
                       action="schedule.update", entity_type="group", entity_id=group.id,
                       details={"changed_fields": ["name", "body", "password"], "body": malicious,
                                "token": "hidden-token", "group_id": str(group.id)},
                       created_at=datetime.now(UTC))
    foreign_event = AuditEvent(organization_id=other.id, actor_user_id=teacher.id,
                               action="group.update", entity_type="group", entity_id=foreign_group.id,
                               details={}, created_at=datetime.now(UTC))
    db.add_all([event, foreign_event]); db.flush()
    _director(client, db, users)
    response = client.get("/api/v1/audit/journal")
    assert response.status_code == 200, response.text
    body = response.json()
    item = next(item for item in body["items"] if item["id"] == str(event.id))
    assert item["actor"]["display_name"] == "Синтетическая Анна"
    assert item["actor"]["role"] == "TEACHER"
    assert item["target"]["display_name"] == "Ромашка"
    assert item["safe_changes"] == ["Изменено: название"]
    assert malicious not in response.text and "hidden-token" not in response.text
    assert str(group.id) not in item["summary"] and str(foreign_group.id) not in response.text
    assert client.get(f"/api/v1/audit/journal?category=groups&actor_user_id={teacher.id}").json()["items"][0]["id"] == str(event.id)
    assert client.get("/api/v1/audit/journal?category=people").json()["items"] == []
    assert client.get(f"/api/v1/audit/journal?context_id={uuid4()}").json()["items"] == []
    assert client.get(f"/api/v1/audit/{event.id}").status_code == 200
    assert client.get(f"/api/v1/audit/{foreign_event.id}").status_code == 404
    _logout(client); _login(client, admin.username)
    assert client.get("/api/v1/audit/journal").status_code == 403
    _logout(client); _login(client, teacher.username)
    assert client.get("/api/v1/audit/journal").status_code == 403

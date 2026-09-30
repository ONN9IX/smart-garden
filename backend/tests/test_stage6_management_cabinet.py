"""Stage 6 DIRECTOR/ADMIN cabinet integration, tenant/RBAC and privacy coverage."""

from datetime import date
from uuid import UUID

from sqlalchemy import select

from app.core.security import hash_password
from app.models.audit_event import AuditEvent
from app.models.child import Child
from app.models.child_diary_entry import ChildDiaryEntry
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.notification import Notification
from app.models.user import User
from tests.conftest import TEST_PASSWORD

MGMT = "/api/v1"
TEACHER = "/api/v1/teacher-management"


def _login(client, username: str, password: str = TEST_PASSWORD) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert response.status_code == 200, response.text


def _director(client, db, users) -> None:
    users[2].must_change_password = False
    db.flush()
    _login(client, users[2].username)


def _logout(client) -> None:
    assert client.post("/api/v1/auth/logout").status_code == 200


def _foundation_teacher(client, db, users):
    organization, _, _, _ = users
    employee = Employee(
        organization_id=organization.id,
        first_name="Синтетическая",
        last_name="Воспитательница",
        position="Воспитатель",
        status="active",
    )
    group = Group(organization_id=organization.id, name="Группа управления", status="active")
    db.add_all([employee, group])
    db.flush()
    credentials = client.post(f"{TEACHER}/employees/{employee.id}/account")
    assert credentials.status_code == 201, credentials.text
    account_id = UUID(credentials.json()["account"]["id"])
    assignment = client.post(f"{TEACHER}/assignments", json={
        "employee_id": str(employee.id),
        "group_id": str(group.id),
    })
    assert assignment.status_code == 201, assignment.text
    return employee, group, db.get(User, account_id), assignment.json()


def test_management_cabinet_director_end_to_end_and_privacy(client, db, users):
    organization, _, director, _ = users
    _director(client, db, users)
    employee, group, teacher, assignment = _foundation_teacher(client, db, users)
    assert teacher is not None

    child = Child(
        organization_id=organization.id,
        group_id=group.id,
        first_name="Ребёнок",
        last_name="Синтетический",
        birth_date=date(2021, 1, 1),
        status="active",
    )
    db.add(child)
    db.flush()

    teachers = client.get(f"{TEACHER}/teachers")
    assert teachers.status_code == 200
    projection = next(item for item in teachers.json()["items"] if item["employee_id"] == str(employee.id))
    assert projection["account"]["user_id"] == str(teacher.id)
    assert projection["assignments"][0]["id"] == assignment["id"]
    assert client.get(f"{TEACHER}/teachers/{employee.id}").status_code == 200

    schedule = client.post(f"{TEACHER}/schedule", json={
        "group_id": str(group.id),
        "weekday": 1,
        "start_time": "09:00",
        "end_time": "10:00",
        "title": "Музыка",
    })
    assert schedule.status_code == 201, schedule.text
    schedule_id = schedule.json()["id"]
    updated_schedule = client.patch(f"{TEACHER}/schedule/{schedule_id}", json={"title": "Ритмика"})
    assert updated_schedule.status_code == 200
    assert updated_schedule.json()["title"] == "Ритмика"

    secret_message = "SENSITIVE-MANAGEMENT-MESSAGE"
    message = client.post(f"{TEACHER}/communications/groups/{group.id}/messages", json={"body": secret_message})
    assert message.status_code == 201
    assert message.json()["sender_user_id"] == str(director.id)
    listed_messages = client.get(f"{TEACHER}/communications/groups/{group.id}/messages")
    assert listed_messages.json()["items"][0]["body"] == secret_message
    assert client.get(f"{TEACHER}/communications/direct/{child.id}/messages").status_code == 404

    diary_secret = "SENSITIVE-DIARY-NOTE"
    diary = ChildDiaryEntry(
        organization_id=organization.id,
        child_id=child.id,
        group_id=group.id,
        date=date(2026, 9, 30),
        author_user_id=teacher.id,
        note=diary_secret,
    )
    db.add(diary)
    db.commit()
    diary_list = client.get(f"{TEACHER}/diary", params={"child_id": str(child.id)})
    assert diary_list.status_code == 200
    assert diary_list.json()["items"][0]["note"] == diary_secret
    assert client.post(f"{TEACHER}/diary", json={"child_id": str(child.id), "note": "Нет"}).status_code == 405

    poll = client.post(f"{TEACHER}/polls", json={
        "group_id": str(group.id),
        "question": "Выберите вариант",
        "options": ["Первый", "Второй"],
    })
    assert poll.status_code == 201, poll.text
    assert poll.json()["total_votes"] == 0
    assert all("voter_user_id" not in option for option in poll.json()["options"])
    closed = client.post(f"{TEACHER}/polls/{poll.json()['id']}/close")
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"

    incident_secret = "SENSITIVE-INCIDENT-DESCRIPTION"
    incident = client.post(f"{TEACHER}/incidents", json={
        "group_id": str(group.id),
        "child_id": str(child.id),
        "occurred_at": "2026-09-30T09:00:00Z",
        "category": "operational",
        "description": incident_secret,
    })
    assert incident.status_code == 201, incident.text
    resolved = client.patch(f"{TEACHER}/incidents/{incident.json()['id']}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    task = client.post(f"{TEACHER}/tasks", json={
        "assignee_employee_id": str(employee.id),
        "group_id": str(group.id),
        "title": "Подготовить материалы",
        "description": "Операционная задача",
        "due_at": "2026-10-01T09:00:00Z",
    })
    assert task.status_code == 201, task.text
    changed_task = client.patch(f"{TEACHER}/tasks/{task.json()['id']}", json={"status": "in_progress"})
    assert changed_task.status_code == 200
    cancelled = client.post(f"{TEACHER}/tasks/{task.json()['id']}/cancel")
    assert cancelled.json()["status"] == "cancelled"

    notification = Notification(
        organization_id=organization.id,
        recipient_user_id=director.id,
        kind="task_attention",
        entity_type="teacher_task",
        entity_id=UUID(task.json()["id"]),
    )
    db.add(notification)
    db.commit()
    notices = client.get(f"{MGMT}/management/notifications")
    assert notices.status_code == 200
    assert [item["id"] for item in notices.json()["items"]] == [str(notification.id)]
    marked = client.post(f"{MGMT}/management/notifications/{notification.id}/read")
    assert marked.status_code == 200
    assert marked.json()["read_at"] is not None

    document = client.post(f"{TEACHER}/document-notices", json={
        "recipient_user_id": str(teacher.id),
        "title": "Ознакомление",
        "kind": "policy_update",
        "requires_ack": True,
    })
    assert document.status_code == 201, document.text
    assert "file" not in document.json()

    consent = client.post(f"{TEACHER}/photo-consents", json={
        "child_id": str(child.id),
        "effective_from": "2026-09-30T00:00:00Z",
        "effective_to": None,
    })
    assert consent.status_code == 200, consent.text
    assert consent.json()["scope"] == "group_photo_report"
    withdrawn = client.post(f"{TEACHER}/photo-consents/{consent.json()['id']}/withdraw")
    assert withdrawn.status_code == 200
    assert withdrawn.json()["status"] == "withdrawn"

    before_name = organization.name
    settings = client.patch(f"{MGMT}/management/settings", json={
        "name": "Детский сад «Синтетический обновлённый»",
        "timezone": "Asia/Yekaterinburg",
    })
    assert settings.status_code == 200, settings.text
    assert settings.json()["timezone"] == "Asia/Yekaterinburg"
    assert settings.json()["name"] != before_name

    today = client.get(f"{MGMT}/management/today")
    assert today.status_code == 200
    payload = today.json()
    assert payload["active_groups"] >= 1
    assert payload["unread_notifications"] == 0
    assert "attention_items" in payload

    audit_rows = list(db.scalars(select(AuditEvent).where(
        AuditEvent.organization_id == organization.id,
    )))
    rendered = str([row.details for row in audit_rows])
    assert secret_message not in rendered
    assert diary_secret not in rendered
    assert incident_secret not in rendered
    settings_event = next(row for row in audit_rows if row.action == "organization.settings_update")
    assert set(settings_event.details["changed_fields"]) == {"name", "timezone"}
    assert "Синтетический обновлённый" not in str(settings_event.details)
    assert "Asia/Yekaterinburg" not in str(settings_event.details)


def test_management_admin_permissions_and_operational_access(client, db, users):
    organization, _, _, admin = users
    _director(client, db, users)
    employee, group, teacher, _ = _foundation_teacher(client, db, users)
    assert teacher is not None
    _logout(client)
    _login(client, admin.username)

    assert client.get(f"{MGMT}/management/today").status_code == 200
    assert client.get(f"{TEACHER}/teachers").status_code == 200
    assert client.get(f"{TEACHER}/assignments").status_code == 200

    assert client.post(f"{TEACHER}/employees/{employee.id}/account/reset-password").status_code == 403
    assert client.post(f"{TEACHER}/assignments", json={
        "employee_id": str(employee.id),
        "group_id": str(group.id),
    }).status_code == 403
    assert client.get(f"{MGMT}/management/settings").status_code == 403
    assert client.patch(f"{MGMT}/management/settings", json={"name": "Нет"}).status_code == 403
    assert client.get("/api/v1/audit").status_code == 403

    schedule = client.post(f"{TEACHER}/schedule", json={
        "group_id": str(group.id),
        "weekday": 2,
        "start_time": "10:00",
        "end_time": "11:00",
        "title": "Прогулка",
    })
    assert schedule.status_code == 201

    other_notification = Notification(
        organization_id=organization.id,
        recipient_user_id=users[2].id,
        kind="private_pointer",
        entity_type="group",
        entity_id=group.id,
    )
    db.add(other_notification)
    db.commit()
    assert str(other_notification.id) not in client.get(f"{MGMT}/management/notifications", params={"status": "all"}).text
    assert client.post(f"{MGMT}/management/notifications/{other_notification.id}/read").status_code == 404


def test_management_tenant_and_schema_boundaries(client, db, users):
    _, other, _, _ = users
    _director(client, db, users)

    foreign_group = Group(organization_id=other.id, name="Чужая группа управления", status="active")
    foreign_child = Child(
        organization_id=other.id,
        group_id=None,
        first_name="Чужой",
        last_name="Ребёнок",
        birth_date=date(2021, 1, 1),
        status="active",
    )
    db.add(foreign_group)
    db.flush()
    foreign_child.group_id = foreign_group.id
    foreign_teacher = User(
        organization_id=other.id,
        username="foreign-teacher-management",
        password_hash=hash_password(TEST_PASSWORD),
        role="TEACHER",
        status="active",
        must_change_password=False,
    )
    db.add_all([foreign_child, foreign_teacher])
    db.flush()

    assert client.get(f"{TEACHER}/schedule", params={"group_id": str(foreign_group.id)}).status_code == 404
    assert client.get(f"{TEACHER}/diary", params={"child_id": str(foreign_child.id)}).status_code == 404
    assert client.post(f"{TEACHER}/incidents", json={
        "group_id": str(foreign_group.id),
        "occurred_at": "2026-09-30T10:00:00Z",
        "category": "other",
        "description": "Чужое",
    }).status_code == 404
    assert client.post(f"{TEACHER}/document-notices", json={
        "recipient_user_id": str(foreign_teacher.id),
        "title": "Чужое",
        "kind": "notice",
        "requires_ack": False,
    }).status_code == 404
    assert client.post(f"{TEACHER}/photo-consents", json={
        "child_id": str(foreign_child.id),
        "effective_from": "2026-09-30T00:00:00Z",
    }).status_code == 404

    assert client.post(f"{TEACHER}/document-notices", json={
        "recipient_user_id": str(foreign_teacher.id),
        "title": "Запрещено",
        "kind": "notice",
        "requires_ack": False,
        "file_url": "https://example.test/secret.pdf",
    }).status_code == 400
    assert client.post(f"{TEACHER}/photo-consents", json={
        "child_id": str(foreign_child.id),
        "effective_from": "2026-09-30T00:00:00Z",
        "evidence_blob": "forbidden",
    }).status_code == 400
    assert client.patch(f"{MGMT}/management/settings", json={"timezone": "Not/AZone"}).status_code == 400


def test_teacher_and_parent_cannot_use_management_cabinet(client, db, users):
    organization, _, director, _ = users
    director.must_change_password = False
    group = Group(organization_id=organization.id, name="Ролевая группа", status="active")
    teacher = User(
        organization_id=organization.id,
        username="teacher-management-denied",
        password_hash=hash_password(TEST_PASSWORD),
        role="TEACHER",
        status="active",
        must_change_password=False,
    )
    db.add_all([group, teacher])
    db.flush()
    employee = Employee(
        organization_id=organization.id,
        user_id=teacher.id,
        first_name="Ролевая",
        last_name="Воспитательница",
        position="Воспитатель",
        status="active",
    )
    parent = User(
        organization_id=organization.id,
        username="parent-management-denied",
        password_hash=hash_password(TEST_PASSWORD),
        role="PARENT",
        status="active",
        must_change_password=False,
    )
    guardian = Guardian(
        organization_id=organization.id,
        user_id=parent.id,
        first_name="Ролевой",
        last_name="Родитель",
        status="active",
    )
    db.add_all([employee, parent, guardian])
    db.commit()

    _login(client, teacher.username)
    assert client.get(f"{MGMT}/management/today").status_code == 403
    assert client.get(f"{TEACHER}/teachers").status_code == 403
    _logout(client)

    _login(client, parent.username)
    assert client.get(f"{MGMT}/management/today").status_code == 403
    assert client.get(f"{TEACHER}/teachers").status_code == 403

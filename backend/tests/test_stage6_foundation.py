"""Stage 6 Foundation identity, lifecycle, assignment and authorization contract."""

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.errors import AppError
from app.core.permissions import require_teacher_group_access
from app.core.security import hash_password
from app.main import app
from app.models.audit_event import AuditEvent
from app.models.auth_session import AuthSession
from app.models.employee import Employee
from app.models.group import Group
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from app.services import audit
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/teacher-management"

STAGE6_AUDIT_ACTIONS = {
    "user_account": {
        "teacher_account.create", "teacher_account.reset", "teacher_account.block", "teacher_account.unblock",
    },
    "teacher_assignment": {
        "teacher_assignment.create", "teacher_assignment.archive", "teacher_assignment.restore",
    },
    "group_schedule_item": {"schedule.create", "schedule.update", "schedule.archive"},
    "communication_message": {"teacher_message.create"},
    "child_diary_entry": {"diary.create", "diary.update"},
    "announcement": {
        "teacher_announcement.create", "teacher_announcement.update", "teacher_announcement.archive",
    },
    "poll": {"poll.create", "poll.close"},
    "poll_vote": {"poll.vote"},
    "incident": {"incident.create", "incident.update", "incident.resolve"},
    "teacher_task": {
        "teacher_task.create", "teacher_task.update", "teacher_task.cancel", "teacher_task.status",
    },
    "notification": {"notification.read"},
    "document_notice": {"document_notice.issue", "document_notice.ack"},
    "photo_consent": {"photo_consent.record", "photo_consent.withdraw"},
    "photo_asset": {"photo.create", "photo.restrict", "photo.remove"},
}


def _login(client, username: str, password: str = TEST_PASSWORD):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def _director(client, users):
    users[2].must_change_password = False
    assert _login(client, "director-test").status_code == 200


def _employee_and_group(db, users, suffix=""):
    employee = Employee(
        organization_id=users[0].id, first_name="Тестовая", last_name=f"Воспитательница{suffix}",
        position="Воспитатель", category="teacher", email=f"teacher{suffix or '-one'}@example.test", status="active",
    )
    group = Group(organization_id=users[0].id, name=f"Группа Foundation{suffix}", status="active")
    db.add_all([employee, group])
    db.flush()
    return employee, group


def test_teacher_account_assignment_access_and_lifecycle(client, db, users):
    _director(client, users)
    employee, group = _employee_and_group(db, users)
    account_path = f"{ROOT}/employees/{employee.id}/account"
    created = client.post(account_path)
    assert created.status_code == 201
    payload = created.json()
    assert payload["role"] == "TEACHER"
    assert payload["username"].startswith("staff-")
    teacher = db.get(User, employee.user_id)
    assert teacher is not None and employee.user_id == teacher.id
    teacher.password_hash = hash_password(TEST_PASSWORD)
    teacher.must_change_password = False
    db.flush()
    assert client.post(account_path + "/block").json()["status"] == "blocked"
    with TestClient(app) as blocked:
        assert _login(blocked, teacher.username).json()["error"]["code"] == "USER_BLOCKED"
    assert client.post(account_path + "/unblock").json()["status"] == "active"

    assigned = client.post(f"{ROOT}/assignments", json={
        "employee_id": str(employee.id), "group_id": str(group.id),
    })
    assert assigned.status_code == 201
    assignment_id = UUID(assigned.json()["id"])
    assert require_teacher_group_access(db, teacher, group.id).id == assignment_id

    with TestClient(app) as teacher_client:
        assert _login(teacher_client, teacher.username).status_code == 200
        assert teacher_client.get("/api/v1/auth/me").json()["user"]["role"] == "TEACHER"
        assert teacher_client.get("/api/v1/employees").status_code == 403
        assert teacher_client.post("/api/v1/groups", json={"name": "Недоступная"}).status_code == 403
        assert teacher_client.get("/api/v1/audit").status_code == 403
        assert teacher_client.post(account_path).status_code == 403
        assert teacher_client.post(f"/api/v1/employees/{employee.id}/account/block").status_code == 403

        assert client.post(f"{ROOT}/assignments/{assignment_id}/archive").json()["status"] == "archived"
        with pytest.raises(AppError) as denied:
            require_teacher_group_access(db, teacher, group.id)
        assert denied.value.status == 404
        assert client.post(f"{ROOT}/assignments/{assignment_id}/restore").json()["status"] == "active"
        assert require_teacher_group_access(db, teacher, group.id)

        assert client.post(f"/api/v1/employees/{employee.id}/archive").json()["account"]["status"] == "blocked"
        assert teacher_client.get("/api/v1/auth/me").status_code in (401, 403)
        assert db.scalar(select(AuthSession).where(
            AuthSession.user_id == teacher.id, AuthSession.revoked_at.is_(None),
        )) is None

    actions = set(db.scalars(select(AuditEvent.action).where(AuditEvent.entity_id.in_([teacher.id, assignment_id]))))
    assert {
        "account.invite", "teacher_account.block", "teacher_account.unblock",
        "teacher_assignment.create", "teacher_assignment.archive", "teacher_assignment.restore",
    } <= actions
    details = list(db.scalars(select(AuditEvent.details).where(AuditEvent.action.like("teacher_%"))))
    assert "token" not in str(details).lower() and "password" not in str(details).lower()


def test_teacher_assignment_management_roles_and_tenant_boundaries(client, db, users):
    organization, other, _, admin = users
    _director(client, users)
    employee, group = _employee_and_group(db, users, "-2")
    client.post(f"{ROOT}/employees/{employee.id}/account")
    foreign_group = Group(organization_id=other.id, name="Чужая группа", status="active")
    foreign_employee = Employee(
        organization_id=other.id, first_name="Чужая", last_name="Воспитательница",
        position="Воспитатель", category="teacher", status="active",
    )
    db.add_all([foreign_group, foreign_employee])
    db.flush()
    for body in (
        {"employee_id": str(employee.id), "group_id": str(foreign_group.id)},
        {"employee_id": str(foreign_employee.id), "group_id": str(group.id)},
    ):
        response = client.post(f"{ROOT}/assignments", json=body)
        assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"

    created = client.post(f"{ROOT}/assignments", json={
        "employee_id": str(employee.id), "group_id": str(group.id),
    })
    assert created.status_code == 201
    duplicate = client.post(f"{ROOT}/assignments", json={
        "employee_id": str(employee.id), "group_id": str(group.id),
    })
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "RELATION_ALREADY_EXISTS"
    with TestClient(app) as admin_client:
        assert _login(admin_client, admin.username).status_code == 200
        assert admin_client.get(f"{ROOT}/assignments").status_code == 200
        assert admin_client.post(f"{ROOT}/assignments", json={
            "employee_id": str(employee.id), "group_id": str(group.id),
        }).status_code == 403
        assert admin_client.post(f"{ROOT}/employees/{employee.id}/account/resend").status_code == 403

    admin_employee = Employee(
        organization_id=organization.id, user_id=admin.id, first_name="Тестовый",
        last_name="Администратор", position="Администратор", category="administrator", status="active",
    )
    db.add(admin_employee)
    db.flush()
    assert client.post(f"{ROOT}/assignments", json={
        "employee_id": str(admin_employee.id), "group_id": str(group.id),
    }).json()["error"]["code"] == "EMPLOYEE_ACCOUNT_NOT_FOUND"


def test_teacher_identity_requires_active_link_assignment_and_group(client, db, users):
    organization, other, director, _ = users
    orphan = User(
        organization_id=organization.id, username="orphan-teacher", password_hash=hash_password(TEST_PASSWORD),
        role="TEACHER", status="active", must_change_password=False,
    )
    db.add(orphan)
    db.flush()
    assert _login(client, orphan.username).status_code == 403
    employee, group = _employee_and_group(db, users, "-3")
    employee.user_id = orphan.id
    employee.category = "teacher"
    db.add(TeacherGroupAssignment(
        organization_id=organization.id, employee_id=employee.id, group_id=group.id,
        status="active", assigned_by=director.id,
    ))
    db.flush()
    assert _login(client, orphan.username).status_code == 200
    assert require_teacher_group_access(db, orphan, group.id)
    unassigned = Group(organization_id=organization.id, name="Неназначенная группа", status="active")
    foreign = Group(organization_id=other.id, name="Чужая группа доступа", status="active")
    db.add_all([unassigned, foreign])
    db.flush()
    for inaccessible_id in (unassigned.id, foreign.id):
        with pytest.raises(AppError) as inaccessible:
            require_teacher_group_access(db, orphan, inaccessible_id)
        assert inaccessible.value.status == 404
    group.status = "archived"
    db.flush()
    with pytest.raises(AppError) as denied:
        require_teacher_group_access(db, orphan, group.id)
    assert denied.value.status == 404


def test_stage6_audit_allowlist_is_complete_and_privacy_safe(db, users):
    actor = users[2]
    for entity_type, actions in STAGE6_AUDIT_ACTIONS.items():
        for action in actions:
            audit.write(db, actor, action, entity_type, uuid4())

    identifier = uuid4()
    audit.write(db, actor, "teacher_account.create", "user_account", uuid4(), {
        "account_role": "TEACHER",
    })
    audit.write(db, actor, "teacher_assignment.create", "teacher_assignment", uuid4(), {
        "employee_id": str(identifier), "group_id": str(identifier),
    })
    audit.write(db, actor, "schedule.update", "group_schedule_item", uuid4(), {
        "changed_fields": ["weekday", "start_time", "end_time", "title", "status"],
    })
    audit.write(db, actor, "teacher_message.create", "communication_message", uuid4(), {
        "thread_id": str(identifier), "group_id": str(identifier), "thread_type": "direct",
    })
    audit.write(db, actor, "incident.resolve", "incident", uuid4(), {
        "child_id": str(identifier), "category": "operational",
        "status_before": "open", "status_after": "resolved",
    })
    audit.write(db, actor, "document_notice.issue", "document_notice", uuid4(), {
        "recipient_user_id": str(identifier), "requires_ack": True,
    })
    audit.write(db, actor, "photo_consent.record", "photo_consent", uuid4(), {
        "child_id": str(identifier), "scope": "group_photo_report",
        "status_before": "withdrawn", "status_after": "granted",
    })
    db.flush()

    for unsafe_key in ("body", "note", "description", "storage_key", "password"):
        with pytest.raises(ValueError):
            audit.write(db, actor, "teacher_message.create", "communication_message", uuid4(), {
                unsafe_key: "sensitive value",
            })
    for action, entity_type in (
        ("teacher_message.create", "incident"),
        ("incident.create", "communication_message"),
    ):
        with pytest.raises(ValueError):
            audit.write(db, actor, action, entity_type, uuid4())

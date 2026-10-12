"""Synthetic PostgreSQL HTTP coverage for tenant-scoped live Control and settings."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from alembic.config import Config
from sqlalchemy import select

from alembic import command
from app.models.account_access_token import AccountAccessToken
from app.models.audit_event import AuditEvent
from app.models.child import Child
from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.notification import Notification
from app.models.operational_alert_state import OperationalAlertState
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.services import management_control
from tests.test_stage6_management_cabinet import _director, _login, _logout


def _alerts(client):
    response = client.get("/api/v1/management/control")
    assert response.status_code == 200, response.text
    return response.json()["alerts"]


def test_control_conditions_resolve_and_state_is_per_user(client, db, users):
    organization, other, director, admin = users
    _director(client, db, users)
    group = Group(organization_id=organization.id, name="Ромашка", status="active")
    foreign = Group(organization_id=other.id, name="Чужой сад", status="active")
    employee = Employee(organization_id=organization.id, first_name="Анна", last_name="Тестовая",
                        position="Воспитатель", category="teacher", status="active")
    db.add_all([group, foreign, employee]); db.flush()
    child = Child(organization_id=organization.id, group_id=group.id, first_name="Кирилл",
                  last_name="Синтетический", birth_date=date(2021, 1, 1), status="active")
    task = TeacherTask(organization_id=organization.id, assignee_employee_id=employee.id,
                       title="Тестовая задача", status="open", due_at=datetime.now(UTC) - timedelta(days=1),
                       created_by=director.id)
    db.add_all([child, task]); db.flush()
    alerts = _alerts(client)
    kinds = {item["kind"] for item in alerts}
    assert {"attendance_missing", "group_without_teacher", "group_without_schedule", "tasks_overdue"} <= kinds
    assert not any("Чужой сад" in item["context"] for item in alerts)
    assert len({item["alert_key"] for item in alerts}) == len(alerts)
    key = next(item["alert_key"] for item in alerts if item["kind"] == "group_without_teacher")
    assert client.post("/api/v1/management/control/alerts/view", json={"alert_key": key}).status_code == 200
    snooze = client.post("/api/v1/management/control/alerts/snooze", json={"alert_key": key, "duration": "one_hour"})
    assert snooze.status_code == 200
    assert datetime.fromisoformat(snooze.json()["snoozed_until"]) < datetime.now(UTC) + timedelta(hours=2)
    assert client.get("/api/v1/management/control").json()["summary"]["snoozed"] == 1
    assert client.post("/api/v1/management/control/alerts/view", json={"alert_key": "foreign:" + str(uuid4())}).status_code == 404
    assert db.scalar(select(OperationalAlertState).where(OperationalAlertState.alert_key == key)).user_id == director.id
    _logout(client); _login(client, admin.username)
    assert next(item for item in _alerts(client) if item["alert_key"] == key)["snoozed_until"] is None
    _logout(client); _login(client, director.username)
    teacher = User(organization_id=organization.id, username="control-teacher", password_hash=director.password_hash,
                   role="TEACHER", status="active", must_change_password=False)
    db.add(teacher); db.flush()
    employee.user_id = teacher.id
    db.add(TeacherGroupAssignment(organization_id=organization.id, employee_id=employee.id,
                                  group_id=group.id, status="active", assigned_by=director.id))
    db.add(GroupScheduleItem(organization_id=organization.id, group_id=group.id, weekday=0,
                             start_time=time(9), end_time=time(10), title="Занятие", status="active",
                             created_by=director.id, updated_by=director.id))
    task.status = "done"
    db.flush()
    kinds = {item["kind"] for item in _alerts(client)}
    assert "group_without_teacher" not in kinds and "group_without_schedule" not in kinds and "tasks_overdue" not in kinds
    _logout(client); _login(client, teacher.username)
    assert client.get("/api/v1/management/control").status_code == 403


def test_control_settings_invites_notifications_timezone_and_role(client, db, users, monkeypatch):
    organization, _other, director, admin = users
    _director(client, db, users)
    parent = User(organization_id=organization.id, username="control-parent", password_hash=director.password_hash,
                  role="PARENT", status="active", must_change_password=False)
    db.add(parent); db.flush()
    guardian = Guardian(organization_id=organization.id, user_id=parent.id, first_name="Мама",
                        last_name="Синтетическая", status="active")
    db.add(guardian); db.flush()
    db.add(AccountAccessToken(organization_id=organization.id, user_id=parent.id, guardian_id=guardian.id,
                              purpose="activation", token_digest="a" * 64, delivery_status="failed",
                              expires_at=datetime.now(UTC) + timedelta(days=1)))
    notice = Notification(organization_id=organization.id, recipient_user_id=director.id,
                          kind="announcement.published", entity_type="announcement", entity_id=uuid4())
    db.add(notice); db.flush()
    assert any(item["kind"] == "parent_invite_failed_or_expired" for item in _alerts(client))
    before = client.get("/api/v1/management/control").json()["event_notifications"]
    assert len(before) == 1
    update = client.patch("/api/v1/management/notification-settings", json={
        "show_informational_notifications": False,
        "attendance_checkpoint_time": "23:59:00",
        "schedule_missing_alert_enabled": False,
    })
    assert update.status_code == 200, update.text
    policy_events = db.scalars(select(AuditEvent).where(
        AuditEvent.organization_id == organization.id,
        AuditEvent.actor_user_id == director.id,
        AuditEvent.action == "organization.settings_update",
    )).all()
    assert len(policy_events) == 1
    assert policy_events[0].details == {"changed_fields": [
        "attendance_checkpoint_time", "schedule_missing_alert_enabled", "show_informational_notifications",
    ]}
    journal = client.get("/api/v1/audit/journal?category=organization")
    assert journal.status_code == 200
    assert any(item["id"] == str(policy_events[0].id) and len(item["safe_changes"]) == 3
               for item in journal.json()["items"])
    assert client.patch("/api/v1/management/notification-settings", json={
        "schedule_missing_alert_enabled": False,
    }).status_code == 200
    assert len(db.scalars(select(AuditEvent).where(
        AuditEvent.organization_id == organization.id,
        AuditEvent.action == "organization.settings_update",
    )).all()) == 1
    assert client.get("/api/v1/management/control").json()["event_notifications"] == []
    assert db.get(Notification, notice.id).read_at is None
    assert client.get("/api/v1/management/notifications?status=all").json()["items"][0]["id"] == str(notice.id)
    assert client.patch("/api/v1/management/notification-settings", json={"schedule_missing_alert_enabled": None}).status_code == 400
    fixed = datetime(2026, 10, 12, 12, 0, tzinfo=ZoneInfo("Europe/Moscow"))
    monkeypatch.setattr(management_control, "organization_now", lambda _organization: fixed)
    group = Group(organization_id=organization.id, name="Группа времени", status="active")
    db.add(group); db.flush()
    assert "attendance_missing" not in {item["kind"] for item in _alerts(client)}
    assert client.patch("/api/v1/management/settings", json={"timezone": "America/Los_Angeles"}).status_code == 200
    assert client.get("/api/v1/management/settings").json()["timezone"] == "America/Los_Angeles"
    assert client.get("/api/v1/management/security-status").json()["failed_or_expired_parent_invites"] == 1
    _logout(client); _login(client, admin.username)
    assert client.get("/api/v1/management/notification-settings").status_code == 403
    assert client.patch("/api/v1/management/notification-settings", json={"schedule_missing_alert_enabled": True}).status_code == 403
    assert client.get("/api/v1/management/security-status").status_code == 403
    _logout(client); _login(client, parent.username)
    assert client.get("/api/v1/management/control").status_code == 403


def test_control_migration_roundtrip(migrations):
    """One reversible E migration; previous 0017 remains intact."""
    from sqlalchemy import inspect

    from app.db.session import engine

    config = Config("alembic.ini")
    try:
        command.downgrade(config, "0017")
        tables = inspect(engine).get_table_names()
        assert "operational_alert_states" not in tables
        assert "organization_notification_settings" not in tables
    finally:
        command.upgrade(config, "0018")
    tables = inspect(engine).get_table_names()
    assert "operational_alert_states" in tables and "organization_notification_settings" in tables

"""Synthetic PostgreSQL HTTP coverage for tenant-scoped live Control and settings."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, time, timedelta
from threading import Barrier
from time import sleep
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from alembic.config import Config
from sqlalchemy import delete, event, select
from sqlalchemy.orm import Session

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
from app.models.organization import Organization
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.services import audit, management_control
from tests.test_stage6_management_cabinet import _director, _login, _logout


def _alerts(client):
    response = client.get("/api/v1/management/control")
    assert response.status_code == 200, response.text
    return response.json()["alerts"]


def test_overdue_occurrence_survives_edits_and_rotates_only_after_resolution(client, db, users):
    organization, other, director, _admin = users
    _director(client, db, users)
    employees = [Employee(organization_id=organization.id, first_name="Тест", last_name=f"Сотрудник {index}",
                          position="Воспитатель", category="teacher", status="active") for index in range(2)]
    for index, employee in enumerate(employees):
        teacher = User(organization_id=organization.id, username=f"control-overdue-teacher-{index}",
                       password_hash=director.password_hash, role="TEACHER", status="active", must_change_password=False)
        db.add(teacher); db.flush()
        employee.user_id = teacher.id
    db.add_all(employees); db.flush()
    url = "/api/v1/teacher-management/tasks"
    past = datetime.now(UTC) - timedelta(days=1)

    def create():
        response = client.post(url, json={"assignee_employee_id": str(employees[0].id),
                                         "title": "Синтетическая задача", "due_at": past.isoformat()})
        assert response.status_code == 201, response.text
        return response.json()["id"]

    def alert():
        return next(item for item in _alerts(client) if item["kind"] == "tasks_overdue")

    task_id = create()
    key = alert()["alert_key"]
    assert client.post("/api/v1/management/control/alerts/snooze", json={
        "alert_key": key, "duration": "one_hour",
    }).status_code == 200
    for index, patch in enumerate(({"description": "Синтетическое описание"},
                                  {"assignee_employee_id": str(employees[1].id)}, {"status": "in_progress"},
                                  {"due_at": (past - timedelta(hours=1)).isoformat()})):
        response = client.patch(f"{url}/{task_id}", json=patch)
        assert response.status_code == 200, response.text
        # The rollback fixture keeps one PostgreSQL transaction timestamp; emulate
        # updated_at advancing as it does across separate real HTTP transactions.
        db.get(TeacherTask, UUID(task_id)).updated_at = datetime.now(UTC) + timedelta(seconds=index + 1)
        db.flush()
        current = alert()
        assert current["alert_key"] == key and current["snoozed_until"] is not None
    second_id = create()
    assert alert()["alert_key"] == key
    assert client.patch(f"{url}/{task_id}", json={"status": "done"}).status_code == 200
    assert alert()["alert_key"] == key
    assert client.patch(f"{url}/{second_id}", json={"status": "done"}).status_code == 200
    assert not any(item["kind"] == "tasks_overdue" for item in _alerts(client))
    assert client.patch(f"{url}/{task_id}", json={"status": "open"}).status_code == 200
    fresh = alert()
    assert fresh["alert_key"] != key and fresh["viewed_at"] is None and fresh["snoozed_until"] is None
    assert client.post("/api/v1/management/control/alerts/view", json={"alert_key": key}).status_code == 404
    fresh_key = fresh["alert_key"]
    assert client.post("/api/v1/management/control/alerts/view", json={"alert_key": fresh_key}).status_code == 200
    _logout(client); _login(client, "control-overdue-teacher-1")
    # Resolve and recur without a manager polling during the inactive interval.
    assert client.patch(f"/api/v1/teacher/tasks/{task_id}", json={"status": "done"}).status_code == 200
    assert client.patch(f"/api/v1/teacher/tasks/{task_id}", json={"status": "open"}).status_code == 200
    _logout(client); _login(client, director.username)
    assert alert()["alert_key"] != fresh_key and alert()["viewed_at"] is None
    events = db.scalars(select(AuditEvent).where(AuditEvent.organization_id == organization.id,
                                               AuditEvent.entity_type == "teacher_task")).all()
    assert all("Синтетическое описание" not in str(event.details) for event in events)
    assert not db.scalars(select(AuditEvent).where(AuditEvent.organization_id == other.id)).all()


@pytest.mark.parametrize("source", ["account", "guardian"])
@pytest.mark.parametrize("delivery", ["failed", "expired"])
def test_parent_invite_recurrence_versions_account_and_guardian(client, db, users, source, delivery):
    organization, other, director, _admin = users
    _director(client, db, users)
    parent = User(organization_id=organization.id, username="control-recurring-parent",
                  password_hash=director.password_hash, role="PARENT", status="active", must_change_password=False)
    db.add(parent); db.flush()
    guardian = Guardian(organization_id=organization.id, user_id=parent.id, first_name="Тест",
                        last_name="Синтетический", status="active")
    db.add(guardian); db.flush()
    token = AccountAccessToken(organization_id=organization.id, user_id=parent.id, guardian_id=guardian.id,
                              purpose="activation", token_digest="b" * 64,
                              delivery_status="failed" if delivery == "failed" else "sent",
                              expires_at=datetime.now(UTC) + timedelta(days=1 if delivery == "failed" else -1))
    db.add(token); db.flush()

    def alert():
        return next(item for item in _alerts(client) if item["kind"] == "parent_invite_failed_or_expired")

    key = alert()["alert_key"]
    assert client.post("/api/v1/management/control/alerts/snooze", json={
        "alert_key": key, "duration": "one_hour",
    }).status_code == 200
    row = parent if source == "account" else guardian
    row.status = "blocked" if source == "account" else "archived"
    row.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    db.flush()
    assert not any(item["kind"] == "parent_invite_failed_or_expired" for item in _alerts(client))
    row.status = "active"
    row.updated_at += timedelta(seconds=1)
    db.flush()
    fresh = alert()
    assert fresh["alert_key"] != key and fresh["viewed_at"] is None and fresh["snoozed_until"] is None
    assert client.post("/api/v1/management/control/alerts/view", json={"alert_key": key}).status_code == 404
    assert token.used_at is None and token.revoked_at is None
    _logout(client)
    director.organization_id = other.id
    db.flush()
    _login(client, director.username)
    assert not any(item["kind"] == "parent_invite_failed_or_expired" for item in _alerts(client))


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
    assignment = TeacherGroupAssignment(organization_id=organization.id, employee_id=employee.id,
                                        group_id=group.id, status="active", assigned_by=director.id)
    db.add(assignment)
    db.add(GroupScheduleItem(organization_id=organization.id, group_id=group.id, weekday=0,
                             start_time=time(9), end_time=time(10), title="Занятие", status="active",
                             created_by=director.id, updated_by=director.id))
    task.status = "done"
    db.flush()
    kinds = {item["kind"] for item in _alerts(client)}
    assert "group_without_teacher" not in kinds and "group_without_schedule" not in kinds and "tasks_overdue" not in kinds
    assignment.status = "archived"
    assignment.archived_at = datetime.now(UTC) + timedelta(seconds=1)
    db.flush()
    recurrence = next(item for item in _alerts(client) if item["kind"] == "group_without_teacher")
    assert recurrence["alert_key"] != key
    assert recurrence["viewed_at"] is None
    _logout(client); _login(client, teacher.username)
    assert client.get("/api/v1/management/control").status_code == 403


def test_control_settings_invites_notifications_timezone_and_role(client, db, users, monkeypatch):
    organization, _other, director, admin = users
    _director(client, db, users)
    assert client.patch("/api/v1/management/notification-settings", json={
        "show_informational_notifications": True,
        "attendance_checkpoint_time": None,
        "schedule_missing_alert_enabled": True,
    }).status_code == 200
    assert db.scalars(select(AuditEvent).where(
        AuditEvent.organization_id == organization.id,
        AuditEvent.action == "organization.settings_update",
    )).all() == []
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


def test_teacher_account_reblocking_creates_new_alert(client, db, users):
    organization, _other, director, _admin = users
    _director(client, db, users)
    teacher = User(organization_id=organization.id, username="control-reblocking-teacher",
                   password_hash=director.password_hash, role="TEACHER", status="active",
                   must_change_password=False)
    group = Group(organization_id=organization.id, name="Повторное условие", status="active")
    db.add_all([teacher, group]); db.flush()
    employee = Employee(organization_id=organization.id, user_id=teacher.id,
                        first_name="Анна", last_name="Синтетическая", position="Воспитатель",
                        category="teacher", status="active")
    db.add(employee); db.flush()
    db.add(TeacherGroupAssignment(organization_id=organization.id, employee_id=employee.id,
                                 group_id=group.id, status="active", assigned_by=director.id))
    db.flush()
    assert not any(item["kind"] == "group_without_teacher" for item in _alerts(client))
    teacher.status = "blocked"
    teacher.updated_at = datetime.now(UTC) + timedelta(seconds=1)
    db.flush()
    first = next(item for item in _alerts(client) if item["kind"] == "group_without_teacher")
    key = first["alert_key"]
    assert client.post("/api/v1/management/control/alerts/snooze", json={
        "alert_key": key, "duration": "one_hour",
    }).status_code == 200
    teacher.status = "active"
    teacher.updated_at += timedelta(seconds=1)
    db.flush()
    assert not any(item["kind"] == "group_without_teacher" for item in _alerts(client))
    teacher.status = "blocked"
    teacher.updated_at += timedelta(seconds=1)
    db.flush()
    recurrence = next(item for item in _alerts(client) if item["kind"] == "group_without_teacher")
    assert recurrence["alert_key"] != key
    assert recurrence["viewed_at"] is None and recurrence["snoozed_until"] is None
    assert client.post("/api/v1/management/control/alerts/view", json={"alert_key": key}).status_code == 404


@pytest.mark.parametrize("operations", [("view", "view"), ("snooze", "snooze"), ("view", "snooze")])
def test_concurrent_first_alert_writes_are_idempotent_and_tenant_scoped(migrations, operations):
    """Exercise real independent PostgreSQL transactions, including the first INSERT race."""
    from app.db.session import engine

    owner_ids, organization_ids, keys = [], [], []
    with Session(engine) as setup:
        for _ in range(2):
            organization = Organization(name="Синтетическая конкурентная проверка", status="active",
                                        timezone="Europe/Moscow")
            setup.add(organization); setup.flush()
            owner = User(organization_id=organization.id, username=f"control-concurrent-{uuid4()}",
                         password_hash="unused-synthetic-hash", role="DIRECTOR", status="active",
                         must_change_password=False)
            group = Group(organization_id=organization.id, name="Синтетическая группа", status="active")
            setup.add_all([owner, group]); setup.flush()
            owner_ids.append(owner.id)
            organization_ids.append(organization.id)
            keys.append(next(alert.alert_key for alert in management_control.active_alerts(setup, owner)
                             if alert.kind == "group_without_teacher"))
        setup.commit()

    barrier = Barrier(4)

    def delay_first_insert(_mapper, _connection, _target):
        # Enlarge the absent-row window; row locks must protect the first INSERT too.
        sleep(0.1)

    def mutate(index, operation):
        with Session(engine) as transaction:
            owner = transaction.get(User, owner_ids[index])
            barrier.wait(timeout=10)
            if operation == "view":
                return management_control.view_alert(transaction, owner, keys[index])
            return management_control.snooze_alert(transaction, owner, keys[index], "one_hour")

    event.listen(OperationalAlertState, "before_insert", delay_first_insert)
    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(mutate, index, operation) for index in range(2) for operation in operations]
            for future in futures:
                assert future.result(timeout=20).viewed_at is not None
        with Session(engine) as verify:
            rows = verify.scalars(select(OperationalAlertState).where(
                OperationalAlertState.organization_id.in_(organization_ids),
            )).all()
            assert len(rows) == 2
            for index in range(2):
                row = next(row for row in rows if row.organization_id == organization_ids[index])
                assert row.user_id == owner_ids[index] and row.alert_key == keys[index]
                assert row.viewed_at is not None
                if "snooze" in operations:
                    assert datetime.now(UTC) < row.snoozed_until < datetime.now(UTC) + timedelta(hours=2)
                actor = verify.get(User, owner_ids[index])
                management_control.view_alert(verify, actor, keys[index])
                with pytest.raises(management_control.AppError) as error:
                    management_control.view_alert(verify, actor, keys[1 - index])
                assert error.value.status == 404
    finally:
        event.remove(OperationalAlertState, "before_insert", delay_first_insert)
        with Session(engine) as cleanup:
            cleanup.execute(delete(OperationalAlertState).where(OperationalAlertState.organization_id.in_(organization_ids)))
            cleanup.execute(delete(Group).where(Group.organization_id.in_(organization_ids)))
            cleanup.execute(delete(User).where(User.organization_id.in_(organization_ids)))
            cleanup.execute(delete(Organization).where(Organization.id.in_(organization_ids)))
            cleanup.commit()


def test_overdue_condition_never_loads_foreign_task_into_session(db, users):
    _organization, other, director, _admin = users
    employee = Employee(organization_id=other.id, first_name="Другой", last_name="Тестовый",
                        position="Воспитатель", category="teacher", status="active")
    foreign_actor = User(organization_id=other.id, username="foreign-overdue-director",
                         password_hash=director.password_hash, role="DIRECTOR", status="active",
                         must_change_password=False)
    db.add_all([employee, foreign_actor]); db.flush()
    task = TeacherTask(organization_id=other.id, assignee_employee_id=employee.id,
                       title="Чужая синтетическая задача", status="open",
                       due_at=datetime.now(UTC) - timedelta(days=1), created_by=foreign_actor.id)
    db.add(task); db.flush()
    task_id = task.id
    db.expunge(task)
    loaded_tasks = []

    def record_load(_session, instance):
        if isinstance(instance, TeacherTask):
            loaded_tasks.append(instance.id)

    event.listen(db, "loaded_as_persistent", record_load)
    try:
        assert audit._overdue_condition(db, director, "teacher_task.update", task_id) == {}
        assert audit._overdue_condition(db, director, "teacher_task.update", uuid4()) == {}
        assert loaded_tasks == []
        assert not any(isinstance(item, TeacherTask) for item in db.identity_map.values())
    finally:
        event.remove(db, "loaded_as_persistent", record_load)

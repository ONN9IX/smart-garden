"""Stage 4 Dashboard current-group, date, tenant, RBAC and query rules."""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select

from app.core import organization_time
from app.main import app
from app.models.attendance import Attendance
from app.models.audit_event import AuditEvent
from app.models.child import Child
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.user import User
from app.services import dashboard
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/dashboard/summary"
FROZEN_UTC = datetime(2026, 9, 28, 22, 30, tzinfo=UTC)


def _freeze_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FROZEN_UTC.astimezone(tz) if tz is not None else FROZEN_UTC.replace(tzinfo=None)

    monkeypatch.setattr(organization_time, "datetime", FrozenDateTime)


def _login(client, username: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200


def test_dashboard_counters_current_group_unknowns_and_no_audit(client, db, users, monkeypatch):
    _freeze_utc(monkeypatch)
    organization, other, director, _ = users
    director.must_change_password = False
    groups = [
        Group(organization_id=organization.id, name="Альфа", status="active"),
        Group(organization_id=organization.id, name="Бета", status="active"),
        Group(organization_id=organization.id, name="Архив", status="archived"),
    ]
    db.add_all(groups)
    db.flush()

    def child(group, first, status="active", tenant_id=None):
        return Child(
            organization_id=tenant_id or organization.id, group_id=group.id, first_name=first,
            last_name="Синтетический", birth_date=date(2020, 1, 1), status=status,
        )

    present = child(groups[0], "Присутствует")
    explicit_unknown = child(groups[0], "Неизвестно")
    missing = child(groups[1], "Без отметки")
    transferred_absent = child(groups[1], "Переведён")
    archived_child = child(groups[0], "Архивный ребёнок", "archived")
    archived_group_child = child(groups[2], "Ребёнок архивной группы")
    db.add_all([present, explicit_unknown, missing, transferred_absent, archived_child, archived_group_child])
    db.flush()
    day = date(2026, 9, 29)  # Europe/Moscow at the frozen UTC instant.

    def mark(item, status, snapshot_group):
        return Attendance(
            organization_id=organization.id, child_id=item.id, group_id=snapshot_group.id,
            date=day, status=status, created_by=director.id, updated_by=director.id,
        )

    db.add_all([
        mark(present, "present", groups[0]),
        mark(explicit_unknown, "unknown", groups[0]),
        mark(transferred_absent, "absent", groups[0]),
        mark(archived_child, "present", groups[0]),
        mark(archived_group_child, "present", groups[2]),
        Employee(organization_id=organization.id, first_name="Активный", last_name="Сотрудник", position="Тест", status="active"),
        Employee(organization_id=organization.id, first_name="Архивный", last_name="Сотрудник", position="Тест", status="archived"),
    ])
    foreign_group = Group(organization_id=other.id, name="Чужая", status="active")
    db.add(foreign_group)
    db.flush()
    db.add(child(foreign_group, "Не должен учитываться", tenant_id=other.id))
    db.commit()
    audit_before = len(list(db.scalars(select(AuditEvent).where(AuditEvent.organization_id == organization.id))))

    _login(client, director.username)
    response = client.get(ROOT)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["date"] == "2026-09-29"
    assert {key: payload[key] for key in (
        "active_children", "present", "on_site", "departed", "absent", "unknown", "needs_arrival", "active_groups", "active_employees",
    )} == {
        "active_children": 4, "present": 1, "on_site": 0, "departed": 0, "absent": 0, "unknown": 3, "needs_arrival": 1,
        "active_groups": 2, "active_employees": 1,
    }
    rows = {row["name"]: row for row in payload["groups"]}
    assert (rows["Альфа"]["active_children"], rows["Альфа"]["present"], rows["Альфа"]["unknown"], rows["Альфа"]["needs_arrival"]) == (2, 1, 1, 1)
    assert (rows["Бета"]["active_children"], rows["Бета"]["present"], rows["Бета"]["absent"], rows["Бета"]["unknown"]) == (2, 0, 0, 2)
    fields = ("active_children", "present", "on_site", "departed", "absent", "unknown", "needs_arrival")
    assert all(payload[key] == sum(row[key] for row in payload["groups"]) for key in fields)
    assert payload["active_children"] == sum(payload[key] for key in ("on_site", "departed", "absent", "unknown", "needs_arrival"))
    db.expire_all()
    assert len(list(db.scalars(select(AuditEvent).where(AuditEvent.organization_id == organization.id)))) == audit_before


def test_dashboard_fixed_query_count_timezone_and_access(client, db, users, monkeypatch):
    _freeze_utc(monkeypatch)
    organization, _, director, admin = users
    director.must_change_password = False
    organization.timezone = "America/Los_Angeles"
    db.commit()
    _ = director.organization
    statements: list[str] = []

    def count_selects(_conn, _cursor, statement, _parameters, _context, _executemany):
        if statement.lstrip().upper().startswith("SELECT"):
            statements.append(statement)

    event.listen(db.bind, "before_cursor_execute", count_selects)
    try:
        result = dashboard.summary(db, director)
    finally:
        event.remove(db.bind, "before_cursor_execute", count_selects)
    assert result.date.isoformat() == "2026-09-28"
    assert len(statements) == 3

    _login(client, admin.username)
    assert client.get(ROOT).status_code == 200
    client.post("/api/v1/auth/logout")
    parent = User(
        organization_id=organization.id, username="dashboard-parent", password_hash=admin.password_hash,
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


def test_dashboard_five_exclusive_attendance_states_and_present_compatibility(client, db, users, monkeypatch):
    _freeze_utc(monkeypatch)
    organization, _, director, _ = users
    director.must_change_password = False
    group = Group(organization_id=organization.id, name="Состояния", status="active")
    db.add(group)
    db.flush()
    children = [Child(
        organization_id=organization.id, group_id=group.id, first_name=f"Ребёнок{i}",
        last_name="Синтетический", birth_date=date(2020, 1, 1), status="active",
    ) for i in range(6)]
    db.add_all(children)
    db.flush()
    day = date(2026, 9, 29)
    records = [
        Attendance(organization_id=organization.id, child_id=children[1].id, group_id=group.id,
                   date=day, status="unknown", created_by=director.id, updated_by=director.id),
        Attendance(organization_id=organization.id, child_id=children[2].id, group_id=group.id,
                   date=day, status="absent", created_by=director.id, updated_by=director.id),
        Attendance(organization_id=organization.id, child_id=children[3].id, group_id=group.id,
                   date=day, status="present", created_by=director.id, updated_by=director.id),
        Attendance(organization_id=organization.id, child_id=children[4].id, group_id=group.id,
                   date=day, status="present", arrival_time=datetime.strptime("08:20", "%H:%M").time(),
                   created_by=director.id, updated_by=director.id),
        Attendance(organization_id=organization.id, child_id=children[5].id, group_id=group.id,
                   date=day, status="present", arrival_time=datetime.strptime("08:25", "%H:%M").time(),
                   departure_time=datetime.strptime("16:10", "%H:%M").time(), created_by=director.id, updated_by=director.id),
    ]
    db.add_all(records)
    db.commit()
    _login(client, director.username)
    payload = client.get(ROOT).json()
    assert {key: payload[key] for key in ("active_children", "present", "on_site", "departed", "absent", "unknown", "needs_arrival")} == {
        "active_children": 6, "present": 3, "on_site": 1, "departed": 1,
        "absent": 1, "unknown": 2, "needs_arrival": 1,
    }

"""PostgreSQL and API regressions for tenant-local Attendance calendar dates."""

import uuid
from datetime import UTC, datetime

import pytest
from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.core import organization_time
from app.core.security import hash_password
from app.db.session import engine
from app.models.organization import Organization
from app.models.user import User
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/attendance"
FROZEN_UTC = datetime(2026, 9, 26, 21, 30, tzinfo=UTC)


def _freeze_utc(monkeypatch: pytest.MonkeyPatch) -> None:
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return FROZEN_UTC.astimezone(tz) if tz is not None else FROZEN_UTC.replace(tzinfo=None)

    monkeypatch.setattr(organization_time, "datetime", FrozenDateTime)


def _login(client, username: str) -> None:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200


def _child(client, suffix: str) -> str:
    group = client.post("/api/v1/groups", json={"name": f"Timezone group {suffix}"})
    assert group.status_code == 201
    child = client.post("/api/v1/children", json={
        "group_id": group.json()["id"], "first_name": "Тестовый", "last_name": f"Ребёнок {suffix}",
        "birth_date": "2020-01-01",
    })
    assert child.status_code == 201
    return child.json()["id"]


def test_moscow_boundary_post_and_list_use_garden_today(client, users, monkeypatch):
    _freeze_utc(monkeypatch)
    _login(client, "admin-test")
    child_id = _child(client, "Moscow")

    today = client.post(ROOT, json={"child_id": child_id, "date": "2026-09-27", "status": "present"})
    assert today.status_code == 201
    assert client.get(ROOT, params={"date": "2026-09-27"}).status_code == 200

    future = client.post(ROOT, json={"child_id": child_id, "date": "2026-09-28", "status": "absent"})
    assert future.status_code == 400
    assert future.json()["error"]["code"] == "INVALID_ATTENDANCE_DATE"
    future_list = client.get(ROOT, params={"date": "2026-09-28"})
    assert future_list.status_code == 400
    assert future_list.json()["error"]["code"] == "INVALID_ATTENDANCE_DATE"


def test_same_instant_uses_each_tenant_timezone(client, db, users, monkeypatch):
    _freeze_utc(monkeypatch)
    western = User(
        organization_id=users[1].id, username="western-timezone-admin",
        password_hash=hash_password(TEST_PASSWORD), role="ADMIN", status="active", must_change_password=False,
    )
    db.add(western)
    db.flush()

    _login(client, "admin-test")
    moscow_child = _child(client, "Moscow tenant")
    assert client.post(ROOT, json={
        "child_id": moscow_child, "date": "2026-09-27", "status": "unknown",
    }).status_code == 201
    assert client.post("/api/v1/auth/logout").status_code == 200

    _login(client, western.username)
    western_child = _child(client, "Western tenant")
    previous_day = client.post(ROOT, json={
        "child_id": western_child, "date": "2026-09-26", "status": "present",
    })
    assert previous_day.status_code == 201
    assert client.get(ROOT, params={"date": "2026-09-26"}).status_code == 200

    western_future = client.post(ROOT, json={
        "child_id": western_child, "date": "2026-09-27", "status": "absent",
    })
    assert western_future.status_code == 400
    assert western_future.json()["error"]["code"] == "INVALID_ATTENDANCE_DATE"
    assert client.get(ROOT, params={"date": "2026-09-27"}).status_code == 400


def test_timezone_validation_rejects_non_iana_value():
    with pytest.raises(ValueError, match="valid IANA timezone"):
        Organization(name="Invalid timezone tenant", status="active", timezone="UTC+03:00")

    with pytest.raises(ValueError, match="valid IANA timezone"):
        organization_time.organization_today(
            OrganizationClockStub(timezone="Invalid/Timezone"),
        )


class OrganizationClockStub:
    def __init__(self, timezone: str) -> None:
        self.timezone = timezone


def test_0009_migration_backfill_not_null_default_and_round_trip(migrations):
    config = Config("alembic.ini")
    existing_id = uuid.uuid4()
    default_id = uuid.uuid4()
    try:
        command.downgrade(config, "0008")
        with engine.begin() as connection:
            connection.execute(text(
                "INSERT INTO organizations (id, name, status) "
                "VALUES (:id, 'Existing synthetic tenant', 'active')",
            ), {"id": existing_id})

        command.upgrade(config, "0009")
        with engine.begin() as connection:
            columns = {column["name"]: column for column in inspect(connection).get_columns("organizations")}
            assert columns["timezone"]["nullable"] is False
            assert columns["timezone"]["type"].length == 64
            assert connection.scalar(text(
                "SELECT timezone FROM organizations WHERE id = :id",
            ), {"id": existing_id}) == "Europe/Moscow"
            connection.execute(text(
                "INSERT INTO organizations (id, name, status) "
                "VALUES (:id, 'New synthetic tenant', 'active')",
            ), {"id": default_id})
            assert connection.scalar(text(
                "SELECT timezone FROM organizations WHERE id = :id",
            ), {"id": default_id}) == "Europe/Moscow"

        command.downgrade(config, "0008")
        with engine.connect() as connection:
            assert "timezone" not in {column["name"] for column in inspect(connection).get_columns("organizations")}

        command.upgrade(config, "0009")
        with engine.connect() as connection:
            values = connection.execute(text(
                "SELECT timezone FROM organizations WHERE id IN (:first, :second) ORDER BY id",
            ), {"first": existing_id, "second": default_id}).scalars().all()
            assert values == ["Europe/Moscow", "Europe/Moscow"]
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(text(
                "DELETE FROM organizations WHERE id IN (:first, :second)",
            ), {"first": existing_id, "second": default_id})

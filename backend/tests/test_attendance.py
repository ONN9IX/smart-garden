"""PostgreSQL attendance contract: unknown, upsert, history and tenant boundaries."""

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient

from app.main import app
from app.models.child import Child
from app.models.group import Group
from tests.conftest import TEST_PASSWORD

ROOT = "/api/v1/attendance"
DAY = "2025-09-20"


def _login(client):
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200


def _group(client, name):
    response = client.post("/api/v1/groups", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _child(client, group_id):
    response = client.post("/api/v1/children", json={"group_id": group_id, "first_name": "Ира", "last_name": "Тестовая", "birth_date": "2020-01-01"})
    assert response.status_code == 201
    return response.json()["id"]


def test_day_upsert_patch_and_group_snapshot(client, db, users):
    _login(client)
    first = _group(client, "Ромашка")
    second = _group(client, "Лилия")
    child = _child(client, first)
    day = client.get(ROOT, params={"date": DAY}).json()["items"]
    assert len(day) == 1 and day[0]["status"] == "unknown" and day[0]["record_id"] is None
    assert client.get(ROOT, params={"date": DAY, "status": "present"}).json()["items"] == []
    payload = {"child_id": child, "date": DAY, "status": "present", "arrival_time": "08:30"}
    created = client.post(ROOT, json=payload)
    assert created.status_code == 201
    record_id = created.json()["record_id"]
    assert created.json()["group"]["id"] == first
    changed = client.post(ROOT, json={**payload, "status": "absent", "arrival_time": None})
    assert changed.status_code == 200 and changed.json()["record_id"] == record_id
    assert changed.json()["created_by"] == created.json()["created_by"]
    assert changed.json()["arrival_time"] is None
    assert client.patch(f"{ROOT}/{record_id}", json={"status": "present", "arrival_time": "09:00", "departure_time": "15:00"}).status_code == 200
    assert client.patch(f"{ROOT}/{record_id}", json={"status": "absent"}).json()["departure_time"] is None
    assert client.patch(f"{ROOT}/{record_id}", json={"departure_time": "10:00"}).json()["error"]["code"] == "INVALID_ATTENDANCE_TIME"
    assert client.post(ROOT, json={**payload, "departure_time": "07:00"}).status_code == 400
    assert client.post(ROOT, json={**payload, "date": str(datetime.now(UTC).date() + timedelta(days=2))}).json()["error"]["code"] == "INVALID_ATTENDANCE_DATE"
    assert client.patch(f"{ROOT}/{record_id}", json={"child_id": child}).status_code == 400

    assert client.patch(f"/api/v1/children/{child}", json={"group_id": second}).status_code == 200
    assert client.get(ROOT, params={"date": DAY, "group_id": first}).json()["items"][0]["record_id"] == record_id
    assert client.get(ROOT, params={"date": DAY, "group_id": second}).json()["items"] == []
    assert client.post(f"/api/v1/children/{child}/archive").status_code == 200
    assert client.get(ROOT, params={"date": DAY}).json()["items"][0]["child"]["status"] == "archived"
    assert client.post(ROOT, json=payload).json()["error"]["code"] == "CHILD_ARCHIVED"


def test_tenant_and_role_boundaries(client, db, users):
    _, other, _, _ = users
    _login(client)
    group_id = _group(client, "Василёк")
    child_id = _child(client, group_id)
    record_id = client.post(ROOT, json={"child_id": child_id, "date": DAY, "status": "unknown"}).json()["record_id"]
    foreign_group = Group(organization_id=other.id, name="Чужая", status="active")
    db.add(foreign_group)
    db.flush()
    foreign_child = Child(organization_id=other.id, group_id=foreign_group.id,
                          first_name="Другой", last_name="Ребёнок", birth_date=date(2020, 1, 1), status="active")
    db.add(foreign_child)
    db.flush()
    assert client.get(ROOT, params={"date": DAY, "group_id": str(foreign_group.id)}).status_code == 404
    assert client.get(ROOT, params={"date": DAY, "child_id": str(foreign_child.id)}).status_code == 404
    assert client.post(ROOT, json={"child_id": str(foreign_child.id), "date": DAY, "status": "absent"}).status_code == 404
    assert client.get(f"{ROOT}/{record_id}").status_code == 200
    with TestClient(app) as anonymous:
        assert anonymous.get(ROOT, params={"date": DAY}).status_code == 401

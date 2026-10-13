"""Safe, tenant-scoped initial staff/schedule batch preview and replay tests."""
from uuid import uuid4

from sqlalchemy import func, select

from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from tests.conftest import TEST_PASSWORD


def test_preview_apply_is_atomic_tenant_scoped_and_idempotent(client, db, users):
    organization, other, director, _ = users
    director.must_change_password = False
    organization.operating_profile = "GYMNASTICS"
    own_group = Group(organization_id=organization.id, name="Синтетическая секция", status="active")
    foreign_group = Group(organization_id=other.id, name="Чужая секция", status="active")
    db.add_all([own_group, foreign_group])
    db.flush()
    login = client.post("/api/v1/auth/login", json={"username": director.username, "password": TEST_PASSWORD})
    assert login.status_code == 200
    payload = {
        "idempotency_key": str(uuid4()),
        "employees": [{"first_name": "Ирина", "last_name": "Примерова", "position": "Тренер", "category": "teacher"}],
        "schedules": [{"group_id": str(own_group.id), "weekday": 1, "start_time": "10:00", "end_time": "11:00", "title": "Тренировка"}],
    }
    preview = client.post("/api/v1/management/initial-setup/preview", json=payload)
    assert preview.status_code == 200, preview.text
    assert preview.json()["ready"] is True
    apply_data = {**payload, "request_digest": preview.json()["request_digest"], "confirmed": True}
    first = client.post("/api/v1/management/initial-setup/apply", json=apply_data)
    assert first.status_code == 200, first.text
    assert first.json()["employee_count"] == 1 and first.json()["schedule_count"] == 1
    replay = client.post("/api/v1/management/initial-setup/apply", json=apply_data)
    assert replay.status_code == 200 and replay.json()["replayed"] is True
    assert db.scalar(select(func.count(Employee.id)).where(Employee.organization_id == organization.id)) == 1
    assert db.scalar(select(Employee.user_id).where(Employee.organization_id == organization.id)) is None
    assert db.scalar(select(func.count(GroupScheduleItem.id)).where(GroupScheduleItem.organization_id == organization.id)) == 1

    foreign_payload = {**payload, "idempotency_key": str(uuid4()), "schedules": [{
        "group_id": str(foreign_group.id), "weekday": 1, "start_time": "12:00", "end_time": "13:00", "title": "Не попадёт в другую организацию",
    }]}
    rejected = client.post("/api/v1/management/initial-setup/preview", json=foreign_payload)
    assert rejected.status_code == 200 and rejected.json()["ready"] is False
    assert rejected.json()["schedule_rows"][0]["status"] == "invalid"

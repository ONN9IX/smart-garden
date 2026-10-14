"""Operating profile and explicitly assigned gymnastics owner-coach coverage."""

from sqlalchemy import select

from app.core.organization_time import organization_today
from app.models.communication import CommunicationMessage, CommunicationThread
from app.models.employee import Employee
from app.models.group import Group
from tests.conftest import TEST_PASSWORD


def _login(client, username="director-test"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200, response.text


def test_legacy_profile_default_and_authenticated_context(client, db, users):
    organization, _, director, _ = users
    director.must_change_password = False
    db.flush()
    _login(client)
    context = client.get("/api/v1/auth/me")
    assert context.status_code == 200
    assert context.json()["organization"]["operating_profile"] == "KINDERGARTEN"
    assert client.get("/api/v1/teacher/today").status_code == 403
    assert organization.operating_profile == "KINDERGARTEN"


def test_gymnastics_owner_can_self_register_as_coach_and_only_access_assigned_groups(client, db, users):
    organization, other, director, _ = users
    organization.operating_profile = "GYMNASTICS"
    director.must_change_password = False
    assigned = Group(organization_id=organization.id, name="Синтетическая группа", status="active")
    unassigned = Group(organization_id=organization.id, name="Другая группа", status="active")
    foreign = Group(organization_id=other.id, name="Чужая группа", status="active")
    db.add_all([assigned, unassigned, foreign])
    db.flush()
    unassigned_thread = CommunicationThread(
        organization_id=organization.id, thread_type="group", audience="all", group_id=unassigned.id,
    )
    db.add(unassigned_thread)
    db.flush()
    db.add(CommunicationMessage(
        organization_id=organization.id,
        thread_id=unassigned_thread.id,
        sender_user_id=director.id,
        body="Синтетическое сообщение чужой группы",
    ))
    db.flush()
    _login(client)
    assert client.get("/api/v1/attendance", params={"date": organization_today(organization).isoformat()}).status_code == 403
    profile = client.post("/api/v1/employees/me/coach-profile", json={"first_name": "Алексей", "last_name": "Примеров"})
    assert profile.status_code == 201, profile.text
    employee = db.scalar(select(Employee).where(Employee.user_id == director.id))
    assert employee is not None and employee.category == "teacher" and employee.status == "active"
    assert client.post("/api/v1/employees/me/coach-profile", json={"first_name": "Алексей", "last_name": "Примеров"}).status_code == 409
    assert client.get("/api/v1/teacher/today").json()["groups"] == []
    assert client.get(f"/api/v1/teacher/groups/{unassigned.id}/children").status_code == 404
    assert client.get(f"/api/v1/teacher/groups/{foreign.id}/children").status_code == 404
    assert client.get("/api/v1/teacher/photos").status_code in {403, 404}
    assert client.post("/api/v1/teacher/attendance/arrival", json={"child_id": "00000000-0000-0000-0000-000000000001"}).status_code == 403
    assignment = client.post("/api/v1/teacher-management/assignments", json={
        "employee_id": str(employee.id), "group_id": str(assigned.id),
    })
    assert assignment.status_code in {200, 201}, assignment.text
    assert client.get("/api/v1/teacher/today").json()["groups"][0]["id"] == str(assigned.id)
    assert client.get(f"/api/v1/teacher/groups/{assigned.id}/children").status_code == 200
    assigned_thread = client.get(
        f"/api/v1/teacher/communications/v2/groups/{assigned.id}/thread",
    )
    assert assigned_thread.status_code == 200, assigned_thread.text
    assert client.get(
        f"/api/v1/teacher/communications/v2/groups/{unassigned.id}/thread",
    ).status_code == 404
    message = client.post(
        f"/api/v1/teacher/communications/v2/threads/{assigned_thread.json()['id']}/messages",
        json={"body": "Сообщение coach профиля", "client_message_id": "e6c4ca5a-a9cc-40c9-b00a-b1734d96d40a"},
    )
    assert message.status_code == 201, message.text
    visible_threads = client.get("/api/v1/teacher/communications/v2/threads")
    assert visible_threads.status_code == 200, visible_threads.text
    assert {item["group_id"] for item in visible_threads.json()} == {str(assigned.id)}
    assert all("чужой группы" not in (item["preview"] or "") for item in visible_threads.json())
    assert client.get(
        f"/api/v1/teacher/communications/v2/threads/{assigned_thread.json()['id']}/messages",
    ).status_code == 200

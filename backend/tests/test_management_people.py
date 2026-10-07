"""DIRECTOR-V2-B synthetic People, Family, Group projection and transfer coverage."""

from datetime import date, datetime, time, timedelta, timezone

from sqlalchemy import func, select

from app.models.attendance import Attendance
from app.models.auth_session import AuthSession
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.services.auth import issue_session
from tests.conftest import TEST_PASSWORD


def _login(client, username="director-test"):
    response = client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD})
    assert response.status_code == 200


def _local_today(organization):
    from app.core.organization_time import organization_today

    return organization_today(organization)


def _group(db, organization_id, name):
    item = Group(organization_id=organization_id, name=name, status="active")
    db.add(item)
    db.flush()
    return item


def test_atomic_family_creation_and_tenant_scoped_duplicate_warnings(client, db, users):
    organization, other, director, _ = users
    director.must_change_password = False
    db.flush()
    _login(client)
    group = _group(db, organization.id, "Семейная группа")
    existing = Guardian(
        organization_id=organization.id, first_name="Анна", last_name="Примерова",
        phone="+7 (999) 222-33-44", email="anna@example.test", status="active",
    )
    foreign = Guardian(
        organization_id=other.id, first_name="Анна", last_name="Примерова",
        email="anna@example.test", status="active",
    )
    db.add_all([existing, foreign])
    db.flush()

    response = client.post("/api/v1/management/families", json={
        "child": {
            "group_id": str(group.id), "first_name": "Кирилл", "last_name": "Иванов",
            "middle_name": None, "birth_date": "2021-02-03",
        },
        "guardians": [
            {"guardian_id": str(existing.id), "relation_type": "mother"},
            {"new_guardian": {
                "first_name": "Сергей", "last_name": "Иванов", "middle_name": "Петрович",
                "phone": None, "email": None,
            }, "relation_type": "father"},
        ],
    })
    assert response.status_code == 201, response.text
    child = response.json()
    assert len(child["guardians"]) == 2
    assert child["group"]["id"] == str(group.id)
    assert db.scalar(select(func.count(Guardian.id)).where(Guardian.organization_id == organization.id)) == 2

    before = db.scalar(select(func.count(Child.id)).where(Child.organization_id == organization.id))
    rejected = client.post("/api/v1/management/families", json={
        "child": {
            "group_id": str(group.id), "first_name": "Не", "last_name": "Создать",
            "birth_date": "2021-02-04",
        },
        "guardians": [{"guardian_id": str(foreign.id), "relation_type": "other"}],
    })
    assert rejected.status_code == 404
    assert db.scalar(select(func.count(Child.id)).where(Child.organization_id == organization.id)) == before

    duplicate = client.post("/api/v1/management/people/duplicates", json={
        "kind": "guardian", "first_name": "Совсем", "last_name": "Другие",
        "phone": "7 999-222-33-44", "email": None,
    })
    assert duplicate.status_code == 200
    assert [item["id"] for item in duplicate.json()["matches"]] == [str(existing.id)]
    child_match = client.post("/api/v1/management/people/duplicates", json={
        "kind": "child", "first_name": "Кирилл", "last_name": "Иванов",
        "birth_date": "2021-02-03",
    })
    assert len(child_match.json()["matches"]) == 1


def test_group_profile_is_aggregated_tenant_scoped_and_uses_current_attendance(db, client, users):
    organization, other, director, admin = users
    _login(client, "admin-test")
    group = _group(db, organization.id, "Ромашка")
    foreign_group = _group(db, other.id, "Чужая")
    children = [Child(
        organization_id=organization.id, group_id=group.id, first_name=first,
        last_name="Ребёнок", birth_date=date(2021, 1, index + 1), status="active",
    ) for index, first in enumerate(("Кирилл", "Анна"))]
    guardian = Guardian(
        organization_id=organization.id, first_name="Иван", last_name="Представитель", status="active",
    )
    teacher = User(
        organization_id=organization.id, username="group-profile-teacher", password_hash="synthetic",
        role="TEACHER", status="active", must_change_password=False,
    )
    db.add_all([*children, guardian, teacher])
    db.flush()
    employee = Employee(
        organization_id=organization.id, user_id=teacher.id, first_name="Мария", last_name="Воспитатель",
        position="Воспитатель", category="teacher", status="active",
    )
    db.add(employee)
    db.flush()
    db.add_all([
        ChildGuardian(organization_id=organization.id, child_id=children[0].id, guardian_id=guardian.id,
                     relation_type="mother", status="active"),
        TeacherGroupAssignment(organization_id=organization.id, employee_id=employee.id, group_id=group.id,
                               assigned_by=director.id, status="active"),
        Attendance(organization_id=organization.id, child_id=children[0].id, group_id=group.id,
                   date=_local_today(organization), status="present", created_by=director.id, updated_by=director.id),
        GroupScheduleItem(organization_id=organization.id, group_id=group.id, weekday=1,
                          start_time=time(9), end_time=time(10), title="Сбор", status="active",
                          created_by=director.id, updated_by=director.id),
        TeacherTask(organization_id=organization.id, assignee_employee_id=employee.id, group_id=group.id,
                    title="Подготовить группу", status="open", due_at=datetime.now(timezone.utc) - timedelta(days=1),
                    created_by=director.id),
    ])
    db.flush()

    result = client.get(f"/api/v1/management/groups/{group.id}/profile")
    assert result.status_code == 200, result.text
    profile = result.json()
    assert profile["active_children"] == 2
    assert profile["present"] == 1 and profile["unknown"] == 1 and profile["absent"] == 0
    assert profile["active_teacher_count"] == 1 and profile["parent_count"] == 1
    assert profile["active_schedule_count"] == 1
    assert profile["open_tasks"] == 1 and profile["overdue_tasks"] == 1
    assert len(profile["children"]) == 2 and len(profile["employees"]) == 1
    assert client.get(f"/api/v1/management/groups/{foreign_group.id}/profile").status_code == 404
    overviews = client.get("/api/v1/management/groups/overview").json()["items"]
    assert [item["group"]["id"] for item in overviews] == [str(group.id)]
    assert admin.organization_id == organization.id


def test_transfer_changes_current_group_and_keeps_attendance_snapshot(client, db, users):
    organization, other, director, _ = users
    director.must_change_password = False
    db.flush()
    _login(client)
    old_group = _group(db, organization.id, "Старая группа")
    new_group = _group(db, organization.id, "Новая группа")
    foreign_group = _group(db, other.id, "Другая организация")
    child = Child(
        organization_id=organization.id, group_id=old_group.id, first_name="Кирилл",
        last_name="Иванов", birth_date=date(2021, 1, 1), status="active",
    )
    db.add(child)
    db.flush()
    attendance = Attendance(
        organization_id=organization.id, child_id=child.id, group_id=old_group.id,
        date=date(2025, 4, 12), status="present", created_by=director.id, updated_by=director.id,
    )
    db.add(attendance)
    db.flush()

    moved = client.post(f"/api/v1/children/{child.id}/transfer", json={"group_id": str(new_group.id)})
    assert moved.status_code == 200 and moved.json()["group"]["id"] == str(new_group.id)
    db.refresh(attendance)
    assert attendance.group_id == old_group.id
    assert client.patch(f"/api/v1/children/{child.id}", json={"group_id": str(old_group.id)}).status_code == 409
    assert client.post(f"/api/v1/children/{child.id}/transfer", json={"group_id": str(foreign_group.id)}).status_code == 404


def test_employee_archive_archives_assignments_and_restore_keeps_access_blocked(client, db, users):
    organization, _, director, _ = users
    director.must_change_password = False
    db.flush()
    _login(client)
    group = _group(db, organization.id, "Архив сотрудников")
    teacher = User(
        organization_id=organization.id, username="archive-b-teacher", password_hash="synthetic",
        role="TEACHER", status="active", must_change_password=False,
    )
    db.add(teacher)
    db.flush()
    employee = Employee(
        organization_id=organization.id, user_id=teacher.id, first_name="Елена", last_name="Учитель",
        position="Воспитатель", category="teacher", status="active",
    )
    db.add(employee)
    db.flush()
    assignment = TeacherGroupAssignment(
        organization_id=organization.id, employee_id=employee.id, group_id=group.id,
        assigned_by=director.id, status="active",
    )
    db.add(assignment)
    token = issue_session(db, teacher)
    db.flush()

    archived = client.post(f"/api/v1/employees/{employee.id}/archive")
    assert archived.status_code == 200
    db.refresh(assignment)
    db.refresh(teacher)
    assert assignment.status == "archived" and assignment.archived_at is not None
    assert teacher.status == "blocked"
    session = db.scalar(select(AuthSession).where(AuthSession.user_id == teacher.id, AuthSession.revoked_at.is_not(None)))
    assert session is not None and token

    restored = client.post(f"/api/v1/employees/{employee.id}/restore")
    assert restored.status_code == 200
    db.refresh(assignment)
    assert restored.json()["account"]["status"] == "blocked"
    assert assignment.status == "archived"

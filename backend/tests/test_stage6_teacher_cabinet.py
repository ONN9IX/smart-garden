"""Complete Stage 6 TEACHER cabinet security, privacy and workflow coverage."""

import struct
import zlib
from datetime import UTC, date, datetime, time, timedelta
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.core.organization_time import organization_today
from app.core.product_features import PRODUCT_FEATURES
from app.core.security import hash_password
from app.main import app
from app.models.announcement import Announcement
from app.models.attendance import Attendance
from app.models.audit_event import AuditEvent
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.communication import CommunicationThread
from app.models.document_notice import DocumentNotice
from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.notification import Notification
from app.models.photo import PhotoConsent
from app.models.poll import Poll, PollOption
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.services import attendance as attendance_service
from app.services.teacher import photos
from tests.conftest import TEST_PASSWORD


def _login(client: TestClient, username: str):
    return client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD})


@pytest.fixture
def cabinet_world(db, users):
    organization, other, director, _admin = users
    director.must_change_password = False
    teacher = User(
        organization_id=organization.id, username="cabinet-teacher",
        password_hash=hash_password(TEST_PASSWORD), role="TEACHER",
        status="active", must_change_password=False,
    )
    other_teacher = User(
        organization_id=organization.id, username="other-cabinet-teacher",
        password_hash=hash_password(TEST_PASSWORD), role="TEACHER",
        status="active", must_change_password=False,
    )
    parent = User(
        organization_id=organization.id, username="cabinet-parent",
        password_hash=hash_password(TEST_PASSWORD), role="PARENT",
        status="active", must_change_password=False,
    )
    db.add_all([teacher, other_teacher, parent])
    db.flush()
    employee = Employee(
        organization_id=organization.id, user_id=teacher.id, first_name="Синтетическая",
        last_name="Воспитательница", position="Воспитатель", category="teacher", status="active",
    )
    other_employee = Employee(
        organization_id=organization.id, user_id=other_teacher.id, first_name="Другая",
        last_name="Воспитательница", position="Воспитатель", category="teacher", status="active",
    )
    assigned = Group(organization_id=organization.id, name="Кабинет группа", status="active")
    unassigned = Group(organization_id=organization.id, name="Неназначенная группа", status="active")
    foreign = Group(organization_id=other.id, name="Чужая группа кабинета", status="active")
    db.add_all([employee, other_employee, assigned, unassigned, foreign])
    db.flush()
    assignment = TeacherGroupAssignment(
        organization_id=organization.id, employee_id=employee.id,
        group_id=assigned.id, status="active", assigned_by=director.id,
    )
    other_assignment = TeacherGroupAssignment(
        organization_id=organization.id, employee_id=other_employee.id,
        group_id=assigned.id, status="active", assigned_by=director.id,
    )
    child = Child(
        organization_id=organization.id, group_id=assigned.id, first_name="Синтетический",
        last_name="Ребёнок", birth_date=date(2020, 1, 1), status="active",
    )
    other_child = Child(
        organization_id=organization.id, group_id=unassigned.id, first_name="Другой",
        last_name="Ребёнок", birth_date=date(2020, 2, 2), status="active",
    )
    no_consent_child = Child(
        organization_id=organization.id, group_id=assigned.id, first_name="Без",
        last_name="Согласия", birth_date=date(2020, 3, 3), status="active",
    )
    db.add_all([assignment, other_assignment, child, other_child, no_consent_child])
    db.flush()
    guardian = Guardian(
        organization_id=organization.id, user_id=parent.id, first_name="Синтетический",
        last_name="Родитель", phone="+70000000000", email="parent@example.test", status="active",
    )
    unrelated_guardian = Guardian(
        organization_id=organization.id, first_name="Невидимый", last_name="Родитель", status="active",
    )
    db.add_all([guardian, unrelated_guardian])
    db.flush()
    relation = ChildGuardian(
        organization_id=organization.id, child_id=child.id,
        guardian_id=guardian.id, relation_type="mother", status="active",
    )
    unrelated_relation = ChildGuardian(
        organization_id=organization.id, child_id=other_child.id,
        guardian_id=unrelated_guardian.id, relation_type="other", status="active",
    )
    schedule = GroupScheduleItem(
        organization_id=organization.id, group_id=assigned.id, weekday=datetime.now(UTC).date().weekday(),
        start_time=time(9, 0), end_time=time(9, 30), title="Синтетическое занятие",
        status="active", created_by=director.id, updated_by=director.id,
    )
    task = TeacherTask(
        organization_id=organization.id, assignee_employee_id=employee.id, group_id=assigned.id,
        title="Синтетическая задача", description="Проверить материалы", status="open", created_by=director.id,
    )
    foreign_task = TeacherTask(
        organization_id=organization.id, assignee_employee_id=other_employee.id, group_id=assigned.id,
        title="Чужая задача", status="open", created_by=director.id,
    )
    notification = Notification(
        organization_id=organization.id, recipient_user_id=teacher.id,
        kind="task.assigned", entity_type="teacher_task", entity_id=task.id,
    )
    foreign_notification = Notification(
        organization_id=organization.id, recipient_user_id=other_teacher.id,
        kind="private", entity_type="teacher_task", entity_id=task.id,
    )
    notice = DocumentNotice(
        organization_id=organization.id, recipient_user_id=teacher.id,
        title="Синтетическое уведомление", kind="policy", requires_ack=True, issued_by=director.id,
    )
    foreign_notice = DocumentNotice(
        organization_id=organization.id, recipient_user_id=other_teacher.id,
        title="Чужое уведомление", kind="policy", requires_ack=True, issued_by=director.id,
    )
    db.add_all([
        relation, unrelated_relation, schedule, task, foreign_task, notification,
        foreign_notification, notice, foreign_notice,
    ])
    db.flush()
    consent = PhotoConsent(
        organization_id=organization.id, child_id=child.id, status="granted",
        scope="group_photo_report", effective_from=datetime.now(UTC) - timedelta(days=1),
        recorded_by=director.id,
    )
    db.add(consent)
    db.flush()
    return SimpleNamespace(
        organization=organization, other=other, director=director, teacher=teacher,
        other_teacher=other_teacher, parent=parent, employee=employee, assigned=assigned,
        unassigned=unassigned, foreign=foreign, assignment=assignment, child=child,
        other_child=other_child, no_consent_child=no_consent_child,
        guardian=guardian, relation=relation,
        unrelated_guardian=unrelated_guardian, schedule=schedule, task=task,
        notification=notification, foreign_notification=foreign_notification,
        notice=notice, foreign_notice=foreign_notice, foreign_task=foreign_task, consent=consent,
    )


def test_parent_linked_children_and_direct_bootstrap(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.parent.username).status_code == 200
    linked = client.get("/api/v1/parent/children")
    assert linked.status_code == 200
    assert linked.json() == [{
        "id": str(world.child.id),
        "first_name": world.child.first_name,
        "last_name": world.child.last_name,
        "middle_name": world.child.middle_name,
    }]
    direct = client.post("/api/v1/parent/communications/direct", json={
        "child_id": str(world.child.id),
    })
    assert direct.status_code == 201
    assert direct.json()["thread_type"] == "direct"
    assert direct.json()["child_id"] == str(world.child.id)
    assert direct.json()["guardian_id"] == str(world.guardian.id)

    world.relation.status = "archived"
    db.flush()
    assert client.get("/api/v1/parent/children").json() == []
    assert client.post("/api/v1/parent/communications/direct", json={
        "child_id": str(world.child.id),
    }).status_code == 404


def test_parent_today_is_linked_child_only_and_garden_local(client, db, cabinet_world):
    world = cabinet_world
    day = organization_today(world.organization)
    world.schedule.weekday = day.weekday()
    db.flush()

    assert _login(client, world.parent.username).status_code == 200
    initial = client.get(f"/api/v1/parent/children/{world.child.id}/today")
    assert initial.status_code == 200
    payload = initial.json()
    assert payload["date"] == day.isoformat()
    assert payload["child"]["id"] == str(world.child.id)
    assert payload["group"] == {"id": str(world.assigned.id), "name": world.assigned.name}
    assert payload["attendance"]["status"] == "unknown"
    assert [item["title"] for item in payload["schedule"]] == ["Синтетическое занятие"]
    assert client.get(f"/api/v1/parent/children/{world.other_child.id}/today").status_code == 404

    db.add(Attendance(
        organization_id=world.organization.id,
        child_id=world.child.id,
        group_id=world.assigned.id,
        date=day,
        status="present",
        arrival_time=time(8, 20),
        created_by=world.director.id,
        updated_by=world.director.id,
    ))
    db.flush()
    marked = client.get(f"/api/v1/parent/children/{world.child.id}/today")
    assert marked.status_code == 200
    assert marked.json()["attendance"]["status"] == "present"
    assert marked.json()["attendance"]["arrival_time"] == "08:20:00"

    world.relation.status = "archived"
    db.flush()
    assert client.get(f"/api/v1/parent/children/{world.child.id}/today").status_code == 404


def test_teacher_daily_groups_attendance_schedule_and_security(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    groups = client.get("/api/v1/teacher/groups")
    assert groups.status_code == 200 and groups.json() == [{"id": str(world.assigned.id), "name": world.assigned.name}]
    for group_id in (world.unassigned.id, world.foreign.id):
        assert client.get(f"/api/v1/teacher/groups/{group_id}").status_code == 404

    roster = client.get(f"/api/v1/teacher/groups/{world.assigned.id}/children").json()
    assert roster[0]["id"] == str(world.child.id)
    assert "birth_date" not in roster[0]
    guardians = client.get(f"/api/v1/teacher/groups/{world.assigned.id}/guardians").json()
    assert {item["id"] for item in guardians} == {str(world.guardian.id)}
    assert guardians[0]["can_message"] is True

    day = organization_today(world.organization).isoformat()
    listed = client.get(f"/api/v1/teacher/attendance?date={day}&group_id={world.assigned.id}")
    assert listed.status_code == 200 and listed.json()[0]["status"] == "unknown"
    saved = client.post("/api/v1/teacher/attendance", json={
        "child_id": str(world.child.id), "date": day, "status": "present", "arrival_time": "08:30",
        "organization_id": str(world.other.id),
    })
    assert saved.status_code == 400
    saved = client.post("/api/v1/teacher/attendance", json={
        "child_id": str(world.child.id), "date": day, "status": "present", "arrival_time": "08:30",
    })
    assert saved.status_code == 201
    today_payload = client.get("/api/v1/teacher/today").json()
    today_counts = next(item for item in today_payload["attendance"] if item["group_id"] == str(world.assigned.id))
    assert (today_counts["present"], today_counts["on_site"], today_counts["departed"], today_counts["needs_arrival"]) == (1, 1, 0, 0)
    record_id = saved.json()["record_id"]
    assert client.post("/api/v1/teacher/attendance", json={
        "child_id": str(world.other_child.id), "date": day, "status": "absent",
    }).status_code == 404
    world.child.group_id = world.unassigned.id
    db.flush()
    assert client.patch(f"/api/v1/teacher/attendance/{record_id}", json={"status": "absent"}).status_code == 404

    schedule = client.get(f"/api/v1/teacher/schedule?group_id={world.assigned.id}")
    assert schedule.status_code == 200 and schedule.json()[0]["title"] == "Синтетическое занятие"
    assert client.get(f"/api/v1/teacher/schedule?group_id={world.unassigned.id}").status_code == 404
    today = client.get("/api/v1/teacher/today")
    assert today.status_code == 200
    assert today.json()["groups"][0]["id"] == str(world.assigned.id)


def test_teacher_arrival_departure_use_garden_clock_and_stay_stable(client, db, cabinet_world, monkeypatch):
    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    monkeypatch.setattr(
        attendance_service, "organization_now",
        lambda organization: datetime(2026, 10, 7, 8, 15, tzinfo=UTC),
    )
    arrived = client.post("/api/v1/teacher/attendance/arrival", json={"child_id": str(world.child.id)})
    repeated = client.post("/api/v1/teacher/attendance/arrival", json={"child_id": str(world.child.id)})
    assert arrived.status_code == repeated.status_code == 200
    assert arrived.json()["arrival_time"] == repeated.json()["arrival_time"] == "08:15:00"
    monkeypatch.setattr(
        attendance_service, "organization_now",
        lambda organization: datetime(2026, 10, 7, 17, 5, tzinfo=UTC),
    )
    departed = client.post("/api/v1/teacher/attendance/departure", json={"child_id": str(world.child.id)})
    assert departed.status_code == 200
    assert departed.json()["departure_time"] == "17:05:00"
    assert db.scalar(select(func.count()).select_from(Attendance).where(
        Attendance.child_id == world.child.id, Attendance.date == date(2026, 10, 7),
    )) == 1
    assert client.post("/api/v1/teacher/attendance/arrival", json={
        "child_id": str(world.other_child.id),
    }).status_code == 404


def test_teacher_communication_participants_and_relation_revocation(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    group_thread = client.get(f"/api/v1/teacher/groups/{world.assigned.id}/communication-thread")
    assert group_thread.status_code == 200
    thread_id = group_thread.json()["id"]
    assert client.post(f"/api/v1/teacher/communications/threads/{thread_id}/messages", json={
        "body": "Синтетическое сообщение", "sender_user_id": str(world.other_teacher.id),
    }).status_code == 400
    sent = client.post(f"/api/v1/teacher/communications/threads/{thread_id}/messages", json={
        "body": "Синтетическое сообщение",
    })
    assert sent.status_code == 201 and sent.json()["sender_user_id"] == str(world.teacher.id)
    assert sent.json()["sender_name"] == "Воспитательница Синтетическая"
    assert sent.json()["sender_role"] == "TEACHER"
    teacher_only = client.get(
        f"/api/v1/teacher/groups/{world.assigned.id}/communication-thread",
        params={"audience": "teachers"},
    )
    assert teacher_only.status_code == 200
    parent_only = CommunicationThread(
        organization_id=world.organization.id,
        thread_type="group",
        group_id=world.assigned.id,
        audience="parents",
    )
    db.add(parent_only)
    db.flush()
    assert client.get(
        f"/api/v1/teacher/communications/threads/{parent_only.id}/messages",
    ).status_code == 404
    direct = client.post("/api/v1/teacher/communications/direct", json={
        "child_id": str(world.child.id), "guardian_id": str(world.guardian.id),
    })
    assert direct.status_code == 201
    direct_id = direct.json()["id"]
    assert client.post("/api/v1/teacher/communications/direct", json={
        "child_id": str(world.child.id), "guardian_id": str(world.unrelated_guardian.id),
    }).status_code == 404
    assert client.get(f"/api/v1/teacher/communications/threads/{direct_id}/messages").status_code == 200
    parent_notifications_before = set(db.scalars(select(Notification.id).where(
        Notification.recipient_user_id == world.parent.id,
        Notification.kind == "communication.message",
    )))
    world.parent.status = "blocked"
    db.flush()
    assert client.get(f"/api/v1/teacher/communications/threads/{direct_id}/messages").status_code == 404
    assert client.post(
        f"/api/v1/teacher/communications/threads/{direct_id}/messages",
        json={"body": "Недоступное сообщение"},
    ).status_code == 404
    guardians = client.get(f"/api/v1/teacher/groups/{world.assigned.id}/guardians").json()
    guardian = next(item for item in guardians if item["id"] == str(world.guardian.id))
    assert guardian["can_message"] is False
    parent_notifications_after = set(db.scalars(select(Notification.id).where(
        Notification.recipient_user_id == world.parent.id,
        Notification.kind == "communication.message",
    )))
    assert parent_notifications_after == parent_notifications_before
    world.parent.status = "active"
    db.flush()

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        visible_threads = parent_client.get("/api/v1/parent/communications/threads").json()
        assert thread_id in {item["id"] for item in visible_threads}
        assert teacher_only.json()["id"] not in {item["id"] for item in visible_threads}
        assert str(parent_only.id) in {item["id"] for item in visible_threads}
        assert parent_client.get(f"/api/v1/parent/communications/threads/{direct_id}/messages").status_code == 200
        parent_message = parent_client.post(
            f"/api/v1/parent/communications/threads/{direct_id}/messages",
            json={"body": "Ответ родителя"},
        )
        assert parent_message.status_code == 201
        assert parent_client.get(f"/api/v1/teacher/communications/threads/{direct_id}/messages").status_code == 403
        world.relation.status = "archived"
        db.flush()
        assert parent_client.get(f"/api/v1/parent/communications/threads/{direct_id}/messages").status_code == 404
    world.assignment.status = "archived"
    db.flush()
    assert client.get(f"/api/v1/teacher/communications/threads/{thread_id}/messages").status_code == 404
    details = list(db.scalars(select(AuditEvent.details).where(AuditEvent.action == "teacher_message.create")))
    assert "Синтетическое сообщение" not in str(details)
    assert "Ответ родителя" not in str(details)


def test_guardian_without_parent_account_has_safe_messaging_state(client, db, cabinet_world):
    world = cabinet_world
    db.add(ChildGuardian(
        organization_id=world.organization.id,
        child_id=world.child.id,
        guardian_id=world.unrelated_guardian.id,
        relation_type="other",
        status="active",
    ))
    db.flush()
    assert _login(client, world.teacher.username).status_code == 200
    guardians = client.get(f"/api/v1/teacher/groups/{world.assigned.id}/guardians")
    unavailable = next(item for item in guardians.json() if item["id"] == str(world.unrelated_guardian.id))
    assert unavailable["can_message"] is False
    response = client.post("/api/v1/teacher/communications/direct", json={
        "child_id": str(world.child.id),
        "guardian_id": str(world.unrelated_guardian.id),
    })
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PARENT_ACCOUNT_UNAVAILABLE"


def test_teacher_diary_announcements_polls_incidents_tasks_notices(client, db, cabinet_world, monkeypatch):
    for feature in ("diary", "polls", "incidents", "document_notices"):
        monkeypatch.setitem(PRODUCT_FEATURES, feature, True)
    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    diary = client.post("/api/v1/teacher/diary", json={
        "child_id": str(world.child.id), "date": datetime.now(UTC).date().isoformat(),
        "note": "Синтетическая запись дня",
    })
    assert diary.status_code == 201
    updated_diary = client.patch(f"/api/v1/teacher/diary/{diary.json()['id']}", json={
        "note": "Обновлённая синтетическая запись",
    })
    assert updated_diary.status_code == 200
    assert updated_diary.json()["note"] == "Обновлённая синтетическая запись"
    assert client.post("/api/v1/teacher/diary", json={
        "child_id": str(world.other_child.id), "date": datetime.now(UTC).date().isoformat(), "note": "Недоступно",
    }).status_code == 404

    assert client.post("/api/v1/teacher/announcements", json={
        "group_id": str(world.assigned.id), "title": "Объявление", "body": "Синтетический текст",
        "target_type": "all",
    }).status_code == 400
    announcement = client.post("/api/v1/teacher/announcements", json={
        "group_id": str(world.assigned.id), "title": "Объявление", "body": "Синтетический текст",
    })
    assert announcement.status_code == 201
    updated_announcement = client.patch(
        f"/api/v1/teacher/announcements/{announcement.json()['id']}",
        json={"title": "Обновлённое объявление", "body": "Обновлённый синтетический текст"},
    )
    assert updated_announcement.status_code == 200
    assert updated_announcement.json()["title"] == "Обновлённое объявление"
    archived_announcement = client.post(
        f"/api/v1/teacher/announcements/{announcement.json()['id']}/archive",
    )
    assert archived_announcement.status_code == 200
    assert archived_announcement.json()["status"] == "archived"
    management_announcement = Announcement(
        organization_id=world.organization.id, target_type="group", group_id=world.assigned.id,
        title="Управляющее объявление", body="Синтетика", status="active",
        created_by=world.director.id, updated_by=world.director.id,
    )
    db.add(management_announcement)
    db.flush()
    assert client.patch(f"/api/v1/teacher/announcements/{management_announcement.id}", json={
        "title": "Подмена",
    }).status_code == 404

    poll = client.post("/api/v1/teacher/polls", json={
        "group_id": str(world.assigned.id), "question": "Синтетический вопрос?",
        "options": ["Да", "Нет"],
    })
    assert poll.status_code == 201 and len(poll.json()["options"]) == 2
    poll_id = poll.json()["id"]
    second_poll = client.post("/api/v1/teacher/polls", json={
        "group_id": str(world.assigned.id), "question": "Другой вопрос?", "options": ["Один", "Два"],
    })
    assert second_poll.status_code == 201

    medical = client.post("/api/v1/teacher/incidents", json={
        "group_id": str(world.assigned.id), "child_id": str(world.child.id),
        "occurred_at": datetime.now(UTC).isoformat(), "category": "operational",
        "description": "Синтетическое событие", "diagnosis": "forbidden",
    })
    assert medical.status_code == 400
    incident = client.post("/api/v1/teacher/incidents", json={
        "group_id": str(world.assigned.id), "child_id": str(world.child.id),
        "occurred_at": datetime.now(UTC).isoformat(), "category": "operational",
        "description": "Синтетическое событие",
    })
    assert incident.status_code == 201
    assert client.patch(f"/api/v1/teacher/incidents/{incident.json()['id']}", json={
        "status": "resolved",
    }).status_code == 200

    assert client.patch(f"/api/v1/teacher/tasks/{world.task.id}", json={
        "status": "done", "title": "Подмена",
    }).status_code == 400
    assert client.patch(f"/api/v1/teacher/tasks/{world.task.id}", json={"status": "done"}).status_code == 200
    assert client.patch(f"/api/v1/teacher/tasks/{world.foreign_task.id}", json={"status": "done"}).status_code == 404
    assert client.post(f"/api/v1/teacher/notifications/{world.foreign_notification.id}/read").status_code == 404
    assert client.post(f"/api/v1/teacher/notifications/{world.notification.id}/read").status_code == 200
    assert client.post(f"/api/v1/teacher/document-notices/{world.notice.id}/ack").status_code == 200
    assert client.post(f"/api/v1/teacher/document-notices/{world.foreign_notice.id}/ack").status_code == 404

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        parent_announcements = parent_client.get("/api/v1/parent/announcements")
        assert parent_announcements.status_code == 200
        assert len({item["id"] for item in parent_announcements.json()}) == len(parent_announcements.json())
        assert parent_client.get(f"/api/v1/parent/children/{world.child.id}/diary").status_code == 200
        parent_polls = parent_client.get("/api/v1/parent/polls")
        eligible_poll = next(item for item in parent_polls.json() if item["id"] == poll_id)
        option_id = eligible_poll["options"][0]["id"]
        assert parent_client.post(f"/api/v1/parent/polls/{poll_id}/vote", json={
            "option_id": option_id,
        }).status_code == 200
        assert parent_client.post(f"/api/v1/parent/polls/{poll_id}/vote", json={
            "option_id": option_id,
        }).status_code == 409
        mismatched_option_id = second_poll.json()["options"][0]["id"]
        assert parent_client.post(f"/api/v1/parent/polls/{poll_id}/vote", json={
            "option_id": mismatched_option_id,
        }).status_code == 404
        inaccessible_poll = Poll(
            organization_id=world.organization.id, group_id=world.unassigned.id,
            question="Недоступный опрос", status="active", created_by=world.director.id,
        )
        db.add(inaccessible_poll)
        db.flush()
        inaccessible_option = PollOption(poll_id=inaccessible_poll.id, label="Нет", sort_order=0)
        db.add(inaccessible_option)
        db.flush()
        assert parent_client.post(f"/api/v1/parent/polls/{inaccessible_poll.id}/vote", json={
            "option_id": str(inaccessible_option.id),
        }).status_code == 404
        assert parent_client.post("/api/v1/teacher/incidents", json={}).status_code == 403

    world.assignment.status = "archived"
    db.flush()
    assert client.patch(f"/api/v1/teacher/announcements/{announcement.json()['id']}", json={
        "title": "Недоступное изменение",
    }).status_code == 404

    audit_details = str(list(db.scalars(select(AuditEvent.details).where(
        AuditEvent.action.in_(("diary.create", "teacher_announcement.create", "incident.create")),
    ))))
    assert "Синтетическая запись дня" not in audit_details
    assert "Синтетический текст" not in audit_details
    assert "Синтетическое событие" not in audit_details


def _png_with_text() -> bytes:
    signature = b"\x89PNG\r\n\x1a\n"

    def chunk(kind: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw_scanline = b"\x00\xff\x00\x00\xff"
    return signature + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + \
        chunk(b"tEXt", b"private\x00must-be-stripped") + chunk(b"IDAT", zlib.compress(raw_scanline)) + chunk(b"IEND", b"")


def test_photo_consent_authenticated_content_and_production_fail_closed(client, db, cabinet_world, monkeypatch):
    monkeypatch.setitem(PRODUCT_FEATURES, "photos", True)
    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    raw = _png_with_text()
    uploaded = client.post("/api/v1/teacher/photos", data={
        "group_id": str(world.assigned.id), "child_ids": str(world.child.id),
    }, files={"file": ("synthetic.png", raw, "image/png")})
    assert uploaded.status_code == 201
    payload = uploaded.json()
    assert "url" not in payload and "storage_key" not in payload
    photo_id = payload["id"]
    content_response = client.get(f"/api/v1/teacher/photos/{photo_id}/content")
    assert content_response.status_code == 200
    assert b"must-be-stripped" not in content_response.content

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        assert parent_client.get(f"/api/v1/parent/photos?child_id={world.child.id}").status_code == 200
        assert parent_client.get(f"/api/v1/parent/photos/{photo_id}/content").status_code == 200

        world.relation.status = "archived"
        db.flush()
        assert parent_client.get(f"/api/v1/parent/photos/{photo_id}/content").status_code == 404
        world.relation.status = "active"
        db.flush()

    assert client.post("/api/v1/teacher/photos", files=[
        ("group_id", (None, str(world.assigned.id))),
        ("child_ids", (None, str(world.child.id))),
        ("child_ids", (None, str(world.no_consent_child.id))),
        ("file", ("synthetic.png", raw, "image/png")),
    ]).status_code == 404

    world.assignment.status = "archived"
    db.flush()
    assert client.get(f"/api/v1/teacher/photos/{photo_id}/content").status_code == 404
    world.assignment.status = "active"
    db.flush()

    world.consent.status = "withdrawn"
    world.consent.effective_to = datetime.now(UTC)
    db.flush()
    assert client.get(f"/api/v1/teacher/photos/{photo_id}/content").status_code == 404
    assert client.post("/api/v1/teacher/photos", data={
        "group_id": str(world.assigned.id), "child_ids": str(world.child.id),
    }, files={"file": ("synthetic.png", raw, "image/png")}).status_code == 404

    world.consent.status = "granted"
    world.consent.effective_to = None
    db.flush()
    monkeypatch.setattr(photos, "get_settings", lambda: SimpleNamespace(app_env="production"))
    assert client.post("/api/v1/teacher/photos", data={
        "group_id": str(world.assigned.id), "child_ids": str(world.child.id),
    }, files={"file": ("synthetic.png", raw, "image/png")}).status_code == 403


def test_assignment_employee_group_revocation_and_management_regression(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    assert client.get("/api/v1/employees").status_code == 403
    assert client.post("/api/v1/groups", json={"name": "Запрещённая"}).status_code == 403
    assert client.get("/api/v1/audit").status_code == 403
    world.assignment.status = "archived"
    db.flush()
    assert client.get(f"/api/v1/teacher/groups/{world.assigned.id}").status_code == 404
    world.assignment.status = "active"
    world.assigned.status = "archived"
    db.flush()
    assert client.get(f"/api/v1/teacher/groups/{world.assigned.id}").status_code == 404
    world.assigned.status = "active"
    world.employee.status = "archived"
    db.flush()
    assert client.get("/api/v1/teacher/groups").status_code == 403

    with TestClient(app) as director_client:
        assert _login(director_client, world.director.username).status_code == 200
        assert director_client.get("/api/v1/groups").status_code == 200
        assert director_client.get("/api/v1/teacher/groups").status_code == 403

"""PostgreSQL-backed tenant, participant, retry and read-state regressions for Communications v2."""

pytest_plugins = ("tests.test_stage6_teacher_cabinet",)

from uuid import UUID, uuid4

from sqlalchemy import select

from app.models.announcement_read_state import AnnouncementReadState
from app.models.audit_event import AuditEvent
from app.models.communication import (
    CommunicationMessage,
    CommunicationReadState,
    CommunicationThread,
)
from app.models.employee import Employee
from app.models.notification import Notification
from app.services.teacher import communications as legacy_communications
from tests.test_stage6_teacher_cabinet import _login


def test_v2_direct_scope_idempotency_unread_and_revocation(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    teachers = client.get(f"/api/v1/teacher/communications/v2/children/{world.child.id}/teachers")
    assert teachers.status_code == 200
    assert str(world.employee.id) in {item["employee_id"] for item in teachers.json()}
    assert len(teachers.json()) == 2
    thread = client.post("/api/v1/teacher/communications/v2/direct", json={
        "child_id": str(world.child.id), "guardian_id": str(world.guardian.id),
    })
    assert thread.status_code == 201
    thread_id = thread.json()["id"]
    message_key = str(uuid4())
    first = client.post(f"/api/v1/teacher/communications/v2/threads/{thread_id}/messages", json={
        "body": "Синтетический текст v2", "client_message_id": message_key,
    })
    retry = client.post(f"/api/v1/teacher/communications/v2/threads/{thread_id}/messages", json={
        "body": "Синтетический текст v2", "client_message_id": message_key,
    })
    assert first.status_code == retry.status_code == 201
    assert first.json()["id"] == retry.json()["id"]
    assert db.scalar(select(CommunicationMessage.id).where(
        CommunicationMessage.client_message_id == message_key,
    )) == UUID(first.json()["id"])
    audit_details = db.scalars(select(AuditEvent.details).where(
        AuditEvent.action == "communication.message.create",
    )).all()
    assert "Синтетический текст v2" not in str(audit_details)

    # The same sender key cannot be replayed into a different conversation.
    group = client.get(f"/api/v1/teacher/communications/v2/groups/{world.assigned.id}/thread")
    assert group.status_code == 200
    collision = client.post(f"/api/v1/teacher/communications/v2/threads/{group.json()['id']}/messages", json={
        "body": "Повтор в другом потоке", "client_message_id": message_key,
    })
    assert collision.status_code == 409
    assert collision.json()["error"]["code"] == "IDEMPOTENCY_KEY_REUSED"

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        options = parent_client.get(f"/api/v1/parent/children/{world.child.id}/teachers")
        assert options.status_code == 200
        assert str(world.employee.id) in {item["employee_id"] for item in options.json()}
        assert len(options.json()) == 2
        other_employee_id = db.scalar(select(Employee.id).where(
            Employee.organization_id == world.organization.id, Employee.id != world.employee.id,
        ))
        separate = parent_client.post("/api/v1/parent/communications/v2/direct", json={
            "child_id": str(world.child.id), "teacher_employee_id": str(other_employee_id),
        })
        assert separate.status_code == 201
        assert separate.json()["id"] != thread_id
        assert client.get(f"/api/v1/teacher/communications/v2/threads/{separate.json()['id']}/messages").status_code == 404
        listed = parent_client.get("/api/v1/parent/communications/v2/threads")
        direct = next(item for item in listed.json() if item["id"] == thread_id)
        assert direct["unread_count"] == 1
        assert direct["child_name"] == "Ребёнок Синтетический"
        read = parent_client.post(f"/api/v1/parent/communications/v2/threads/{thread_id}/read", json={
            "last_read_message_id": first.json()["id"],
        })
        assert read.status_code == 200
        assert next(item for item in parent_client.get("/api/v1/parent/communications/v2/threads").json() if item["id"] == thread_id)["unread_count"] == 0
        assert parent_client.post(f"/api/v1/parent/communications/v2/threads/{thread_id}/read", json={
            "last_read_message_id": str(uuid4()),
        }).status_code == 404
        assert parent_client.post(f"/api/v1/parent/communications/v2/threads/{thread_id}/messages", json={
            "body": "Ответ", "client_message_id": str(uuid4()),
        }).status_code == 201
        newer = client.post(f"/api/v1/teacher/communications/v2/threads/{thread_id}/messages", json={
            "body": "Следующее синтетическое сообщение", "client_message_id": str(uuid4()),
        })
        assert newer.status_code == 201
        assert parent_client.post(f"/api/v1/parent/communications/v2/threads/{thread_id}/read", json={
            "last_read_message_id": newer.json()["id"],
        }).status_code == 200
        stale = parent_client.post(f"/api/v1/parent/communications/v2/threads/{thread_id}/read", json={
            "last_read_message_id": first.json()["id"],
        })
        assert stale.status_code == 200
        cursor = db.scalar(select(CommunicationReadState).where(
            CommunicationReadState.organization_id == world.organization.id,
            CommunicationReadState.thread_id == UUID(thread_id),
            CommunicationReadState.user_id == world.parent.id,
        ))
        assert cursor.last_read_message_id == UUID(newer.json()["id"])

    world.assignment.status = "archived"
    db.flush()
    assert client.get(f"/api/v1/teacher/communications/v2/threads/{thread_id}/messages").status_code == 404
    assert client.get(f"/api/v1/teacher/communications/v2/threads/{separate.json()['id']}/messages").status_code == 404
    # Legacy direct conversations are preserved but not visible or mutable through v2.
    legacy = legacy_communications.parent_direct(db, world.parent, world.child.id)
    legacy_record = db.get(CommunicationThread, legacy.id)
    assert legacy_record.teacher_employee_id is None
    v2_list = client.get("/api/v1/teacher/communications/v2/threads").json()
    assert legacy.id not in {item["id"] for item in v2_list}


def test_v2_group_visibility_and_announcement_audience_read_receipt(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.director.username).status_code == 200
    created = client.post("/api/v1/communications/v2/announcements", json={
        "target_type": "group", "group_id": str(world.assigned.id), "audience": "parents",
        "title": "Синтетическое объявление", "body": "Только для участников родительской аудитории",
    })
    assert created.status_code == 201
    announcement_id = created.json()["id"]
    assert created.json()["recipient_count"] == 1
    notifications_before = db.scalars(select(Notification.id).where(
        Notification.kind == "announcement.published", Notification.entity_id == announcement_id,
    )).all()
    assert len(notifications_before) == 1
    # Content edits never re-notify recipients and the published audience cannot be changed by PATCH.
    edited = client.patch(f"/api/v1/communications/v2/announcements/{announcement_id}", json={
        "body": "Обновлённый синтетический текст",
    })
    assert edited.status_code == 200
    assert len(db.scalars(select(Notification.id).where(
        Notification.kind == "announcement.published", Notification.entity_id == announcement_id,
    )).all()) == 1
    assert client.patch(f"/api/v1/communications/v2/announcements/{announcement_id}", json={
        "audience": "staff",
    }).status_code == 400

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        parent_items = parent_client.get("/api/v1/communications/v2/announcements")
        assert parent_items.status_code == 200
        assert parent_items.json()[0]["id"] == announcement_id
        assert parent_items.json()[0]["unread"] is True
        marked = parent_client.post(f"/api/v1/communications/v2/announcements/{announcement_id}/read")
        assert marked.status_code == 200
        assert db.scalar(select(AnnouncementReadState.id).where(
            AnnouncementReadState.announcement_id == announcement_id,
            AnnouncementReadState.user_id == world.parent.id,
        )) is not None
        assert parent_client.get("/api/v1/communications/v2/announcements").json()[0]["unread"] is False

    assert _login(client, world.teacher.username).status_code == 200
    teacher_items = client.get("/api/v1/communications/v2/announcements")
    assert teacher_items.status_code == 200
    assert announcement_id not in {item["id"] for item in teacher_items.json()}
    assert client.post(f"/api/v1/communications/v2/announcements/{announcement_id}/read").status_code == 404


def test_v2_group_channels_are_role_scoped(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.director.username).status_code == 200
    staff = client.get(
        f"/api/v1/teacher-management/communications/v2/groups/{world.assigned.id}/thread",
        params={"audience": "teachers"},
    )
    assert staff.status_code == 200
    assert staff.json()["audience"] == "teachers"
    direct = CommunicationThread(
        organization_id=world.organization.id, thread_type="direct", audience="all",
        group_id=world.assigned.id, child_id=world.child.id, guardian_id=world.guardian.id,
        teacher_employee_id=world.employee.id,
    )
    db.add(direct)
    db.flush()
    assert client.get(f"/api/v1/teacher-management/communications/v2/threads/{direct.id}/messages").status_code == 404

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        parent_threads = parent_client.get("/api/v1/parent/communications/v2/threads").json()
        assert staff.json()["id"] not in {item["id"] for item in parent_threads}
        assert parent_client.get(
            f"/api/v1/parent/communications/v2/threads/{staff.json()['id']}/messages",
        ).status_code == 404
        assert parent_client.get(
            f"/api/v1/parent/communications/v2/groups/{world.assigned.id}/thread",
        ).status_code == 200

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


def test_parent_v2_rejects_legacy_parents_group_but_legacy_api_keeps_it(client, db, cabinet_world):
    world = cabinet_world
    legacy = CommunicationThread(
        organization_id=world.organization.id, thread_type="group", audience="parents",
        group_id=world.assigned.id,
    )
    db.add(legacy)
    db.flush()
    message = CommunicationMessage(
        organization_id=world.organization.id, thread_id=legacy.id,
        sender_user_id=world.teacher.id, body="Синтетическое историческое сообщение",
    )
    db.add(message)
    db.flush()

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        listed = parent_client.get("/api/v1/parent/communications/v2/threads")
        assert listed.status_code == 200
        assert str(legacy.id) not in {item["id"] for item in listed.json()}
        assert parent_client.get(f"/api/v1/parent/communications/v2/threads/{legacy.id}/messages").status_code == 404
        assert parent_client.post(f"/api/v1/parent/communications/v2/threads/{legacy.id}/messages", json={
            "body": "Запрещённая запись", "client_message_id": str(uuid4()),
        }).status_code == 404
        assert parent_client.post(f"/api/v1/parent/communications/v2/threads/{legacy.id}/read", json={
            "last_read_message_id": str(message.id),
        }).status_code == 404
        # The historical route and row remain available under the legacy contract.
        legacy_messages = parent_client.get(f"/api/v1/parent/communications/threads/{legacy.id}/messages")
        assert legacy_messages.status_code == 200
        assert legacy_messages.json()[0]["id"] == str(message.id)
        legacy_send = parent_client.post(f"/api/v1/parent/communications/threads/{legacy.id}/messages", json={
            "body": "Разрешённое legacy сообщение",
        })
        assert legacy_send.status_code == 201
        # The supported audience=all Parent Group channel remains accessible.
        group = parent_client.get(f"/api/v1/parent/communications/v2/groups/{world.assigned.id}/thread")
        assert group.status_code == 200 and group.json()["audience"] == "all"


def test_announcement_preview_matches_frozen_audience_matrix_and_group_fanout(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.director.username).status_code == 200
    base = "/api/v1/communications/v2/announcements/preview"
    expected = {
        ("group", "all"): (3, 1, 2),
        ("group", "parents"): (1, 1, 0),
        ("group", "staff"): (2, 0, 2),
        ("all", "all"): (3, 1, 2),
        ("all", "parents"): (1, 1, 0),
        ("all", "staff"): (2, 0, 2),
    }
    for (target, audience), counts in expected.items():
        payload = {"target_type": target, "audience": audience}
        if target == "group":
            payload["group_id"] = str(world.assigned.id)
        response = client.post(base, json=payload)
        assert response.status_code == 200, response.text
        assert response.json() == {
            "recipient_count": counts[0], "parents_count": counts[1], "staff_count": counts[2],
        }
        assert set(response.json()) == {"recipient_count", "parents_count", "staff_count"}

    foreign_preview = client.post(base, json={
        "target_type": "group", "group_id": str(world.foreign.id), "audience": "all",
    })
    assert foreign_preview.status_code == 404

    created = client.post("/api/v1/communications/v2/announcements", json={
        "target_type": "group", "group_id": str(world.assigned.id), "audience": "all",
        "title": "Синтетический охват", "body": "Тестовое групповое сообщение",
    })
    assert created.status_code == 201
    recipient_ids = set(db.scalars(select(Notification.recipient_user_id).where(
        Notification.kind == "announcement.published", Notification.entity_id == UUID(created.json()["id"]),
    )))
    assert recipient_ids == {world.parent.id, world.teacher.id, world.other_teacher.id}
    assert world.director.id not in recipient_ids

    staff_created = client.post("/api/v1/communications/v2/announcements", json={
        "target_type": "group", "group_id": str(world.assigned.id), "audience": "staff",
        "title": "Синтетическое служебное объявление", "body": "Только назначенным воспитателям",
    })
    assert staff_created.status_code == 201 and staff_created.json()["recipient_count"] == 2
    staff_recipients = set(db.scalars(select(Notification.recipient_user_id).where(
        Notification.kind == "announcement.published", Notification.entity_id == UUID(staff_created.json()["id"]),
    )))
    assert staff_recipients == {world.teacher.id, world.other_teacher.id}

    # The author is excluded from notification fanout and count-only preview for a staff audience.
    assert _login(client, world.teacher.username).status_code == 200
    teacher_preview = client.post(base, json={
        "target_type": "group", "group_id": str(world.assigned.id), "audience": "staff",
    })
    assert teacher_preview.status_code == 200
    assert teacher_preview.json() == {"recipient_count": 1, "parents_count": 0, "staff_count": 1}
    assert client.post(base, json={
        "target_type": "group", "group_id": str(world.unassigned.id), "audience": "all",
    }).status_code == 404
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        assert parent_client.post(base, json={"target_type": "all", "audience": "all"}).status_code == 403


def test_parent_announcement_detail_and_read_recheck_revoked_guardian(client, db, cabinet_world):
    world = cabinet_world
    assert _login(client, world.director.username).status_code == 200
    created = client.post("/api/v1/communications/v2/announcements", json={
        "target_type": "group", "group_id": str(world.assigned.id), "audience": "parents",
        "title": "Синтетическое объявление", "body": "Скрыть после отзыва",
    })
    assert created.status_code == 201
    announcement_id = created.json()["id"]

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as parent_client:
        assert _login(parent_client, world.parent.username).status_code == 200
        assert parent_client.get(f"/api/v1/communications/v2/announcements/{announcement_id}").status_code == 200
        world.relation.status = "archived"
        db.flush()
        assert parent_client.get(f"/api/v1/communications/v2/announcements/{announcement_id}").status_code == 404
        assert parent_client.post(f"/api/v1/communications/v2/announcements/{announcement_id}/read").status_code == 404


def _privacy_group_message(client, world):
    assert _login(client, world.teacher.username).status_code == 200
    thread = client.get(f"/api/v1/teacher/communications/v2/groups/{world.assigned.id}/thread").json()
    assert _login(client, world.parent.username).status_code == 200
    path = f"/api/v1/parent/communications/v2/threads/{thread['id']}/messages"
    sent = client.post(path, json={"body": "Историческое синтетическое сообщение", "client_message_id": str(uuid4())})
    assert sent.status_code == 201
    assert "sender_child_context" not in sent.json()
    return thread, sent.json()


def test_teacher_relationship_projection_is_absent_from_other_transports(client, db, cabinet_world, users):
    world = cabinet_world
    thread, message = _privacy_group_message(client, world)
    expected_keys = {"id", "thread_id", "sender_user_id", "sender_role", "sender_name", "body", "created_at"}
    assert set(message) == expected_keys
    parent_path = f"/api/v1/parent/communications/v2/threads/{thread['id']}/messages"
    assert set(client.get(parent_path).json()[0]) == expected_keys
    assert _login(client, world.teacher.username).status_code == 200
    teacher_path = f"/api/v1/teacher/communications/v2/threads/{thread['id']}/messages"
    response = client.get(teacher_path)
    assert response.status_code == 200
    assert response.json()[0]["sender_child_context"] == {
        "child_name": "Ребёнок Синтетический", "relation_type": "mother", "multiple_children": False,
    }
    teacher_send = client.post(teacher_path, json={"body": "Ответ", "client_message_id": str(uuid4())})
    assert teacher_send.status_code == 201
    assert teacher_send.json()["sender_child_context"] is None
    # Even legacy Teacher messages retain the original transport shape.
    assert set(client.get(f"/api/v1/teacher/communications/threads/{thread['id']}/messages").json()[0]) == expected_keys
    for actor in (world.director, users[3]):
        assert _login(client, actor.username).status_code == 200
        path = f"/api/v1/teacher-management/communications/v2/threads/{thread['id']}/messages"
        assert set(client.get(path).json()[0]) == expected_keys | {"group_id", "audience"}
        sent = client.post(path, json={"body": "Служебный ответ", "client_message_id": str(uuid4())})
        assert sent.status_code == 201
        assert set(sent.json()) == expected_keys | {"group_id", "audience"}
        assert client.get(teacher_path).status_code == 403
    # Projection metadata never enters audit or notifications.
    assert "sender_child_context" not in str(db.scalars(select(AuditEvent.details)).all())
    assert "sender_child_context" not in str(db.scalars(select(Notification.kind)).all())


def test_teacher_historic_relationship_is_current_and_group_scoped(client, db, cabinet_world):
    from app.models.child_guardian import ChildGuardian

    world = cabinet_world
    thread, _ = _privacy_group_message(client, world)
    # A second link outside the permitted group must neither appear nor count as ambiguity.
    outside = ChildGuardian(organization_id=world.organization.id, child_id=world.other_child.id,
                            guardian_id=world.guardian.id, relation_type="father", status="active")
    db.add(outside)
    db.flush()
    assert _login(client, world.teacher.username).status_code == 200
    path = f"/api/v1/teacher/communications/v2/threads/{thread['id']}/messages"
    assert client.get(path).json()[0]["sender_child_context"]["multiple_children"] is False
    world.relation.relation_type = "legal_guardian"
    world.child.first_name = "Обновлённый"
    db.flush()
    assert client.get(path).json()[0]["sender_child_context"] == {
        "child_name": "Ребёнок Обновлённый", "relation_type": "legal_guardian", "multiple_children": False,
    }
    second = ChildGuardian(organization_id=world.organization.id, child_id=world.no_consent_child.id,
                           guardian_id=world.guardian.id, relation_type="other", status="active")
    db.add(second)
    db.flush()
    assert client.get(path).json()[0]["sender_child_context"] == {
        "child_name": None, "relation_type": None, "multiple_children": True,
    }
    second.status = "archived"
    world.child.group_id = world.unassigned.id
    db.flush()
    assert client.get(path).json()[0]["sender_child_context"] is None
    world.child.group_id = world.assigned.id
    world.child.status = "archived"
    db.flush()
    assert client.get(path).json()[0]["sender_child_context"] is None


def test_teacher_projection_revocation_and_tenant_denial(client, db, cabinet_world):
    import pytest

    from app.core.errors import AppError
    from app.services import communications_v2

    world = cabinet_world
    thread, _ = _privacy_group_message(client, world)
    assert _login(client, world.teacher.username).status_code == 200
    path = f"/api/v1/teacher/communications/v2/threads/{thread['id']}/messages"
    for record in (world.relation, world.guardian, world.parent):
        record.status = "archived" if record is not world.parent else "blocked"
        db.flush()
        assert client.get(path).json()[0]["sender_child_context"] is None
        record.status = "active"
        db.flush()
    # A forged cross-tenant relation cannot project a foreign child's identity.
    from datetime import date

    from app.models.child import Child
    from app.models.child_guardian import ChildGuardian

    foreign_child = Child(organization_id=world.other.id, group_id=world.foreign.id,
                          first_name="Чужой", last_name="Синтетический", birth_date=date(2020, 1, 1), status="active")
    db.add(foreign_child)
    db.flush()
    db.add(ChildGuardian(organization_id=world.organization.id, child_id=foreign_child.id,
                         guardian_id=world.guardian.id, relation_type="other", status="active"))
    db.flush()
    assert client.get(path).json()[0]["sender_child_context"]["multiple_children"] is False
    foreign_thread = CommunicationThread(organization_id=world.other.id, group_id=world.foreign.id,
                                         thread_type="group", audience="all")
    db.add(foreign_thread)
    db.flush()
    assert client.get(f"/api/v1/teacher/communications/v2/threads/{foreign_thread.id}/messages").status_code == 404
    assert client.get(f"/api/v1/teacher/communications/v2/threads/{uuid4()}/messages").status_code == 404
    with pytest.raises(AppError):
        communications_v2.teacher_message_responses(db, world.parent, UUID(thread["id"]), [])
    world.assignment.status = "archived"
    db.flush()
    assert client.get(path).status_code == 404
    assert client.post(path, json={"body": "Запрещено", "client_message_id": str(uuid4())}).status_code == 404


def test_teacher_direct_projection_binds_exact_child_and_rechecks_retry(client, db, cabinet_world):
    from app.models.child_guardian import ChildGuardian

    world = cabinet_world
    assert _login(client, world.teacher.username).status_code == 200
    thread = client.post("/api/v1/teacher/communications/v2/direct", json={
        "child_id": str(world.child.id), "guardian_id": str(world.guardian.id),
    }).json()
    db.add(ChildGuardian(organization_id=world.organization.id, child_id=world.no_consent_child.id,
                         guardian_id=world.guardian.id, relation_type="father", status="active"))
    db.flush()
    assert _login(client, world.parent.username).status_code == 200
    parent_key = str(uuid4())
    assert client.post(f"/api/v1/parent/communications/v2/threads/{thread['id']}/messages", json={
        "body": "Личное сообщение", "client_message_id": parent_key,
    }).status_code == 201
    assert client.get(f"/api/v1/parent/communications/threads/{thread['id']}/messages").status_code == 200
    assert _login(client, world.teacher.username).status_code == 200
    path = f"/api/v1/teacher/communications/v2/threads/{thread['id']}/messages"
    assert client.get(path).json()[0]["sender_child_context"] == {
        "child_name": "Ребёнок Синтетический", "relation_type": "mother", "multiple_children": False,
    }
    key = str(uuid4())
    assert client.post(path, json={"body": "Ответ", "client_message_id": key}).status_code == 201
    teacher_legacy = f"/api/v1/teacher/communications/threads/{thread['id']}/messages"
    assert client.get(teacher_legacy).status_code == 200
    world.relation.status = "archived"
    db.flush()
    assert client.get(path).status_code == 404
    assert client.post(path, json={"body": "Ответ", "client_message_id": key}).status_code == 404
    world.relation.status = "active"
    from app.models.teacher_group_assignment import TeacherGroupAssignment

    db.add(TeacherGroupAssignment(organization_id=world.organization.id, employee_id=world.employee.id,
                                 group_id=world.unassigned.id, status="active", assigned_by=world.director.id))
    world.child.group_id = world.unassigned.id
    db.flush()
    assert client.get(path).status_code == 404
    assert client.get(teacher_legacy).status_code == 404
    assert client.post(teacher_legacy, json={"body": "После перевода"}).status_code == 404
    # The second linked child keeps A in the parent's allowed groups. The old
    # direct thread must nevertheless deny read, write, retry and read-state.
    assert _login(client, world.parent.username).status_code == 200
    parent_path = f"/api/v1/parent/communications/v2/threads/{thread['id']}"
    parent_legacy = f"/api/v1/parent/communications/threads/{thread['id']}/messages"
    assert client.get(f"{parent_path}/messages").status_code == 404
    assert client.get(parent_legacy).status_code == 404
    assert client.post(parent_legacy, json={"body": "После перевода"}).status_code == 404
    assert client.post(f"{parent_path}/messages", json={
        "body": "После перевода", "client_message_id": str(uuid4()),
    }).status_code == 404
    assert client.post(f"{parent_path}/messages", json={
        "body": "Личное сообщение", "client_message_id": parent_key,
    }).status_code == 404
    assert client.post(f"{parent_path}/read", json={
        "last_read_message_id": str(uuid4()),
    }).status_code == 404
    assert thread["id"] not in {item["id"] for item in client.get(
        "/api/v1/parent/communications/v2/threads",
    ).json()}


def test_teacher_relationship_projection_is_batched_and_staff_has_no_hint(client, db, cabinet_world):
    from sqlalchemy import event

    world = cabinet_world
    thread, _ = _privacy_group_message(client, world)
    for _ in range(12):
        assert client.post(f"/api/v1/parent/communications/v2/threads/{thread['id']}/messages", json={
            "body": "История", "client_message_id": str(uuid4()),
        }).status_code == 201
    assert _login(client, world.teacher.username).status_code == 200
    statements = []

    def collect(_connection, _cursor, statement, _parameters, _context, _many):
        if "child_guardians" in statement.lower():
            statements.append(statement)

    connection = db.connection()
    event.listen(connection, "before_cursor_execute", collect)
    try:
        result = client.get(f"/api/v1/teacher/communications/v2/threads/{thread['id']}/messages")
    finally:
        event.remove(connection, "before_cursor_execute", collect)
    assert result.status_code == 200
    assert len(result.json()) == 13
    assert len(statements) == 1
    assert all(item["sender_child_context"]["relation_type"] == "mother" for item in result.json())
    staff = client.get(f"/api/v1/teacher/communications/v2/groups/{world.assigned.id}/thread", params={"audience": "teachers"}).json()
    # A historic anomalous Parent-authored row in staff must not create a relationship disclosure.
    db.add(CommunicationMessage(organization_id=world.organization.id, thread_id=UUID(staff["id"]),
                                sender_user_id=world.parent.id, body="Синтетическая историческая строка"))
    db.flush()
    assert client.get(f"/api/v1/teacher/communications/v2/threads/{staff['id']}/messages").json()[0]["sender_child_context"] is None

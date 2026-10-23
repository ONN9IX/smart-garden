"""Synthetic privacy/security integration, including hostile tenants and roles."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, date, datetime, timedelta
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.db.base import Base
from app.db.session import engine
from app.models.audit_event import AuditEvent
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.organization import Organization
from app.models.privacy import (
    BasisAttestation,
    ConsentEvent,
    LegalDocument,
    PaperConsent,
    PrivacyRequest,
)
from app.models.user import User
from app.schemas.privacy import PaperConsentInput, RequestInput
from app.services import email_delivery, privacy
from app.services.auth import COOKIE_NAME, issue_session
from app.services.privacy_catalog import install_catalog
from tests.privacy_helpers import install_synthetic_catalog, synthetic_catalog

ROOT = "/api/v1/privacy"


def as_user(client, db, user):
    user.must_change_password = False
    token = issue_session(db, user)
    db.flush()
    client.cookies.set(COOKIE_NAME, token)


@pytest.fixture
def world(db, users):
    organization, other, director, admin = users
    people = []
    for role, suffix, org in (
        ("PARENT", "parent", organization),
        ("PARENT", "other-parent", organization),
        ("TEACHER", "teacher", organization),
        ("DIRECTOR", "foreign", other),
    ):
        user = User(
            organization_id=org.id,
            username=f"privacy-{suffix}",
            password_hash=director.password_hash,
            role=role,
            status="active",
            must_change_password=False,
        )
        db.add(user)
        db.flush()
        people.append(user)
    parent, second_parent, teacher, foreign_director = people
    employee = Employee(
        organization_id=organization.id,
        user_id=teacher.id,
        first_name="Синтетический",
        last_name="Педагог",
        category="teacher",
        position="Воспитатель",
        status="active",
    )
    group = Group(
        organization_id=organization.id, name="Синтетическая группа", status="active"
    )
    foreign_group = Group(
        organization_id=other.id, name="Чужая синтетическая группа", status="active"
    )
    db.add_all([employee, group, foreign_group])
    db.flush()
    child = Child(
        organization_id=organization.id,
        group_id=group.id,
        first_name="Синтетический",
        last_name="Ребёнок",
        birth_date=date(2020, 1, 1),
        status="active",
    )
    foreign_child = Child(
        organization_id=other.id,
        group_id=foreign_group.id,
        first_name="Чужой",
        last_name="Синтетический",
        birth_date=date(2020, 1, 1),
        status="active",
    )
    db.add_all([child, foreign_child])
    db.flush()
    guardians, links = [], []
    for index, user in enumerate((parent, second_parent)):
        guardian = Guardian(
            organization_id=organization.id,
            user_id=user.id,
            first_name="Синтетический",
            last_name=f"Представитель {index}",
            email=f"privacy-{index}@example.test",
            status="active",
        )
        db.add(guardian)
        db.flush()
        guardians.append(guardian)
        link = ChildGuardian(
            organization_id=organization.id,
            child_id=child.id,
            guardian_id=guardian.id,
            relation_type="legal_guardian",
            status="active",
        )
        db.add(link)
        db.flush()
        links.append(link)
    catalog = install_synthetic_catalog(db, organization.id)
    return {
        "org": organization,
        "other": other,
        "director": director,
        "admin": admin,
        "parent": parent,
        "second_parent": second_parent,
        "teacher": teacher,
        "foreign": foreign_director,
        "child": child,
        "foreign_child": foreign_child,
        "guardians": guardians,
        "links": links,
        "catalog": catalog,
    }


def paper_payload(w, *, child=True):
    return {
        "purpose_id": str(w["catalog"].purposes[1].id),
        "document_id": str(w["catalog"].documents[1].id),
        **(
            {"child_id": str(w["child"].id), "guardian_id": str(w["guardians"][0].id)}
            if child
            else {"subject_user_id": str(w["teacher"].id)}
        ),
        "received_on": str(datetime.now(UTC).date() - timedelta(days=1)),
        "original_held_confirmed": True,
        "authority_confirmed": True,
        "idempotency_key": str(uuid4()),
    }


def record(client, db, w, payload=None):
    as_user(client, db, w["director"])
    response = client.post(ROOT + "/consents", json=payload or paper_payload(w))
    assert response.status_code == 201, response.text
    return response.json()


def test_public_empty_no_fake_operator_or_approval_route(client, users):
    response = client.get(ROOT + "/public/provider")
    assert response.status_code == 200 and response.json()["documents"] == []
    assert response.headers["Cache-Control"] == "no-store"
    assert client.get(ROOT + f"/public/gardens/{users[0].id}").json()["documents"] == []
    assert client.get(ROOT + "/me").status_code == 401
    assert (
        client.post(
            ROOT + "/documents/publish", json={"status": "published"}
        ).status_code
        == 404
    )


def test_public_only_approved_effective_documents_exact_operator_scope(
    client, db, world
):
    w = world
    other = install_synthetic_catalog(db, w["other"].id)
    draft = (
        synthetic_catalog(w["org"].id)
        .documents[0]
        .model_copy(update={"status": "draft", "version": "draft-only"})
    )
    db.add(
        LegalDocument(**{**draft.model_dump(), "operator": draft.operator.model_dump()})
    )
    db.flush()
    result = client.get(ROOT + f"/public/gardens/{w['org'].id}").json()["documents"]
    assert [d["id"] for d in result] == [str(w["catalog"].documents[0].id)]
    assert str(other.documents[0].id) not in str(result) and "draft-only" not in str(
        result
    )
    assert "approval_reference" not in result[0]
    assert client.get(ROOT + "/public/provider").json()["documents"] == []
    document = db.get(LegalDocument, w["catalog"].documents[0].id)
    document.status = "retired"
    db.flush()
    assert client.get(ROOT + f"/public/gardens/{w['org'].id}").json()["documents"] == []


def test_invitation_fail_closed_then_attestation_is_not_consent(
    client, db, world, monkeypatch
):
    w = world
    as_user(client, db, w["director"])
    guardian = Guardian(
        organization_id=w["org"].id,
        first_name="Синтетический",
        last_name="Новый",
        email="new-privacy@example.test",
        status="active",
    )
    db.add(guardian)
    db.flush()
    sender = email_delivery.InMemoryEmailSender([])
    monkeypatch.setattr(email_delivery, "get_email_sender", lambda: sender)
    path = f"/api/v1/guardians/{guardian.id}/account"
    denied = client.post(path)
    assert (
        denied.status_code == 409
        and denied.json()["error"]["code"] == "PRIVACY_BASIS_REQUIRED"
    )
    assert guardian.user_id is None and not sender.messages
    payload = {
        "profile_type": "guardian",
        "profile_ids": [str(guardian.id)],
        "purpose_id": str(w["catalog"].purposes[0].id),
        "documents_confirmed": True,
    }
    assert (
        client.post(
            ROOT + "/attestations", json={**payload, "documents_confirmed": False}
        ).status_code
        == 400
    )
    confirmed = client.post(ROOT + "/attestations", json=payload)
    assert (
        confirmed.status_code == 201 and confirmed.json()["is_subject_consent"] is False
    )
    evidence = db.scalar(
        select(BasisAttestation).where(BasisAttestation.profile_id == guardian.id)
    )
    assert (
        evidence.actor_user_id == w["director"].id
        and evidence.organization_id == w["org"].id
        and evidence.created_at
    )
    assert db.scalar(select(func.count(PaperConsent.id))) == 0
    assert client.post(path).status_code == 201 and len(sender.messages) == 1
    raw = sender.messages[0]["text"].split("#token=")[1].splitlines()[0]
    assert (
        client.post(
            "/api/v1/auth/activate",
            json={"token": raw, "new_password": "synthetic-new-password-243"},
        ).status_code
        == 200
    )
    assert db.scalar(select(func.count(PaperConsent.id))) == 0
    document = db.get(LegalDocument, w["catalog"].documents[0].id)
    document.status = "retired"
    db.flush()
    assert client.post(path + "/resend").status_code == 409


@pytest.mark.parametrize("role", ["DIRECTOR", "ADMIN", "TEACHER", "PARENT"])
def test_four_roles_scoped_overview_and_private_request_queue(client, db, world, role):
    w = world
    user = {
        "DIRECTOR": w["director"],
        "ADMIN": w["admin"],
        "TEACHER": w["teacher"],
        "PARENT": w["parent"],
    }[role]
    as_user(client, db, user)
    me = client.get(ROOT + "/me")
    assert me.status_code == 200 and me.json()["organization_id"] == str(w["org"].id)
    assert client.get(ROOT + "/operator/requests").status_code == (
        200 if role == "DIRECTOR" else 403
    )
    payload = {
        "profile_type": "guardian",
        "profile_ids": [str(w["guardians"][0].id)],
        "purpose_id": str(w["catalog"].purposes[0].id),
        "documents_confirmed": True,
    }
    assert client.post(ROOT + "/attestations", json=payload).status_code == (
        201 if role in {"DIRECTOR", "ADMIN"} else 403
    )
    if role not in {"DIRECTOR", "ADMIN"}:
        assert client.post(ROOT + "/consents", json=paper_payload(w)).status_code == 403


def test_foreign_subject_document_purpose_and_owner_cookie_denied(client, db, world):
    w = world
    as_user(client, db, w["director"])
    other = install_synthetic_catalog(db, w["other"].id)
    payload = paper_payload(w)
    for fields, status in (
        ({"child_id": str(w["foreign_child"].id)}, 404),
        ({"purpose_id": str(other.purposes[1].id)}, 404),
        ({"document_id": str(other.documents[1].id)}, 409),
    ):
        assert (
            client.post(ROOT + "/consents", json={**payload, **fields}).status_code
            == status
        )
    client.cookies.clear()
    client.cookies.set("promax_platform_session", "synthetic-owner-cookie")
    assert client.get(ROOT + "/me").status_code == 401
    assert client.get(ROOT + "/consents").status_code == 401


def test_paper_consent_private_history_withdrawal_retry_and_no_automatic_deletion(
    client, db, world
):
    w = world
    payload = paper_payload(w)
    item = record(client, db, w, payload)
    assert item["status"] == "recorded" and item["document_version"] == "synthetic-v1"
    assert item["recorded_by"] == str(w["director"].id)
    retry = client.post(ROOT + "/consents", json=payload)
    assert retry.status_code == 201 and retry.json()["id"] == item["id"]
    assert (
        client.post(
            ROOT + "/consents",
            json={**payload, "received_on": str(datetime.now(UTC).date())},
        ).status_code
        == 409
    )
    as_user(client, db, w["second_parent"])
    assert client.get(ROOT + "/consents").json() == []
    assert client.post(ROOT + f"/consents/{item['id']}/withdraw").status_code == 404
    as_user(client, db, w["teacher"])
    assert client.get(ROOT + "/consents").json() == []
    assert client.post(ROOT + f"/consents/{item['id']}/withdraw").status_code == 404
    as_user(client, db, w["parent"])
    assert len(client.get(ROOT + "/consents").json()) == 1
    for _ in range(2):
        withdrawn = client.post(ROOT + f"/consents/{item['id']}/withdraw")
        assert (
            withdrawn.status_code == 200 and withdrawn.json()["status"] == "withdrawn"
        )
        assert len(withdrawn.json()["history"]) == 2
    assert client.get("/api/v1/auth/me").status_code == 200
    assert db.get(Child, w["child"].id) is not None
    assert (
        db.scalar(
            select(func.count(ConsentEvent.id)).where(
                ConsentEvent.consent_id == UUID(item["id"])
            )
        )
        == 2
    )
    as_user(client, db, w["director"])
    assert (
        client.post(
            ROOT + "/consents", json={**payload, "idempotency_key": str(uuid4())}
        ).status_code
        == 409
    )


def test_revoked_parent_link_hides_consent_and_request_child_context(client, db, world):
    w = world
    item = record(client, db, w)
    as_user(client, db, w["parent"])
    assert (
        client.post(
            ROOT + "/requests",
            json={
                "kind": "access",
                "child_id": str(w["child"].id),
                "idempotency_key": str(uuid4()),
            },
        ).status_code
        == 201
    )
    w["links"][0].status = "archived"
    db.flush()
    assert client.get(ROOT + "/consents").json() == []
    assert client.get(ROOT + "/requests").json() == []
    assert not any(s["child_id"] for s in client.get(ROOT + "/subjects").json())
    assert client.post(ROOT + f"/consents/{item['id']}/withdraw").status_code == 404
    assert (
        client.post(
            ROOT + "/requests",
            json={
                "kind": "access",
                "child_id": str(w["child"].id),
                "idempotency_key": str(uuid4()),
            },
        ).status_code
        == 404
    )


def test_teacher_only_own_consent_and_no_group_roster_from_privacy(client, db, world):
    w = world
    item = record(client, db, w, paper_payload(w, child=False))
    as_user(client, db, w["teacher"])
    assert [r["id"] for r in client.get(ROOT + "/consents").json()] == [item["id"]]
    assert client.get(ROOT + "/subjects").json() == [
        {
            "subject_user_id": str(w["teacher"].id),
            "child_id": None,
            "guardian_id": None,
            "label": "Мои данные",
        }
    ]
    assert (
        client.post(
            ROOT + "/requests",
            json={
                "kind": "correction",
                "child_id": str(w["child"].id),
                "idempotency_key": str(uuid4()),
            },
        ).status_code
        == 404
    )


def test_document_version_changes_never_create_new_consent(client, db, world):
    w = world
    item = record(client, db, w)
    old = db.get(LegalDocument, w["catalog"].documents[0].id)
    old.status = "retired"
    db.flush()
    replacement = synthetic_catalog(w["org"].id)
    for value in replacement.documents + replacement.purposes:
        value.version = "synthetic-v2"
    install_catalog(db, replacement, reviewed=True, app_env="test")
    as_user(client, db, w["parent"])
    consents = client.get(ROOT + "/consents").json()
    assert (
        len(consents) == 1
        and consents[0]["document_version"] == "synthetic-v1"
        and not consents[0]["current_version"]
    )
    assert client.post(ROOT + f"/consents/{item['id']}/withdraw").status_code == 200
    assert client.get("/api/v1/teacher/photos").status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [
        ("original_held_confirmed", False),
        ("authority_confirmed", False),
        ("received_on", "2099-01-01"),
        ("scan", "passport-secret"),
    ],
)
def test_cannot_record_unverified_original_future_receipt_or_scan(
    client, db, world, field, value
):
    as_user(client, db, world["director"])
    assert (
        client.post(
            ROOT + "/consents", json={**paper_payload(world), field: value}
        ).status_code
        == 400
    )
    assert db.scalar(select(func.count(PaperConsent.id))) == 0


@pytest.mark.parametrize(
    "kind", ["access", "correction", "withdrawal", "stop_processing", "erasure"]
)
def test_request_types_private_idempotent_routed_and_manual(client, db, world, kind):
    w = world
    as_user(client, db, w["parent"])
    payload = {"kind": kind, "idempotency_key": str(uuid4())}
    created = client.post(ROOT + "/requests", json=payload)
    assert created.status_code == 201
    item = created.json()
    assert (
        item["status"] == "submitted"
        and item["needs_deadline"]
        and item["due_at"] is None
    )
    assert client.post(ROOT + "/requests", json=payload).json()["id"] == item["id"]
    assert (
        client.post(
            ROOT + "/requests", json={**payload, "child_id": str(w["child"].id)}
        ).status_code
        == 409
    )
    as_user(client, db, w["second_parent"])
    assert client.get(ROOT + "/requests").json() == []
    as_user(client, db, w["foreign"])
    assert client.get(ROOT + "/operator/requests").json() == []
    assert (
        client.post(
            ROOT + f"/operator/requests/{item['id']}/status",
            json={
                "status": "verifying",
                "expected_status": "submitted",
                "due_at": "2026-11-01T12:00:00Z",
            },
        ).status_code
        == 404
    )
    as_user(client, db, w["director"])
    assert [r["id"] for r in client.get(ROOT + "/operator/requests").json()] == [
        item["id"]
    ]
    assert db.get(User, w["parent"].id).status == "active"


def test_request_status_expected_state_deadline_decision_and_history(client, db, world):
    w = world
    as_user(client, db, w["parent"])
    item = client.post(
        ROOT + "/requests", json={"kind": "erasure", "idempotency_key": str(uuid4())}
    ).json()
    path = ROOT + f"/operator/requests/{item['id']}/status"
    transition = {
        "status": "verifying",
        "expected_status": "submitted",
        "due_at": "2020-01-01T12:00:00Z",
    }
    assert client.post(path, json=transition).status_code == 403
    as_user(client, db, w["director"])
    assert (
        client.post(
            path, json={"status": "verifying", "expected_status": "submitted"}
        ).status_code
        == 400
    )
    assert (
        client.post(path, json={**transition, "status": "completed"}).status_code == 409
    )
    moved = client.post(path, json=transition)
    assert moved.status_code == 200 and moved.json()["overdue"]
    assert client.post(path, json=transition).status_code == 409
    assert (
        client.post(
            path, json={"status": "in_review", "expected_status": "verifying"}
        ).status_code
        == 200
    )
    finish = {
        "status": "completed",
        "expected_status": "in_review",
        "decision_code": "fulfilled_offline",
    }
    assert client.post(path, json=finish).status_code == 400
    done = client.post(path, json={**finish, "outcome_confirmed": True})
    assert done.status_code == 200 and len(done.json()["history"]) == 4
    assert not done.json()["overdue"] and db.get(User, w["parent"].id) is not None


def test_extra_subject_tenant_fields_origin_and_logs_are_private(
    client, db, world, caplog
):
    w = world
    as_user(client, db, w["parent"])
    payload = {"kind": "access", "idempotency_key": str(uuid4())}
    for key in ("organization_id", "requester_user_id", "passport", "details", "token"):
        response = client.post(
            ROOT + "/requests", json={**payload, key: "synthetic-private-secret"}
        )
        assert (
            response.status_code == 400
            and "synthetic-private-secret" not in response.text
        )
    assert (
        client.post(
            ROOT + "/requests",
            json=payload,
            headers={"Origin": "https://evil.example.test"},
        ).status_code
        == 403
    )
    assert db.scalar(select(func.count(PrivacyRequest.id))) == 0
    assert "synthetic-private-secret" not in caplog.text
    item = client.post(ROOT + "/requests", json=payload).json()
    event = db.scalar(
        select(AuditEvent).where(AuditEvent.entity_id == UUID(item["id"]))
    )
    assert event.details == {} and event.action == "privacy.request.create"


def test_evidence_and_legal_versions_are_database_immutable(db, world):
    document = world["catalog"].documents[0]
    for statement in (
        "UPDATE privacy_documents SET content = 'rewritten' WHERE id = :id",
        "DELETE FROM privacy_documents WHERE id = :id",
    ):
        with pytest.raises(DBAPIError), db.begin_nested():
            db.execute(text(statement), {"id": document.id})
    assert db.get(LegalDocument, document.id).content_hash == document.content_hash


def test_missing_register_fields_are_explicitly_unapproved(client, db, users):
    as_user(client, db, users[2])
    register = client.get(ROOT + "/me").json()["purposes"]
    assert {p["code"] for p in register} >= {
        "account_access",
        "child_roster",
        "attendance",
        "rights_requests",
    }
    assert all(
        not p["ready"] and p["legal_basis"] is None and p["retention"] is None
        for p in register
    )
    assert all(
        p["processors"] is None
        and p["locations"] is None
        and p["consent_required"] is None
        for p in register
    )


def test_paper_duplicate_new_key_and_receipt_before_document_rejected(
    client, db, world
):
    payload = paper_payload(world)
    record(client, db, world, payload)
    duplicate = client.post(
        ROOT + "/consents", json={**payload, "idempotency_key": str(uuid4())}
    )
    assert (
        duplicate.status_code == 409
        and duplicate.json()["error"]["code"] == "PRIVACY_ALREADY_RECORDED"
    )
    assert (
        client.post(
            ROOT + "/consents",
            json={
                **payload,
                "idempotency_key": str(uuid4()),
                "received_on": "2000-01-01",
            },
        ).status_code
        == 400
    )


@pytest.mark.parametrize(
    "zone,hour,receipt_offset,expected",
    [
        ("Europe/Moscow", 23, 1, 201),
        ("America/Los_Angeles", 0, 0, 400),
    ],
)
def test_original_date_uses_operator_day_not_utc(
    client, db, world, monkeypatch, zone, hour, receipt_offset, expected
):
    from app.core import organization_time

    frozen = (datetime.now(UTC) + timedelta(days=2)).replace(hour=hour, minute=30)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)

    monkeypatch.setattr(organization_time, "datetime", FrozenDateTime)
    world["org"].timezone = zone
    as_user(client, db, world["director"])
    payload = paper_payload(world)
    payload["received_on"] = str(frozen.date() + timedelta(days=receipt_offset))
    assert client.post(ROOT + "/consents", json=payload).status_code == expected


def test_withdrawal_requires_a_later_operator_calendar_day(
    client, db, world, monkeypatch
):
    from app.core import organization_time

    world["org"].timezone = "Europe/Moscow"
    item = record(client, db, world)
    frozen = (datetime.now(UTC) + timedelta(days=2)).replace(hour=23, minute=30)

    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen.astimezone(tz) if tz else frozen.replace(tzinfo=None)

    monkeypatch.setattr(organization_time, "datetime", FrozenDateTime)
    db.add(
        ConsentEvent(
            organization_id=world["org"].id,
            consent_id=UUID(item["id"]),
            actor_user_id=world["parent"].id,
            action="withdrawn",
            created_at=frozen,
        )
    )
    db.flush()
    payload = {
        **paper_payload(world),
        "received_on": str(frozen.date() + timedelta(days=1)),
    }
    response = client.post(ROOT + "/consents", json=payload)
    assert (
        response.status_code == 409
        and response.json()["error"]["code"] == "PRIVACY_NEW_ORIGINAL_REQUIRED"
    )
    frozen += timedelta(days=1)
    payload = {
        **payload,
        "received_on": str(frozen.date() + timedelta(days=1)),
        "idempotency_key": str(uuid4()),
    }
    assert client.post(ROOT + "/consents", json=payload).status_code == 201


def test_concurrent_request_record_and_withdrawal_use_single_evidence(migrations):
    """Two PostgreSQL connections contend on a tenant in an isolated NEW schema."""
    schema = "privacy_race_" + uuid4().hex
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    isolated = engine.execution_options(schema_translate_map={None: schema})
    try:
        Base.metadata.create_all(isolated)
        with Session(isolated, expire_on_commit=False) as setup:
            org = Organization(
                name="СИНТЕТИЧЕСКИЙ конкурентный тест",
                status="active",
                timezone="Europe/Moscow",
            )
            setup.add(org)
            setup.flush()
            actor = User(
                organization_id=org.id,
                username="synthetic-privacy-race",
                password_hash="synthetic-unused",
                role="DIRECTOR",
                status="active",
                must_change_password=False,
            )
            setup.add(actor)
            setup.flush()
            catalog = install_synthetic_catalog(setup, org.id)
            setup.commit()
            actor_id = actor.id
            paper = PaperConsentInput(
                purpose_id=catalog.purposes[1].id,
                document_id=catalog.documents[1].id,
                subject_user_id=actor.id,
                received_on=datetime.now(UTC).date(),
                original_held_confirmed=True,
                authority_confirmed=True,
                idempotency_key=uuid4(),
            )
        request = RequestInput(kind="access", idempotency_key=uuid4())

        def race(operation):
            barrier = Barrier(2)

            def run():
                with Session(isolated, expire_on_commit=False) as session:
                    user = session.get(User, actor_id)
                    pid = session.scalar(select(func.pg_backend_pid()))
                    barrier.wait(timeout=10)
                    result = operation(session, user)
                    session.commit()
                    return result, pid

            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run) for _ in range(2)]
                results = [future.result(timeout=15) for future in futures]
            assert len({r[1] for r in results}) == 2
            assert results[0][0]["id"] == results[1][0]["id"]
            return results[0][0]

        race(lambda db, user: privacy.create_request(db, user, request))
        item = race(lambda db, user: privacy.record_consent(db, user, paper))
        race(lambda db, user: privacy.withdraw_consent(db, user, UUID(str(item["id"]))))
        with Session(isolated) as verify:
            assert verify.scalar(select(func.count(PrivacyRequest.id))) == 1
            assert verify.scalar(select(func.count(PaperConsent.id))) == 1
            assert verify.scalar(select(func.count(ConsentEvent.id))) == 2
    finally:
        with engine.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))

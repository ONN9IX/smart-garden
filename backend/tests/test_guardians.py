"""Guardian API tests use synthetic tenant data and verify account revocation."""

from datetime import date

from app.models.auth_session import AuthSession
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.user import User
from app.services.auth import issue_session
from tests.conftest import TEST_PASSWORD


def _login(client):
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200


def test_optional_contact_normalization_and_tenant(client, db, users):
    _, other, _, _ = users
    _login(client)
    root = "/api/v1/guardians"
    payload = {"first_name": " Анна ", "last_name": "Тестовая", "middle_name": "", "phone": "", "email": "ANNA@EXAMPLE.TEST"}
    response = client.post(root, json=payload)
    assert response.status_code == 201
    guardian = response.json()
    assert guardian["first_name"] == "Анна"
    assert guardian["middle_name"] is None and guardian["phone"] is None
    assert guardian["email"] == "anna@example.test"
    assert guardian["children"] == [] and guardian["account"] is None
    assert "organization_id" not in guardian
    duplicate = client.post(root, json=payload)
    assert duplicate.status_code == 201
    assert len(client.get(f"{root}?q=анна").json()["items"]) == 2
    assert client.post(root, json={**payload, "organization_id": str(other.id)}).status_code == 400
    assert client.post(root, json={**payload, "email": "invalid"}).status_code == 400
    assert client.patch(f"{root}/{guardian['id']}", json={"phone": "+79990000000", "email": None}).json()["email"] is None
    foreign = Guardian(organization_id=other.id, first_name="Чужая", last_name="Тестовая", status="active")
    db.add(foreign)
    db.flush()
    assert client.get(f"{root}/{foreign.id}").json()["error"]["code"] == "NOT_FOUND"
    assert client.patch(f"{root}/{foreign.id}", json={"phone": "123"}).status_code == 404
    assert client.post(f"{root}/{foreign.id}/archive").status_code == 404
    assert client.post(f"{root}/{guardian['id']}/archive").json()["status"] == "archived"
    remaining = client.get(root).json()["items"]
    assert len(remaining) == 1 and remaining[0]["id"] == duplicate.json()["id"]
    assert client.post(f"{root}/{guardian['id']}/restore").json()["status"] == "active"


def test_archive_requires_unlink_and_blocks_parent_session(client, db, users):
    organization, _, _, _ = users
    _login(client)
    group = Group(organization_id=organization.id, name="Группа", status="active")
    db.add(group)
    db.flush()
    child = Child(
        organization_id=organization.id, group_id=group.id, first_name="Ребёнок",
        last_name="Тестовый", birth_date=date(2021, 1, 1), status="active",
    )
    parent = User(
        organization_id=organization.id, username="parent-guardian", role="PARENT",
        status="active", password_hash="synthetic-hash", must_change_password=False,
    )
    db.add_all([child, parent])
    db.flush()
    guardian = Guardian(
        organization_id=organization.id, user_id=parent.id,
        first_name="Представитель", last_name="Тестовый", status="active",
    )
    db.add(guardian)
    db.flush()
    link = ChildGuardian(
        organization_id=organization.id, child_id=child.id, guardian_id=guardian.id,
        relation_type="other", status="active",
    )
    token = issue_session(db, parent)
    db.add(link)
    db.flush()
    session = db.query(AuthSession).filter_by(user_id=parent.id).one()
    rejected = client.post(f"/api/v1/guardians/{guardian.id}/archive")
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "GUARDIAN_HAS_ACTIVE_CHILDREN"
    assert parent.status == "active" and session.revoked_at is None
    link.status = "archived"
    db.flush()
    archived = client.post(f"/api/v1/guardians/{guardian.id}/archive")
    assert archived.status_code == 200
    assert archived.json()["account"]["status"] == "blocked"
    assert parent.status == "blocked"
    db.refresh(session)
    assert session.revoked_at is not None and token
    restored = client.post(f"/api/v1/guardians/{guardian.id}/restore")
    assert restored.status_code == 200
    assert restored.json()["account"]["status"] == "blocked"

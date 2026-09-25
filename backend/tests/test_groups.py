"""Group API integration against two synthetic PostgreSQL tenants."""

from datetime import date
from uuid import UUID

from app.models.child import Child
from app.models.group import Group


def _login(client):
    from tests.conftest import TEST_PASSWORD

    response = client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD})
    assert response.status_code == 200


def test_group_lifecycle_and_conflicts(client, db, users):
    organization, other, _, _ = users
    _login(client)
    root = "/api/v1/groups"
    assert client.post(root, json={"name": "  Ромашка  ", "organization_id": str(other.id)}).status_code == 400
    created = client.post(root, json={"name": " Ромашка "})
    assert created.status_code == 201
    group = created.json()
    assert group["name"] == "Ромашка" and "organization_id" not in group
    group_id = group["id"]
    assert client.post(root, json={"name": "ромашка"}).json()["error"]["code"] == "GROUP_NAME_CONFLICT"
    second_tenant = Group(organization_id=other.id, name="Ромашка", status="active")
    db.add(second_tenant)
    db.flush()
    assert [item["id"] for item in client.get(root).json()["items"]] == [group_id]
    assert client.get(f"{root}/{second_tenant.id}").json()["error"]["code"] == "NOT_FOUND"
    assert client.patch(f"{root}/{second_tenant.id}", json={"name": "Чужая"}).status_code == 404
    assert client.patch(f"{root}/{group_id}", json={"name": "  Солнце  "}).json()["name"] == "Солнце"
    assert client.post(f"{root}/{group_id}/archive").json()["status"] == "archived"
    assert client.get(root).json()["items"] == []
    assert len(client.get(f"{root}?status=archived").json()["items"]) == 1
    assert client.post(f"{root}/{group_id}/restore").json()["status"] == "active"
    assert db.get(Group, UUID(group_id)).organization_id == organization.id


def test_archiving_nonempty_and_restoring_conflict(client, db, users):
    organization, _, _, _ = users
    _login(client)
    root = "/api/v1/groups"
    first = client.post(root, json={"name": "Первая"}).json()
    group_id = first["id"]
    child = Child(
        organization_id=organization.id, group_id=group_id, first_name="Тест",
        last_name="Ребёнок", birth_date=date(2021, 1, 1), status="active",
    )
    db.add(child)
    db.flush()
    rejected = client.post(f"{root}/{group_id}/archive")
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "GROUP_NOT_EMPTY"
    child.status = "archived"
    db.flush()
    assert client.post(f"{root}/{group_id}/archive").status_code == 200
    assert client.post(root, json={"name": "ПЕРВАЯ"}).status_code == 201
    conflict = client.post(f"{root}/{group_id}/restore")
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "GROUP_NAME_CONFLICT"


def test_parent_is_forbidden_group_management(client, db, users):
    from app.core.security import hash_password
    from app.models.user import User
    from app.services.auth import COOKIE_NAME, issue_session

    organization, _, _, _ = users
    parent = User(
        organization_id=organization.id, username="parent-groups", role="PARENT",
        status="active", must_change_password=False, password_hash=hash_password("synthetic-password-123"),
    )
    db.add(parent)
    db.flush()
    token = issue_session(db, parent)
    db.flush()
    client.cookies.set(COOKIE_NAME, token, path="/api/v1")
    response = client.get("/api/v1/groups")
    assert response.status_code == 403

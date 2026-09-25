"""Synthetic child API integration, group state and tenant isolation."""

from datetime import date, datetime, timedelta, timezone

from app.models.child import Child
from app.models.group import Group
from tests.conftest import TEST_PASSWORD


def _login(client):
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200


def _group(client, name):
    response = client.post("/api/v1/groups", json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _child_data(group_id, first_name="Тест"):
    return {"group_id": group_id, "first_name": first_name, "last_name": "Ребёнок", "middle_name": None, "birth_date": "2021-05-10"}


def test_create_edit_filter_archive_and_duplicates(client, users):
    _login(client)
    group_id = _group(client, "Кедр")
    other_id = _group(client, "Дуб")
    response = client.post("/api/v1/children", json=_child_data(group_id))
    assert response.status_code == 201
    child = response.json()
    assert child["group"]["id"] == group_id
    assert child["guardians"] == [] and "organization_id" not in child
    assert client.post("/api/v1/children", json=_child_data(group_id)).status_code == 201
    assert len(client.get(f"/api/v1/children?group_id={group_id}&q=ребён").json()["items"]) == 2
    assert client.get(f"/api/v1/children?group_id={other_id}").json()["items"] == []
    edited = client.patch(f"/api/v1/children/{child['id']}", json={"group_id": other_id, "middle_name": " Тестович "})
    assert edited.status_code == 200
    assert edited.json()["group"]["id"] == other_id and edited.json()["middle_name"] == "Тестович"
    assert client.post(f"/api/v1/children/{child['id']}/archive").json()["status"] == "archived"
    assert len(client.get("/api/v1/children").json()["items"]) == 1
    assert len(client.get("/api/v1/children?status=archived").json()["items"]) == 1
    assert client.post(f"/api/v1/children/{child['id']}/restore").json()["status"] == "active"


def test_bad_date_group_and_foreign_tenant_hidden(client, db, users):
    _, other, _, _ = users
    _login(client)
    group_id = _group(client, "Сад")
    future = _child_data(group_id)
    future["birth_date"] = (datetime.now(timezone.utc).date() + timedelta(days=4)).isoformat()
    assert client.post("/api/v1/children", json=future).json()["error"]["code"] == "INVALID_BIRTH_DATE"
    assert client.post("/api/v1/children", json={**_child_data(group_id), "organization_id": str(other.id)}).status_code == 400
    assert client.patch("/api/v1/children/00000000-0000-0000-0000-000000000001", json={}).status_code == 400
    foreign_group = Group(organization_id=other.id, name="Чужая", status="active")
    db.add(foreign_group)
    db.flush()
    assert client.post("/api/v1/children", json=_child_data(str(foreign_group.id))).json()["error"]["code"] == "NOT_FOUND"
    assert client.get(f"/api/v1/children?group_id={foreign_group.id}").status_code == 404
    foreign_child = Child(
        organization_id=other.id, group_id=foreign_group.id, first_name="Чужой",
        last_name="Ребёнок", birth_date=date(2021, 5, 10), status="active",
    )
    db.add(foreign_child)
    db.flush()
    assert client.get(f"/api/v1/children/{foreign_child.id}").json()["error"]["code"] == "NOT_FOUND"
    assert client.post(f"/api/v1/children/{foreign_child.id}/archive").status_code == 404
    local = client.post("/api/v1/children", json=_child_data(group_id)).json()
    assert client.patch(f"/api/v1/children/{local['id']}", json={"group_id": str(foreign_group.id)}).status_code == 404
    assert client.post(f"/api/v1/groups/{group_id}/archive").json()["error"]["code"] == "GROUP_NOT_EMPTY"


def test_archived_group_cannot_receive_or_restore_child(client, users):
    _login(client)
    group_id = _group(client, "Архивная")
    child = client.post("/api/v1/children", json=_child_data(group_id)).json()
    assert client.post(f"/api/v1/children/{child['id']}/archive").status_code == 200
    assert client.post(f"/api/v1/groups/{group_id}/archive").status_code == 200
    assert client.post("/api/v1/children", json=_child_data(group_id)).json()["error"]["code"] == "GROUP_ARCHIVED"
    assert client.post(f"/api/v1/children/{child['id']}/restore").json()["error"]["code"] == "GROUP_ARCHIVED"

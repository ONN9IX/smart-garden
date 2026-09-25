"""Synthetic many-to-many contract and tenant-bound relation lifecycle."""

from app.models.guardian import Guardian
from tests.conftest import TEST_PASSWORD


def _login(client):
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200


def test_link_multiple_edit_archive_reactivate(client, users):
    _login(client)
    group_id = client.post("/api/v1/groups", json={"name": "Садовая"}).json()["id"]
    child_ids = [
        client.post("/api/v1/children", json={
            "group_id": group_id, "first_name": "Ребёнок", "last_name": f"Тестовый {index}",
            "birth_date": "2021-01-01",
        }).json()["id"]
        for index in (1, 2)
    ]
    guardian_ids = [
        client.post("/api/v1/guardians", json={"first_name": "Представитель", "last_name": f"Тестовый {index}"}).json()["id"]
        for index in (1, 2)
    ]
    path = f"/api/v1/children/{child_ids[0]}/guardians"
    first = client.post(path, json={"guardian_id": guardian_ids[0], "relation_type": "mother"})
    assert first.status_code == 201
    link_id = first.json()["id"]
    assert first.json()["guardian"]["id"] == guardian_ids[0]
    assert client.post(path, json={"guardian_id": guardian_ids[1], "relation_type": "father"}).status_code == 201
    assert client.post(f"/api/v1/children/{child_ids[1]}/guardians", json={"guardian_id": guardian_ids[0], "relation_type": "other"}).status_code == 201
    assert len(client.get(f"/api/v1/children/{child_ids[0]}").json()["guardians"]) == 2
    assert len(client.get(f"/api/v1/guardians/{guardian_ids[0]}").json()["children"]) == 2
    duplicate = client.post(path, json={"guardian_id": guardian_ids[0], "relation_type": "mother"})
    assert duplicate.status_code == 409 and duplicate.json()["error"]["code"] == "RELATION_ALREADY_EXISTS"
    assert client.patch(f"{path}/{guardian_ids[0]}", json={"relation_type": "legal_guardian"}).json()["relation_type"] == "legal_guardian"
    assert client.post(f"{path}/{guardian_ids[0]}/archive").json()["status"] == "archived"
    assert client.patch(f"{path}/{guardian_ids[0]}", json={"relation_type": "father"}).status_code == 404
    restored = client.post(path, json={"guardian_id": guardian_ids[0], "relation_type": "father"})
    assert restored.status_code == 200
    assert restored.json()["id"] == link_id and restored.json()["relation_type"] == "father"
    assert client.post(f"{path}/{guardian_ids[0]}/archive").status_code == 200
    assert client.post(f"{path}/{guardian_ids[0]}/restore").json()["status"] == "active"
    assert client.post("/api/v1/guardians", json={"first_name": "Без", "last_name": "Связей"}).status_code == 201


def test_foreign_tenant_and_archived_entities_rejected(client, db, users):
    _, other, _, _ = users
    _login(client)
    group_id = client.post("/api/v1/groups", json={"name": "Лес"}).json()["id"]
    child_id = client.post("/api/v1/children", json={
        "group_id": group_id, "first_name": "Ребёнок", "last_name": "Тестовый", "birth_date": "2021-01-01",
    }).json()["id"]
    guardian_id = client.post("/api/v1/guardians", json={"first_name": "Представитель", "last_name": "Тестовый"}).json()["id"]
    foreign = Guardian(organization_id=other.id, first_name="Чужой", last_name="Тестовый", status="active")
    db.add(foreign)
    db.flush()
    path = f"/api/v1/children/{child_id}/guardians"
    assert client.post(path, json={"guardian_id": str(foreign.id), "relation_type": "other"}).json()["error"]["code"] == "NOT_FOUND"
    assert client.post(path, json={"guardian_id": guardian_id, "relation_type": "unknown"}).status_code == 400
    assert client.post(f"/api/v1/guardians/{guardian_id}/archive").status_code == 200
    assert client.post(path, json={"guardian_id": guardian_id, "relation_type": "other"}).json()["error"]["code"] == "GUARDIAN_ARCHIVED"
    assert client.post(f"/api/v1/guardians/{guardian_id}/restore").status_code == 200
    assert client.post(f"/api/v1/children/{child_id}/archive").status_code == 200
    assert client.post(path, json={"guardian_id": guardian_id, "relation_type": "other"}).json()["error"]["code"] == "CHILD_ARCHIVED"

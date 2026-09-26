"""Two authenticated tenants cannot read, mutate or link each other's records."""

from fastapi.testclient import TestClient

from app.core.security import hash_password
from app.main import app
from app.models.user import User
from tests.conftest import TEST_PASSWORD


def _login(client, username):
    assert client.post("/api/v1/auth/login", json={"username": username, "password": TEST_PASSWORD}).status_code == 200


def test_two_directors_are_isolated(client, db, users):
    _, other, _, _ = users
    director_b = User(
        organization_id=other.id, username="director-other-test", role="DIRECTOR",
        status="active", password_hash=hash_password(TEST_PASSWORD), must_change_password=False,
    )
    db.add(director_b)
    db.flush()
    _login(client, "admin-test")
    group_a = client.post("/api/v1/groups", json={"name": "Общая"}).json()["id"]
    child_a = client.post("/api/v1/children", json={
        "group_id": group_a, "first_name": "Тестовый", "last_name": "Ребёнок", "birth_date": "2020-01-01",
    }).json()["id"]
    guardian_a = client.post("/api/v1/guardians", json={"first_name": "Тестовый", "last_name": "Представитель"}).json()["id"]

    with TestClient(app) as other_client:
        _login(other_client, "director-other-test")
        group_b = other_client.post("/api/v1/groups", json={"name": "Общая"}).json()["id"]
        child_b = other_client.post("/api/v1/children", json={
            "group_id": group_b, "first_name": "Другой", "last_name": "Ребёнок", "birth_date": "2020-01-01",
        }).json()["id"]
        guardian_b = other_client.post("/api/v1/guardians", json={"first_name": "Другой", "last_name": "Представитель"}).json()["id"]
        for root, foreign_id in (("groups", group_a), ("children", child_a), ("guardians", guardian_a)):
            response = other_client.get(f"/api/v1/{root}/{foreign_id}")
            assert response.status_code == 404 and response.json()["error"]["code"] == "NOT_FOUND"
        assert other_client.patch(f"/api/v1/guardians/{guardian_a}", json={"first_name": "Чужой"}).status_code == 404
        assert other_client.post("/api/v1/children", json={
            "group_id": group_a, "first_name": "Чужой", "last_name": "Ребёнок", "birth_date": "2020-01-01",
        }).status_code == 404
        assert other_client.post(f"/api/v1/children/{child_b}/guardians", json={
            "guardian_id": guardian_a, "relation_type": "other",
        }).status_code == 404
        assert client.post(f"/api/v1/children/{child_a}/guardians", json={
            "guardian_id": guardian_b, "relation_type": "other",
        }).status_code == 404
        assert [item["id"] for item in other_client.get("/api/v1/groups").json()["items"]] == [group_b]
        assert [item["id"] for item in client.get("/api/v1/groups").json()["items"]] == [group_a]

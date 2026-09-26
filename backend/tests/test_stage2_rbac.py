"""PARENT may use auth but every Stage 2 management route requires manager role."""

from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_PASSWORD


def test_parent_cannot_manage_any_stage2_entity(client, users):
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200
    group_id = client.post("/api/v1/groups", json={"name": "Группа"}).json()["id"]
    child_id = client.post("/api/v1/children", json={
        "group_id": group_id, "first_name": "Ребёнок", "last_name": "Тестовый", "birth_date": "2020-01-01",
    }).json()["id"]
    guardian_id = client.post("/api/v1/guardians", json={"first_name": "Представитель", "last_name": "Тестовый"}).json()["id"]
    credentials = client.post(f"/api/v1/guardians/{guardian_id}/account").json()
    with TestClient(app) as parent:
        assert parent.post("/api/v1/auth/login", json={
            "username": credentials["account"]["username"], "password": credentials["temporary_password"],
        }).status_code == 200
        assert parent.post("/api/v1/auth/change-password", json={"new_password": "new-parent-secret-123"}).status_code == 200
        operations = (
            ("get", "/api/v1/groups", None),
            ("post", "/api/v1/groups", {"name": "Запрещено"}),
            ("get", f"/api/v1/groups/{group_id}", None),
            ("patch", f"/api/v1/groups/{group_id}", {"name": "Запрещено"}),
            ("post", f"/api/v1/groups/{group_id}/archive", None),
            ("get", "/api/v1/children", None),
            ("post", "/api/v1/children", {"group_id": group_id, "first_name": "Тест", "last_name": "Тест", "birth_date": "2020-01-01"}),
            ("get", f"/api/v1/children/{child_id}", None),
            ("patch", f"/api/v1/children/{child_id}", {"first_name": "Запрещено"}),
            ("post", f"/api/v1/children/{child_id}/guardians", {"guardian_id": guardian_id, "relation_type": "other"}),
            ("get", "/api/v1/guardians", None),
            ("post", "/api/v1/guardians", {"first_name": "Тест", "last_name": "Тест"}),
            ("get", f"/api/v1/guardians/{guardian_id}", None),
            ("patch", f"/api/v1/guardians/{guardian_id}", {"first_name": "Запрещено"}),
            ("post", f"/api/v1/guardians/{guardian_id}/account/reset-password", None),
        )
        for method, path, payload in operations:
            response = getattr(parent, method)(path, json=payload) if payload is not None else getattr(parent, method)(path)
            assert response.status_code == 403 and response.json()["error"]["code"] == "FORBIDDEN"
        assert parent.get("/api/v1/auth/me").status_code == 200

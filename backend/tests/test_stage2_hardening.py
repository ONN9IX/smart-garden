"""Stage 2 contract, safe cross-origin behavior and idempotent synthetic seed."""

from sqlalchemy import func, select

from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.group import Group
from app.models.guardian import Guardian
from app.services.seed import seed_stage2
from tests.conftest import TEST_PASSWORD


def test_stage2_seed_is_idempotent_and_minimal(db, users):
    organization, other, _, _ = users
    seed_stage2(db, organization)
    db.flush()
    seed_stage2(db, organization)
    db.flush()
    for model in (Group, Child, Guardian, ChildGuardian):
        assert db.scalar(select(func.count()).select_from(model).where(model.organization_id == organization.id)) == 1
        assert db.scalar(select(func.count()).select_from(model).where(model.organization_id == other.id)) == 0
    guardian = db.scalar(select(Guardian).where(Guardian.organization_id == organization.id))
    assert db.scalar(select(Group).where(Group.organization_id == organization.id)).name == "Ромашка"
    assert guardian.phone is None and guardian.email is None and guardian.user_id is None


def test_openapi_stage2_endpoints_and_parent_role(client):
    spec = client.get("/openapi.json").json()
    expected = {
        "/api/v1/groups": {"get", "post"},
        "/api/v1/groups/{group_id}": {"get", "patch"},
        "/api/v1/groups/{group_id}/archive": {"post"},
        "/api/v1/groups/{group_id}/restore": {"post"},
        "/api/v1/children": {"get", "post"},
        "/api/v1/children/{child_id}": {"get", "patch"},
        "/api/v1/children/{child_id}/archive": {"post"},
        "/api/v1/children/{child_id}/restore": {"post"},
        "/api/v1/children/{child_id}/guardians": {"post"},
        "/api/v1/children/{child_id}/guardians/{guardian_id}": {"patch"},
        "/api/v1/children/{child_id}/guardians/{guardian_id}/archive": {"post"},
        "/api/v1/children/{child_id}/guardians/{guardian_id}/restore": {"post"},
        "/api/v1/guardians": {"get", "post"},
        "/api/v1/guardians/{guardian_id}": {"get", "patch"},
        "/api/v1/guardians/{guardian_id}/archive": {"post"},
        "/api/v1/guardians/{guardian_id}/restore": {"post"},
        "/api/v1/guardians/{guardian_id}/account": {"post"},
        "/api/v1/guardians/{guardian_id}/account/reset-password": {"post"},
        "/api/v1/guardians/{guardian_id}/account/block": {"post"},
        "/api/v1/guardians/{guardian_id}/account/unblock": {"post"},
    }
    for path, methods in expected.items():
        assert methods <= spec["paths"][path].keys()
        for method in methods:
            operation = spec["paths"][path][method]
            for status in ("400", "401", "403", "404", "409", "500"):
                assert operation["responses"][status]["content"]["application/json"]["schema"]["$ref"].endswith("/ErrorResponse")
    assert "PARENT" in spec["components"]["schemas"]["UserResponse"]["properties"]["role"]["enum"]
    assert "temporary_password" in spec["components"]["schemas"]["TemporaryCredentials"]["properties"]
    for name in ("GroupWrite", "ChildCreate", "ChildPatch", "GuardianCreate", "GuardianPatch"):
        assert "organization_id" not in spec["components"]["schemas"][name]["properties"]
    for path in spec["paths"]:
        assert "temporary_password" not in path


def test_patch_cors_and_safe_validation(client, users):
    origin = "http://localhost:3000"
    preflight = client.options(
        "/api/v1/guardians/00000000-0000-0000-0000-000000000000",
        headers={"Origin": origin, "Access-Control-Request-Method": "PATCH"},
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == origin
    assert "PATCH" in preflight.headers["access-control-allow-methods"]
    assert client.post("/api/v1/auth/login", json={"username": "admin-test", "password": TEST_PASSWORD}).status_code == 200
    bad = client.patch("/api/v1/groups/no-such-id", json={"name": "secret-personal-input"})
    assert bad.status_code == 400 and "secret-personal-input" not in str(bad.json())
    denied = client.patch(
        "/api/v1/groups/00000000-0000-0000-0000-000000000000",
        json={"name": "secret-personal-input"}, headers={"Origin": "https://untrusted.example"},
    )
    assert denied.status_code == 403 and "secret-personal-input" not in str(denied.json())

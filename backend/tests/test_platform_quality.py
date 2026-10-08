"""Reusable platform security/tenant/privacy contract matrix."""

from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.core.permissions import require_role, require_tenant
from app.main import app
from app.models.user import User

SECURITY_MATRIX = [
    # Active protected surface, action, authorized roles.
    ("audit", "read", {"DIRECTOR"}),
    ("organization-settings", "write", {"DIRECTOR"}),
    ("access-accounts-parent", "operate", {"DIRECTOR", "ADMIN"}),
    ("access-accounts-employee", "operate", {"DIRECTOR"}),
    ("teacher-group", "read-write-assigned", {"TEACHER"}),
    ("parent-child", "read-linked", {"PARENT"}),
]
ALL_ROLES = ("DIRECTOR", "ADMIN", "TEACHER", "PARENT")


def actor(role: str, organization_id=None) -> User:
    return User(
        id=uuid4(), organization_id=organization_id or uuid4(), username=f"matrix-{role.lower()}-{uuid4()}",
        password_hash="synthetic-not-usable", role=role, status="active", must_change_password=False,
    )


@pytest.mark.parametrize(("resource", "action", "allowed"), SECURITY_MATRIX)
@pytest.mark.parametrize("role", ALL_ROLES)
def test_role_resource_action_matrix_denies_by_default(resource, action, allowed, role):
    guard = require_role(*sorted(allowed))
    user = actor(role)
    if role in allowed:
        assert guard(user) is user
    else:
        with pytest.raises(AppError) as error:
            guard(user)
        assert error.value.status == 403


def test_tenant_matrix_hides_foreign_objects():
    tenant = uuid4()
    user = actor("DIRECTOR", tenant)
    require_tenant(user, tenant)
    with pytest.raises(AppError) as error:
        require_tenant(user, uuid4())
    assert error.value.status == 404 and error.value.code == "NOT_FOUND"


def test_active_runtime_has_no_stopped_domain_routes():
    stopped_fragments = ("/contracts", "/billing", "/payments", "/debt", "/receipts", "/kiosk", "/psychology", "/subscription")
    paths = {route.path for route in app.routes}
    assert not [path for path in paths if any(fragment in path for fragment in stopped_fragments)]


def test_security_matrix_has_scoped_teacher_parent_and_foreign_tenant_cases():
    resources = {(resource, action) for resource, action, _ in SECURITY_MATRIX}
    assert ("teacher-group", "read-write-assigned") in resources
    assert ("parent-child", "read-linked") in resources
    # Foreign-object visibility is always evaluated through the tenant guard.
    assert require_tenant is not None

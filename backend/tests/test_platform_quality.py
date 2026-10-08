"""Reusable platform security/tenant/privacy integration matrix."""

from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.core.errors import AppError
from app.core.permissions import require_role, require_tenant
from app.core.security import hash_password
from app.main import app
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from tests.conftest import TEST_PASSWORD

ALL_ROLES = ("DIRECTOR", "ADMIN", "TEACHER", "PARENT")


def actor(role: str, organization_id=None) -> User:
    return User(
        id=uuid4(),
        organization_id=organization_id or uuid4(),
        username=f"matrix-{role.lower()}-{uuid4()}",
        password_hash="synthetic-not-usable",
        role=role,
        status="active",
        must_change_password=False,
    )


@pytest.mark.parametrize("role", ALL_ROLES)
def test_low_level_role_guard_remains_deny_by_default(role):
    """Supplementary guard test; endpoint coverage lives in the matrix below."""
    guard = require_role("DIRECTOR", "ADMIN")
    user = actor(role)
    if role in {"DIRECTOR", "ADMIN"}:
        assert guard(user) is user
    else:
        with pytest.raises(AppError) as error:
            guard(user)
        assert error.value.status == 403


def test_low_level_tenant_guard_hides_foreign_objects():
    """Supplementary guard test for the common 404 tenant-hiding contract."""
    tenant = uuid4()
    user = actor("DIRECTOR", tenant)
    require_tenant(user, tenant)
    with pytest.raises(AppError) as error:
        require_tenant(user, uuid4())
    assert error.value.status == 404 and error.value.code == "NOT_FOUND"


@pytest.fixture
def security_world(db, users):
    organization, foreign_organization, director, admin = users
    director.must_change_password = False
    password_hash = hash_password(TEST_PASSWORD)
    assigned_teacher = User(
        organization_id=organization.id,
        username="matrix-assigned-teacher",
        password_hash=password_hash,
        role="TEACHER",
        status="active",
        must_change_password=False,
    )
    unassigned_teacher = User(
        organization_id=organization.id,
        username="matrix-unassigned-teacher",
        password_hash=password_hash,
        role="TEACHER",
        status="active",
        must_change_password=False,
    )
    linked_parent = User(
        organization_id=organization.id,
        username="matrix-linked-parent",
        password_hash=password_hash,
        role="PARENT",
        status="active",
        must_change_password=False,
    )
    unlinked_parent = User(
        organization_id=organization.id,
        username="matrix-unlinked-parent",
        password_hash=password_hash,
        role="PARENT",
        status="active",
        must_change_password=False,
    )
    db.add_all([assigned_teacher, unassigned_teacher, linked_parent, unlinked_parent])
    db.flush()

    assigned_employee = Employee(
        organization_id=organization.id,
        user_id=assigned_teacher.id,
        first_name="Матрица",
        last_name="Назначенный",
        position="Воспитатель",
        category="teacher",
        status="active",
    )
    unassigned_employee = Employee(
        organization_id=organization.id,
        user_id=unassigned_teacher.id,
        first_name="Матрица",
        last_name="Без назначения",
        position="Воспитатель",
        category="teacher",
        status="active",
    )
    assigned_group = Group(
        organization_id=organization.id,
        name="Матрица доступная группа",
        status="active",
    )
    unassigned_group = Group(
        organization_id=organization.id,
        name="Матрица скрытая группа",
        status="active",
    )
    archived_group = Group(
        organization_id=organization.id,
        name="Матрица архивная группа",
        status="archived",
    )
    foreign_group = Group(
        organization_id=foreign_organization.id,
        name="FOREIGN-TENANT-GROUP-SECRET",
        status="active",
    )
    db.add_all([
        assigned_employee,
        unassigned_employee,
        assigned_group,
        unassigned_group,
        archived_group,
        foreign_group,
    ])
    db.flush()

    assignment = TeacherGroupAssignment(
        organization_id=organization.id,
        employee_id=assigned_employee.id,
        group_id=assigned_group.id,
        status="active",
        assigned_by=director.id,
    )
    linked_child = Child(
        organization_id=organization.id,
        group_id=assigned_group.id,
        first_name="Матрица",
        last_name="Связанный ребёнок",
        birth_date=date(2020, 1, 1),
        status="active",
    )
    unlinked_child = Child(
        organization_id=organization.id,
        group_id=unassigned_group.id,
        first_name="Матрица",
        last_name="Несвязанный ребёнок",
        birth_date=date(2020, 2, 2),
        status="active",
    )
    archived_child = Child(
        organization_id=organization.id,
        group_id=assigned_group.id,
        first_name="Матрица",
        last_name="Архивный ребёнок",
        birth_date=date(2020, 3, 3),
        status="archived",
    )
    foreign_child = Child(
        organization_id=foreign_organization.id,
        group_id=foreign_group.id,
        first_name="FOREIGN-TENANT-CHILD-SECRET",
        last_name="Никогда не раскрывать",
        birth_date=date(2020, 4, 4),
        status="active",
    )
    db.add_all([assignment, linked_child, unlinked_child, archived_child, foreign_child])
    db.flush()

    linked_guardian = Guardian(
        organization_id=organization.id,
        user_id=linked_parent.id,
        first_name="Матрица",
        last_name="Связанный родитель",
        status="active",
    )
    unlinked_guardian = Guardian(
        organization_id=organization.id,
        user_id=unlinked_parent.id,
        first_name="Матрица",
        last_name="Несвязанный родитель",
        status="active",
    )
    db.add_all([linked_guardian, unlinked_guardian])
    db.flush()
    relation = ChildGuardian(
        organization_id=organization.id,
        child_id=linked_child.id,
        guardian_id=linked_guardian.id,
        relation_type="legal_guardian",
        status="active",
    )
    db.add(relation)
    db.flush()
    return SimpleNamespace(
        director=director,
        admin=admin,
        assigned_teacher=assigned_teacher,
        unassigned_teacher=unassigned_teacher,
        linked_parent=linked_parent,
        unlinked_parent=unlinked_parent,
        assigned_group=assigned_group,
        unassigned_group=unassigned_group,
        archived_group=archived_group,
        foreign_group=foreign_group,
        assignment=assignment,
        linked_child=linked_child,
        unlinked_child=unlinked_child,
        archived_child=archived_child,
        foreign_child=foreign_child,
        relation=relation,
        missing_id=uuid4(),
    )


ACCESS_MATRIX = (
    # Management roles and tenant hiding.
    ("director", "management-linked-child", 200, None, None),
    ("admin", "management-linked-child", 200, None, None),
    ("director", "management-foreign-child", 404, "NOT_FOUND", None),
    ("admin", "management-missing-child", 404, "NOT_FOUND", None),
    # Role-denied management operations.
    ("assigned_teacher", "management-linked-child", 403, "FORBIDDEN", None),
    ("linked_parent", "management-assigned-group", 403, "FORBIDDEN", None),
    # TEACHER assignment, tenant, archive and revoked-assignment boundaries.
    ("assigned_teacher", "teacher-assigned-group", 200, None, None),
    ("assigned_teacher", "teacher-unassigned-group", 404, "NOT_FOUND", None),
    ("unassigned_teacher", "teacher-assigned-group", 404, "NOT_FOUND", None),
    ("assigned_teacher", "teacher-foreign-group", 404, "NOT_FOUND", None),
    ("assigned_teacher", "teacher-archived-group", 404, "NOT_FOUND", None),
    ("assigned_teacher", "teacher-assigned-group", 404, "NOT_FOUND", "revoke-assignment"),
    # PARENT linkage, tenant, archive and revoked-link boundaries.
    ("linked_parent", "parent-linked-child", 200, None, None),
    ("linked_parent", "parent-unlinked-child", 404, "NOT_FOUND", None),
    ("unlinked_parent", "parent-linked-child", 404, "NOT_FOUND", None),
    ("linked_parent", "parent-foreign-child", 404, "NOT_FOUND", None),
    ("linked_parent", "parent-archived-child", 404, "NOT_FOUND", None),
    ("linked_parent", "parent-linked-child", 404, "NOT_FOUND", "revoke-parent-link"),
    # Existing authenticated sessions fail closed after an account is blocked.
    ("director", "management-linked-child", 403, "USER_BLOCKED", "block-actor"),
    ("assigned_teacher", "teacher-assigned-group", 403, "USER_BLOCKED", "block-actor"),
    ("linked_parent", "parent-linked-child", 403, "USER_BLOCKED", "block-actor"),
)


def _matrix_path(world, resource: str) -> str:
    paths = {
        "management-linked-child": f"/api/v1/children/{world.linked_child.id}",
        "management-foreign-child": f"/api/v1/children/{world.foreign_child.id}",
        "management-missing-child": f"/api/v1/children/{world.missing_id}",
        "management-assigned-group": f"/api/v1/groups/{world.assigned_group.id}",
        "teacher-assigned-group": f"/api/v1/teacher/groups/{world.assigned_group.id}",
        "teacher-unassigned-group": f"/api/v1/teacher/groups/{world.unassigned_group.id}",
        "teacher-foreign-group": f"/api/v1/teacher/groups/{world.foreign_group.id}",
        "teacher-archived-group": f"/api/v1/teacher/groups/{world.archived_group.id}",
        "parent-linked-child": f"/api/v1/parent/children/{world.linked_child.id}/today",
        "parent-unlinked-child": f"/api/v1/parent/children/{world.unlinked_child.id}/today",
        "parent-foreign-child": f"/api/v1/parent/children/{world.foreign_child.id}/today",
        "parent-archived-child": f"/api/v1/parent/children/{world.archived_child.id}/today",
    }
    return paths[resource]


@pytest.mark.parametrize(
    ("actor_name", "resource", "expected_status", "expected_code", "mutation"),
    ACCESS_MATRIX,
    ids=[
        f"{actor_name}-{resource}-{mutation or 'active'}"
        for actor_name, resource, _, _, mutation in ACCESS_MATRIX
    ],
)
def test_real_protected_resource_access_matrix(
    client, db, security_world, actor_name, resource, expected_status, expected_code, mutation,
):
    """Exercise actual protected HTTP operations with PostgreSQL-backed relationships."""
    world = security_world
    actor_user = getattr(world, actor_name)
    logged_in = client.post("/api/v1/auth/login", json={
        "username": actor_user.username,
        "password": TEST_PASSWORD,
    })
    assert logged_in.status_code == 200, logged_in.text

    if mutation == "revoke-assignment":
        world.assignment.status = "archived"
    elif mutation == "revoke-parent-link":
        world.relation.status = "archived"
    elif mutation == "block-actor":
        actor_user.status = "blocked"
    db.flush()

    response = client.get(_matrix_path(world, resource))
    assert response.status_code == expected_status, response.text
    if expected_code is not None:
        assert response.json()["error"]["code"] == expected_code
        rendered = response.text
        assert "FOREIGN-TENANT-GROUP-SECRET" not in rendered
        assert "FOREIGN-TENANT-CHILD-SECRET" not in rendered
        assert str(world.foreign_group.id) not in rendered
        assert str(world.foreign_child.id) not in rendered
    elif resource == "management-linked-child":
        assert response.json()["id"] == str(world.linked_child.id)
    elif resource == "parent-linked-child":
        assert response.json()["child"]["id"] == str(world.linked_child.id)
    else:
        assert response.json()["id"] == str(world.assigned_group.id)


def test_active_runtime_has_no_stopped_domain_routes():
    stopped_fragments = (
        "/contracts",
        "/billing",
        "/payments",
        "/debt",
        "/receipts",
        "/kiosk",
        "/psychology",
        "/subscription",
    )
    paths = {route.path for route in app.routes if hasattr(route, "path")}
    assert not [
        path
        for path in paths
        if any(fragment in path for fragment in stopped_fragments)
    ]

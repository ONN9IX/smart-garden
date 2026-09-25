"""Synthetic PostgreSQL schema checks for Stage 2 tenant records and constraints."""

from datetime import date

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.db.session import engine
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.user import User


def _group(organization_id, name="Подготовительная"):
    return Group(organization_id=organization_id, name=name, status="active")


def _child(organization_id, group_id, first_name="Ребёнок"):
    return Child(
        organization_id=organization_id,
        group_id=group_id,
        first_name=first_name,
        last_name="Тестовый",
        birth_date=date(2021, 1, 1),
        status="active",
    )


def _guardian(organization_id, first_name="Представитель"):
    return Guardian(organization_id=organization_id, first_name=first_name, last_name="Тестовый", status="active")


def _invalid(db, record):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(record)
        db.flush()


def test_schema_indexes_and_registration(migrations):
    from app.db.base import Base

    assert {"groups", "children", "guardians", "child_guardians"} <= set(Base.metadata.tables)
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert {"groups", "children", "guardians", "child_guardians"} <= set(inspector.get_table_names())
        indexes = {index["name"] for table in ("groups", "children", "guardians") for index in inspector.get_indexes(table)}
        assert {"uq_groups_active_name", "ix_groups_organization_status", "ix_children_organization_status_group", "ix_guardians_organization_status"} <= indexes


def test_role_and_group_name_constraints(db, users):
    organization, other, _, _ = users
    parent = User(
        organization_id=organization.id,
        username="parent-synthetic",
        password_hash="synthetic-hash",
        role="PARENT",
        status="active",
        must_change_password=True,
    )
    db.add_all([parent, _group(organization.id)])
    db.flush()
    _invalid(db, _group(organization.id, " подготовительная "))
    db.add_all([_group(other.id), Group(organization_id=organization.id, name="ПОДГОТОВИТЕЛЬНАЯ", status="archived")])
    db.flush()
    _invalid(db, Group(organization_id=organization.id, name="Некорректная", status="unknown"))
    _invalid(
        db,
        User(
            organization_id=organization.id,
            username="invalid-role",
            password_hash="synthetic-hash",
            role="INVALID",
            status="active",
            must_change_password=True,
        ),
    )


def test_children_guardians_and_link_constraints(db, users):
    organization, _, _, _ = users
    group = _group(organization.id)
    db.add(group)
    db.flush()
    child = _child(organization.id, group.id)
    twin = _child(organization.id, group.id)
    guardian = _guardian(organization.id)
    db.add_all([child, twin, guardian])
    db.flush()
    assert len(group.children) == 2
    assert guardian.phone is None and guardian.email is None and guardian.user_id is None

    link = ChildGuardian(
        organization_id=organization.id,
        child_id=child.id,
        guardian_id=guardian.id,
        relation_type="mother",
        status="active",
    )
    db.add(link)
    db.flush()
    assert db.scalar(select(ChildGuardian).where(ChildGuardian.child_id == child.id)).guardian == guardian
    link.status = "archived"
    db.flush()
    _invalid(
        db,
        ChildGuardian(
            organization_id=organization.id,
            child_id=child.id,
            guardian_id=guardian.id,
            relation_type="father",
            status="active",
        ),
    )
    _invalid(
        db,
        ChildGuardian(
            organization_id=organization.id,
            child_id=twin.id,
            guardian_id=guardian.id,
            relation_type="unknown",
            status="active",
        ),
    )
    link.status = "active"
    link.relation_type = "legal_guardian"
    db.flush()
    assert link.relation_type == "legal_guardian"


def test_parent_account_is_one_to_one(db, users):
    organization, _, _, _ = users
    parent = User(
        organization_id=organization.id,
        username="parent-unique",
        password_hash="synthetic-hash",
        role="PARENT",
        status="active",
        must_change_password=True,
    )
    db.add(parent)
    db.flush()
    guardian = _guardian(organization.id)
    guardian.user_id = parent.id
    db.add(guardian)
    db.flush()
    assert guardian.user == parent
    duplicate = _guardian(organization.id, "Другой")
    duplicate.user_id = parent.id
    _invalid(db, duplicate)

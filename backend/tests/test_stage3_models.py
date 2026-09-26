"""PostgreSQL migration and constraint checks with synthetic staff and child records."""

from datetime import date, time

import pytest
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

from app.db.session import engine
from app.models.attendance import Attendance
from app.models.child import Child
from app.models.employee import Employee
from app.models.group import Group


def _invalid(db, record):
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(record)
        db.flush()


def test_stage3_tables_and_indexes(migrations):
    from app.db.base import Base

    assert {"employees", "attendance"} <= set(Base.metadata.tables)
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert {"employees", "attendance"} <= set(inspector.get_table_names())
        indexes = {index["name"] for table in ("employees", "attendance") for index in inspector.get_indexes(table)}
        assert {
            "ix_employees_organization_status", "ix_attendance_organization_date_group",
            "ix_attendance_organization_date_status",
        } <= indexes


def test_employee_optional_account_and_constraints(db, users):
    organization, other, _, admin = users
    without_account = Employee(
        organization_id=organization.id, first_name="Тестовая", last_name="Сотрудница",
        position="Воспитатель", status="active",
    )
    linked = Employee(
        organization_id=organization.id, user_id=admin.id,
        first_name="Тестовый", last_name="Администратор", position="Администратор", status="active",
    )
    db.add_all([without_account, linked])
    db.flush()
    assert without_account.user_id is None and linked.user == admin
    db.add(Employee(organization_id=other.id, first_name="Тестовая", last_name="Сотрудница", position="Воспитатель", status="active"))
    db.flush()
    _invalid(db, Employee(
        organization_id=organization.id, user_id=admin.id, first_name="Другой",
        last_name="Администратор", position="Администратор", status="active",
    ))
    _invalid(db, Employee(organization_id=organization.id, first_name=" ", last_name="Тест", position="Помощник", status="active"))
    _invalid(db, Employee(organization_id=organization.id, first_name="Тест", last_name="Тест", position=" ", status="active"))
    _invalid(db, Employee(organization_id=organization.id, first_name="Тест", last_name="Тест", position="Помощник", status="invalid"))


def test_attendance_unique_time_state_and_group_snapshot(db, users):
    organization, _, _, admin = users
    first_group = Group(organization_id=organization.id, name="Первая", status="active")
    second_group = Group(organization_id=organization.id, name="Вторая", status="active")
    db.add_all([first_group, second_group])
    db.flush()
    child = Child(
        organization_id=organization.id, group_id=first_group.id,
        first_name="Ребёнок", last_name="Тестовый", birth_date=date(2020, 1, 1), status="active",
    )
    db.add(child)
    db.flush()
    day = date(2026, 9, 1)

    def record(*, on=day, status="present", arrival=time(8, 30), departure=None):
        return Attendance(
            organization_id=organization.id, child_id=child.id, group_id=first_group.id,
            date=on, status=status, arrival_time=arrival, departure_time=departure,
            created_by=admin.id, updated_by=admin.id,
        )

    marked = record(departure=time(16, 15))
    db.add(marked)
    db.flush()
    child.group_id = second_group.id
    db.flush()
    assert marked.group_id == first_group.id and child.group_id == second_group.id
    _invalid(db, record())
    _invalid(db, record(on=date(2026, 9, 2), status="absent"))
    _invalid(db, record(on=date(2026, 9, 3), status="unknown"))
    _invalid(db, record(on=date(2026, 9, 4), arrival=None, departure=time(16, 15)))
    _invalid(db, record(on=date(2026, 9, 5), departure=time(8, 0)))
    _invalid(db, record(on=date(2026, 9, 6), status="invalid", arrival=None))
    db.add_all([
        record(on=date(2026, 9, 2), status="absent", arrival=None),
        record(on=date(2026, 9, 3), status="unknown", arrival=None),
        record(on=date(2026, 9, 4), arrival=None),
    ])
    db.flush()

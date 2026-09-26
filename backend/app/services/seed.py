"""Synthetic local/demo organization and users.

Run after migrations. Generated temporary passwords are printed once locally;
neither passwords nor their plaintext equivalents are persisted or committed.
"""

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import generate_temporary_password, hash_password
from app.db.session import SessionLocal
from app.models.attendance import Attendance
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.organization import Organization
from app.models.user import User


def seed_stage2(db: Session, organization: Organization) -> None:
    """Add plainly synthetic records once; never overwrite edited demo records."""
    group = db.scalar(select(Group).where(Group.organization_id == organization.id, Group.name == "Ромашка"))
    if group is None:
        group = Group(organization_id=organization.id, name="Ромашка", status="active")
        db.add(group)
        db.flush()

    child = db.scalar(select(Child).where(
        Child.organization_id == organization.id, Child.group_id == group.id,
        Child.first_name == "Тестовый", Child.last_name == "Ребёнок",
        Child.birth_date == date(2020, 1, 1),
    ))
    if child is None:
        child = Child(
            organization_id=organization.id, group_id=group.id, first_name="Тестовый",
            last_name="Ребёнок", birth_date=date(2020, 1, 1), status="active",
        )
        db.add(child)
        db.flush()

    guardian = db.scalar(select(Guardian).where(
        Guardian.organization_id == organization.id,
        Guardian.first_name == "Тестовый", Guardian.last_name == "Представитель",
    ))
    if guardian is None:
        guardian = Guardian(
            organization_id=organization.id, first_name="Тестовый",
            last_name="Представитель", status="active",
        )
        db.add(guardian)
        db.flush()

    if db.scalar(select(ChildGuardian.id).where(
        ChildGuardian.child_id == child.id, ChildGuardian.guardian_id == guardian.id,
    )) is None:
        db.add(ChildGuardian(
            organization_id=organization.id, child_id=child.id, guardian_id=guardian.id,
            relation_type="other", status="active",
        ))



def seed_stage3(db: Session, organization: Organization) -> None:
    """Idempotent synthetic staff and historical manual marks."""
    if db.scalar(select(Employee.id).where(
        Employee.organization_id == organization.id,
        Employee.first_name == "Тестовая", Employee.last_name == "Сотрудница",
    )) is None:
        db.add(Employee(
            organization_id=organization.id, first_name="Тестовая",
            last_name="Сотрудница", position="Помощник воспитателя", status="active",
        ))
    child = db.scalar(select(Child).where(
        Child.organization_id == organization.id,
        Child.first_name == "Тестовый", Child.last_name == "Ребёнок",
    ))
    author = db.scalar(select(User).where(User.username == "stage3-director-demo"))
    if child is None or author is None:
        raise RuntimeError("Synthetic Stage 2 child and Stage 3 director must exist before attendance seed")
    for day, status in ((date(2025, 9, 20), "present"), (date(2025, 9, 21), "absent")):
        if db.scalar(select(Attendance.id).where(Attendance.child_id == child.id, Attendance.date == day)) is None:
            db.add(Attendance(
                organization_id=organization.id, child_id=child.id, group_id=child.group_id,
                date=day, status=status, created_by=author.id, updated_by=author.id,
            ))

def main() -> None:
    if get_settings().app_env not in {"development", "test"}:
        raise RuntimeError("Synthetic seed can only run in development or test")

    with SessionLocal() as db:
        organization = db.scalar(select(Organization).where(Organization.name == "Детский сад «Солнышко»"))
        if organization is None:
            organization = Organization(name="Детский сад «Солнышко»", status="active")
            db.add(organization)
            db.flush()

        issued: list[tuple[str, str]] = []
        for username, role in (("director-demo", "DIRECTOR"), ("admin-demo", "ADMIN"), ("stage2-director-demo", "DIRECTOR"), ("stage3-director-demo", "DIRECTOR")):
            if db.scalar(select(User).where(User.username == username)) is not None:
                continue
            temporary_password = generate_temporary_password()
            db.add(User(
                organization_id=organization.id, username=username, role=role, status="active",
                password_hash=hash_password(temporary_password), must_change_password=True,
            ))
            issued.append((username, temporary_password))
        db.flush()
        seed_stage2(db, organization)
        seed_stage3(db, organization)
        db.commit()
        for username, password in issued:
            print(f"{username}: temporary password (displayed once): {password}")
        if not issued:
            print("Demo users already exist. Their passwords have not been reset.")


if __name__ == "__main__":
    main()

"""Synthetic local/demo organization and users.

Run after migrations. Generated temporary passwords are printed once locally;
neither passwords nor their plaintext equivalents are persisted or committed.
"""

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import generate_temporary_password, hash_password
from app.db.session import SessionLocal
from app.models.organization import Organization
from app.models.user import User


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
        for username, role in (("director-demo", "DIRECTOR"), ("admin-demo", "ADMIN")):
            if db.scalar(select(User).where(User.username == username)) is not None:
                continue
            temporary_password = generate_temporary_password()
            db.add(User(
                organization_id=organization.id, username=username, role=role, status="active",
                password_hash=hash_password(temporary_password), must_change_password=True,
            ))
            issued.append((username, temporary_password))
        db.commit()
        for username, password in issued:
            print(f"{username}: temporary password (displayed once): {password}")
        if not issued:
            print("Demo users already exist. Their passwords have not been reset.")


if __name__ == "__main__":
    main()

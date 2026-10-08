#!/usr/bin/env python3
"""Create disposable synthetic browser-canary identities and one-time links."""

import secrets
import stat
import sys
from datetime import timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.account_access_token import AccountAccessToken
from app.models.employee import Employee
from app.models.group import Group
from app.models.organization import Organization
from app.models.user import User
from app.services.account_access import token_digest
from app.services.auth import utc_now
from sqlalchemy import select


def _password() -> str:
    return f"compat-{secrets.token_urlsafe(24)}"


def _write_environment(path: Path, values: dict[str, str]) -> None:
    if any("\n" in value or "\r" in value for value in values.values()):
        raise RuntimeError("generated compatibility value contains a newline")
    path.write_text("".join(f"{name}={value}\n" for name, value in values.items()))
    path.chmod(stat.S_IRUSR | stat.S_IWUSR)


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: compatibility-browser-fixtures.py OUTPUT_ENV")
    output = Path(sys.argv[1])
    now = utc_now()
    director_password = _password()
    activation_password = _password()
    reset_password = _password()
    activation_raw = secrets.token_urlsafe(48)
    reset_raw = secrets.token_urlsafe(48)

    with SessionLocal() as db:
        organization = db.scalar(select(Organization).where(
            Organization.name == "Compatibility Canary Synthetic Garden",
        ))
        if organization is not None:
            raise RuntimeError("compatibility browser fixtures require a clean disposable database")
        organization = Organization(
            name="Compatibility Canary Synthetic Garden",
            status="active",
            timezone="Europe/Moscow",
        )
        db.add(organization)
        db.flush()

        director = User(
            organization_id=organization.id,
            username="compatibility-director",
            password_hash=hash_password(director_password),
            role="DIRECTOR",
            status="active",
            must_change_password=False,
        )
        activation_user = User(
            organization_id=organization.id,
            username="compatibility-activation",
            password_hash=hash_password(_password()),
            role="TEACHER",
            status="active",
            must_change_password=True,
        )
        reset_user = User(
            organization_id=organization.id,
            username="compatibility-reset",
            password_hash=hash_password(_password()),
            role="ADMIN",
            status="active",
            must_change_password=False,
        )
        group = Group(
            organization_id=organization.id,
            name="Compatibility Synthetic Group",
            status="active",
        )
        db.add_all([director, activation_user, reset_user, group])
        db.flush()

        activation_employee = Employee(
            organization_id=organization.id,
            user_id=activation_user.id,
            first_name="Compatibility",
            last_name="Activation",
            position="Synthetic teacher",
            category="teacher",
            email="activation@compatibility.example.test",
            status="active",
        )
        reset_employee = Employee(
            organization_id=organization.id,
            user_id=reset_user.id,
            first_name="Compatibility",
            last_name="Reset",
            position="Synthetic administrator",
            category="administrator",
            email="reset@compatibility.example.test",
            status="active",
        )
        db.add_all([activation_employee, reset_employee])
        db.flush()
        db.add_all([
            AccountAccessToken(
                organization_id=organization.id,
                user_id=activation_user.id,
                employee_id=activation_employee.id,
                created_by_user_id=director.id,
                purpose="activation",
                token_digest=token_digest(activation_raw),
                delivery_status="sent",
                expires_at=now + timedelta(hours=1),
                sent_at=now,
            ),
            AccountAccessToken(
                organization_id=organization.id,
                user_id=reset_user.id,
                employee_id=reset_employee.id,
                purpose="password_reset",
                token_digest=token_digest(reset_raw),
                delivery_status="sent",
                expires_at=now + timedelta(hours=1),
                sent_at=now,
            ),
        ])
        db.commit()

    _write_environment(output, {
        "COMPAT_DIRECTOR_USERNAME": director.username,
        "COMPAT_DIRECTOR_PASSWORD": director_password,
        "COMPAT_ACTIVATION_USERNAME": activation_user.username,
        "COMPAT_ACTIVATION_TOKEN": activation_raw,
        "COMPAT_ACTIVATION_PASSWORD": activation_password,
        "COMPAT_RESET_USERNAME": reset_user.username,
        "COMPAT_RESET_TOKEN": reset_raw,
        "COMPAT_RESET_PASSWORD": reset_password,
        "COMPAT_GROUP_ID": str(group.id),
        "COMPAT_GROUP_NAME": group.name,
    })


if __name__ == "__main__":
    main()

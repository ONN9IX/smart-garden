"""Trusted offline operator bootstrap/recovery only; never exposed as HTTP.

Run: python -m app.services.platform_bootstrap create|recover USERNAME --secret-file /trusted/path
Passwords are entered through getpass. Enrollment is written once to an external
0600 file, never stdout. Production ops owns the encryption key and enrollment
file custody, MFA recovery verification and removal after enrollment.
"""

import argparse
import getpass
import json
import os
from pathlib import Path

import pyotp
from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from app.core import platform_security as security
from app.core.security import hash_password, normalize_username
from app.db.session import SessionLocal
from app.models.platform_operator import PlatformOperator
from app.models.platform_session import PlatformSession
from app.services import platform_audit


def configure_operator(db, username: str, password: str, *, recover: bool = False):
    username = normalize_username(username)
    security.cipher()
    operator = db.scalar(
        select(PlatformOperator)
        .where(PlatformOperator.username == username)
        .with_for_update()
    )
    if (operator is None) == recover:
        raise ValueError("Operator create/recovery precondition failed")
    secret = pyotp.random_base32()
    encrypted = security.encrypt_secret(secret)
    if not recover:
        operator = PlatformOperator(
            username=username,
            password_hash=hash_password(password),
            totp_secret_ciphertext=encrypted,
        )
        db.add(operator)
        db.flush()
    else:
        operator.password_hash = hash_password(password)
        operator.totp_secret_ciphertext = encrypted
        operator.last_totp_counter = -1
        operator.failed_attempts = 0
        operator.locked_until = None
        operator.status = "active"
        db.execute(
            update(PlatformSession)
            .where(PlatformSession.operator_id == operator.id)
            .values(revoked_at=security.utc_now())
        )
    platform_audit.write(
        db, operator.id, "operator.recover" if recover else "operator.create"
    )
    return operator, secret


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("create", "recover"))
    parser.add_argument("username")
    parser.add_argument("--secret-file", required=True)
    args = parser.parse_args()
    path = Path(args.secret_file).resolve()
    if path.is_relative_to(Path(__file__).resolve().parents[3]):
        raise SystemExit("Enrollment file must be outside the repository")
    password = getpass.getpass("New operator password: ")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords do not match")
    if (
        args.action == "recover"
        and input("Confirm operator username: ") != args.username
    ):
        raise SystemExit("Recovery confirmation failed")
    # O_EXCL/O_NOFOLLOW prevents overwriting or following an enrollment-file symlink.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with SessionLocal() as db:
            operator, secret = configure_operator(
                db, args.username, password, recover=args.action == "recover"
            )
            with os.fdopen(fd, "w") as output:
                os.fchmod(output.fileno(), 0o600)
                json.dump(
                    {
                        "provisioning_uri": pyotp.TOTP(secret).provisioning_uri(
                            operator.username, issuer_name="ПРОМАКС Platform"
                        )
                    },
                    output,
                )
                output.flush()
                os.fsync(output.fileno())
            db.commit()
    except (SQLAlchemyError, OSError, ValueError):
        path.unlink(missing_ok=True)
        raise SystemExit("Bootstrap failed; no credential was logged") from None


if __name__ == "__main__":
    main()

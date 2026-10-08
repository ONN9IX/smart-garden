"""Secure invitation, recovery and access lifecycle shared by all non-DIRECTOR roles."""

import hashlib
import re
import secrets
import smtplib
import string
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_password, valid_password
from app.models.account_access_token import AccountAccessToken
from app.models.auth_session import AuthSession
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.user import User
from app.schemas.account_access import (
    AccessAccountItem,
    AccessAccountSections,
    BulkParentResponse,
    BulkPreflight,
    BulkResultItem,
    InviteResponse,
)
from app.services import audit, email_delivery
from app.services.auth import utc_now

ALPHABET = string.ascii_lowercase + string.digits
EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def token_digest(raw: str) -> str:
    try:
        return hashlib.sha256(raw.encode("ascii")).hexdigest()
    except UnicodeEncodeError:
        raise AppError(400, "ACCESS_LINK_INVALID") from None


def _new_username(db: Session, prefix: str) -> str:
    for _ in range(20):
        username = prefix + "-" + "".join(secrets.choice(ALPHABET) for _ in range(10))
        if db.scalar(select(User.id).where(User.username == username)) is None:
            return username
    raise AppError(409, "USERNAME_ALREADY_EXISTS")


def _unusable_password() -> str:
    return hash_password(secrets.token_urlsafe(48))


def _tenant_user(
    db: Session, user_id: UUID | None, organization_id: UUID, *, for_update: bool = False,
) -> User | None:
    if user_id is None:
        return None
    query = select(User).where(
        User.id == user_id, User.organization_id == organization_id,
    )
    return db.scalar(query.with_for_update(of=User) if for_update else query)


def revoke_sessions(db: Session, user_id: UUID) -> None:
    db.execute(update(AuthSession).where(
        AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None),
    ).values(revoked_at=utc_now()))


def _revoke_tokens(db: Session, user_id: UUID, purpose: str) -> None:
    db.execute(update(AccountAccessToken).where(
        AccountAccessToken.user_id == user_id,
        AccountAccessToken.purpose == purpose,
        AccountAccessToken.used_at.is_(None),
        AccountAccessToken.revoked_at.is_(None),
    ).values(revoked_at=utc_now()))


def _create_token(
    db: Session, user: User, purpose: str, *, guardian_id: UUID | None = None,
    employee_id: UUID | None = None, created_by_user_id: UUID | None = None,
) -> tuple[AccountAccessToken, str]:
    # The row lock serializes replacement across all application workers. The
    # partial unique index is a second line of defence for every DB writer.
    locked_user = db.scalar(select(User).where(
        User.id == user.id, User.organization_id == user.organization_id,
    ).with_for_update(of=User))
    if locked_user is None:
        raise AppError(404, "NOT_FOUND")
    _revoke_tokens(db, locked_user.id, purpose)
    raw = secrets.token_urlsafe(48)
    ttl = get_settings().activation_ttl_seconds if purpose == "activation" else get_settings().reset_ttl_seconds
    grant = AccountAccessToken(
        organization_id=locked_user.organization_id, user_id=locked_user.id, guardian_id=guardian_id,
        employee_id=employee_id, purpose=purpose, token_digest=token_digest(raw),
        created_by_user_id=created_by_user_id, delivery_status="pending",
        expires_at=utc_now() + timedelta(seconds=ttl),
    )
    db.add(grant)
    db.flush()
    return grant, raw


def _deliver(db: Session, grant: AccountAccessToken, raw: str, email: str, purpose: str) -> None:
    settings = get_settings()
    path = "activate" if purpose == "activation" else "reset-password"
    subject = "Активация доступа" if purpose == "activation" else "Восстановление доступа"
    base = (settings.public_app_base_url or "http://localhost:3000").rstrip("/")
    text = f"Откройте ссылку, чтобы продолжить: {base}/{path}#token={raw}\nСсылка одноразовая."
    try:
        email_delivery.get_email_sender().send(recipient=email, subject=subject, text=text)
    except (OSError, RuntimeError, smtplib.SMTPException):
        grant.delivery_status = "failed"
    else:
        grant.delivery_status = "sent"
        grant.sent_at = utc_now()
    db.commit()


def _valid_email(email: str | None) -> str:
    normalized = (email or "").strip().lower()
    if not EMAIL_RE.fullmatch(normalized) or len(normalized) > 254:
        raise AppError(409, "ACCOUNT_EMAIL_REQUIRED", "email")
    return normalized


def invite_guardian(db: Session, actor: User, guardian_id: UUID) -> InviteResponse:
    guardian = db.scalar(select(Guardian).where(
        Guardian.id == guardian_id, Guardian.organization_id == actor.organization_id,
    ).with_for_update())
    if guardian is None:
        raise AppError(404, "NOT_FOUND")
    if guardian.status != "active":
        raise AppError(409, "GUARDIAN_ARCHIVED")
    email = _valid_email(guardian.email)
    parent = _tenant_user(db, guardian.user_id, actor.organization_id)
    if parent is not None and (parent.organization_id != actor.organization_id or parent.role != "PARENT"):
        raise AppError(409, "PARENT_ACCOUNT_ALREADY_EXISTS")
    if parent is None:
        parent = User(
            organization_id=actor.organization_id, username=_new_username(db, "parent"),
            password_hash=_unusable_password(), role="PARENT", status="active", must_change_password=True,
        )
        db.add(parent)
        db.flush()
        guardian.user_id = parent.id
    elif not parent.must_change_password:
        raise AppError(409, "ACCOUNT_ALREADY_ACTIVATED")
    else:
        parent.password_hash = _unusable_password()
        revoke_sessions(db, parent.id)
    grant, raw = _create_token(
        db, parent, "activation", guardian_id=guardian.id, created_by_user_id=actor.id,
    )
    audit.write(db, actor, "account.invite", "user_account", parent.id, {"account_role": "PARENT"})
    db.commit()
    _deliver(db, grant, raw, email, "activation")
    return InviteResponse(username=parent.username, role="PARENT", status=grant.delivery_status)


def invite_employee(db: Session, actor: User, employee_id: UUID, role: str) -> InviteResponse:
    employee = db.scalar(select(Employee).where(
        Employee.id == employee_id, Employee.organization_id == actor.organization_id,
    ).with_for_update())
    if employee is None:
        raise AppError(404, "NOT_FOUND")
    if employee.status != "active":
        raise AppError(409, "EMPLOYEE_ARCHIVED")
    expected = {"TEACHER": "teacher", "ADMIN": "administrator"}.get(role)
    if expected is None or employee.category != expected:
        raise AppError(409, "EMPLOYEE_CATEGORY_CONFLICT", "category")
    email = _valid_email(employee.email)
    account = _tenant_user(db, employee.user_id, actor.organization_id)
    if account is not None and (account.organization_id != actor.organization_id or account.role not in {"TEACHER", "ADMIN"}):
        raise AppError(409, "EMPLOYEE_ACCOUNT_ALREADY_EXISTS")
    if account is None:
        account = User(
            organization_id=actor.organization_id, username=_new_username(db, "staff"),
            password_hash=_unusable_password(), role=role, status="active", must_change_password=True,
        )
        db.add(account)
        db.flush()
        employee.user_id = account.id
    elif account.role != role:
        raise AppError(409, "EMPLOYEE_CATEGORY_CONFLICT", "role")
    elif not account.must_change_password:
        raise AppError(409, "ACCOUNT_ALREADY_ACTIVATED")
    else:
        account.password_hash = _unusable_password()
        revoke_sessions(db, account.id)
    grant, raw = _create_token(
        db, account, "activation", employee_id=employee.id, created_by_user_id=actor.id,
    )
    audit.write(db, actor, "account.invite", "user_account", account.id, {"account_role": role})
    db.commit()
    _deliver(db, grant, raw, email, "activation")
    return InviteResponse(username=account.username, role=role, status=grant.delivery_status)


def _grant_for_raw(db: Session, raw: str, purpose: str) -> AccountAccessToken:
    grant = db.scalar(select(AccountAccessToken).where(
        AccountAccessToken.token_digest == token_digest(raw),
    ).with_for_update())
    now = utc_now()
    if (
        grant is None or grant.purpose != purpose or grant.used_at is not None
        or grant.revoked_at is not None or grant.expires_at <= now
    ):
        raise AppError(400, "ACCESS_LINK_INVALID")
    return grant


def _bound_account(db: Session, grant: AccountAccessToken, *, allow_blocked: bool) -> User:
    user = db.scalar(select(User).where(
        User.id == grant.user_id, User.organization_id == grant.organization_id,
        User.role.in_(("PARENT", "TEACHER", "ADMIN")),
    ))
    if user is None or (user.status != "active" and not (allow_blocked and user.status == "blocked")):
        raise AppError(400, "ACCESS_LINK_INVALID")
    if grant.guardian_id:
        linked = db.scalar(select(Guardian.id).where(
            Guardian.id == grant.guardian_id, Guardian.user_id == user.id,
            Guardian.organization_id == grant.organization_id, Guardian.status == "active",
        ))
    else:
        linked = db.scalar(select(Employee.id).where(
            Employee.id == grant.employee_id, Employee.user_id == user.id,
            Employee.organization_id == grant.organization_id, Employee.status == "active",
        ))
    if linked is None:
        raise AppError(400, "ACCESS_LINK_INVALID")
    return user


def complete_password_action(db: Session, raw: str, new_password: str, purpose: str) -> None:
    if not valid_password(new_password):
        raise AppError(400, "INVALID_PASSWORD", "new_password")
    grant = _grant_for_raw(db, raw, purpose)
    user = _bound_account(db, grant, allow_blocked=purpose == "password_reset")
    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    grant.used_at = utc_now()
    revoke_sessions(db, user.id)
    db.commit()


def request_password_reset(db: Session, identifier: str) -> None:
    users = eligible_users_for_identifier(db, identifier)
    if len(users) != 1:
        return
    user, profile, email = users[0]
    grant, raw = _create_token(
        db, user, "password_reset",
        guardian_id=profile.id if isinstance(profile, Guardian) else None,
        employee_id=profile.id if isinstance(profile, Employee) else None,
    )
    db.commit()
    _deliver(db, grant, raw, email, "password_reset")


def eligible_users_for_identifier(db: Session, identifier: str) -> list[tuple[User, Guardian | Employee, str]]:
    normalized = identifier.strip().lower()
    result: list[tuple[User, Guardian | Employee, str]] = []
    username_user = db.scalar(select(User).where(User.username == normalized))
    candidates: list[tuple[User, Guardian | Employee]] = []
    if username_user and username_user.role in {"PARENT", "TEACHER", "ADMIN"}:
        if username_user.role == "PARENT":
            profile = db.scalar(select(Guardian).where(Guardian.user_id == username_user.id, Guardian.status == "active"))
        else:
            profile = db.scalar(select(Employee).where(Employee.user_id == username_user.id, Employee.status == "active"))
        if profile:
            candidates.append((username_user, profile))
    elif "@" in normalized:
        guardians = db.scalars(select(Guardian).where(func.lower(Guardian.email) == normalized, Guardian.status == "active", Guardian.user_id.is_not(None))).all()
        employees = db.scalars(select(Employee).where(func.lower(Employee.email) == normalized, Employee.status == "active", Employee.user_id.is_not(None))).all()
        for profile in [*guardians, *employees]:
            user = _tenant_user(db, profile.user_id, profile.organization_id)
            if user and user.role in {"PARENT", "TEACHER", "ADMIN"}:
                candidates.append((user, profile))
    for user, profile in candidates:
        if user.status in {"active", "blocked"} and profile.email:
            result.append((user, profile, profile.email.strip().lower()))
    return result


def change_employee_role(db: Session, actor: User, employee_id: UUID, role: str) -> None:
    employee = db.scalar(select(Employee).where(
        Employee.id == employee_id, Employee.organization_id == actor.organization_id,
    ).with_for_update())
    account = _tenant_user(db, employee.user_id, actor.organization_id, for_update=True) if employee else None
    if employee is None or account is None or account.role not in {"TEACHER", "ADMIN"}:
        raise AppError(404, "EMPLOYEE_ACCOUNT_NOT_FOUND")
    if role not in {"TEACHER", "ADMIN"}:
        raise AppError(409, "ROLE_CHANGE_NOT_ALLOWED")
    before = account.role
    if before == role:
        return
    account.role = role
    revoke_sessions(db, account.id)
    if before == "TEACHER":
        db.execute(update(TeacherGroupAssignment).where(
            TeacherGroupAssignment.employee_id == employee.id,
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.status == "active",
        ).values(status="archived", archived_at=utc_now()))
    audit.write(db, actor, "account.role_change", "user_account", account.id, {"account_role": role})
    db.commit()


def revoke_profile_sessions(db: Session, actor: User, profile_type: str, profile_id: UUID) -> None:
    model = Guardian if profile_type == "guardian" else Employee
    profile = db.scalar(select(model).where(
        model.id == profile_id, model.organization_id == actor.organization_id,
    ))
    if profile is None or profile.user_id is None:
        raise AppError(404, "NOT_FOUND")
    account = db.scalar(select(User).where(
        User.id == profile.user_id, User.organization_id == actor.organization_id,
        User.role.in_(("PARENT", "TEACHER", "ADMIN")),
    ))
    if account is None:
        raise AppError(404, "NOT_FOUND")
    revoke_sessions(db, account.id)
    audit.write(db, actor, "account.revoke_sessions", "user_account", account.id, {"account_role": account.role})
    db.commit()


def mask_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    local, domain = email.split("@", 1)
    return f"{local[:1]}***@{domain}"


def _latest_activation(db: Session, user_id: UUID) -> AccountAccessToken | None:
    return db.scalar(select(AccountAccessToken).where(
        AccountAccessToken.user_id == user_id, AccountAccessToken.purpose == "activation",
    ).order_by(AccountAccessToken.created_at.desc(), AccountAccessToken.id.desc()).limit(1))


def _human_status(db: Session, user: User | None) -> str:
    if user is None:
        return "no_account"
    if user.status == "blocked":
        return "blocked"
    if not user.must_change_password:
        return "activated"
    grant = _latest_activation(db, user.id)
    if grant is None:
        return "no_account"
    if grant.delivery_status == "failed":
        return "delivery_failed"
    if grant.expires_at <= utc_now() or grant.revoked_at is not None:
        return "invite_expired"
    return "invited"


def _full_name(profile: Guardian | Employee) -> str:
    return " ".join(filter(None, (profile.last_name, profile.first_name, profile.middle_name)))


def access_sections(db: Session, actor: User) -> AccessAccountSections:
    sections: dict[str, list[AccessAccountItem]] = {
        "parents": [], "teachers": [], "administrators": [], "other_employees": [], "blocked": [],
    }
    guardians = db.scalars(select(Guardian).where(
        Guardian.organization_id == actor.organization_id,
    ).order_by(Guardian.last_name, Guardian.first_name)).all()
    for profile in guardians:
        account = _tenant_user(db, profile.user_id, actor.organization_id)
        item = AccessAccountItem(
            profile_id=profile.id, profile_type="guardian", full_name=_full_name(profile), context="Родитель",
            username=account.username if account else None, role="PARENT" if account else None,
            masked_email=mask_email(profile.email), status=_human_status(db, account),
            last_login_at=account.last_login_at if account else None,
        )
        sections["blocked" if item.status == "blocked" else "parents"].append(item)
    employees = db.scalars(select(Employee).where(
        Employee.organization_id == actor.organization_id,
    ).order_by(Employee.last_name, Employee.first_name)).all()
    for profile in employees:
        account = _tenant_user(db, profile.user_id, actor.organization_id)
        groups = db.scalars(select(Group.name).join(
            TeacherGroupAssignment, TeacherGroupAssignment.group_id == Group.id,
        ).where(
            TeacherGroupAssignment.employee_id == profile.id,
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.status == "active", Group.status == "active",
        ).order_by(Group.name)).all()
        item = AccessAccountItem(
            profile_id=profile.id, profile_type="employee", full_name=_full_name(profile),
            context=profile.position, username=account.username if account else None,
            role=account.role if account and account.role in {"TEACHER", "ADMIN"} else None,
            masked_email=mask_email(profile.email), status=_human_status(db, account),
            last_login_at=account.last_login_at if account else None, groups=list(groups),
        )
        if item.status == "blocked":
            key = "blocked"
        elif item.role == "TEACHER" or profile.category == "teacher":
            key = "teachers"
        elif item.role == "ADMIN" or profile.category == "administrator":
            key = "administrators"
        else:
            key = "other_employees"
        sections[key].append(item)
    return AccessAccountSections(**sections)


def _has_active_child(db: Session, guardian: Guardian) -> bool:
    return db.scalar(select(Child.id).join(
        ChildGuardian, ChildGuardian.child_id == Child.id,
    ).where(
        ChildGuardian.guardian_id == guardian.id,
        ChildGuardian.organization_id == guardian.organization_id,
        ChildGuardian.status == "active", Child.status == "active",
    ).limit(1)) is not None


def bulk_parent_invites(
    db: Session, actor: User, guardian_ids: list[UUID], confirm: bool,
) -> BulkParentResponse:
    unique_ids = list(dict.fromkeys(guardian_ids))
    guardians = {item.id: item for item in db.scalars(select(Guardian).where(
        Guardian.organization_id == actor.organization_id, Guardian.id.in_(unique_ids),
    )).all()}
    preflight = BulkPreflight()
    eligible: list[Guardian] = []
    for guardian_id in unique_ids:
        guardian = guardians.get(guardian_id)
        if guardian is None or guardian.status != "active":
            preflight.archived += 1
            continue
        try:
            _valid_email(guardian.email)
        except AppError:
            preflight.missing_or_invalid_email += 1
            continue
        if not _has_active_child(db, guardian):
            preflight.no_active_linked_child += 1
            continue
        account = _tenant_user(db, guardian.user_id, actor.organization_id)
        status = _human_status(db, account)
        if status == "activated":
            preflight.activated += 1
        elif status == "blocked":
            preflight.blocked += 1
        elif status == "invited":
            preflight.already_invited += 1
        else:
            preflight.eligible += 1
            if status in {"delivery_failed", "invite_expired"}:
                preflight.failed_or_expired += 1
            eligible.append(guardian)
    if not confirm:
        return BulkParentResponse(preflight=preflight)
    results: list[BulkResultItem] = []
    for guardian in eligible:
        try:
            invitation = invite_guardian(db, actor, guardian.id)
            results.append(BulkResultItem(
                guardian_id=guardian.id, result="sent" if invitation.status == "sent" else "failed",
                reason=None if invitation.status == "sent" else "delivery_failed",
            ))
        except (AppError, SQLAlchemyError):
            db.rollback()
            results.append(BulkResultItem(guardian_id=guardian.id, result="failed", reason="processing_failed"))
    return BulkParentResponse(preflight=preflight, results=results)

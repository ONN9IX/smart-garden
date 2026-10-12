"""Atomic, idempotent onboarding and deliberately separate tenant lifecycle."""

import hashlib

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError

from app.core import platform_security as security
from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import generate_temporary_password, hash_password
from app.models.auth_session import AuthSession
from app.models.organization import Organization
from app.models.platform_provisioning_request import PlatformProvisioningRequest
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User
from app.schemas.platform import OrganizationView, ProvisioningView, SubscriptionView
from app.services import platform_audit


def view(db, organization: Organization) -> OrganizationView:
    # Only the initial Director's safe state is projected, never a raw User row.
    state = db.execute(
        select(User.status, User.must_change_password)
        .join(
            PlatformProvisioningRequest,
            PlatformProvisioningRequest.director_user_id == User.id,
        )
        .where(
            PlatformProvisioningRequest.organization_id == organization.id,
            User.organization_id == organization.id,
        )
    ).first()
    onboarding = (
        "not_platform_provisioned"
        if state is None
        else "blocked"
        if state.status != "active"
        else "password_change_required"
        if state.must_change_password
        else "active"
    )
    subscription = db.get(TenantSubscription, organization.id)
    return OrganizationView(
        id=organization.id,
        name=organization.name,
        timezone=organization.timezone,
        status=organization.status,
        created_at=organization.created_at,
        onboarding_status=onboarding,
        subscription=SubscriptionView.model_validate(subscription)
        if subscription
        else None,
    )


def get(db, organization_id, *, locked: bool = False):
    query = select(Organization).where(Organization.id == organization_id)
    if locked:
        query = query.with_for_update().execution_options(populate_existing=True)
    item = db.scalar(query)
    if item is None:
        raise AppError(404, "NOT_FOUND")
    return item


def listing(db, search: str = "", status: str | None = None):
    query = select(Organization)
    if search:
        query = query.where(Organization.name.icontains(search, autoescape=True))
    if status:
        query = query.where(Organization.status == status)
    items = db.scalars(
        query.order_by(Organization.created_at.desc(), Organization.id).limit(100)
    ).all()
    return [view(db, item) for item in items]


def overview(db):
    organization_counts = dict(
        db.execute(
            select(Organization.status, func.count(Organization.id)).group_by(
                Organization.status
            )
        ).all()
    )
    subscription_counts = dict(
        db.execute(
            select(
                TenantSubscription.status,
                func.count(TenantSubscription.organization_id),
            ).group_by(TenantSubscription.status)
        ).all()
    )
    pending = db.scalar(
        select(func.count(User.id))
        .join(
            PlatformProvisioningRequest,
            PlatformProvisioningRequest.director_user_id == User.id,
        )
        .where(
            User.organization_id == PlatformProvisioningRequest.organization_id,
            User.must_change_password.is_(True),
        )
    )
    return {
        "organizations": {
            status: organization_counts.get(status, 0)
            for status in ("active", "blocked", "archived")
        },
        "subscriptions": {
            status: subscription_counts.get(status, 0)
            for status in (
                "trial",
                "active",
                "past_due",
                "cancel_at_period_end",
                "cancelled",
            )
        },
        "pending_director_setup": pending,
    }


def provision(db, operator_id, payload):
    if not get_settings().platform_credential_handoff_enabled:
        raise AppError(503, "FORBIDDEN")
    fingerprint = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    security.advisory_lock(db, "platform-provision:" + str(payload.idempotency_key))
    prior = db.get(PlatformProvisioningRequest, payload.idempotency_key)
    if prior:
        if prior.operator_id != operator_id:
            raise AppError(404, "NOT_FOUND")
        if prior.request_fingerprint != fingerprint:
            raise AppError(409, "IDEMPOTENCY_KEY_REUSED")
        return ProvisioningView(
            organization=view(db, get(db, prior.organization_id)), replayed=True
        )
    password = generate_temporary_password()
    try:
        organization = Organization(
            name=payload.name, timezone=payload.timezone, status="active"
        )
        db.add(organization)
        db.flush()
        director = User(
            organization_id=organization.id,
            username=payload.director_username,
            password_hash=hash_password(password),
            role="DIRECTOR",
            status="active",
            must_change_password=True,
        )
        db.add(director)
        db.flush()
        db.add(
            TenantSubscription(
                organization_id=organization.id, **payload.subscription.model_dump()
            )
        )
        db.add(
            PlatformProvisioningRequest(
                id=payload.idempotency_key,
                operator_id=operator_id,
                organization_id=organization.id,
                director_user_id=director.id,
                request_fingerprint=fingerprint,
            )
        )
        platform_audit.write(db, operator_id, "organization.create", organization.id)
        db.flush()
        result = ProvisioningView(
            organization=view(db, organization),
            temporary_password=password,
            replayed=False,
        )
        db.commit()
        return result
    except IntegrityError:
        db.rollback()
        raise AppError(409, "USERNAME_ALREADY_EXISTS") from None


def lifecycle(db, operator_id, organization_id, payload, *, block: bool):
    organization = get(db, organization_id, locked=True)
    if (
        payload.confirmation_name != organization.name
        or organization.status == "archived"
    ):
        raise AppError(400, "VALIDATION_ERROR")
    target = "blocked" if block else "active"
    if organization.status != target:
        previous = organization.status
        organization.status = target
        if block:
            db.execute(
                update(AuthSession)
                .where(
                    AuthSession.user_id.in_(
                        select(User.id).where(User.organization_id == organization.id)
                    ),
                    AuthSession.revoked_at.is_(None),
                )
                .values(revoked_at=security.utc_now())
            )
        platform_audit.write(
            db,
            operator_id,
            "organization.block" if block else "organization.unblock",
            organization.id,
            {
                "before_status": previous,
                "after_status": target,
                "reason": payload.reason,
            },
        )
        db.flush()
    result = view(db, organization)
    db.commit()
    return result

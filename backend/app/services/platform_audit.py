"""Separate bounded operator Audit, with no passwords, names, tokens or payloads."""

from sqlalchemy import select

from app.models.platform_audit_event import PlatformAuditEvent

ACTIONS = {
    "operator.create",
    "operator.recover",
    "auth.login",
    "auth.failure",
    "auth.logout",
    "auth.step_up",
    "organization.create",
    "organization.block",
    "organization.unblock",
    "organization.profile_change",
    "subscription.update",
}
FIELDS = {"before_status", "after_status", "before_profile", "after_profile", "reason", "changed_fields"}
SUBSCRIPTION_FIELDS = {
    "status",
    "plan_code",
    "currency",
    "interval",
    "price_minor",
    "trial_ends_at",
    "period_start",
    "period_end",
}


def write(db, operator_id, action: str, organization_id=None, details=None) -> None:
    details = details or {}
    if action not in ACTIONS or not set(details) <= FIELDS:
        raise ValueError("Invalid platform audit event")
    for key, value in details.items():
        if key == "changed_fields":
            if not isinstance(value, list) or not set(value) <= SUBSCRIPTION_FIELDS:
                raise ValueError("Invalid audit fields")
        elif value not in {
            "active",
            "blocked",
            "archived",
            "trial",
            "past_due",
            "cancel_at_period_end",
            "cancelled",
            "owner_request",
            "security",
            "administrative",
            "KINDERGARTEN",
            "GYMNASTICS",
        }:
            raise ValueError("Invalid audit state")
    db.add(
        PlatformAuditEvent(
            operator_id=operator_id,
            organization_id=organization_id,
            action=action,
            details=details,
        )
    )


def listing(db, organization_id=None):
    query = select(PlatformAuditEvent)
    if organization_id:
        query = query.where(PlatformAuditEvent.organization_id == organization_id)
    return db.scalars(
        query.order_by(
            PlatformAuditEvent.created_at.desc(), PlatformAuditEvent.id
        ).limit(50)
    ).all()

"""Owner-controlled commercial metadata; never touches Organization.status."""

from app.models.tenant_subscription import TenantSubscription
from app.schemas.platform import SubscriptionView
from app.services import platform_audit, platform_organizations


def update(db, operator_id, organization_id, payload):
    organization = platform_organizations.get(db, organization_id, locked=True)
    if payload.confirmation_name != organization.name:
        from app.core.errors import AppError

        raise AppError(400, "VALIDATION_ERROR")
    subscription = db.get(TenantSubscription, organization_id)
    values = payload.subscription.model_dump()
    changed = [
        field
        for field, value in values.items()
        if subscription is None or getattr(subscription, field) != value
    ]
    if subscription is None:
        subscription = TenantSubscription(organization_id=organization_id, **values)
        db.add(subscription)
    else:
        for field, value in values.items():
            setattr(subscription, field, value)
    if changed:
        platform_audit.write(
            db,
            operator_id,
            "subscription.update",
            organization_id,
            {"changed_fields": changed},
        )
    db.flush()
    result = SubscriptionView.model_validate(subscription)
    db.commit()
    return result


def director_view(db, user):
    subscription = db.get(TenantSubscription, user.organization_id)
    return {
        "subscription": SubscriptionView.model_validate(subscription)
        if subscription
        else None
    }

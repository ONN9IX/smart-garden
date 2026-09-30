"""Track A shared Audit integration for privacy-safe Organization settings changes."""

import pytest
from sqlalchemy import select

from app.models.audit_event import AuditEvent
from app.services import audit


def test_organization_settings_audit_accepts_only_changed_field_names(db, users):
    actor = users[2]

    first = audit.write(
        db, actor, "organization.settings_update", "organization", actor.organization_id,
        {"changed_fields": ["name"]},
    )
    second = audit.write(
        db, actor, "organization.settings_update", "organization", actor.organization_id,
        {"changed_fields": ["timezone", "name"]},
    )
    db.flush()

    rows = list(db.scalars(select(AuditEvent).where(AuditEvent.id.in_([first.id, second.id]))))
    assert {tuple(row.details["changed_fields"]) for row in rows} == {("name",), ("timezone", "name")}
    rendered = str([row.details for row in rows])
    assert "Europe/Moscow" not in rendered
    assert "Детский сад" not in rendered


@pytest.mark.parametrize(
    ("action", "entity_type", "details", "message"),
    [
        ("organization.update", "organization", {"changed_fields": ["name"]}, "action/entity"),
        ("organization.settings_update", "group", {"changed_fields": ["name"]}, "action/entity"),
        ("organization.settings_update", "organization", {"changed_fields": ["status"]}, "organization settings"),
        ("organization.settings_update", "organization", {"changed_fields": ["name"], "group_id": None}, "organization settings"),
        ("organization.settings_update", "organization", {}, "organization settings"),
    ],
)
def test_organization_settings_audit_rejects_non_contract_details(db, users, action, entity_type, details, message):
    with pytest.raises(ValueError, match=message):
        audit.write(db, users[2], action, entity_type, users[2].organization_id, details)


def test_existing_writer_still_rejects_sensitive_details(db, users):
    with pytest.raises(ValueError, match="non-whitelisted"):
        audit.write(
            db, users[2], "organization.settings_update", "organization", users[2].organization_id,
            {"changed_fields": ["name"], "secret": "forbidden"},
        )

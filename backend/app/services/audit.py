"""Single privacy-minimized writer and tenant-scoped read service for Audit."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditActor, AuditEventList, AuditEventResponse

_ALLOWED_DETAIL_KEYS = {
    "changed_fields",
    "status_before",
    "status_after",
    "account_role",
    "relation_type",
    "child_id",
    "guardian_id",
    "before",
    "after",
    "target_type",
    "group_id",
}
_ALLOWED_ACTIONS = {
    "group": {"group.create", "group.update", "group.archive", "group.restore"},
    "child": {"child.create", "child.update", "child.archive", "child.restore"},
    "guardian": {"guardian.create", "guardian.update", "guardian.archive", "guardian.restore"},
    "child_guardian": {
        "child_guardian.create", "child_guardian.update", "child_guardian.archive", "child_guardian.restore",
    },
    "employee": {"employee.create", "employee.update", "employee.archive", "employee.restore"},
    "user_account": {"account.create", "account.reset_password", "account.block", "account.unblock"},
    "attendance": {"attendance.create", "attendance.update"},
    "announcement": {"announcement.create", "announcement.update", "announcement.archive"},
}
_ALLOWED_CHANGED_FIELDS = {
    "name", "group_id", "first_name", "last_name", "middle_name", "birth_date",
    "phone", "email", "position", "relation_type", "status", "arrival_time", "departure_time",
    "target_type",
}
_ALLOWED_STATUSES = {"active", "archived", "blocked"}
_ALLOWED_RELATIONS = {"mother", "father", "legal_guardian", "other"}
_ALLOWED_ACCOUNT_ROLES = {"ADMIN", "PARENT"}
_ALLOWED_ATTENDANCE_STATUSES = {"present", "absent", "unknown"}
_ALLOWED_ANNOUNCEMENT_TARGETS = {"all", "group"}


def _validate_details(details: dict[str, Any]) -> None:
    if set(details) - _ALLOWED_DETAIL_KEYS:
        raise ValueError("Audit details contain non-whitelisted keys")
    fields = details.get("changed_fields")
    if fields is not None and (
        not isinstance(fields, list)
        or any(not isinstance(field, str) or field not in _ALLOWED_CHANGED_FIELDS for field in fields)
    ):
        raise ValueError("Audit changed_fields are invalid")
    for key in ("status_before", "status_after"):
        if key in details and details[key] not in _ALLOWED_STATUSES:
            raise ValueError("Audit status is invalid")
    if "account_role" in details and details["account_role"] not in _ALLOWED_ACCOUNT_ROLES:
        raise ValueError("Audit account role is invalid")
    if "relation_type" in details and details["relation_type"] not in _ALLOWED_RELATIONS:
        raise ValueError("Audit relation type is invalid")
    for key in ("child_id", "guardian_id"):
        if key in details:
            UUID(str(details[key]))
    if "target_type" in details and details["target_type"] not in _ALLOWED_ANNOUNCEMENT_TARGETS:
        raise ValueError("Audit announcement target is invalid")
    if "group_id" in details and details["group_id"] is not None:
        UUID(str(details["group_id"]))
    for key in ("before", "after"):
        if key not in details:
            continue
        value = details[key]
        if not isinstance(value, dict) or set(value) != {"status", "arrival_time", "departure_time"}:
            raise ValueError("Audit attendance state is invalid")
        if value["status"] not in _ALLOWED_ATTENDANCE_STATUSES:
            raise ValueError("Audit attendance status is invalid")
        for time_key in ("arrival_time", "departure_time"):
            time_value = value[time_key]
            if time_value is not None and (
                not isinstance(time_value, str)
                or len(time_value) != 5
                or time_value[2] != ":"
                or not time_value.replace(":", "").isdigit()
            ):
                raise ValueError("Audit attendance time is invalid")


def write(
    db: Session,
    actor: User,
    action: str,
    entity_type: str,
    entity_id: UUID | None,
    details: dict[str, Any] | None = None,
) -> AuditEvent:
    """Add an event to the caller's transaction; this function never commits."""
    safe_details = details or {}
    if action not in _ALLOWED_ACTIONS.get(entity_type, set()):
        raise ValueError("Audit action/entity combination is invalid")
    _validate_details(safe_details)
    event = AuditEvent(
        organization_id=actor.organization_id,
        actor_user_id=actor.id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        details=safe_details,
    )
    db.add(event)
    return event


def changed_fields(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    return sorted(key for key, value in after.items() if before.get(key) != value)


def response(event: AuditEvent) -> AuditEventResponse:
    return AuditEventResponse(
        id=event.id,
        action=event.action,
        entity_type=event.entity_type,
        entity_id=event.entity_id,
        actor=AuditActor(id=event.actor.id, username=event.actor.username, role=event.actor.role),
        details=event.details,
        created_at=event.created_at,
    )


def list_events(
    db: Session,
    actor: User,
    *,
    entity_type: str | None,
    action: str | None,
    actor_user_id: UUID | None,
    date_from: date | None,
    date_to: date | None,
    limit: int,
    offset: int,
) -> AuditEventList:
    query = select(AuditEvent).where(AuditEvent.organization_id == actor.organization_id)
    if entity_type:
        query = query.where(AuditEvent.entity_type == entity_type)
    if action:
        query = query.where(AuditEvent.action == action)
    if actor_user_id:
        query = query.where(AuditEvent.actor_user_id == actor_user_id)
    if date_from:
        query = query.where(AuditEvent.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC))
    if date_to and date_to < date.max:
        query = query.where(
            AuditEvent.created_at < datetime.combine(date_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC),
        )
    events = db.scalars(query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit).offset(offset))
    return AuditEventList(items=[response(event) for event in events], limit=limit, offset=offset)


def get_event(db: Session, actor: User, event_id: UUID) -> AuditEventResponse:
    event = db.scalar(select(AuditEvent).where(
        AuditEvent.id == event_id,
        AuditEvent.organization_id == actor.organization_id,
    ))
    if event is None:
        raise AppError(404, "NOT_FOUND")
    return response(event)

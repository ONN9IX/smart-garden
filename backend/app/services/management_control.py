"""Tenant-scoped live conditions and minimal per-user Control view state."""

from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.organization_time import organization_now
from app.models.account_access_token import AccountAccessToken
from app.models.employee import Employee
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.operational_alert_state import OperationalAlertState
from app.models.organization import Organization
from app.models.organization_notification_settings import (
    OrganizationNotificationSettings,
)
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.schemas.management_cabinet import ManagementAttentionItem, ManagementTodayGroup
from app.schemas.management_control import (
    ControlNotification,
    ControlSummary,
    ManagementControl,
    OperationalAlert,
    OrganizationNotificationSettingsPatch,
    OrganizationNotificationSettingsResponse,
    SecurityStatus,
)
from app.services import audit
from app.services.auth import utc_now


def notification_settings(db: Session, actor: User) -> OrganizationNotificationSettingsResponse:
    row = db.get(OrganizationNotificationSettings, actor.organization_id)
    return OrganizationNotificationSettingsResponse(
        show_informational_notifications=row.show_informational_notifications if row else True,
        attendance_checkpoint_time=row.attendance_checkpoint_time if row else None,
        schedule_missing_alert_enabled=row.schedule_missing_alert_enabled if row else True,
    )


def update_notification_settings(
    db: Session, actor: User, payload: OrganizationNotificationSettingsPatch,
) -> OrganizationNotificationSettingsResponse:
    if actor.role != "DIRECTOR":
        raise AppError(403, "FORBIDDEN")
    # The tenant root always exists, including before its first policy row.
    db.scalar(select(Organization.id).where(Organization.id == actor.organization_id).with_for_update())
    row = db.get(OrganizationNotificationSettings, actor.organization_id)
    effective = notification_settings(db, actor)
    values = payload.model_dump(exclude_unset=True)
    changed = sorted(field for field, value in values.items() if getattr(effective, field) != value)
    if changed:
        if row is None:
            row = OrganizationNotificationSettings(organization_id=actor.organization_id)
            db.add(row)
        for field in changed:
            setattr(row, field, values[field])
        audit.write(db, actor, "organization.settings_update", "organization", actor.organization_id,
                    {"changed_fields": changed})
        db.commit()
    return notification_settings(db, actor)


def _parent_invite_ids(db: Session, actor: User, now: datetime) -> list[UUID]:
    rows = db.execute(
        select(AccountAccessToken.user_id)
        .join(Guardian, Guardian.id == AccountAccessToken.guardian_id)
        .join(User, User.id == AccountAccessToken.user_id)
        .where(
            AccountAccessToken.organization_id == actor.organization_id,
            AccountAccessToken.purpose == "activation",
            AccountAccessToken.used_at.is_(None), AccountAccessToken.revoked_at.is_(None),
            ((AccountAccessToken.delivery_status == "failed") | (AccountAccessToken.expires_at <= now)),
            Guardian.organization_id == actor.organization_id, Guardian.status == "active",
            User.organization_id == actor.organization_id, User.role == "PARENT", User.status == "active",
        ).distinct()
    )
    return sorted(rows.scalars(), key=str)


def condition_items(
    db: Session, actor: User, groups: list[ManagementTodayGroup], day: date,
    *, now: datetime | None = None,
) -> list[ManagementAttentionItem]:
    """Shared current conditions for Today and Control; no alert rows are created."""
    local_now = now or organization_now(actor.organization)
    settings = notification_settings(db, actor)
    items: list[ManagementAttentionItem] = []
    if settings.attendance_checkpoint_time is None or local_now.time() >= settings.attendance_checkpoint_time:
        items.extend(ManagementAttentionItem(
            kind="attendance_missing", entity_type="attendance", entity_id=group.group_id,
            count=group.unknown + group.needs_arrival,
        ) for group in groups if group.unknown or group.needs_arrival)
    items.extend(ManagementAttentionItem(
        kind="group_without_teacher", entity_type="group", entity_id=group.group_id,
    ) for group in groups if not group.has_active_teacher)
    if settings.schedule_missing_alert_enabled:
        items.extend(ManagementAttentionItem(
            kind="group_without_schedule", entity_type="group", entity_id=group.group_id,
        ) for group in groups if not group.has_active_weekly_schedule)
    overdue_count = db.scalar(select(func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.status.in_(("open", "in_progress")),
        TeacherTask.due_at.is_not(None), TeacherTask.due_at < local_now.astimezone(UTC),
    )) or 0
    if overdue_count:
        items.append(ManagementAttentionItem(
            kind="tasks_overdue", entity_type="teacher_task", count=overdue_count,
        ))
    items.extend(ManagementAttentionItem(
        kind="parent_invite_failed_or_expired", entity_type="user_account", entity_id=user_id,
    ) for user_id in _parent_invite_ids(db, actor, local_now.astimezone(UTC)))
    return items


def _occurrence(db: Session, actor: User, item: ManagementAttentionItem) -> str:
    """Version a live condition by its source rows, so a resolved condition can recur as new."""
    if item.kind == "group_without_teacher":
        rows = db.execute(select(TeacherGroupAssignment.created_at, TeacherGroupAssignment.archived_at,
                                 Employee.updated_at).join(Employee, Employee.id == TeacherGroupAssignment.employee_id)
                          .where(TeacherGroupAssignment.organization_id == actor.organization_id,
                                 TeacherGroupAssignment.group_id == item.entity_id,
                                 Employee.organization_id == actor.organization_id)).all()
        moments = [value for row in rows for value in row if value is not None]
    elif item.kind == "group_without_schedule":
        moments = db.scalars(select(GroupScheduleItem.updated_at).where(
            GroupScheduleItem.organization_id == actor.organization_id,
            GroupScheduleItem.group_id == item.entity_id)).all()
    elif item.kind == "tasks_overdue":
        moments = db.scalars(select(TeacherTask.updated_at).where(
            TeacherTask.organization_id == actor.organization_id,
            TeacherTask.status.in_(("open", "in_progress")),
            TeacherTask.due_at.is_not(None), TeacherTask.due_at < organization_now(actor.organization).astimezone(UTC),
        )).all()
    else:
        moments = db.scalars(select(AccountAccessToken.created_at).where(
            AccountAccessToken.organization_id == actor.organization_id,
            AccountAccessToken.user_id == item.entity_id,
            AccountAccessToken.purpose == "activation",
        )).all()
    return str(int(max(moments).timestamp() * 1_000_000)) if moments else "initial"


def _alert(db: Session, actor: User, item: ManagementAttentionItem, day: date,
           group_names: dict[UUID, str]) -> OperationalAlert:
    kind, entity = item.kind, item.entity_id
    key = f"{kind}:{entity}:{day.isoformat()}" if kind == "attendance_missing" else f"{kind}:{entity}:{_occurrence(db, actor, item)}"
    name = group_names.get(entity, "Группа") if entity else "Группа"
    if kind == "attendance_missing":
        return OperationalAlert(alert_key=key, kind=kind, priority="important", title="Посещаемость не завершена",
                                context=f"{name}: требуется отметить детей ({item.count or 0})", action_href="/attendance")
    if kind == "group_without_teacher":
        return OperationalAlert(alert_key=key, kind=kind, priority="important", title="Нет воспитателя",
                                context=name, action_href=f"/groups/{entity}")
    if kind == "group_without_schedule":
        return OperationalAlert(alert_key=key, kind=kind, priority="important", title="Нет расписания",
                                context=name, action_href="/schedule")
    if kind == "tasks_overdue":
        return OperationalAlert(alert_key=key, kind=kind, priority="important", title="Задача просрочена",
                                context="Проверьте сроки выполнения", action_href="/tasks")
    return OperationalAlert(alert_key=key, kind=kind, priority="important", title="Приглашение родителю не доставлено",
                            context="Проверьте доступ родителя", action_href="/access-accounts")


def active_alerts(db: Session, actor: User) -> list[OperationalAlert]:
    if actor.role not in {"DIRECTOR", "ADMIN"}:
        raise AppError(403, "FORBIDDEN")
    from app.services.management_cabinet import management_today

    today = management_today(db, actor)
    names = {group.group_id: group.group_name for group in today.groups}
    return [_alert(db, actor, item, today.date, names) for item in today.attention_items if item.kind != "notifications_unread"]


def _eligible(db: Session, actor: User, key: str) -> OperationalAlert:
    return next((item for item in active_alerts(db, actor) if item.alert_key == key), None) or _not_found()


def _not_found():
    raise AppError(404, "NOT_FOUND")


def _state(db: Session, actor: User, key: str) -> OperationalAlertState:
    row = db.scalar(select(OperationalAlertState).where(
        OperationalAlertState.organization_id == actor.organization_id,
        OperationalAlertState.user_id == actor.id, OperationalAlertState.alert_key == key,
    ).with_for_update())
    if row is None:
        row = OperationalAlertState(organization_id=actor.organization_id, user_id=actor.id, alert_key=key)
        db.add(row)
    return row


def view_alert(db: Session, actor: User, key: str) -> OperationalAlert:
    alert = _eligible(db, actor, key)
    row = _state(db, actor, key)
    row.viewed_at = utc_now()
    db.commit()
    alert.viewed_at = row.viewed_at
    return alert


def snooze_alert(db: Session, actor: User, key: str, duration: str) -> OperationalAlert:
    alert = _eligible(db, actor, key)
    now = utc_now()
    if duration == "one_hour":
        until = now + timedelta(hours=1)
    else:
        local = organization_now(actor.organization)
        tomorrow = local.date() + timedelta(days=1)
        until = datetime.combine(tomorrow, time(8, 0), tzinfo=local.tzinfo).astimezone(UTC)
    row = _state(db, actor, key)
    row.snoozed_until = until
    row.viewed_at = row.viewed_at or now
    db.commit()
    alert.snoozed_until, alert.viewed_at = until, row.viewed_at
    return alert


_NOTIFICATION_LABELS = {
    "communication.message": ("Новое сообщение", "important"),
    "announcement.published": ("Новое объявление", "info"),
    "teacher_task.assigned": ("Назначена задача", "important"),
}


def control(db: Session, actor: User) -> ManagementControl:
    if actor.role not in {"DIRECTOR", "ADMIN"}:
        raise AppError(403, "FORBIDDEN")
    alerts = active_alerts(db, actor)
    now = utc_now()
    keys = [item.alert_key for item in alerts]
    states = {row.alert_key: row for row in db.scalars(select(OperationalAlertState).where(
        OperationalAlertState.organization_id == actor.organization_id,
        OperationalAlertState.user_id == actor.id,
        OperationalAlertState.alert_key.in_(keys),
    ))} if keys else {}
    for alert in alerts:
        state = states.get(alert.alert_key)
        if state:
            alert.viewed_at, alert.snoozed_until = state.viewed_at, state.snoozed_until
    from app.services.management_cabinet import list_notifications

    settings = notification_settings(db, actor)
    events = []
    for event in list_notifications(db, actor, "all").items:
        # Unknown future kinds stay visible until their priority policy is defined.
        title, priority = _NOTIFICATION_LABELS.get(event.kind, ("Событие в саду", "important"))
        if priority == "info" and not settings.show_informational_notifications:
            continue
        events.append(ControlNotification(id=event.id, title=title, priority=priority,
                                          read_at=event.read_at, created_at=event.created_at))
    return ManagementControl(alerts=alerts, event_notifications=events, summary=ControlSummary(
        new=sum(item.viewed_at is None and not (item.snoozed_until and item.snoozed_until > now) for item in alerts)
        + sum(event.read_at is None for event in events),
        important=sum(item.priority == "important" and not (item.snoozed_until and item.snoozed_until > now) for item in alerts)
        + sum(event.priority == "important" and event.read_at is None for event in events),
        snoozed=sum(bool(item.snoozed_until and item.snoozed_until > now) for item in alerts),
    ))


def security_status(db: Session, actor: User) -> SecurityStatus:
    if actor.role != "DIRECTOR":
        raise AppError(403, "FORBIDDEN")
    blocked = db.scalar(select(func.count(User.id)).where(
        User.organization_id == actor.organization_id, User.status == "blocked",
    )) or 0
    invites = len(_parent_invite_ids(db, actor, utc_now()))
    return SecurityStatus(blocked_accounts=blocked, failed_or_expired_parent_invites=invites)

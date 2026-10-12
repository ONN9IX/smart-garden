"""Safe tenant-scoped human reading of the existing append-only Audit stream."""

from datetime import UTC, date, datetime, timedelta
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models.audit_event import AuditEvent
from app.models.child import Child
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.user import User
from app.schemas.audit_journal import (
    JournalActor,
    JournalCategory,
    JournalItem,
    JournalList,
    JournalTarget,
)

_CATEGORIES: dict[str, JournalCategory] = {
    "user_account": "access", "notification": "access",
    "child": "people", "guardian": "people", "child_guardian": "people", "employee": "people",
    "group": "groups", "teacher_assignment": "groups", "group_schedule_item": "groups",
    "attendance": "operations", "teacher_task": "operations",
    "announcement": "communications", "communication_message": "communications",
    "document_notice": "documents", "organization": "organization",
}
_TARGETS = {
    "user_account": "Аккаунт", "notification": "Уведомление", "child": "Ребёнок",
    "guardian": "Представитель", "child_guardian": "Связь ребёнка и представителя",
    "employee": "Сотрудник", "group": "Группа", "teacher_assignment": "Назначение воспитателя",
    "group_schedule_item": "Расписание", "attendance": "Посещаемость", "teacher_task": "Задача",
    "announcement": "Объявление", "communication_message": "Сообщение",
    "document_notice": "Документ", "organization": "Организация",
}
_VERBS = {
    "create": "Создано", "update": "Изменено", "archive": "Архивировано", "restore": "Восстановлено",
    "block": "Заблокировано", "unblock": "Разблокировано", "reset": "Обновлён доступ к",
    "reset_password": "Обновлён доступ к", "invite": "Отправлено приглашение для",
    "read": "Прочитано", "status": "Изменён статус", "cancel": "Отменено",
    "publish": "Опубликовано", "assigned": "Назначено", "role_change": "Изменена роль",
    "revoke_sessions": "Отозваны сеансы", "settings_update": "Изменены настройки",
}
_SAFE_FIELDS = {
    "name": "название", "timezone": "часовой пояс", "status": "статус",
    "group_id": "группа", "position": "должность", "weekday": "день недели",
    "start_time": "время начала", "end_time": "время окончания", "due_at": "срок",
    "read_at": "отметка о прочтении", "arrival_time": "время прихода",
    "departure_time": "время ухода", "assignee_employee_id": "исполнитель",
    "show_informational_notifications": "информационные уведомления",
    "attendance_checkpoint_time": "время проверки посещаемости",
    "schedule_missing_alert_enabled": "напоминание о расписании",
}


def _full_name(person) -> str:
    return " ".join(part for part in (person.last_name, person.first_name, person.middle_name) if part)


def _actor(db: Session, tenant: UUID, user: User) -> JournalActor:
    person = db.scalar(select(Employee).where(Employee.organization_id == tenant, Employee.user_id == user.id))
    if person is None:
        person = db.scalar(select(Guardian).where(Guardian.organization_id == tenant, Guardian.user_id == user.id))
    name = _full_name(person) if person else user.username
    return JournalActor(id=user.id, display_name=name, role=user.role)


def _target(db: Session, tenant: UUID, event: AuditEvent) -> JournalTarget:
    label = _TARGETS[event.entity_type]
    name = label
    if event.entity_id:
        model = {"group": Group, "child": Child, "employee": Employee, "guardian": Guardian}.get(event.entity_type)
        if model:
            person = db.scalar(select(model).where(model.id == event.entity_id, model.organization_id == tenant))
            if person:
                name = person.name if isinstance(person, Group) else _full_name(person)
    return JournalTarget(type=event.entity_type, display_name=name)


def _item(db: Session, tenant: UUID, event: AuditEvent) -> JournalItem:
    target = _target(db, tenant, event)
    verb = _VERBS.get(event.action.rsplit(".", 1)[-1], "Зафиксировано действие:")
    fields = event.details.get("changed_fields") if isinstance(event.details, dict) else None
    changes = [f"Изменено: {_SAFE_FIELDS[field]}" for field in fields if field in _SAFE_FIELDS] if isinstance(fields, list) else []
    return JournalItem(
        id=event.id, created_at=event.created_at, category=_CATEGORIES[event.entity_type],
        actor=_actor(db, tenant, event.actor), summary=f"{verb} {target.display_name}",
        target=target, safe_changes=changes,
    )


def list_journal(
    db: Session, actor: User, *, category: JournalCategory | None,
    actor_user_id: UUID | None, context_id: UUID | None,
    date_from: date | None, date_to: date | None, limit: int, offset: int,
) -> JournalList:
    query = select(AuditEvent).join(User, User.id == AuditEvent.actor_user_id).where(
        AuditEvent.organization_id == actor.organization_id,
        User.organization_id == actor.organization_id,
        AuditEvent.entity_type.in_(_CATEGORIES),
    )
    if category:
        query = query.where(AuditEvent.entity_type.in_(
            entity for entity, mapped in _CATEGORIES.items() if mapped == category
        ))
    if actor_user_id:
        query = query.where(AuditEvent.actor_user_id == actor_user_id)
    if context_id:
        query = query.where(or_(AuditEvent.entity_id == context_id,
                                AuditEvent.details["group_id"].astext == str(context_id)))
    if date_from:
        query = query.where(AuditEvent.created_at >= datetime.combine(date_from, datetime.min.time(), tzinfo=UTC))
    if date_to and date_to < date.max:
        query = query.where(AuditEvent.created_at < datetime.combine(
            date_to + timedelta(days=1), datetime.min.time(), tzinfo=UTC,
        ))
    rows = db.scalars(query.order_by(AuditEvent.created_at.desc(), AuditEvent.id.desc()).limit(limit).offset(offset)).all()
    actor_ids = db.scalars(select(AuditEvent.actor_user_id).join(User, User.id == AuditEvent.actor_user_id).where(
        AuditEvent.organization_id == actor.organization_id, User.organization_id == actor.organization_id,
        AuditEvent.entity_type.in_(_CATEGORIES),
    ).distinct()).all()
    actors = db.scalars(select(User).where(User.id.in_(actor_ids), User.organization_id == actor.organization_id)).all()
    return JournalList(items=[_item(db, actor.organization_id, event) for event in rows],
                       actors=[_actor(db, actor.organization_id, user) for user in actors], limit=limit, offset=offset)

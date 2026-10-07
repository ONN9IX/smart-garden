"""Tenant-scoped People preflight, family creation and Group/Employee projections."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.core.organization_time import organization_today
from app.models.attendance import Attendance
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User
from app.schemas.management_people import (
    DuplicateCheck,
    DuplicateCheckResponse,
    DuplicateMatch,
    EmployeeAssignmentProfile,
    EmployeeProfile,
    FamilyCreate,
    GroupOverviewItem,
    GroupOverviewList,
    GroupProfile,
    GroupProfileChild,
    GroupProfileEmployee,
    GroupProfileParent,
    GroupProfileScheduleItem,
    GuardianSearchMatch,
    GuardianSearchRequest,
    GuardianSearchResponse,
)
from app.services import audit
from app.services import children as child_service
from app.services.auth import utc_now


def _full_name(last_name: str, first_name: str, middle_name: str | None) -> str:
    return " ".join(part.strip() for part in (last_name, first_name, middle_name or "") if part and part.strip())


def _employee_category_label(category: str) -> str:
    return {"teacher": "Воспитатель", "administrator": "Администратор", "other": "Сотрудник"}.get(category, "Сотрудник")


def _normalized_name(last_name, first_name, middle_name):
    return func.lower(func.regexp_replace(
        func.concat_ws(
            " ", func.btrim(last_name), func.btrim(first_name),
            func.nullif(func.btrim(func.coalesce(middle_name, "")), ""),
        ),
        r"\s+", " ", "g",
    ))


def _phone_digits(value: str | None) -> str | None:
    if not value:
        return None
    digits = "".join(character for character in value if character.isdigit())
    return digits if len(digits) >= 7 else None


def duplicate_matches(db: Session, actor: User, payload: DuplicateCheck) -> DuplicateCheckResponse:
    name_key = _full_name(payload.last_name, payload.first_name, payload.middle_name).casefold()
    phone_key = _phone_digits(payload.phone)
    email_key = payload.email.casefold() if payload.email else None
    matches: list[DuplicateMatch] = []

    if payload.kind == "child":
        stmt = select(Child, Group.name).join(Group, Group.id == Child.group_id).where(
            Child.organization_id == actor.organization_id,
            Group.organization_id == actor.organization_id,
            Child.birth_date == payload.birth_date,
            _normalized_name(Child.last_name, Child.first_name, Child.middle_name) == name_key,
        ).order_by(Child.status, Child.last_name, Child.first_name, Child.id).limit(25)
        matches = [DuplicateMatch(
            id=child.id,
            full_name=_full_name(child.last_name, child.first_name, child.middle_name),
            context=f"Группа «{group_name}» · {child.birth_date:%d.%m.%Y}",
        ) for child, group_name in db.execute(stmt)]
    elif payload.kind == "guardian":
        predicates = [_normalized_name(Guardian.last_name, Guardian.first_name, Guardian.middle_name) == name_key]
        if email_key:
            predicates.append(func.lower(func.btrim(Guardian.email)) == email_key)
        if phone_key:
            predicates.append(func.regexp_replace(func.coalesce(Guardian.phone, ""), r"[^0-9]", "", "g") == phone_key)
        stmt = select(Guardian).where(
            Guardian.organization_id == actor.organization_id, or_(*predicates),
        ).order_by(Guardian.status, Guardian.last_name, Guardian.first_name, Guardian.id).limit(25)
        matches = [DuplicateMatch(
            id=item.id, full_name=_full_name(item.last_name, item.first_name, item.middle_name),
            context="Представитель",
        ) for item in db.scalars(stmt)]
    else:
        predicates = [_normalized_name(Employee.last_name, Employee.first_name, Employee.middle_name) == name_key]
        if email_key:
            predicates.append(func.lower(func.btrim(Employee.email)) == email_key)
        if phone_key:
            predicates.append(func.regexp_replace(func.coalesce(Employee.phone, ""), r"[^0-9]", "", "g") == phone_key)
        stmt = select(Employee).where(
            Employee.organization_id == actor.organization_id, or_(*predicates),
        ).order_by(Employee.status, Employee.last_name, Employee.first_name, Employee.id).limit(25)
        matches = [DuplicateMatch(
            id=item.id, full_name=_full_name(item.last_name, item.first_name, item.middle_name),
            context=f"{item.position} · {_employee_category_label(item.category)}",
        ) for item in db.scalars(stmt)]
    return DuplicateCheckResponse(matches=matches)


def search_guardians(db: Session, actor: User, payload: GuardianSearchRequest) -> GuardianSearchResponse:
    query = payload.query.strip()
    pattern = f"%{query}%"
    predicates = [
        Guardian.first_name.ilike(pattern), Guardian.last_name.ilike(pattern),
        Guardian.middle_name.ilike(pattern),
        func.concat_ws(" ", Guardian.last_name, Guardian.first_name, func.coalesce(Guardian.middle_name, "")).ilike(pattern),
        func.lower(Guardian.email).ilike(pattern.lower()),
    ]
    digits = _phone_digits(query)
    if digits:
        predicates.append(func.regexp_replace(func.coalesce(Guardian.phone, ""), r"[^0-9]", "", "g").ilike(f"%{digits}%"))
    rows = db.execute(
        select(Guardian, User.status)
        .outerjoin(User, and_(User.id == Guardian.user_id, User.organization_id == actor.organization_id, User.role == "PARENT"))
        .where(Guardian.organization_id == actor.organization_id, Guardian.status == "active", or_(*predicates))
        .order_by(Guardian.last_name, Guardian.first_name, Guardian.id).limit(20)
    )
    return GuardianSearchResponse(matches=[GuardianSearchMatch(
        id=guardian.id, full_name=_full_name(guardian.last_name, guardian.first_name, guardian.middle_name),
        phone=guardian.phone, email=guardian.email,
        account_status=account_status if account_status in {"active", "blocked"} else None,
    ) for guardian, account_status in rows])


def create_family(db: Session, actor: User, payload: FamilyCreate):
    child_payload = payload.child
    if child_payload.birth_date > utc_now().date():
        raise AppError(400, "INVALID_BIRTH_DATE", "birth_date")
    group = db.scalar(select(Group).where(
        Group.id == child_payload.group_id,
        Group.organization_id == actor.organization_id,
    ).with_for_update())
    if group is None:
        raise AppError(404, "NOT_FOUND")
    if group.status != "active":
        raise AppError(409, "GROUP_ARCHIVED", "group_id")

    guardian_ids = [entry.guardian_id for entry in payload.guardians if entry.guardian_id is not None]
    existing_guardians: dict[UUID, Guardian] = {}
    if guardian_ids:
        existing_guardians = {
            item.id: item for item in db.scalars(select(Guardian).where(
                Guardian.id.in_(guardian_ids), Guardian.organization_id == actor.organization_id,
            ).order_by(Guardian.id).with_for_update())
        }
        if len(existing_guardians) != len(set(guardian_ids)):
            raise AppError(404, "NOT_FOUND")
        if any(item.status != "active" for item in existing_guardians.values()):
            raise AppError(409, "GUARDIAN_ARCHIVED")

    child: Child | None = None
    try:
        with db.begin_nested():
            child = Child(
                organization_id=actor.organization_id,
                group_id=group.id,
                first_name=child_payload.first_name,
                last_name=child_payload.last_name,
                middle_name=child_payload.middle_name,
                birth_date=child_payload.birth_date,
                status="active",
            )
            db.add(child)
            db.flush()
            audit.write(db, actor, "child.create", "child", child.id)

            seen: set[UUID] = set()
            for entry in payload.guardians:
                if entry.guardian_id is not None:
                    guardian = existing_guardians[entry.guardian_id]
                else:
                    assert entry.new_guardian is not None
                    guardian = Guardian(
                        organization_id=actor.organization_id,
                        **entry.new_guardian.model_dump(),
                        status="active",
                    )
                    db.add(guardian)
                    db.flush()
                    audit.write(db, actor, "guardian.create", "guardian", guardian.id)
                if guardian.id in seen:
                    raise AppError(409, "RELATION_ALREADY_EXISTS")
                seen.add(guardian.id)
                link = ChildGuardian(
                    organization_id=actor.organization_id,
                    child_id=child.id,
                    guardian_id=guardian.id,
                    relation_type=entry.relation_type,
                    status="active",
                )
                db.add(link)
                db.flush()
                audit.write(db, actor, "child_guardian.create", "child_guardian", link.id, {
                    "child_id": str(child.id), "guardian_id": str(guardian.id),
                    "relation_type": entry.relation_type,
                })
    except IntegrityError:
        raise AppError(409, "RELATION_ALREADY_EXISTS") from None

    db.commit()
    assert child is not None
    db.refresh(child)
    return child_service.detail(child)


def group_profile(db: Session, actor: User, group_id: UUID) -> GroupProfile:
    group = db.scalar(select(Group).where(
        Group.id == group_id, Group.organization_id == actor.organization_id,
    ))
    if group is None:
        raise AppError(404, "NOT_FOUND")
    today = organization_today(actor.organization)
    now = datetime.now(UTC)

    children_rows = list(db.scalars(select(Child).where(
        Child.organization_id == actor.organization_id,
        Child.group_id == group.id,
        Child.status == "active",
    ).order_by(Child.last_name, Child.first_name, Child.id)))
    child_ids = [item.id for item in children_rows]
    attendance_by_child: dict[UUID, str] = {}
    if child_ids:
        attendance_by_child = dict(db.execute(select(Attendance.child_id, Attendance.status).where(
            Attendance.organization_id == actor.organization_id,
            Attendance.group_id == group.id,
            Attendance.child_id.in_(child_ids),
            Attendance.date == today,
        )))
    guardian_count_by_child: dict[UUID, int] = {}
    if child_ids:
        guardian_count_by_child = dict(db.execute(
            select(ChildGuardian.child_id, func.count(ChildGuardian.id))
            .join(Guardian, Guardian.id == ChildGuardian.guardian_id)
            .where(
                ChildGuardian.organization_id == actor.organization_id,
                ChildGuardian.child_id.in_(child_ids),
                ChildGuardian.status == "active",
                Guardian.organization_id == actor.organization_id,
                Guardian.status == "active",
            ).group_by(ChildGuardian.child_id)
        ))
    children = [GroupProfileChild(
        id=item.id, first_name=item.first_name, last_name=item.last_name,
        middle_name=item.middle_name, status=item.status,
        today_attendance=attendance_by_child.get(item.id),
        active_guardian_count=guardian_count_by_child.get(item.id, 0),
    ) for item in children_rows]
    present = sum(item.today_attendance == "present" for item in children)
    absent = sum(item.today_attendance == "absent" for item in children)
    unknown = len(children) - present - absent

    employees = [GroupProfileEmployee(
        id=employee.id, first_name=employee.first_name, last_name=employee.last_name,
        middle_name=employee.middle_name, position=employee.position,
        category=employee.category, account_status=user.status,
    ) for employee, user in db.execute(
        select(Employee, User)
        .join(TeacherGroupAssignment, TeacherGroupAssignment.employee_id == Employee.id)
        .join(User, User.id == Employee.user_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.group_id == group.id,
            TeacherGroupAssignment.status == "active",
            Employee.organization_id == actor.organization_id,
            Employee.status == "active",
            Employee.category == "teacher",
            User.organization_id == actor.organization_id,
            User.role == "TEACHER",
            User.status == "active",
        ).order_by(Employee.last_name, Employee.first_name, Employee.id)
    )]

    parents: list[GroupProfileParent] = []
    if child_ids:
        parent_rows = db.execute(
            select(Guardian, Child, ChildGuardian, User.status)
            .join(ChildGuardian, ChildGuardian.guardian_id == Guardian.id)
            .join(Child, Child.id == ChildGuardian.child_id)
            .outerjoin(User, and_(
                User.id == Guardian.user_id,
                User.organization_id == actor.organization_id,
                User.role == "PARENT",
            ))
            .where(
                Child.organization_id == actor.organization_id,
                Child.group_id == group.id,
                Child.status == "active",
                ChildGuardian.organization_id == actor.organization_id,
                ChildGuardian.status == "active",
                Guardian.organization_id == actor.organization_id,
                Guardian.status == "active",
            ).order_by(Guardian.last_name, Guardian.first_name, Child.last_name, Child.first_name)
        )
        parents = [GroupProfileParent(
            id=guardian.id, first_name=guardian.first_name, last_name=guardian.last_name,
            middle_name=guardian.middle_name, phone=guardian.phone, email=guardian.email,
            account_status=account_status if account_status in {"active", "blocked"} else None,
            child_id=child.id,
            child_name=_full_name(child.last_name, child.first_name, child.middle_name),
            relation_type=link.relation_type,
        ) for guardian, child, link, account_status in parent_rows]

    schedule_rows = list(db.scalars(select(GroupScheduleItem).where(
        GroupScheduleItem.organization_id == actor.organization_id,
        GroupScheduleItem.group_id == group.id,
        GroupScheduleItem.status == "active",
    ).order_by(GroupScheduleItem.weekday, GroupScheduleItem.start_time, GroupScheduleItem.id)))
    schedule = [GroupProfileScheduleItem(
        id=item.id, weekday=item.weekday, start_time=item.start_time,
        end_time=item.end_time, title=item.title,
    ) for item in schedule_rows]

    open_tasks = db.scalar(select(func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.group_id == group.id,
        TeacherTask.status.in_(("open", "in_progress")),
    )) or 0
    overdue_tasks = db.scalar(select(func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.group_id == group.id,
        TeacherTask.status.in_(("open", "in_progress")),
        TeacherTask.due_at.is_not(None), TeacherTask.due_at < now,
    )) or 0
    return GroupProfile(
        group=group, local_date=today, active_children=len(children), present=present,
        absent=absent, unknown=unknown, active_teacher_count=len(employees),
        parent_count=len({item.id for item in parents}), active_schedule_count=len(schedule),
        open_tasks=open_tasks, overdue_tasks=overdue_tasks, children=children,
        employees=employees, parents=parents, schedule=schedule,
    )


def group_overviews(db: Session, actor: User, status: str = "active") -> GroupOverviewList:
    group_query = select(Group).where(Group.organization_id == actor.organization_id)
    if status != "all":
        group_query = group_query.where(Group.status == status)
    groups = list(db.scalars(group_query.order_by(Group.name, Group.id)))
    group_ids = [group.id for group in groups]
    if not group_ids:
        return GroupOverviewList(items=[])

    child_counts = dict(db.execute(select(Child.group_id, func.count(Child.id)).where(
        Child.organization_id == actor.organization_id, Child.group_id.in_(group_ids), Child.status == "active",
    ).group_by(Child.group_id)))

    attendance_counts: dict[UUID, dict[str, int]] = {}
    today = organization_today(actor.organization)
    attendance_rows = db.execute(
        select(Attendance.group_id, Attendance.status, func.count(Attendance.id))
        .join(Child, Child.id == Attendance.child_id)
        .where(
            Attendance.organization_id == actor.organization_id,
            Attendance.group_id.in_(group_ids), Attendance.date == today,
            Child.organization_id == actor.organization_id, Child.group_id == Attendance.group_id,
            Child.status == "active",
        ).group_by(Attendance.group_id, Attendance.status)
    )
    for group_id, attendance_status, count in attendance_rows:
        attendance_counts.setdefault(group_id, {})[attendance_status] = count

    teacher_names: dict[UUID, list[str]] = {}
    teacher_rows = db.execute(
        select(TeacherGroupAssignment.group_id, Employee.last_name, Employee.first_name, Employee.middle_name)
        .join(Employee, Employee.id == TeacherGroupAssignment.employee_id)
        .join(User, User.id == Employee.user_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.group_id.in_(group_ids), TeacherGroupAssignment.status == "active",
            Employee.organization_id == actor.organization_id, Employee.status == "active",
            Employee.category == "teacher", User.organization_id == actor.organization_id,
            User.role == "TEACHER", User.status == "active",
        ).order_by(Employee.last_name, Employee.first_name, Employee.id)
    )
    for group_id, last_name, first_name, middle_name in teacher_rows:
        teacher_names.setdefault(group_id, []).append(_full_name(last_name, first_name, middle_name))

    scheduled = set(db.scalars(select(GroupScheduleItem.group_id).where(
        GroupScheduleItem.organization_id == actor.organization_id,
        GroupScheduleItem.group_id.in_(group_ids), GroupScheduleItem.status == "active",
    ).distinct()))

    now = datetime.now(UTC)
    open_task_counts = dict(db.execute(select(TeacherTask.group_id, func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id, TeacherTask.group_id.in_(group_ids),
        TeacherTask.status.in_(("open", "in_progress")),
    ).group_by(TeacherTask.group_id)))
    overdue_task_counts = dict(db.execute(select(TeacherTask.group_id, func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id, TeacherTask.group_id.in_(group_ids),
        TeacherTask.status.in_(("open", "in_progress")), TeacherTask.due_at.is_not(None),
        TeacherTask.due_at < now,
    ).group_by(TeacherTask.group_id)))

    items = []
    for group in groups:
        counts = attendance_counts.get(group.id, {})
        present = counts.get("present", 0)
        absent = counts.get("absent", 0)
        child_count = child_counts.get(group.id, 0)
        items.append(GroupOverviewItem(
            group=group, active_children=child_count, present=present, absent=absent,
            unknown=max(0, child_count - present - absent),
            active_teacher_names=teacher_names.get(group.id, []),
            has_active_weekly_schedule=group.id in scheduled,
            open_tasks=open_task_counts.get(group.id, 0),
            overdue_tasks=overdue_task_counts.get(group.id, 0),
        ))
    return GroupOverviewList(items=items)


def employee_profile(db: Session, actor: User, employee_id: UUID) -> EmployeeProfile:
    employee = db.scalar(select(Employee.id).where(
        Employee.id == employee_id, Employee.organization_id == actor.organization_id,
    ))
    if employee is None:
        raise AppError(404, "NOT_FOUND")
    assignments = [EmployeeAssignmentProfile(
        group_id=group.id, group_name=group.name,
        status=assignment.status, archived_at=assignment.archived_at,
    ) for assignment, group in db.execute(
        select(TeacherGroupAssignment, Group)
        .join(Group, Group.id == TeacherGroupAssignment.group_id)
        .where(
            TeacherGroupAssignment.organization_id == actor.organization_id,
            TeacherGroupAssignment.employee_id == employee_id,
            Group.organization_id == actor.organization_id,
        ).order_by(TeacherGroupAssignment.status, Group.name, Group.id)
    )]
    now = datetime.now(UTC)
    open_tasks = db.scalar(select(func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.assignee_employee_id == employee_id,
        TeacherTask.status.in_(("open", "in_progress")),
    )) or 0
    overdue_tasks = db.scalar(select(func.count(TeacherTask.id)).where(
        TeacherTask.organization_id == actor.organization_id,
        TeacherTask.assignee_employee_id == employee_id,
        TeacherTask.status.in_(("open", "in_progress")),
        TeacherTask.due_at.is_not(None), TeacherTask.due_at < now,
    )) or 0
    return EmployeeProfile(employee_id=employee_id, assignments=assignments, open_tasks=open_tasks, overdue_tasks=overdue_tasks)

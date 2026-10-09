"""Current tenant operational snapshot; reads have no Audit side effects."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.organization_time import organization_today
from app.models.employee import Employee
from app.models.group import Group
from app.models.user import User
from app.schemas.dashboard import DashboardGroup, DashboardSummary
from app.services.attendance_counts import count_group_attendance


def summary(db: Session, actor: User) -> DashboardSummary:
    day = organization_today(actor.organization)
    group_rows = db.execute(
        select(Group.id, Group.name).where(
            Group.organization_id == actor.organization_id, Group.status == "active",
        ).order_by(Group.name, Group.id)
    ).all()
    counts = count_group_attendance(db, actor.organization_id, [row.id for row in group_rows], day)
    groups = [DashboardGroup(
        id=row.id, name=row.name, **counts[row.id].__dict__,
    ) for row in group_rows]
    active_employees = db.scalar(select(func.count(Employee.id)).where(
        Employee.organization_id == actor.organization_id,
        Employee.status == "active",
    )) or 0
    totals = {key: sum(getattr(group, key) for group in groups) for key in (
        "active_children", "present", "on_site", "departed", "absent", "unknown", "needs_arrival",
    )}
    return DashboardSummary(
        date=day, **totals, active_groups=len(groups), active_employees=active_employees, groups=groups,
    )

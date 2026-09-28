"""Current tenant operational snapshot; reads have no Audit side effects."""

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.core.organization_time import organization_today
from app.models.attendance import Attendance
from app.models.child import Child
from app.models.employee import Employee
from app.models.group import Group
from app.models.user import User
from app.schemas.dashboard import DashboardGroup, DashboardSummary


def summary(db: Session, actor: User) -> DashboardSummary:
    day = organization_today(actor.organization)
    group_rows = db.execute(
        select(
            Group.id,
            Group.name,
            func.count(Child.id).label("active_children"),
            func.count(Child.id).filter(Attendance.status == "present").label("present"),
            func.count(Child.id).filter(Attendance.status == "absent").label("absent"),
        )
        .outerjoin(
            Child,
            and_(
                Child.group_id == Group.id,
                Child.organization_id == actor.organization_id,
                Child.status == "active",
            ),
        )
        .outerjoin(
            Attendance,
            and_(
                Attendance.child_id == Child.id,
                Attendance.organization_id == actor.organization_id,
                Attendance.date == day,
            ),
        )
        .where(Group.organization_id == actor.organization_id, Group.status == "active")
        .group_by(Group.id, Group.name)
        .order_by(Group.name, Group.id)
    ).all()
    groups = [
        DashboardGroup(
            id=row.id,
            name=row.name,
            active_children=row.active_children,
            present=row.present,
            absent=row.absent,
            unknown=row.active_children - row.present - row.absent,
        )
        for row in group_rows
    ]
    active_employees = db.scalar(select(func.count(Employee.id)).where(
        Employee.organization_id == actor.organization_id,
        Employee.status == "active",
    )) or 0
    return DashboardSummary(
        date=day,
        active_children=sum(group.active_children for group in groups),
        present=sum(group.present for group in groups),
        absent=sum(group.absent for group in groups),
        unknown=sum(group.unknown for group in groups),
        active_groups=len(groups),
        active_employees=active_employees,
        groups=groups,
    )

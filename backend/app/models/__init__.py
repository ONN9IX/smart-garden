"""Import all tables so Alembic receives complete metadata."""

from app.models.attendance import Attendance
from app.models.auth_session import AuthSession
from app.models.child import Child
from app.models.child_guardian import ChildGuardian
from app.models.employee import Employee
from app.models.group import Group
from app.models.guardian import Guardian
from app.models.organization import Organization
from app.models.user import User

__all__ = ["Attendance", "AuthSession", "Child", "ChildGuardian", "Employee", "Group", "Guardian", "Organization", "User"]

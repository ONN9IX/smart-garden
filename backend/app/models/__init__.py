"""Import all tables so Alembic receives complete metadata."""

from app.models.account_access_token import AccountAccessToken
from app.models.announcement import Announcement
from app.models.attendance import Attendance
from app.models.audit_event import AuditEvent
from app.models.auth_session import AuthSession
from app.models.child import Child
from app.models.child_diary_entry import ChildDiaryEntry
from app.models.child_guardian import ChildGuardian
from app.models.communication import CommunicationMessage, CommunicationThread
from app.models.document_notice import DocumentNotice
from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.incident import Incident
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.photo import PhotoAsset, PhotoAssetChild, PhotoConsent
from app.models.poll import Poll, PollOption, PollVote
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.user import User

__all__ = [
    "AccountAccessToken",
    "Announcement", "Attendance", "AuditEvent", "AuthSession", "Child", "ChildDiaryEntry", "ChildGuardian",
    "CommunicationMessage", "CommunicationThread", "DocumentNotice", "Employee", "Group", "GroupScheduleItem",
    "Guardian", "Incident", "Notification", "Organization", "PhotoAsset", "PhotoAssetChild", "PhotoConsent",
    "Poll", "PollOption", "PollVote", "TeacherGroupAssignment", "TeacherTask", "User",
]

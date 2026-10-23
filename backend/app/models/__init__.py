"""Import all tables so Alembic receives complete metadata."""

from app.models.account_access_token import AccountAccessToken
from app.models.announcement import Announcement
from app.models.announcement_read_state import AnnouncementReadState
from app.models.attendance import Attendance
from app.models.audit_event import AuditEvent
from app.models.auth_session import AuthSession
from app.models.child import Child
from app.models.child_diary_entry import ChildDiaryEntry
from app.models.child_guardian import ChildGuardian
from app.models.communication import (
    CommunicationMessage,
    CommunicationReadState,
    CommunicationThread,
)
from app.models.document_notice import DocumentNotice
from app.models.employee import Employee
from app.models.group import Group
from app.models.group_schedule_item import GroupScheduleItem
from app.models.guardian import Guardian
from app.models.incident import Incident
from app.models.initial_setup_batch import InitialSetupBatch
from app.models.notification import Notification
from app.models.operational_alert_state import OperationalAlertState
from app.models.organization import Organization
from app.models.organization_notification_settings import (
    OrganizationNotificationSettings,
)
from app.models.photo import PhotoAsset, PhotoAssetChild, PhotoConsent
from app.models.platform_audit_event import PlatformAuditEvent
from app.models.platform_operator import PlatformOperator
from app.models.platform_provisioning_request import PlatformProvisioningRequest
from app.models.platform_session import PlatformSession
from app.models.poll import Poll, PollOption, PollVote
from app.models.privacy import (
    BasisAttestation,
    ConsentEvent,
    LegalDocument,
    PaperConsent,
    PrivacyRequest,
    ProcessingPurpose,
    RequestEvent,
)
from app.models.teacher_group_assignment import TeacherGroupAssignment
from app.models.teacher_task import TeacherTask
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User

__all__ = [
    "AccountAccessToken",
    "Announcement",
    "AnnouncementReadState",
    "Attendance",
    "AuditEvent",
    "AuthSession",
    "BasisAttestation",
    "Child",
    "ChildDiaryEntry",
    "ChildGuardian",
    "CommunicationMessage",
    "CommunicationReadState",
    "CommunicationThread",
    "ConsentEvent",
    "DocumentNotice",
    "Employee",
    "Group",
    "GroupScheduleItem",
    "Guardian",
    "Incident",
    "InitialSetupBatch",
    "LegalDocument",
    "Notification",
    "OperationalAlertState",
    "Organization",
    "OrganizationNotificationSettings",
    "PaperConsent",
    "PhotoAsset",
    "PhotoAssetChild",
    "PhotoConsent",
    "PlatformAuditEvent",
    "PlatformOperator",
    "PlatformProvisioningRequest",
    "PlatformSession",
    "Poll",
    "PollOption",
    "PollVote",
    "PrivacyRequest",
    "ProcessingPurpose",
    "RequestEvent",
    "TeacherGroupAssignment",
    "TeacherTask",
    "TenantSubscription",
    "User",
]

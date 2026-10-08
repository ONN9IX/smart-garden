"""Safe public and management contracts for secure account access."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class InviteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["TEACHER", "ADMIN"] | None = None


class InviteResponse(BaseModel):
    username: str
    role: Literal["PARENT", "TEACHER", "ADMIN"]
    status: Literal["pending", "sent", "failed"]


class PasswordActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=512)
    new_password: str = Field(min_length=1, max_length=128)


class TokenCheckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str = Field(min_length=32, max_length=512)


class ForgotPasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    identifier: str = Field(min_length=3, max_length=254)


class PublicMessageResponse(BaseModel):
    message: str


class AccountActionResponse(BaseModel):
    success: Literal[True] = True


class RoleChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    role: Literal["TEACHER", "ADMIN"]


class RevokeSessionsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_type: Literal["guardian", "employee"]
    profile_id: UUID


class AccessAccountItem(BaseModel):
    profile_id: UUID
    profile_type: Literal["guardian", "employee"]
    full_name: str
    context: str
    username: str | None
    role: Literal["PARENT", "TEACHER", "ADMIN"] | None
    masked_email: str | None
    status: Literal["no_account", "invited", "delivery_failed", "invite_expired", "activated", "blocked"]
    last_login_at: datetime | None
    groups: list[str] = []


class AccessAccountSections(BaseModel):
    parents: list[AccessAccountItem]
    teachers: list[AccessAccountItem]
    administrators: list[AccessAccountItem]
    other_employees: list[AccessAccountItem]
    blocked: list[AccessAccountItem]


class BulkParentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    guardian_ids: list[UUID] = Field(max_length=100)
    confirm: bool = False


class BulkPreflight(BaseModel):
    eligible: int = 0
    missing_or_invalid_email: int = 0
    activated: int = 0
    already_invited: int = 0
    failed_or_expired: int = 0
    blocked: int = 0
    archived: int = 0
    no_active_linked_child: int = 0


class BulkResultItem(BaseModel):
    guardian_id: UUID
    result: Literal["sent", "failed", "skipped"]
    reason: str | None = None


class BulkParentResponse(BaseModel):
    preflight: BulkPreflight
    results: list[BulkResultItem] = []

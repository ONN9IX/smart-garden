"""Stage 1 request and response schemas, matching docs/03-api-contract-v0.1.md."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    new_password: str = Field(min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: UUID
    username: str
    role: Literal["DIRECTOR", "ADMIN"]
    status: Literal["active"]
    must_change_password: bool


class OrganizationResponse(BaseModel):
    id: UUID
    name: str


class AuthResponse(BaseModel):
    user: UserResponse
    organization: OrganizationResponse


class ChangePasswordResponse(BaseModel):
    success: Literal[True] = True
    must_change_password: Literal[False] = False


class SuccessResponse(BaseModel):
    success: Literal[True] = True


class ErrorBody(BaseModel):
    code: str
    message: str
    field: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody

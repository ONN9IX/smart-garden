"""Stage 1 auth HTTP handlers matching docs/03-api-contract-v0.1.md.

Security: requests and responses never contain the raw session token; only Set-Cookie does.
"""

from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, Response
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.core.security import hash_password, valid_password, verify_password
from app.db.session import get_db
from app.models.auth_session import AuthSession
from app.models.user import User
from app.schemas.auth import (
    AuthResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    ErrorResponse,
    LoginRequest,
    OrganizationResponse,
    SuccessResponse,
    UserResponse,
)
from app.services.auth import (
    COOKIE_NAME,
    authenticate_credentials,
    current_identity,
    issue_session,
    session_from_token,
    utc_now,
)

router = APIRouter(prefix="/auth", tags=["Авторизация"])
COMMON_ERRORS = {400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}


def auth_response(user: User) -> AuthResponse:
    return AuthResponse(
        user=UserResponse(id=user.id, username=user.username, role=user.role, status=user.status, must_change_password=user.must_change_password),
        organization=OrganizationResponse(id=user.organization.id, name=user.organization.name),
    )


def set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME, value=token, max_age=settings.auth_session_ttl_seconds,
        httponly=True, secure=settings.secure_cookie, samesite="lax", path="/api/v1",
    )


@router.post("/login", response_model=AuthResponse, responses=COMMON_ERRORS, summary="Войти по логину и паролю")
def login(payload: LoginRequest, response: Response, db: Annotated[Session, Depends(get_db)]) -> AuthResponse:
    user = authenticate_credentials(db, payload.username, payload.password)
    user.last_login_at = utc_now()
    token = issue_session(db, user)
    db.commit()
    set_session_cookie(response, token)
    return auth_response(user)


@router.get("/me", response_model=AuthResponse, responses=COMMON_ERRORS, summary="Текущий пользователь и детский сад")
def me(user: Annotated[User, Depends(current_identity)]) -> AuthResponse:
    return auth_response(user)


@router.post("/change-password", response_model=ChangePasswordResponse, responses=COMMON_ERRORS, summary="Обязательная смена временного пароля")
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    user: Annotated[User, Depends(current_identity)],
    db: Annotated[Session, Depends(get_db)],
) -> ChangePasswordResponse:
    if not user.must_change_password:
        raise AppError(403, "FORBIDDEN")
    if not valid_password(payload.new_password) or verify_password(user.password_hash, payload.new_password):
        raise AppError(400, "INVALID_PASSWORD", "new_password")
    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = False
    db.execute(update(AuthSession).where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None)).values(revoked_at=utc_now()))
    token = issue_session(db, user)
    db.commit()
    set_session_cookie(response, token)
    return ChangePasswordResponse()


@router.post("/logout", response_model=SuccessResponse, responses=COMMON_ERRORS, summary="Завершить текущую сессию")
def logout(
    response: Response,
    _user: Annotated[User, Depends(current_identity)],
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str | None, Cookie(alias=COOKIE_NAME)] = None,
) -> SuccessResponse:
    session = session_from_token(db, token)
    session.revoked_at = utc_now()
    db.commit()
    response.delete_cookie(COOKIE_NAME, path="/api/v1", secure=get_settings().secure_cookie, httponly=True, samesite="lax")
    return SuccessResponse()

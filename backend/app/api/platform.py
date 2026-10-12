"""Independent platform HTTP surface and one DIRECTOR-only subscription read."""

from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session

from app.core import platform_security as security
from app.core.config import get_settings
from app.core.permissions import require_role
from app.db.session import get_db
from app.models.user import User
from app.schemas.platform import (
    AuditView,
    CreateOrganizationInput,
    IdentityView,
    LifecycleInput,
    LoginInput,
    MFAInput,
    OrganizationView,
    ProvisioningView,
    SubscriptionChangeInput,
    SubscriptionView,
)
from app.services import (
    platform_audit,
    platform_auth,
    platform_organizations,
    platform_subscriptions,
)

router = APIRouter(prefix="/platform", tags=["Platform owner"])
tenant_router = APIRouter(prefix="/settings", tags=["Subscription metadata"])
Database = Annotated[Session, Depends(get_db)]


def token(request: Request) -> str | None:
    return request.cookies.get(security.COOKIE_NAME)


def cookie(response: Response, value: str, max_age: int) -> None:
    response.set_cookie(
        security.COOKIE_NAME,
        value,
        max_age=max_age,
        httponly=True,
        secure=get_settings().secure_cookie,
        samesite="strict",
        path=security.COOKIE_PATH,
    )


def owner(request: Request, db: Database):
    return platform_auth.session_identity(db, token(request))


Owner = Annotated[tuple, Depends(owner)]


def mutation(request: Request, db: Database):
    identity = platform_auth.session_identity(db, token(request))
    security.enforce_write(request, token(request))
    platform_auth.require_fresh(identity[0])
    return identity


FreshOwner = Annotated[tuple, Depends(mutation)]


@router.post("/auth/login")
def login(payload: LoginInput, request: Request, response: Response, db: Database):
    security.enforce_write(request)
    raw = platform_auth.password_login(
        db,
        payload.username,
        payload.password,
        request.client.host if request.client else "unknown",
    )
    cookie(response, raw, 300)
    return {"mfa_required": True, "csrf_token": security.csrf_token(raw)}


@router.post("/auth/mfa/verify", response_model=IdentityView)
def verify(payload: MFAInput, request: Request, response: Response, db: Database):
    raw = token(request)
    security.enforce_write(request, raw)
    session, operator = platform_auth.verify_mfa(db, raw, payload.code)
    cookie(response, raw, get_settings().platform_session_ttl_seconds)
    return platform_auth.identity_view(session, operator, raw)


@router.post("/auth/step-up", response_model=IdentityView)
def step_up(payload: MFAInput, request: Request, db: Database):
    raw = token(request)
    security.enforce_write(request, raw)
    session, operator = platform_auth.verify_mfa(db, raw, payload.code, step_up=True)
    return platform_auth.identity_view(session, operator, raw)


@router.get("/auth/me", response_model=IdentityView)
def me(request: Request, identity: Owner):
    return platform_auth.identity_view(*identity, token(request))


@router.post("/auth/logout")
def logout(request: Request, response: Response, db: Database, _identity: Owner):
    security.enforce_write(request, token(request))
    platform_auth.logout(db, token(request))
    response.delete_cookie(
        security.COOKIE_NAME,
        path=security.COOKIE_PATH,
        httponly=True,
        secure=get_settings().secure_cookie,
        samesite="strict",
    )
    return {"success": True}


@router.get("/overview")
def overview(db: Database, _identity: Owner):
    return platform_organizations.overview(db)


@router.get("/organizations", response_model=list[OrganizationView])
def organizations(
    db: Database,
    _identity: Owner,
    search: str = Query("", max_length=200),
    status: Literal["active", "blocked", "archived"] | None = None,
):
    return platform_organizations.listing(db, search, status)


@router.get("/organizations/{organization_id}", response_model=OrganizationView)
def organization(organization_id: UUID, db: Database, _identity: Owner):
    return platform_organizations.view(
        db, platform_organizations.get(db, organization_id)
    )


@router.post(
    "/organizations", response_model=ProvisioningView, response_model_exclude_none=True
)
def provision(
    payload: CreateOrganizationInput,
    request: Request,
    db: Database,
    identity: FreshOwner,
):
    return platform_organizations.provision(db, identity[1].id, payload)


@router.post("/organizations/{organization_id}/block", response_model=OrganizationView)
def block(
    organization_id: UUID, payload: LifecycleInput, db: Database, identity: FreshOwner
):
    return platform_organizations.lifecycle(
        db, identity[1].id, organization_id, payload, block=True
    )


@router.post(
    "/organizations/{organization_id}/unblock", response_model=OrganizationView
)
def unblock(
    organization_id: UUID, payload: LifecycleInput, db: Database, identity: FreshOwner
):
    return platform_organizations.lifecycle(
        db, identity[1].id, organization_id, payload, block=False
    )


@router.patch(
    "/organizations/{organization_id}/subscription", response_model=SubscriptionView
)
def subscription(
    organization_id: UUID,
    payload: SubscriptionChangeInput,
    db: Database,
    identity: FreshOwner,
):
    return platform_subscriptions.update(db, identity[1].id, organization_id, payload)


@router.get("/audit", response_model=list[AuditView])
def audit(db: Database, _identity: Owner, organization_id: UUID | None = None):
    return platform_audit.listing(db, organization_id)


@tenant_router.get("/subscription")
def director_subscription(
    response: Response,
    db: Database,
    user: Annotated[User, Depends(require_role("DIRECTOR"))],
):
    response.headers["Cache-Control"] = "no-store"
    return platform_subscriptions.director_view(db, user)

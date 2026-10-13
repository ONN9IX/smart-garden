"""Synthetic provisioning, tenant isolation, lifecycle and metadata checks."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import UUID, uuid4

import pyotp
import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import engine
from app.models.auth_session import AuthSession
from app.models.group import Group
from app.models.organization import Organization
from app.models.platform_audit_event import PlatformAuditEvent
from app.models.platform_operator import PlatformOperator
from app.models.platform_provisioning_request import PlatformProvisioningRequest
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User
from app.schemas.platform import CreateOrganizationInput
from app.services import platform_organizations
from app.services.platform_bootstrap import configure_operator
from tests.conftest import TEST_PASSWORD
from tests.test_platform_owner_auth import (
    ROOT,
    authenticate,
    headers,
    platform_schema,  # noqa: F401
)
from tests.test_platform_owner_auth import (
    platform_owner as owner_fixture,
)


@pytest.fixture
def platform_owner(db, monkeypatch):
    return owner_fixture.__wrapped__(db, monkeypatch)


def payload():
    return {
        "idempotency_key": str(uuid4()),
        "name": "Синтетический сад 221",
        "timezone": "Europe/Moscow",
        "director_username": "synthetic-director-221",
        "credential_handoff_confirmed": True,
        "subscription": {
            "status": "trial",
            "price_minor": 0,
            "trial_ends_at": "2030-01-15T00:00:00Z",
        },
    }


def create(client, csrf, data=None):
    response = client.post(
        ROOT + "/organizations", json=data or payload(), headers=headers(csrf)
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_atomic_idempotent_secret_once_and_forced_password(
    client, platform_owner, db, caplog
):
    csrf = authenticate(client, platform_owner)
    data = payload()
    first = create(client, csrf, data)
    replay = create(client, csrf, data)
    assert replay["replayed"] and "temporary_password" not in replay
    assert first["organization"]["id"] == replay["organization"]["id"]
    assert db.scalar(select(func.count(Organization.id))) == 1
    changed = dict(data, name="Другое название")
    assert (
        client.post(
            ROOT + "/organizations", json=changed, headers=headers(csrf)
        ).status_code
        == 409
    )
    duplicate = dict(data, idempotency_key=str(uuid4()))
    assert (
        client.post(
            ROOT + "/organizations", json=duplicate, headers=headers(csrf)
        ).status_code
        == 409
    )
    assert db.scalar(select(func.count(Organization.id))) == 1
    director = db.scalar(select(User).where(User.username == data["director_username"]))
    assert director.role == "DIRECTOR" and director.must_change_password
    secret = first["temporary_password"]
    for route in ("/organizations", "/overview", "/audit"):
        body = str(client.get(ROOT + route).json())
        assert (
            secret not in body
            and "password_hash" not in body
            and "guardian" not in body
            and "chat" not in body
        )
    assert secret not in caplog.text and secret not in str(
        db.scalars(select(PlatformAuditEvent.details)).all()
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": director.username, "password": secret},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/settings/subscription").status_code == 403
    assert (
        client.post(
            "/api/v1/auth/change-password",
            json={"new_password": "synthetic-replacement-password-221"},
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/settings/subscription").json()["subscription"]["status"]
        == "trial"
    )


def test_handoff_schema_injection_and_fresh_mfa(client, platform_owner, monkeypatch):
    csrf = authenticate(client, platform_owner)
    data = payload()
    for modified in (
        dict(data, organization_id=str(uuid4())),
        dict(data, timezone="Invalid/Zone"),
        dict(data, credential_handoff_confirmed=False),
        dict(data, subscription={"status": "trial", "price_minor": -1}),
    ):
        assert (
            client.post(
                ROOT + "/organizations", json=modified, headers=headers(csrf)
            ).status_code
            == 400
        )
    monkeypatch.setattr(get_settings(), "platform_credential_handoff_enabled", False)
    assert (
        client.post(
            ROOT + "/organizations", json=data, headers=headers(csrf)
        ).status_code
        == 503
    )
    monkeypatch.setattr(get_settings(), "platform_credential_handoff_enabled", True)
    platform_owner[2][0] += timedelta(
        seconds=get_settings().platform_step_up_seconds + 1
    )
    assert (
        client.post(
            ROOT + "/organizations", json=data, headers=headers(csrf)
        ).status_code
        == 403
    )
    assert (
        client.post(
            ROOT + "/auth/step-up",
            json={"code": pyotp.TOTP(platform_owner[1]).at(platform_owner[2][0])},
            headers=headers(csrf),
        ).status_code
        == 200
    )
    assert create(client, csrf, data)["organization"]["status"] == "active"


def test_profile_provisioning_change_audit_and_data_conflict(client, platform_owner, db):
    csrf = authenticate(client, platform_owner)
    data = dict(payload(), operating_profile="GYMNASTICS")
    provisioned = create(client, csrf, data)
    organization = provisioned["organization"]
    assert organization["operating_profile"] == "GYMNASTICS"
    path = ROOT + f"/organizations/{organization['id']}/profile"
    changed = client.patch(path, json={
        "confirmation_name": organization["name"],
        "operating_profile": "KINDERGARTEN",
    }, headers=headers(csrf))
    assert changed.status_code == 200, changed.text
    assert changed.json()["operating_profile"] == "KINDERGARTEN"
    event = db.scalar(select(PlatformAuditEvent).where(
        PlatformAuditEvent.action == "organization.profile_change",
        PlatformAuditEvent.organization_id == UUID(organization["id"]),
    ))
    assert event is not None
    assert event.details["before_profile"] == "GYMNASTICS"
    assert event.details["after_profile"] == "KINDERGARTEN"

    tenant = db.get(Organization, UUID(organization["id"]))
    db.add(Group(organization_id=tenant.id, name="Синтетическая группа", status="active"))
    db.flush()
    rejected = client.patch(path, json={
        "confirmation_name": tenant.name,
        "operating_profile": "GYMNASTICS",
    }, headers=headers(csrf))
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "PROFILE_CHANGE_BLOCKED"


def test_block_revokes_only_target_and_unblock_preserves_user(
    client, platform_owner, users, db
):
    csrf = authenticate(client, platform_owner)
    organization, other, director, admin = users
    director.must_change_password = False
    db.flush()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": director.username, "password": TEST_PASSWORD},
        ).status_code
        == 200
    )
    session = db.scalar(select(AuthSession).where(AuthSession.user_id == director.id))
    path = ROOT + f"/organizations/{organization.id}"
    data = {"confirmation_name": "wrong", "reason": "security"}
    assert (
        client.post(path + "/block", json=data, headers=headers(csrf)).status_code
        == 400
    )
    data["confirmation_name"] = organization.name
    assert (
        client.post(path + "/block", json=data, headers=headers(csrf)).status_code
        == 200
    )
    assert session.revoked_at is not None and other.status == "active"
    assert client.get("/api/v1/auth/me").status_code != 200
    admin.status = "blocked"
    db.flush()
    assert (
        client.post(path + "/block", json=data, headers=headers(csrf)).status_code
        == 200
    )
    assert (
        db.scalar(
            select(func.count(PlatformAuditEvent.id)).where(
                PlatformAuditEvent.action == "organization.block"
            )
        )
        == 1
    )
    assert (
        client.post(path + "/unblock", json=data, headers=headers(csrf)).status_code
        == 200
    )
    assert admin.status == "blocked" and session.revoked_at is not None


def test_billing_is_metadata_and_director_read_is_tenant_scoped(
    client, platform_owner, users, db
):
    csrf = authenticate(client, platform_owner)
    organization, other, director, admin = users
    director.must_change_password = False
    db.flush()
    for status in ("active", "past_due", "cancel_at_period_end", "cancelled"):
        response = client.patch(
            ROOT + f"/organizations/{organization.id}/subscription",
            json={
                "confirmation_name": organization.name,
                "subscription": {"status": status, "price_minor": 12345},
            },
            headers=headers(csrf),
        )
        assert response.status_code == 200 and organization.status == "active"
    assert db.get(Organization, organization.id) is not None
    db.add(
        TenantSubscription(
            organization_id=other.id,
            status="active",
            plan_code="standard",
            currency="RUB",
            interval="yearly",
            price_minor=999,
        )
    )
    db.flush()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": director.username, "password": TEST_PASSWORD},
        ).status_code
        == 200
    )
    response = client.get(
        "/api/v1/settings/subscription", params={"organization_id": str(other.id)}
    )
    assert response.json()["subscription"]["price_minor"] == 12345
    assert str(other.id) not in response.text
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": TEST_PASSWORD},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/settings/subscription").status_code == 403
    client.cookies.delete(
        "promax_platform_session", domain="testserver.local", path="/api/v1/platform"
    )
    assert (
        client.patch(
            ROOT + f"/organizations/{organization.id}/subscription",
            json={},
            headers=headers(csrf),
        ).status_code
        == 401
    )


def test_concurrent_retries_one_committed_tenant(platform_owner):
    # Independent real PostgreSQL transactions, not the rollback fixture connection.
    with Session(engine) as db:
        operator, _ = configure_operator(
            db, "concurrent-synthetic-owner", "concurrent-synthetic-password"
        )
        operator_id = operator.id
        db.commit()
    data = CreateOrganizationInput.model_validate(
        dict(payload(), director_username="concurrent-director-221")
    )
    organization_id = None
    try:

        def provision(_):
            with Session(engine) as db:
                return platform_organizations.provision(db, operator_id, data)

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(provision, range(2)))
        organization_id = results[0].organization.id
        assert {result.organization.id for result in results} == {organization_id}
        assert sum(result.temporary_password is not None for result in results) == 1
        with Session(engine) as db:
            assert (
                db.scalar(
                    select(func.count(PlatformProvisioningRequest.id)).where(
                        PlatformProvisioningRequest.id == data.idempotency_key
                    )
                )
                == 1
            )
    finally:
        with Session(engine) as db:
            db.execute(
                delete(PlatformAuditEvent).where(
                    PlatformAuditEvent.operator_id == operator_id
                )
            )
            db.execute(
                delete(PlatformProvisioningRequest).where(
                    PlatformProvisioningRequest.operator_id == operator_id
                )
            )
            if organization_id:
                db.execute(
                    delete(TenantSubscription).where(
                        TenantSubscription.organization_id == organization_id
                    )
                )
                db.execute(delete(User).where(User.organization_id == organization_id))
                db.execute(
                    delete(Organization).where(Organization.id == organization_id)
                )
            db.execute(
                delete(PlatformOperator).where(PlatformOperator.id == operator_id)
            )
            db.commit()


@pytest.mark.parametrize("role", ["ADMIN", "TEACHER", "PARENT"])
def test_commercial_metadata_denied_to_other_tenant_roles(
    client, platform_owner, users, db, role
):
    from app.core.security import hash_password

    user = User(
        organization_id=users[0].id,
        username="synthetic-" + role.lower(),
        password_hash=hash_password(TEST_PASSWORD),
        role=role,
        status="active",
        must_change_password=False,
    )
    db.add(user)
    db.flush()
    if role == "TEACHER":
        from app.models.employee import Employee

        db.add(
            Employee(
                organization_id=user.organization_id,
                user_id=user.id,
                first_name="Тест",
                last_name="Синтетический",
                position="Воспитатель",
                category="teacher",
                status="active",
            )
        )
    elif role == "PARENT":
        from app.models.guardian import Guardian

        db.add(
            Guardian(
                organization_id=user.organization_id,
                user_id=user.id,
                first_name="Тест",
                last_name="Синтетический",
                status="active",
            )
        )
    db.flush()
    assert (
        client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": TEST_PASSWORD},
        ).status_code
        == 200
    )
    assert client.get("/api/v1/settings/subscription").status_code == 403
    assert client.get(ROOT + "/organizations").status_code == 401

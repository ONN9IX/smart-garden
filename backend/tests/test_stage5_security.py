"""Targeted Stage 5 production configuration security tests."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings

DATABASE_URL = "postgresql+psycopg://stage5:synthetic@db.example.test:5432/smart_garden"
STRONG_TEST_SECRET = "stage5-synthetic-strong-secret-9X4m2Q7p"


def settings(**overrides) -> Settings:
    values = {
        "app_env": "development",
        "database_url": DATABASE_URL,
        "secret_key": "CHANGE_ME_LOCAL",
        "cors_origins": "http://localhost:3000",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize("app_env", ["staging", "production"])
@pytest.mark.parametrize(
    "secret_key",
    ["CHANGE_ME_LOCAL", "too-short", "a" * 32, "replace-me-placeholder-secret-value"],
)
def test_shared_environment_rejects_unsafe_secret(app_env, secret_key):
    with pytest.raises(ValidationError, match="strong SECRET_KEY"):
        settings(
            app_env=app_env,
            secret_key=secret_key,
            cors_origins="https://garden.example.test",
        )


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_shared_environment_rejects_empty_cors(app_env):
    with pytest.raises(ValidationError, match="explicit CORS_ORIGINS"):
        settings(
            app_env=app_env,
            secret_key=STRONG_TEST_SECRET,
            cors_origins=" , ",
        )


@pytest.mark.parametrize("app_env", ["development", "test", "staging", "production"])
@pytest.mark.parametrize("origin", ["*", "https://*.example.test"])
def test_wildcard_cors_is_rejected(app_env, origin):
    with pytest.raises(ValidationError, match="Wildcard CORS origin"):
        settings(
            app_env=app_env,
            secret_key=STRONG_TEST_SECRET,
            cors_origins=origin,
        )


@pytest.mark.parametrize("app_env", ["staging", "production"])
@pytest.mark.parametrize(
    "origin",
    [
        "http://localhost:3000",
        "https://admin.localhost",
        "http://127.0.0.1:3000",
        "https://[::1]:3000",
        "http://0.0.0.0:3000",
    ],
)
def test_shared_environment_rejects_local_or_loopback_origin(app_env, origin):
    with pytest.raises(ValidationError, match="non-development CORS origins"):
        settings(
            app_env=app_env,
            secret_key=STRONG_TEST_SECRET,
            cors_origins=origin,
        )


@pytest.mark.parametrize("app_env", ["staging", "production"])
def test_valid_explicit_shared_environment_config_is_accepted(app_env):
    configured = settings(
        app_env=app_env,
        secret_key=STRONG_TEST_SECRET,
        cors_origins="https://app.example.test, https://admin.example.test",
    )

    assert configured.allowed_origins == [
        "https://app.example.test",
        "https://admin.example.test",
    ]
    assert configured.secure_cookie is True


@pytest.mark.parametrize("app_env", ["development", "test"])
def test_local_environment_remains_intentionally_usable(app_env):
    configured = settings(app_env=app_env)

    assert configured.allowed_origins == ["http://localhost:3000"]
    assert configured.secure_cookie is False


def test_existing_auth_configuration_contract_is_preserved():
    configured = settings(
        auth_session_ttl_seconds=3600,
        cors_origins="http://localhost:3000, http://127.0.0.1:3000",
    )

    assert configured.auth_session_ttl_seconds == 3600
    assert configured.allowed_origins == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    assert configured.database_url.startswith("postgresql+psycopg://")


def test_postgresql_only_contract_is_preserved():
    with pytest.raises(ValidationError, match="must use PostgreSQL"):
        settings(database_url="sqlite:///synthetic.db")

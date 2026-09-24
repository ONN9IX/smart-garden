"""Database-free checks for security primitives and the published API contract."""

import os

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "unit-test-secret-not-for-production")
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://unused:unused@localhost:5432/unused")

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.security import (
    generate_session_token,
    generate_temporary_password,
    hash_password,
    hash_session_token,
    normalize_username,
    valid_password,
    verify_password,
)
from app.main import app


def test_password_hash_and_token_separation():
    password = generate_temporary_password()
    assert valid_password(password)
    digest = hash_password(password)
    assert digest.startswith("$argon2id$")
    assert verify_password(digest, password)
    assert not verify_password(digest, "incorrect-password")
    token = generate_session_token()
    assert len(token) >= 64
    assert hash_session_token(token) != token
    assert len(hash_session_token(token)) == 64


def test_username_normalization_and_strict_database_setting():
    assert normalize_username("Director-DEMO") == "director-demo"
    try:
        normalize_username(" director-demo")
        assert False, "leading spaces must fail"
    except ValueError:
        pass
    try:
        Settings(database_url="sqlite:///test.db", secret_key="test")
        assert False, "SQLite must fail"
    except ValueError:
        pass


def test_openapi_matches_frontend_transport_and_cookie_security():
    spec = app.openapi()
    paths = spec["paths"]
    assert set(paths) == {"/api/v1/health", "/api/v1/auth/login", "/api/v1/auth/me", "/api/v1/auth/change-password", "/api/v1/auth/logout"}
    assert spec["components"]["securitySchemes"]["APIKeyCookie"]["name"] == "smart_garden_session"
    assert paths["/api/v1/auth/me"]["get"]["security"] == [{"APIKeyCookie": []}]
    login_schema = spec["components"]["schemas"]["LoginRequest"]["properties"]
    assert set(login_schema) == {"username", "password"}
    change_schema = spec["components"]["schemas"]["ChangePasswordRequest"]["properties"]
    assert set(change_schema) == {"new_password"}
    response_schema = spec["components"]["schemas"]["AuthResponse"]["properties"]
    assert set(response_schema) == {"user", "organization"}


def test_validation_is_400_and_untrusted_origin_is_403():
    with TestClient(app) as client:
        invalid = client.post("/api/v1/auth/login", json={"password": "bad"})
        assert invalid.status_code == 400
        assert invalid.json()["error"] == {"code": "VALIDATION_ERROR", "message": "Проверьте введённые данные.", "field": None}
        cross_site = client.post("/api/v1/auth/login", json={}, headers={"Origin": "https://untrusted.example"})
        assert cross_site.status_code == 403

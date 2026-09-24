"""PostgreSQL integration fixtures; each test rolls back its synthetic records."""

import os
import secrets

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("SECRET_KEY", "test-only-secret-not-for-production")

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from alembic import command
from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import engine, get_db
from app.main import app
from app.models.organization import Organization
from app.models.user import User

TEST_PASSWORD = secrets.token_urlsafe(24)


@pytest.fixture(scope="session", autouse=True)
def migrations():
    # CI supplies a disposable PostgreSQL service, not an in-memory replacement.
    if get_settings().app_env != "test":
        raise RuntimeError("Integration tests require APP_ENV=test and a disposable PostgreSQL instance")
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    yield


@pytest.fixture
def db(migrations):
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False) as session:
            yield session
        transaction.rollback()


@pytest.fixture
def client(db):
    def override_db():
        yield db

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def users(db):
    organization = Organization(name="Детский сад «Тестовый»", status="active")
    other = Organization(name="Детский сад «Другой»", status="active")
    db.add_all([organization, other])
    db.flush()
    director = User(organization_id=organization.id, username="director-test", password_hash=hash_password(TEST_PASSWORD), role="DIRECTOR", status="active", must_change_password=True)
    admin = User(organization_id=organization.id, username="admin-test", password_hash=hash_password(TEST_PASSWORD), role="ADMIN", status="active", must_change_password=False)
    db.add_all([director, admin])
    db.flush()
    return organization, other, director, admin

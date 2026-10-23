"""One reversible round-trip on the disposable PostgreSQL test database."""

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from alembic import command
from app.db.session import engine


def test_platform_migration_round_trip(migrations):
    config = Config("alembic.ini")
    assert ScriptDirectory.from_config(config).get_heads() == ["0021"]
    command.upgrade(config, "head")
    tables = {
        "platform_operators",
        "platform_sessions",
        "platform_audit_events",
        "platform_provisioning_requests",
        "tenant_subscriptions",
        "initial_setup_batches",
        "privacy_documents",
        "privacy_purposes",
        "privacy_attestations",
        "privacy_paper_consents",
        "privacy_consent_events",
        "privacy_requests",
        "privacy_request_events",
    }
    assert tables.issubset(inspect(engine).get_table_names())
    command.downgrade(config, "0018")
    try:
        assert tables.isdisjoint(inspect(engine).get_table_names())
    finally:
        command.upgrade(config, "head")
    assert tables.issubset(inspect(engine).get_table_names())
    indexes = {
        item["name"] for item in inspect(engine).get_indexes("platform_sessions")
    }
    assert {
        "ix_platform_sessions_expires_at",
        "ix_platform_sessions_revoked_at",
    } <= indexes
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version")) == "0021"
        )

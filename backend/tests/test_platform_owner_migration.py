"""One reversible round-trip on the disposable PostgreSQL test database."""

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text

from alembic import command
from app.db.session import engine


def test_platform_migration_round_trip(migrations):
    config = Config("alembic.ini")
    assert ScriptDirectory.from_config(config).get_heads() == ["0019"]
    command.upgrade(config, "0019")
    tables = {
        "platform_operators",
        "platform_sessions",
        "platform_audit_events",
        "platform_provisioning_requests",
        "tenant_subscriptions",
    }
    assert tables.issubset(inspect(engine).get_table_names())
    command.downgrade(config, "0018")
    try:
        assert tables.isdisjoint(inspect(engine).get_table_names())
    finally:
        command.upgrade(config, "0019")
    assert tables.issubset(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert (
            connection.scalar(text("SELECT version_num FROM alembic_version")) == "0019"
        )

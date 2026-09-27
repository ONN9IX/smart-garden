"""PostgreSQL-only Audit migration contract and round trip."""

import uuid

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.db.session import engine


def test_0010_audit_migration_round_trip(migrations):
    config = Config("alembic.ini")
    organization_id = uuid.uuid4()
    try:
        command.downgrade(config, "0009")
        with engine.begin() as connection:
            assert "audit_events" not in inspect(connection).get_table_names()
            connection.execute(text(
                "INSERT INTO organizations (id, name, status, timezone) "
                "VALUES (:id, 'Synthetic migration tenant', 'active', 'Europe/Moscow')",
            ), {"id": organization_id})

        command.upgrade(config, "0010")
        with engine.connect() as connection:
            inspector = inspect(connection)
            columns = {column["name"]: column for column in inspector.get_columns("audit_events")}
            assert set(columns) == {
                "id", "organization_id", "actor_user_id", "action", "entity_type",
                "entity_id", "details", "created_at",
            }
            assert columns["action"]["type"].length == 64
            assert columns["entity_type"]["type"].length == 32
            assert columns["details"]["nullable"] is False
            indexes = {index["name"] for index in inspector.get_indexes("audit_events")}
            assert indexes == {
                "ix_audit_events_organization_created_at",
                "ix_audit_events_organization_entity",
                "ix_audit_events_organization_actor_created_at",
            }
            assert connection.scalar(text(
                "SELECT column_default FROM information_schema.columns "
                "WHERE table_name = 'audit_events' AND column_name = 'details'",
            )) == "'{}'::jsonb"

        command.downgrade(config, "0009")
        with engine.connect() as connection:
            assert "audit_events" not in inspect(connection).get_table_names()
            assert connection.scalar(text(
                "SELECT name FROM organizations WHERE id = :id",
            ), {"id": organization_id}) == "Synthetic migration tenant"
        command.upgrade(config, "0010")
        with engine.connect() as connection:
            assert "audit_events" in inspect(connection).get_table_names()
            assert connection.scalar(text(
                "SELECT timezone FROM organizations WHERE id = :id",
            ), {"id": organization_id}) == "Europe/Moscow"
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": organization_id})

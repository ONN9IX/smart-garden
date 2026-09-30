"""PostgreSQL-only Stage 6 Foundation schema contract and round trip."""

import uuid

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.db.session import engine

TABLES = {
    "teacher_group_assignments", "group_schedule_items", "communication_threads", "communication_messages",
    "child_diary_entries", "polls", "poll_options", "poll_votes", "incidents", "teacher_tasks",
    "notifications", "document_notices", "photo_consents", "photo_assets", "photo_asset_children",
}


def test_0012_stage6_foundation_migration_round_trip(migrations):
    config = Config("alembic.ini")
    organization_id, teacher_id = uuid.uuid4(), uuid.uuid4()
    try:
        command.downgrade(config, "0011")
        with engine.connect() as connection:
            assert TABLES.isdisjoint(inspect(connection).get_table_names())
        command.upgrade(config, "0012")
        with engine.begin() as connection:
            inspector = inspect(connection)
            assert TABLES <= set(inspector.get_table_names())
            assert {item["name"] for item in inspector.get_columns("teacher_group_assignments")} == {
                "id", "organization_id", "employee_id", "group_id", "status", "assigned_by", "created_at", "archived_at",
            }
            assert {item["name"] for item in inspector.get_indexes("teacher_group_assignments")} >= {
                "ix_teacher_group_assignments_organization_employee_status",
                "ix_teacher_group_assignments_organization_group_status",
            }
            assert "uq_teacher_group_assignments_employee_group" in {
                item["name"] for item in inspector.get_unique_constraints("teacher_group_assignments")
            }
            assert {item["name"] for item in inspector.get_indexes("communication_threads")} >= {
                "uq_communication_threads_group", "uq_communication_threads_direct",
            }
            assert "uq_poll_votes_poll_voter" in {
                item["name"] for item in inspector.get_unique_constraints("poll_votes")
            }
            connection.execute(text(
                "INSERT INTO organizations (id, name, status, timezone) VALUES "
                "(:id, 'Stage 6 migration tenant', 'active', 'Europe/Moscow')",
            ), {"id": organization_id})
            connection.execute(text(
                "INSERT INTO users (id, organization_id, username, password_hash, role, status, must_change_password) "
                "VALUES (:id, :organization_id, 'migration-teacher', 'synthetic', 'TEACHER', 'active', false)",
            ), {"id": teacher_id, "organization_id": organization_id})
            connection.execute(text("DELETE FROM users WHERE id = :id"), {"id": teacher_id})
        command.downgrade(config, "0011")
        with engine.connect() as connection:
            assert TABLES.isdisjoint(inspect(connection).get_table_names())
        command.upgrade(config, "0012")
        with engine.connect() as connection:
            assert TABLES <= set(inspect(connection).get_table_names())
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": organization_id})

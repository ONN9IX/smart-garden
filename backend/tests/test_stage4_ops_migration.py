"""PostgreSQL-only Announcement migration contract and round trip."""

import uuid

from alembic.config import Config
from sqlalchemy import inspect, text

from alembic import command
from app.db.session import engine


def test_0011_announcements_migration_round_trip(migrations):
    config = Config("alembic.ini")
    organization_id, user_id, group_id, announcement_id = (uuid.uuid4() for _ in range(4))
    try:
        command.downgrade(config, "0010")
        with engine.begin() as connection:
            assert "announcements" not in inspect(connection).get_table_names()
            connection.execute(text(
                "INSERT INTO organizations (id, name, status, timezone) "
                "VALUES (:id, 'Synthetic migration tenant', 'active', 'Europe/Moscow')",
            ), {"id": organization_id})
            connection.execute(text(
                "INSERT INTO users (id, organization_id, username, password_hash, role, status, must_change_password) "
                "VALUES (:id, :organization_id, 'migration-user', 'synthetic', 'DIRECTOR', 'active', false)",
            ), {"id": user_id, "organization_id": organization_id})
            connection.execute(text(
                "INSERT INTO groups (id, organization_id, name, status) "
                "VALUES (:id, :organization_id, 'Migration group', 'active')",
            ), {"id": group_id, "organization_id": organization_id})

        command.upgrade(config, "0011")
        with engine.begin() as connection:
            inspector = inspect(connection)
            columns = {column["name"]: column for column in inspector.get_columns("announcements")}
            assert set(columns) == {
                "id", "organization_id", "target_type", "group_id", "title", "body", "status",
                "created_by", "updated_by", "archived_at", "created_at", "updated_at",
            }
            assert columns["title"]["type"].length == 120
            assert columns["body"]["type"].length == 2000
            assert columns["organization_id"]["nullable"] is False
            assert columns["group_id"]["nullable"] is True
            assert {index["name"] for index in inspector.get_indexes("announcements")} == {
                "ix_announcements_organization_group",
                "ix_announcements_organization_status_created_at",
            }
            connection.execute(text(
                "INSERT INTO announcements "
                "(id, organization_id, target_type, group_id, title, body, status, created_by, updated_by) "
                "VALUES (:id, :organization_id, 'group', :group_id, 'Synthetic title', "
                "'Synthetic body', 'active', :user_id, :user_id)",
            ), {
                "id": announcement_id, "organization_id": organization_id,
                "group_id": group_id, "user_id": user_id,
            })

        command.downgrade(config, "0010")
        with engine.connect() as connection:
            assert "announcements" not in inspect(connection).get_table_names()
            assert connection.scalar(text("SELECT name FROM groups WHERE id = :id"), {"id": group_id}) == "Migration group"
            assert "audit_events" in inspect(connection).get_table_names()

        command.upgrade(config, "0011")
        with engine.connect() as connection:
            assert "announcements" in inspect(connection).get_table_names()
    finally:
        command.upgrade(config, "head")
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM announcements WHERE organization_id = :id"), {"id": organization_id})
            connection.execute(text("DELETE FROM groups WHERE organization_id = :id"), {"id": organization_id})
            connection.execute(text("DELETE FROM users WHERE organization_id = :id"), {"id": organization_id})
            connection.execute(text("DELETE FROM organizations WHERE id = :id"), {"id": organization_id})

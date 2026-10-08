"""Add eligible teacher channels, idempotent messages and private read state."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "communication_threads",
        sa.Column("teacher_employee_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_communication_threads_teacher_employee_id_employees",
        "communication_threads", "employees", ["teacher_employee_id"], ["id"],
    )
    op.drop_index("uq_communication_threads_direct", table_name="communication_threads")
    op.create_index(
        "uq_communication_threads_direct_teacher", "communication_threads",
        ["organization_id", "group_id", "child_id", "guardian_id", "teacher_employee_id"], unique=True,
        postgresql_where=sa.text("thread_type = 'direct' AND teacher_employee_id IS NOT NULL"),
    )
    op.drop_constraint("ck_communication_threads_context", "communication_threads", type_="check")
    op.create_check_constraint(
        "ck_communication_threads_context", "communication_threads",
        "(thread_type = 'group' AND child_id IS NULL AND guardian_id IS NULL AND teacher_employee_id IS NULL) OR "
        "(thread_type = 'direct' AND child_id IS NOT NULL AND guardian_id IS NOT NULL)",
    )

    op.add_column(
        "communication_messages",
        sa.Column("client_message_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "uq_communication_messages_sender_client_id", "communication_messages",
        ["organization_id", "sender_user_id", "client_message_id"], unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
    )
    op.drop_index("ix_communication_messages_organization_thread_created", table_name="communication_messages")
    op.create_index(
        "ix_communication_messages_organization_thread_created", "communication_messages",
        ["organization_id", "thread_id", "created_at", "id"],
    )

    op.create_table(
        "communication_read_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("last_read_message_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["thread_id"], ["communication_threads.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["last_read_message_id"], ["communication_messages.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_communication_read_state_user_thread", "communication_read_states",
        ["organization_id", "thread_id", "user_id"], unique=True,
    )
    op.create_index(
        "ix_communication_read_state_organization_user", "communication_read_states",
        ["organization_id", "user_id"],
    )

    op.add_column("announcements", sa.Column("audience", sa.String(length=16), server_default="all", nullable=False))
    op.create_check_constraint("ck_announcements_audience", "announcements", "audience IN ('all', 'parents', 'staff')")
    op.create_table(
        "announcement_read_states",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("announcement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"]),
        sa.ForeignKeyConstraint(["announcement_id"], ["announcements.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_announcement_read_state_user_announcement", "announcement_read_states",
        ["organization_id", "announcement_id", "user_id"], unique=True,
    )
    op.create_index(
        "ix_announcement_read_state_organization_user", "announcement_read_states",
        ["organization_id", "user_id"],
    )

    # Preserve notification history while ensuring one active unread signal per thread/announcement.
    op.execute(sa.text("""
        WITH ranked AS (
            SELECT id, row_number() OVER (
                PARTITION BY organization_id, recipient_user_id, entity_id
                ORDER BY created_at, id
            ) AS ordinal
            FROM notifications
            WHERE read_at IS NULL AND entity_id IS NOT NULL
              AND kind = 'communication.message' AND entity_type = 'communication_thread'
        )
        UPDATE notifications AS n SET read_at = now()
        FROM ranked AS r WHERE n.id = r.id AND r.ordinal > 1
    """))
    op.execute(sa.text("""
        WITH ranked AS (
            SELECT id, row_number() OVER (
                PARTITION BY organization_id, recipient_user_id, entity_id
                ORDER BY created_at, id
            ) AS ordinal
            FROM notifications
            WHERE read_at IS NULL AND entity_id IS NOT NULL
              AND kind = 'announcement.published' AND entity_type = 'announcement'
        )
        UPDATE notifications AS n SET read_at = now()
        FROM ranked AS r WHERE n.id = r.id AND r.ordinal > 1
    """))
    op.create_index(
        "uq_notifications_unread_communication_thread", "notifications",
        ["organization_id", "recipient_user_id", "entity_id"], unique=True,
        postgresql_where=sa.text(
            "read_at IS NULL AND kind = 'communication.message' AND "
            "entity_type = 'communication_thread' AND entity_id IS NOT NULL"
        ),
    )
    op.create_index(
        "uq_notifications_unread_announcement", "notifications",
        ["organization_id", "recipient_user_id", "entity_id"], unique=True,
        postgresql_where=sa.text(
            "read_at IS NULL AND kind = 'announcement.published' AND "
            "entity_type = 'announcement' AND entity_id IS NOT NULL"
        ),
    )


def downgrade() -> None:
    connection = op.get_bind()
    has_v2_state = connection.execute(sa.text("""
        SELECT
            EXISTS (SELECT 1 FROM communication_threads WHERE teacher_employee_id IS NOT NULL)
            OR EXISTS (SELECT 1 FROM communication_messages WHERE client_message_id IS NOT NULL)
            OR EXISTS (SELECT 1 FROM communication_read_states)
            OR EXISTS (SELECT 1 FROM announcement_read_states)
            OR EXISTS (SELECT 1 FROM announcements WHERE audience <> 'all')
            OR EXISTS (
                SELECT 1 FROM notifications
                WHERE kind = 'announcement.published' AND entity_type = 'announcement'
            )
    """)).scalar_one()
    if has_v2_state:
        raise RuntimeError(
            "Refusing to remove Communications v2 data: downgrade would broaden direct-chat access "
            "or erase idempotency/audience/read state."
        )
    op.drop_index("uq_notifications_unread_announcement", table_name="notifications")
    op.drop_index("uq_notifications_unread_communication_thread", table_name="notifications")
    op.drop_index("ix_announcement_read_state_organization_user", table_name="announcement_read_states")
    op.drop_index("uq_announcement_read_state_user_announcement", table_name="announcement_read_states")
    op.drop_table("announcement_read_states")
    op.drop_constraint("ck_announcements_audience", "announcements", type_="check")
    op.drop_column("announcements", "audience")
    op.drop_index("ix_communication_read_state_organization_user", table_name="communication_read_states")
    op.drop_index("uq_communication_read_state_user_thread", table_name="communication_read_states")
    op.drop_table("communication_read_states")
    op.drop_index("ix_communication_messages_organization_thread_created", table_name="communication_messages")
    op.create_index(
        "ix_communication_messages_organization_thread_created", "communication_messages",
        ["organization_id", "thread_id", "created_at"],
    )
    op.drop_index("uq_communication_messages_sender_client_id", table_name="communication_messages")
    op.drop_column("communication_messages", "client_message_id")
    op.drop_constraint("ck_communication_threads_context", "communication_threads", type_="check")
    op.create_check_constraint(
        "ck_communication_threads_context", "communication_threads",
        "(thread_type = 'group' AND child_id IS NULL AND guardian_id IS NULL) OR "
        "(thread_type = 'direct' AND child_id IS NOT NULL AND guardian_id IS NOT NULL)",
    )
    op.drop_index("uq_communication_threads_direct_teacher", table_name="communication_threads")
    op.create_index(
        "uq_communication_threads_direct", "communication_threads", ["group_id", "child_id", "guardian_id"],
        unique=True, postgresql_where=sa.text("thread_type = 'direct'"),
    )
    op.drop_constraint("fk_communication_threads_teacher_employee_id_employees", "communication_threads", type_="foreignkey")
    op.drop_column("communication_threads", "teacher_employee_id")

"""Stage 6 teacher identity and complete domain schema. Revision ID: 0012; down_revision: 0011."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('DIRECTOR', 'ADMIN', 'TEACHER', 'PARENT')")

    op.create_table(
        "teacher_group_assignments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("assigned_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("archived_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_teacher_group_assignments_status"),
        sa.UniqueConstraint("employee_id", "group_id", name="uq_teacher_group_assignments_employee_group"),
    )
    op.create_index("ix_teacher_group_assignments_organization_employee_status", "teacher_group_assignments", ["organization_id", "employee_id", "status"])
    op.create_index("ix_teacher_group_assignments_organization_group_status", "teacher_group_assignments", ["organization_id", "group_id", "status"])

    op.create_table(
        "group_schedule_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("weekday", sa.Integer(), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False), sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("weekday BETWEEN 0 AND 6", name="ck_group_schedule_items_weekday"),
        sa.CheckConstraint("end_time > start_time", name="ck_group_schedule_items_time_order"),
        sa.CheckConstraint("status IN ('active', 'archived')", name="ck_group_schedule_items_status"),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_group_schedule_items_title_nonempty"),
    )
    op.create_index("ix_group_schedule_items_organization_group_status", "group_schedule_items", ["organization_id", "group_id", "status"])

    op.create_table(
        "communication_threads",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("thread_type", sa.String(16), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id")),
        sa.Column("guardian_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("guardians.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("thread_type IN ('group', 'direct')", name="ck_communication_threads_type"),
        sa.CheckConstraint("(thread_type = 'group' AND child_id IS NULL AND guardian_id IS NULL) OR (thread_type = 'direct' AND child_id IS NOT NULL AND guardian_id IS NOT NULL)", name="ck_communication_threads_context"),
    )
    op.create_index("ix_communication_threads_organization_group", "communication_threads", ["organization_id", "group_id"])
    op.create_index("uq_communication_threads_group", "communication_threads", ["group_id"], unique=True, postgresql_where=sa.text("thread_type = 'group'"))
    op.create_index("uq_communication_threads_direct", "communication_threads", ["group_id", "child_id", "guardian_id"], unique=True, postgresql_where=sa.text("thread_type = 'direct'"))

    op.create_table(
        "communication_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("thread_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("communication_threads.id"), nullable=False),
        sa.Column("sender_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("body", sa.String(4000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(btrim(body)) > 0", name="ck_communication_messages_body_nonempty"),
    )
    op.create_index("ix_communication_messages_organization_thread_created", "communication_messages", ["organization_id", "thread_id", "created_at"])

    op.create_table(
        "child_diary_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("author_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("note", sa.String(4000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(btrim(note)) > 0", name="ck_child_diary_entries_note_nonempty"),
    )
    op.create_index("ix_child_diary_entries_organization_child_date", "child_diary_entries", ["organization_id", "child_id", "date"])

    op.create_table(
        "polls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("question", sa.String(500), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("closes_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('active', 'closed', 'archived')", name="ck_polls_status"),
        sa.CheckConstraint("length(btrim(question)) > 0", name="ck_polls_question_nonempty"),
    )
    op.create_index("ix_polls_organization_group_status", "polls", ["organization_id", "group_id", "status"])
    op.create_table(
        "poll_options",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("polls.id"), nullable=False),
        sa.Column("label", sa.String(240), nullable=False), sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.CheckConstraint("length(btrim(label)) > 0", name="ck_poll_options_label_nonempty"),
        sa.UniqueConstraint("poll_id", "sort_order", name="uq_poll_options_poll_sort_order"),
    )
    op.create_table(
        "poll_votes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("poll_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("polls.id"), nullable=False),
        sa.Column("option_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("poll_options.id"), nullable=False),
        sa.Column("voter_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("poll_id", "voter_user_id", name="uq_poll_votes_poll_voter"),
    )
    op.create_index("ix_poll_votes_organization_poll", "poll_votes", ["organization_id", "poll_id"])

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id")),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("category", sa.String(16), nullable=False), sa.Column("description", sa.String(4000), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("reported_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("resolved_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("category IN ('safety', 'behavior', 'operational', 'other')", name="ck_incidents_category"),
        sa.CheckConstraint("status IN ('open', 'resolved')", name="ck_incidents_status"),
        sa.CheckConstraint("length(btrim(description)) > 0", name="ck_incidents_description_nonempty"),
    )
    op.create_index("ix_incidents_organization_group_status", "incidents", ["organization_id", "group_id", "status"])

    op.create_table(
        "teacher_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("assignee_employee_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("employees.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id")),
        sa.Column("title", sa.String(240), nullable=False), sa.Column("description", sa.String(4000)),
        sa.Column("due_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(16), nullable=False, server_default="open"),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('open', 'in_progress', 'done', 'cancelled')", name="ck_teacher_tasks_status"),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_teacher_tasks_title_nonempty"),
    )
    op.create_index("ix_teacher_tasks_organization_assignee_status", "teacher_tasks", ["organization_id", "assignee_employee_id", "status"])
    op.create_index("ix_teacher_tasks_organization_group", "teacher_tasks", ["organization_id", "group_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False), sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True)), sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_notifications_organization_recipient_read", "notifications", ["organization_id", "recipient_user_id", "read_at"])

    op.create_table(
        "document_notices",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("recipient_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("title", sa.String(240), nullable=False), sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("requires_ack", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("issued_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("length(btrim(title)) > 0", name="ck_document_notices_title_nonempty"),
    )
    op.create_index("ix_document_notices_organization_recipient_created", "document_notices", ["organization_id", "recipient_user_id", "created_at"])

    op.create_table(
        "photo_consents",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("scope", sa.String(32), nullable=False, server_default="group_photo_report"),
        sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_to", sa.DateTime(timezone=True)),
        sa.Column("recorded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('granted', 'withdrawn')", name="ck_photo_consents_status"),
        sa.CheckConstraint("scope = 'group_photo_report'", name="ck_photo_consents_scope"),
        sa.UniqueConstraint("child_id", "scope", name="uq_photo_consents_child_scope"),
    )
    op.create_index("ix_photo_consents_organization_child_status", "photo_consents", ["organization_id", "child_id", "status"])

    op.create_table(
        "photo_assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("group_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("groups.id"), nullable=False),
        sa.Column("storage_key", sa.String(512), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(100), nullable=False), sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True)),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("status", sa.String(16), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("size_bytes > 0", name="ck_photo_assets_size_positive"),
        sa.CheckConstraint("status IN ('active', 'restricted', 'removed')", name="ck_photo_assets_status"),
    )
    op.create_index("ix_photo_assets_organization_group_status", "photo_assets", ["organization_id", "group_id", "status"])

    op.create_table(
        "photo_asset_children",
        sa.Column("organization_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id"), primary_key=True),
        sa.Column("photo_asset_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("photo_assets.id"), primary_key=True),
        sa.Column("child_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("children.id"), primary_key=True),
        sa.UniqueConstraint("photo_asset_id", "child_id", name="uq_photo_asset_children_asset_child"),
    )
    op.create_index("ix_photo_asset_children_organization_child", "photo_asset_children", ["organization_id", "child_id"])


def downgrade() -> None:
    op.drop_index("ix_photo_asset_children_organization_child", table_name="photo_asset_children")
    op.drop_table("photo_asset_children")
    op.drop_index("ix_photo_assets_organization_group_status", table_name="photo_assets")
    op.drop_table("photo_assets")
    op.drop_index("ix_photo_consents_organization_child_status", table_name="photo_consents")
    op.drop_table("photo_consents")
    op.drop_index("ix_document_notices_organization_recipient_created", table_name="document_notices")
    op.drop_table("document_notices")
    op.drop_index("ix_notifications_organization_recipient_read", table_name="notifications")
    op.drop_table("notifications")
    op.drop_index("ix_teacher_tasks_organization_group", table_name="teacher_tasks")
    op.drop_index("ix_teacher_tasks_organization_assignee_status", table_name="teacher_tasks")
    op.drop_table("teacher_tasks")
    op.drop_index("ix_incidents_organization_group_status", table_name="incidents")
    op.drop_table("incidents")
    op.drop_index("ix_poll_votes_organization_poll", table_name="poll_votes")
    op.drop_table("poll_votes")
    op.drop_table("poll_options")
    op.drop_index("ix_polls_organization_group_status", table_name="polls")
    op.drop_table("polls")
    op.drop_index("ix_child_diary_entries_organization_child_date", table_name="child_diary_entries")
    op.drop_table("child_diary_entries")
    op.drop_index("ix_communication_messages_organization_thread_created", table_name="communication_messages")
    op.drop_table("communication_messages")
    op.drop_index("uq_communication_threads_direct", table_name="communication_threads")
    op.drop_index("uq_communication_threads_group", table_name="communication_threads")
    op.drop_index("ix_communication_threads_organization_group", table_name="communication_threads")
    op.drop_table("communication_threads")
    op.drop_index("ix_group_schedule_items_organization_group_status", table_name="group_schedule_items")
    op.drop_table("group_schedule_items")
    op.drop_index("ix_teacher_group_assignments_organization_group_status", table_name="teacher_group_assignments")
    op.drop_index("ix_teacher_group_assignments_organization_employee_status", table_name="teacher_group_assignments")
    op.drop_table("teacher_group_assignments")
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('DIRECTOR', 'ADMIN', 'PARENT')")

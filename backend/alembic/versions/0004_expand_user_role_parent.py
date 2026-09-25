"""Allow PARENT users. Revision ID: 0004; down_revision: 0003."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_constraint("users_role_check", "users", type_="check")
    op.create_check_constraint("ck_users_role", "users", "role IN ('DIRECTOR', 'ADMIN', 'PARENT')")


def downgrade() -> None:
    # A PARENT account cannot satisfy the old constraint; fail without deleting data.
    op.drop_constraint("ck_users_role", "users", type_="check")
    op.create_check_constraint("users_role_check", "users", "role IN ('DIRECTOR', 'ADMIN')")

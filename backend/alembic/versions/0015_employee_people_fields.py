"""Add employee business category and optional contact fields. Revision: 0015."""

import sqlalchemy as sa

from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("employees", sa.Column("category", sa.String(length=16), nullable=True))
    op.add_column("employees", sa.Column("phone", sa.String(length=32), nullable=True))
    op.add_column("employees", sa.Column("email", sa.String(length=254), nullable=True))
    op.execute(
        """
        UPDATE employees AS employee
        SET category = CASE
            WHEN EXISTS (
                SELECT 1 FROM users AS linked_user
                WHERE linked_user.id = employee.user_id AND linked_user.role = 'TEACHER'
            ) THEN 'teacher'
            WHEN EXISTS (
                SELECT 1 FROM users AS linked_user
                WHERE linked_user.id = employee.user_id AND linked_user.role = 'ADMIN'
            ) THEN 'administrator'
            ELSE 'other'
        END
        """
    )
    op.alter_column("employees", "category", nullable=False)
    op.create_check_constraint(
        "ck_employees_category", "employees", "category IN ('teacher', 'administrator', 'other')",
    )
    op.create_index(
        "ix_employees_organization_status_category", "employees",
        ["organization_id", "status", "category"],
    )


def downgrade() -> None:
    op.drop_index("ix_employees_organization_status_category", table_name="employees")
    op.drop_constraint("ck_employees_category", "employees", type_="check")
    op.drop_column("employees", "email")
    op.drop_column("employees", "phone")
    op.drop_column("employees", "category")

"""admin auth domain tables

Revision ID: 20260415_09
Revises: 20260415_08
Create Date: 2026-04-15 14:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260415_09"
down_revision: str | None = "20260415_08"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "admin_user",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="ops_admin"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("email", name="uq_admin_user_email"),
        sa.UniqueConstraint("username", name="uq_admin_user_username"),
    )
    op.create_index("ix_admin_user_email", "admin_user", ["email"])
    op.create_index("ix_admin_user_username", "admin_user", ["username"])
    op.create_index("ix_admin_user_role", "admin_user", ["role"])

    op.create_table(
        "operation_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("request_path", sa.String(length=255), nullable=True),
        sa.Column("request_method", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="success"),
        sa.Column("detail_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["admin_user.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_operation_log_admin_user_id", "operation_log", ["admin_user_id"])
    op.create_index("ix_operation_log_action", "operation_log", ["action"])


def downgrade() -> None:
    op.drop_index("ix_operation_log_action", table_name="operation_log")
    op.drop_index("ix_operation_log_admin_user_id", table_name="operation_log")
    op.drop_table("operation_log")
    op.drop_index("ix_admin_user_role", table_name="admin_user")
    op.drop_index("ix_admin_user_username", table_name="admin_user")
    op.drop_index("ix_admin_user_email", table_name="admin_user")
    op.drop_table("admin_user")

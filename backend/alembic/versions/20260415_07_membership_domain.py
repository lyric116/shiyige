"""membership domain tables

Revision ID: 20260415_07
Revises: 20260414_06
Create Date: 2026-04-15 10:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260415_07"
down_revision: str | None = "20260414_06"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "member_level",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("level_order", sa.Integer(), nullable=False),
        sa.Column("min_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discount_rate", sa.Numeric(4, 2), nullable=False),
        sa.Column("points_rate", sa.Numeric(4, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("code", name="uq_member_level_code"),
        sa.UniqueConstraint("name", name="uq_member_level_name"),
        sa.UniqueConstraint("level_order", name="uq_member_level_level_order"),
    )
    op.create_index("ix_member_level_code", "member_level", ["code"])
    op.create_index("ix_member_level_level_order", "member_level", ["level_order"])

    op.create_table(
        "point_account",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("member_level_id", sa.Integer(), nullable=False),
        sa.Column("points_balance", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("lifetime_points", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_spent_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["member_level_id"], ["member_level.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_point_account_user_id"),
    )
    op.create_index("ix_point_account_user_id", "point_account", ["user_id"])
    op.create_index("ix_point_account_member_level_id", "point_account", ["member_level_id"])

    op.create_table(
        "point_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("point_account_id", sa.Integer(), nullable=False),
        sa.Column("change_type", sa.String(length=50), nullable=False),
        sa.Column("change_amount", sa.Integer(), nullable=False),
        sa.Column("balance_after", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=True),
        sa.Column("source_id", sa.Integer(), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("ext_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["point_account_id"], ["point_account.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_point_log_point_account_id", "point_log", ["point_account_id"])
    op.create_index("ix_point_log_change_type", "point_log", ["change_type"])
    op.create_index("ix_point_log_source_type", "point_log", ["source_type"])


def downgrade() -> None:
    op.drop_index("ix_point_log_source_type", table_name="point_log")
    op.drop_index("ix_point_log_change_type", table_name="point_log")
    op.drop_index("ix_point_log_point_account_id", table_name="point_log")
    op.drop_table("point_log")
    op.drop_index("ix_point_account_member_level_id", table_name="point_account")
    op.drop_index("ix_point_account_user_id", table_name="point_account")
    op.drop_table("point_account")
    op.drop_index("ix_member_level_level_order", table_name="member_level")
    op.drop_index("ix_member_level_code", table_name="member_level")
    op.drop_table("member_level")

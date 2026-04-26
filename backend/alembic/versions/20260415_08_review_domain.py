"""review domain tables

Revision ID: 20260415_08
Revises: 20260415_07
Create Date: 2026-04-15 12:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260415_08"
down_revision: str | None = "20260415_07"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "review",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("is_anonymous", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "product_id", name="uq_review_user_id_product_id"),
    )
    op.create_index("ix_review_user_id", "review", ["user_id"])
    op.create_index("ix_review_product_id", "review", ["product_id"])
    op.create_index("ix_review_order_id", "review", ["order_id"])

    op.create_table(
        "review_image",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("review_id", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["review_id"], ["review.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_review_image_review_id", "review_image", ["review_id"])


def downgrade() -> None:
    op.drop_index("ix_review_image_review_id", table_name="review_image")
    op.drop_table("review_image")
    op.drop_index("ix_review_order_id", table_name="review")
    op.drop_index("ix_review_product_id", table_name="review")
    op.drop_index("ix_review_user_id", table_name="review")
    op.drop_table("review")

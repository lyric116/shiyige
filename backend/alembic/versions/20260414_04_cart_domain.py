"""cart domain tables

Revision ID: 20260414_04
Revises: 20260414_03
Create Date: 2026-04-14 03:10:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260414_04"
down_revision: str | None = "20260414_03"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cart",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_cart_user_id"),
    )
    op.create_index("ix_cart_user_id", "cart", ["user_id"])

    op.create_table(
        "cart_item",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cart_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["cart_id"], ["cart.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["sku_id"], ["product_sku.id"]),
        sa.UniqueConstraint("cart_id", "sku_id", name="uq_cart_item_cart_id_sku_id"),
    )
    op.create_index("ix_cart_item_cart_id", "cart_item", ["cart_id"])
    op.create_index("ix_cart_item_product_id", "cart_item", ["product_id"])
    op.create_index("ix_cart_item_sku_id", "cart_item", ["sku_id"])


def downgrade() -> None:
    op.drop_index("ix_cart_item_sku_id", table_name="cart_item")
    op.drop_index("ix_cart_item_product_id", table_name="cart_item")
    op.drop_index("ix_cart_item_cart_id", table_name="cart_item")
    op.drop_table("cart_item")
    op.drop_index("ix_cart_user_id", table_name="cart")
    op.drop_table("cart")

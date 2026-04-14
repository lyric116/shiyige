"""order domain tables

Revision ID: 20260414_05
Revises: 20260414_04
Create Date: 2026-04-14 05:30:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260414_05"
down_revision: str | None = "20260414_04"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_no", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING_PAYMENT"),
        sa.Column("goods_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("shipping_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
        sa.Column("payable_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("recipient_name", sa.String(length=100), nullable=False),
        sa.Column("recipient_phone", sa.String(length=20), nullable=False),
        sa.Column("recipient_region", sa.String(length=100), nullable=False),
        sa.Column("recipient_detail_address", sa.String(length=255), nullable=False),
        sa.Column("recipient_postal_code", sa.String(length=20), nullable=True),
        sa.Column("buyer_note", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=100), nullable=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.UniqueConstraint("idempotency_key", name="uq_orders_idempotency_key"),
        sa.UniqueConstraint("order_no", name="uq_orders_order_no"),
    )
    op.create_index("ix_orders_order_no", "orders", ["order_no"])
    op.create_index("ix_orders_user_id", "orders", ["user_id"])
    op.create_index("ix_orders_idempotency_key", "orders", ["idempotency_key"])

    op.create_table(
        "order_item",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("sku_name", sa.String(length=200), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("unit_member_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("subtotal_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["sku_id"], ["product_sku.id"]),
    )
    op.create_index("ix_order_item_order_id", "order_item", ["order_id"])
    op.create_index("ix_order_item_product_id", "order_item", ["product_id"])
    op.create_index("ix_order_item_sku_id", "order_item", ["sku_id"])

    op.create_table(
        "payment_record",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("payment_no", sa.String(length=64), nullable=False),
        sa.Column("payment_method", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("payment_no", name="uq_payment_record_payment_no"),
    )
    op.create_index("ix_payment_record_order_id", "payment_record", ["order_id"])
    op.create_index("ix_payment_record_payment_no", "payment_record", ["payment_no"])


def downgrade() -> None:
    op.drop_index("ix_payment_record_payment_no", table_name="payment_record")
    op.drop_index("ix_payment_record_order_id", table_name="payment_record")
    op.drop_table("payment_record")
    op.drop_index("ix_order_item_sku_id", table_name="order_item")
    op.drop_index("ix_order_item_product_id", table_name="order_item")
    op.drop_index("ix_order_item_order_id", table_name="order_item")
    op.drop_table("order_item")
    op.drop_index("ix_orders_idempotency_key", table_name="orders")
    op.drop_index("ix_orders_user_id", table_name="orders")
    op.drop_index("ix_orders_order_no", table_name="orders")
    op.drop_table("orders")

"""product domain tables

Revision ID: 20260414_03
Revises: 20260413_02
Create Date: 2026-04-14 01:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260414_03"
down_revision: str | None = "20260413_02"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "category",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("name", name="uq_category_name"),
        sa.UniqueConstraint("slug", name="uq_category_slug"),
    )
    op.create_index("ix_category_name", "category", ["name"])
    op.create_index("ix_category_slug", "category", ["slug"])

    op.create_table(
        "product",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("subtitle", sa.String(length=255), nullable=True),
        sa.Column("cover_url", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("culture_summary", sa.Text(), nullable=True),
        sa.Column("dynasty_style", sa.String(length=100), nullable=True),
        sa.Column("craft_type", sa.String(length=100), nullable=True),
        sa.Column("festival_tag", sa.String(length=100), nullable=True),
        sa.Column("scene_tag", sa.String(length=100), nullable=True),
        sa.Column("status", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["category.id"]),
    )
    op.create_index("ix_product_category_id", "product", ["category_id"])
    op.create_index("ix_product_name", "product", ["name"])

    op.create_table(
        "product_sku",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("sku_code", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("specs_json", sa.JSON(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("member_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("sku_code", name="uq_product_sku_sku_code"),
    )
    op.create_index("ix_product_sku_product_id", "product_sku", ["product_id"])
    op.create_index("ix_product_sku_sku_code", "product_sku", ["sku_code"])

    op.create_table(
        "product_media",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False, server_default="image"),
        sa.Column("url", sa.String(length=255), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_product_media_product_id", "product_media", ["product_id"])

    op.create_table(
        "product_tag",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("tag", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_product_tag_product_id", "product_tag", ["product_id"])
    op.create_index("ix_product_tag_tag", "product_tag", ["tag"])

    op.create_table(
        "inventory",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("sku_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["sku_id"], ["product_sku.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("sku_id", name="uq_inventory_sku_id"),
    )
    op.create_index("ix_inventory_sku_id", "inventory", ["sku_id"])


def downgrade() -> None:
    op.drop_index("ix_inventory_sku_id", table_name="inventory")
    op.drop_table("inventory")
    op.drop_index("ix_product_tag_tag", table_name="product_tag")
    op.drop_index("ix_product_tag_product_id", table_name="product_tag")
    op.drop_table("product_tag")
    op.drop_index("ix_product_media_product_id", table_name="product_media")
    op.drop_table("product_media")
    op.drop_index("ix_product_sku_sku_code", table_name="product_sku")
    op.drop_index("ix_product_sku_product_id", table_name="product_sku")
    op.drop_table("product_sku")
    op.drop_index("ix_product_name", table_name="product")
    op.drop_index("ix_product_category_id", table_name="product")
    op.drop_table("product")
    op.drop_index("ix_category_slug", table_name="category")
    op.drop_index("ix_category_name", table_name="category")
    op.drop_table("category")

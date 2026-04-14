"""embedding domain tables

Revision ID: 20260414_06
Revises: 20260414_05
Create Date: 2026-04-14 08:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260414_06"
down_revision: str | None = "20260414_05"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_embedding",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("embedding_text", sa.Text(), nullable=False),
        sa.Column("embedding_vector", sa.JSON(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("last_indexed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", name="uq_product_embedding_product_id"),
    )
    op.create_index("ix_product_embedding_product_id", "product_embedding", ["product_id"])
    op.create_index("ix_product_embedding_model_name", "product_embedding", ["model_name"])
    op.create_index("ix_product_embedding_content_hash", "product_embedding", ["content_hash"])

    op.create_table(
        "user_interest_profile",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("model_name", sa.String(length=100), nullable=False),
        sa.Column("profile_text", sa.Text(), nullable=True),
        sa.Column("embedding_vector", sa.JSON(), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("behavior_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_event_at", sa.DateTime(), nullable=True),
        sa.Column("last_built_at", sa.DateTime(), nullable=True),
        sa.Column("ext_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_user_interest_profile_user_id"),
    )
    op.create_index("ix_user_interest_profile_user_id", "user_interest_profile", ["user_id"])
    op.create_index("ix_user_interest_profile_model_name", "user_interest_profile", ["model_name"])
    op.create_index("ix_user_interest_profile_content_hash", "user_interest_profile", ["content_hash"])


def downgrade() -> None:
    op.drop_index("ix_user_interest_profile_content_hash", table_name="user_interest_profile")
    op.drop_index("ix_user_interest_profile_model_name", table_name="user_interest_profile")
    op.drop_index("ix_user_interest_profile_user_id", table_name="user_interest_profile")
    op.drop_table("user_interest_profile")
    op.drop_index("ix_product_embedding_content_hash", table_name="product_embedding")
    op.drop_index("ix_product_embedding_model_name", table_name="product_embedding")
    op.drop_index("ix_product_embedding_product_id", table_name="product_embedding")
    op.drop_table("product_embedding")

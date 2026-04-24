"""qdrant vector metadata

Revision ID: 20260424_10
Revises: 20260415_09
Create Date: 2026-04-24 23:30:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260424_10"
down_revision: str | None = "20260415_09"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "product_embedding",
        sa.Column("qdrant_point_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "product_embedding",
        sa.Column("qdrant_collection", sa.String(length=120), nullable=True),
    )
    op.add_column(
        "product_embedding",
        sa.Column(
            "index_status",
            sa.String(length=32),
            nullable=False,
            server_default="pending",
        ),
    )
    op.add_column(
        "product_embedding",
        sa.Column("index_error", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_product_embedding_qdrant_point_id",
        "product_embedding",
        ["qdrant_point_id"],
    )
    op.create_index(
        "ix_product_embedding_qdrant_collection",
        "product_embedding",
        ["qdrant_collection"],
    )
    op.create_index("ix_product_embedding_index_status", "product_embedding", ["index_status"])

    op.add_column(
        "user_interest_profile",
        sa.Column("qdrant_user_point_id", sa.String(length=128), nullable=True),
    )
    op.add_column(
        "user_interest_profile",
        sa.Column("profile_version", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "user_interest_profile",
        sa.Column("last_synced_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_user_interest_profile_qdrant_user_point_id",
        "user_interest_profile",
        ["qdrant_user_point_id"],
    )
    op.create_index(
        "ix_user_interest_profile_profile_version",
        "user_interest_profile",
        ["profile_version"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_user_interest_profile_profile_version",
        table_name="user_interest_profile",
    )
    op.drop_index(
        "ix_user_interest_profile_qdrant_user_point_id",
        table_name="user_interest_profile",
    )
    op.drop_column("user_interest_profile", "last_synced_at")
    op.drop_column("user_interest_profile", "profile_version")
    op.drop_column("user_interest_profile", "qdrant_user_point_id")

    op.drop_index("ix_product_embedding_index_status", table_name="product_embedding")
    op.drop_index("ix_product_embedding_qdrant_collection", table_name="product_embedding")
    op.drop_index("ix_product_embedding_qdrant_point_id", table_name="product_embedding")
    op.drop_column("product_embedding", "index_error")
    op.drop_column("product_embedding", "index_status")
    op.drop_column("product_embedding", "qdrant_collection")
    op.drop_column("product_embedding", "qdrant_point_id")

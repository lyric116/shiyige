"""recommendation and search logging tables

Revision ID: 20260424_12
Revises: 20260424_11
Create Date: 2026-04-24 18:20:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260424_12"
down_revision: str | None = "20260424_11"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def _create_index_if_missing(
    index_name: str,
    table_name: str,
    columns: list[str],
    *,
    unique: bool = False,
) -> None:
    if not _index_exists(table_name, index_name):
        op.create_index(index_name, table_name, columns, unique=unique)


def upgrade() -> None:
    if not _table_exists("recommendation_request_log"):
        op.create_table(
            "recommendation_request_log",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("slot", sa.String(length=50), nullable=False),
            sa.Column("pipeline_version", sa.String(length=64), nullable=False),
            sa.Column("model_version", sa.String(length=64), nullable=False),
            sa.Column("candidate_count", sa.Integer(), nullable=False),
            sa.Column("final_product_ids", sa.JSON(), nullable=True),
            sa.Column("latency_ms", sa.Float(), nullable=False),
            sa.Column("fallback_used", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_request_log")),
            sa.UniqueConstraint(
                "request_id", name=op.f("uq_recommendation_request_log_request_id")
            ),
        )
    _create_index_if_missing(
        op.f("ix_recommendation_request_log_request_id"),
        "recommendation_request_log",
        ["request_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_request_log_user_id"),
        "recommendation_request_log",
        ["user_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_request_log_slot"),
        "recommendation_request_log",
        ["slot"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_request_log_pipeline_version"),
        "recommendation_request_log",
        ["pipeline_version"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_request_log_model_version"),
        "recommendation_request_log",
        ["model_version"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_request_log_fallback_used"),
        "recommendation_request_log",
        ["fallback_used"],
        unique=False,
    )

    if not _table_exists("recommendation_impression_log"):
        op.create_table(
            "recommendation_impression_log",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("rank_position", sa.Integer(), nullable=False),
            sa.Column("recall_channels", sa.JSON(), nullable=True),
            sa.Column("final_score", sa.Float(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_impression_log")),
        )
    _create_index_if_missing(
        op.f("ix_recommendation_impression_log_request_id"),
        "recommendation_impression_log",
        ["request_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_impression_log_user_id"),
        "recommendation_impression_log",
        ["user_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_impression_log_product_id"),
        "recommendation_impression_log",
        ["product_id"],
        unique=False,
    )

    if not _table_exists("recommendation_click_log"):
        op.create_table(
            "recommendation_click_log",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("action_type", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_click_log")),
        )
    _create_index_if_missing(
        op.f("ix_recommendation_click_log_request_id"),
        "recommendation_click_log",
        ["request_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_click_log_user_id"),
        "recommendation_click_log",
        ["user_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_click_log_product_id"),
        "recommendation_click_log",
        ["product_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_click_log_action_type"),
        "recommendation_click_log",
        ["action_type"],
        unique=False,
    )

    if not _table_exists("recommendation_conversion_log"):
        op.create_table(
            "recommendation_conversion_log",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("order_id", sa.Integer(), nullable=True),
            sa.Column("action_type", sa.String(length=50), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_conversion_log")),
        )
    _create_index_if_missing(
        op.f("ix_recommendation_conversion_log_request_id"),
        "recommendation_conversion_log",
        ["request_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_conversion_log_user_id"),
        "recommendation_conversion_log",
        ["user_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_conversion_log_product_id"),
        "recommendation_conversion_log",
        ["product_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_conversion_log_order_id"),
        "recommendation_conversion_log",
        ["order_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_recommendation_conversion_log_action_type"),
        "recommendation_conversion_log",
        ["action_type"],
        unique=False,
    )

    if not _table_exists("search_request_log"):
        op.create_table(
            "search_request_log",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("query", sa.String(length=255), nullable=False),
            sa.Column("mode", sa.String(length=32), nullable=False),
            sa.Column("pipeline_version", sa.String(length=64), nullable=False),
            sa.Column("total_results", sa.Integer(), nullable=False),
            sa.Column("latency_ms", sa.Float(), nullable=False),
            sa.Column("filters_json", sa.JSON(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_search_request_log")),
            sa.UniqueConstraint("request_id", name=op.f("uq_search_request_log_request_id")),
        )
    _create_index_if_missing(
        op.f("ix_search_request_log_request_id"),
        "search_request_log",
        ["request_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_search_request_log_user_id"),
        "search_request_log",
        ["user_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_search_request_log_query"),
        "search_request_log",
        ["query"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_search_request_log_mode"),
        "search_request_log",
        ["mode"],
        unique=False,
    )

    if not _table_exists("search_result_log"):
        op.create_table(
            "search_result_log",
            sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
            sa.Column("request_id", sa.String(length=64), nullable=False),
            sa.Column("product_id", sa.Integer(), nullable=False),
            sa.Column("rank_position", sa.Integer(), nullable=False),
            sa.Column("score", sa.Float(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_search_result_log")),
        )
    _create_index_if_missing(
        op.f("ix_search_result_log_request_id"),
        "search_result_log",
        ["request_id"],
        unique=False,
    )
    _create_index_if_missing(
        op.f("ix_search_result_log_product_id"),
        "search_result_log",
        ["product_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_search_result_log_product_id"), table_name="search_result_log")
    op.drop_index(op.f("ix_search_result_log_request_id"), table_name="search_result_log")
    op.drop_table("search_result_log")

    op.drop_index(op.f("ix_search_request_log_mode"), table_name="search_request_log")
    op.drop_index(op.f("ix_search_request_log_query"), table_name="search_request_log")
    op.drop_index(op.f("ix_search_request_log_user_id"), table_name="search_request_log")
    op.drop_index(op.f("ix_search_request_log_request_id"), table_name="search_request_log")
    op.drop_table("search_request_log")

    op.drop_index(
        op.f("ix_recommendation_conversion_log_action_type"),
        table_name="recommendation_conversion_log",
    )
    op.drop_index(
        op.f("ix_recommendation_conversion_log_order_id"),
        table_name="recommendation_conversion_log",
    )
    op.drop_index(
        op.f("ix_recommendation_conversion_log_product_id"),
        table_name="recommendation_conversion_log",
    )
    op.drop_index(
        op.f("ix_recommendation_conversion_log_user_id"),
        table_name="recommendation_conversion_log",
    )
    op.drop_index(
        op.f("ix_recommendation_conversion_log_request_id"),
        table_name="recommendation_conversion_log",
    )
    op.drop_table("recommendation_conversion_log")

    op.drop_index(
        op.f("ix_recommendation_click_log_action_type"),
        table_name="recommendation_click_log",
    )
    op.drop_index(
        op.f("ix_recommendation_click_log_product_id"),
        table_name="recommendation_click_log",
    )
    op.drop_index(
        op.f("ix_recommendation_click_log_user_id"),
        table_name="recommendation_click_log",
    )
    op.drop_index(
        op.f("ix_recommendation_click_log_request_id"),
        table_name="recommendation_click_log",
    )
    op.drop_table("recommendation_click_log")

    op.drop_index(
        op.f("ix_recommendation_impression_log_product_id"),
        table_name="recommendation_impression_log",
    )
    op.drop_index(
        op.f("ix_recommendation_impression_log_user_id"),
        table_name="recommendation_impression_log",
    )
    op.drop_index(
        op.f("ix_recommendation_impression_log_request_id"),
        table_name="recommendation_impression_log",
    )
    op.drop_table("recommendation_impression_log")

    op.drop_index(
        op.f("ix_recommendation_request_log_fallback_used"),
        table_name="recommendation_request_log",
    )
    op.drop_index(
        op.f("ix_recommendation_request_log_model_version"),
        table_name="recommendation_request_log",
    )
    op.drop_index(
        op.f("ix_recommendation_request_log_pipeline_version"),
        table_name="recommendation_request_log",
    )
    op.drop_index(
        op.f("ix_recommendation_request_log_slot"),
        table_name="recommendation_request_log",
    )
    op.drop_index(
        op.f("ix_recommendation_request_log_user_id"),
        table_name="recommendation_request_log",
    )
    op.drop_index(
        op.f("ix_recommendation_request_log_request_id"),
        table_name="recommendation_request_log",
    )
    op.drop_table("recommendation_request_log")

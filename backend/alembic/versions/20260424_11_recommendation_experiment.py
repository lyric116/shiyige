"""recommendation experiment metadata

Revision ID: 20260424_11
Revises: 20260424_10
Create Date: 2026-04-24 23:55:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260424_11"
down_revision: str | None = "20260424_10"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendation_experiment",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("experiment_key", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("strategy", sa.String(length=80), nullable=False),
        sa.Column("pipeline_version", sa.String(length=64), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("artifact_json", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_recommendation_experiment")),
        sa.UniqueConstraint(
            "experiment_key",
            name=op.f("uq_recommendation_experiment_experiment_key"),
        ),
    )
    op.create_index(
        op.f("ix_recommendation_experiment_experiment_key"),
        "recommendation_experiment",
        ["experiment_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_experiment_strategy"),
        "recommendation_experiment",
        ["strategy"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_experiment_pipeline_version"),
        "recommendation_experiment",
        ["pipeline_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_experiment_model_version"),
        "recommendation_experiment",
        ["model_version"],
        unique=False,
    )
    op.create_index(
        op.f("ix_recommendation_experiment_is_active"),
        "recommendation_experiment",
        ["is_active"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_recommendation_experiment_is_active"),
        table_name="recommendation_experiment",
    )
    op.drop_index(
        op.f("ix_recommendation_experiment_model_version"),
        table_name="recommendation_experiment",
    )
    op.drop_index(
        op.f("ix_recommendation_experiment_pipeline_version"),
        table_name="recommendation_experiment",
    )
    op.drop_index(
        op.f("ix_recommendation_experiment_strategy"),
        table_name="recommendation_experiment",
    )
    op.drop_index(
        op.f("ix_recommendation_experiment_experiment_key"),
        table_name="recommendation_experiment",
    )
    op.drop_table("recommendation_experiment")

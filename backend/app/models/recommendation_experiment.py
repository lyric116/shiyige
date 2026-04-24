from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.models.base import Base, TimestampMixin


class RecommendationExperiment(TimestampMixin, Base):
    __tablename__ = "recommendation_experiment"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    experiment_key: Mapped[str] = mapped_column(
        String(120),
        unique=True,
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    strategy: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    pipeline_version: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    config_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    artifact_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

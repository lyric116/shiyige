from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from qdrant_client import QdrantClient, models
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.models.recommendation_experiment import RecommendationExperiment
from backend.app.models.user import UserBehaviorLog
from backend.app.services.collaborative_filtering import (
    COLLABORATIVE_ITEM_EXPERIMENT_KEY,
    build_item_cooccurrence_map,
    build_user_sparse_vector,
)
from backend.app.services.qdrant_client import create_qdrant_client


def ensure_collaborative_collection(
    *,
    client: QdrantClient | None = None,
    settings: AppSettings | None = None,
) -> dict[str, object]:
    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    try:
        created = False
        if not qdrant_client.collection_exists(app_settings.qdrant_collection_cf):
            qdrant_client.create_collection(
                collection_name=app_settings.qdrant_collection_cf,
                vectors_config={},
                sparse_vectors_config={"interactions": models.SparseVectorParams()},
                on_disk_payload=True,
            )
            created = True

        qdrant_client.create_payload_index(
            app_settings.qdrant_collection_cf,
            "user_id",
            models.PayloadSchemaType.INTEGER,
            wait=True,
        )
        return {
            "collection_name": app_settings.qdrant_collection_cf,
            "created": created,
            "sparse_vectors": ["interactions"],
        }
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()


def build_collaborative_index(
    db: Session,
    *,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
    now: datetime | None = None,
) -> dict[str, object]:
    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    reference_time = now or datetime.utcnow()
    try:
        ensure_collaborative_collection(client=qdrant_client, settings=app_settings)

        logs = db.scalars(
            select(UserBehaviorLog).order_by(
                UserBehaviorLog.user_id.asc(),
                UserBehaviorLog.created_at.asc(),
                UserBehaviorLog.id.asc(),
            )
        ).all()
        logs_by_user: dict[int, list[UserBehaviorLog]] = defaultdict(list)
        for log in logs:
            logs_by_user[log.user_id].append(log)

        points: list[models.PointStruct] = []
        indexed_users = 0
        for user_id, user_logs in logs_by_user.items():
            sparse_vector = build_user_sparse_vector(user_logs, now=reference_time)
            if not sparse_vector.indices:
                continue

            indexed_users += 1
            points.append(
                models.PointStruct(
                    id=user_id,
                    vector={"interactions": sparse_vector},
                    payload={
                        "user_id": user_id,
                        "behavior_count": len(user_logs),
                        "updated_at": user_logs[-1].created_at.isoformat(),
                    },
                )
            )

        if points:
            qdrant_client.upsert(
                app_settings.qdrant_collection_cf,
                points=points,
                wait=True,
            )

        item_cooccurrence = build_item_cooccurrence_map(db)
        upsert_collaborative_experiment(
            db,
            experiment_key=COLLABORATIVE_ITEM_EXPERIMENT_KEY,
            name="Collaborative Item Cooccurrence",
            strategy="item_cooccurrence",
            pipeline_version=app_settings.recommendation_pipeline_version,
            model_version="cooccurrence-v1",
            config_json={"top_k": 12},
            artifact_json={
                "item_cooccurrence": item_cooccurrence,
                "user_count": len(logs_by_user),
                "indexed_users": indexed_users,
                "built_at": reference_time.isoformat(),
            },
            description="Offline collaborative filtering build artifacts.",
        )
        db.commit()

        point_count = qdrant_client.count(app_settings.qdrant_collection_cf, exact=True).count
        return {
            "collection_name": app_settings.qdrant_collection_cf,
            "indexed_users": indexed_users,
            "qdrant_points": point_count,
            "item_nodes": len(item_cooccurrence),
            "built_at": reference_time.isoformat(),
        }
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()


def upsert_collaborative_experiment(
    db: Session,
    *,
    experiment_key: str,
    name: str,
    strategy: str,
    pipeline_version: str,
    model_version: str,
    config_json: dict[str, object],
    artifact_json: dict[str, object],
    description: str,
) -> RecommendationExperiment:
    experiment = db.scalar(
        select(RecommendationExperiment).where(
            RecommendationExperiment.experiment_key == experiment_key
        )
    )
    if experiment is None:
        experiment = RecommendationExperiment(
            experiment_key=experiment_key,
            name=name,
            strategy=strategy,
        )

    experiment.name = name
    experiment.strategy = strategy
    experiment.pipeline_version = pipeline_version
    experiment.model_version = model_version
    experiment.is_active = True
    experiment.config_json = config_json
    experiment.artifact_json = artifact_json
    experiment.description = description
    db.add(experiment)
    return experiment

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings
from backend.app.models.base import Base
from backend.app.models.recommendation_experiment import RecommendationExperiment
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.collaborative_filtering import (
    COLLABORATIVE_ITEM_EXPERIMENT_KEY,
    recall_collaborative_user_candidates,
    recall_item_cooccurrence_candidates,
)
from backend.app.services.qdrant_client import create_qdrant_client, get_qdrant_connection_status
from backend.app.tasks.collaborative_index_tasks import build_collaborative_index
from backend.scripts.seed_base_data import seed_base_data


def build_settings(collection_name: str) -> AppSettings:
    return AppSettings(
        vector_db_provider="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection_cf=collection_name,
        qdrant_collection_users="cf-test-users",
        qdrant_collection_products="cf-test-products",
    )


@pytest.fixture
def seeded_session(db_engine) -> Session:
    Base.metadata.create_all(db_engine)
    session = Session(db_engine)
    try:
        seed_base_data(session)
        yield session
    finally:
        session.close()


def create_user(session: Session, *, email: str, username: str) -> User:
    user = User(
        email=email,
        username=username,
        password_hash="hashed-password",
        role="user",
        is_active=True,
    )
    user.profile = UserProfile(display_name=username)
    session.add(user)
    session.flush()
    return user


def add_behavior(session: Session, *, user_id: int, behavior_type: str, product_id: int) -> None:
    session.add(
        UserBehaviorLog(
            user_id=user_id,
            behavior_type=behavior_type,
            target_type="product",
            target_id=product_id,
        )
    )


def test_collaborative_index_builds_sparse_user_vectors_and_item_cooccurrence(
    seeded_session: Session,
) -> None:
    settings = build_settings(f"shiyige_collaborative_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for collaborative filtering test")

    user_a = create_user(
        seeded_session,
        email="cf-a@example.com",
        username="cf-a",
    )
    user_b = create_user(
        seeded_session,
        email="cf-b@example.com",
        username="cf-b",
    )
    add_behavior(seeded_session, user_id=user_a.id, behavior_type="view_product", product_id=1)
    add_behavior(seeded_session, user_id=user_a.id, behavior_type="add_to_cart", product_id=1)
    add_behavior(seeded_session, user_id=user_a.id, behavior_type="add_to_cart", product_id=4)
    add_behavior(seeded_session, user_id=user_b.id, behavior_type="view_product", product_id=1)
    add_behavior(seeded_session, user_id=user_b.id, behavior_type="add_to_cart", product_id=1)
    seeded_session.commit()

    client = create_qdrant_client(settings)
    try:
        if client.collection_exists(settings.qdrant_collection_cf):
            client.delete_collection(settings.qdrant_collection_cf)

        result = build_collaborative_index(
            seeded_session,
            settings=settings,
            client=client,
        )
        experiment = seeded_session.scalar(
            select(RecommendationExperiment).where(
                RecommendationExperiment.experiment_key == COLLABORATIVE_ITEM_EXPERIMENT_KEY
            )
        )
        collaborative_candidates = recall_collaborative_user_candidates(
            seeded_session,
            user_id=user_b.id,
            consumed_product_ids={1},
            top_terms=["汉服"],
            settings=settings,
            client=client,
        )
        cooccurrence_candidates = recall_item_cooccurrence_candidates(
            seeded_session,
            seed_product_ids=[1],
            consumed_product_ids={1},
            top_terms=["汉服"],
        )

        assert result["indexed_users"] == 2
        assert result["qdrant_points"] == 2
        assert experiment is not None
        assert experiment.artifact_json["item_cooccurrence"]
        assert any(candidate.product_id == 4 for candidate in collaborative_candidates)
        assert any(
            candidate.recall_channel == "collaborative_user"
            for candidate in collaborative_candidates
        )
        assert any(candidate.product_id == 4 for candidate in cooccurrence_candidates)
        assert any(
            candidate.recall_channel == "item_cooccurrence" for candidate in cooccurrence_candidates
        )
    finally:
        if client.collection_exists(settings.qdrant_collection_cf):
            client.delete_collection(settings.qdrant_collection_cf)
        client.close()

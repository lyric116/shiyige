from __future__ import annotations

import uuid

import pytest
from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings
from backend.app.models.base import Base
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.embedding_registry import get_embedding_bundle
from backend.app.services.qdrant_client import create_qdrant_client, get_qdrant_connection_status
from backend.app.services.recommendation_pipeline import run_recommendation_pipeline
from backend.app.services.recommendations import recommend_products_for_user
from backend.app.tasks.qdrant_index_tasks import sync_products_to_qdrant
from backend.scripts.seed_base_data import seed_base_data


def build_settings(collection_name: str) -> AppSettings:
    return AppSettings(
        vector_db_provider="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection_products=collection_name,
        qdrant_collection_users="pipeline-test-users",
        qdrant_collection_cf="pipeline-test-cf",
        embedding_provider="local_hash",
        embedding_model_name="dense-test",
        embedding_dimension=8,
        embedding_model_source="test",
        embedding_model_revision="test",
        sparse_embedding_provider="local_hash",
        sparse_embedding_model_name="sparse-test",
        sparse_embedding_dimension=0,
        sparse_embedding_model_source="test",
        sparse_embedding_model_revision="test",
        colbert_embedding_provider="local_hash",
        colbert_embedding_model_name="colbert-test",
        colbert_embedding_dimension=8,
        colbert_embedding_model_source="test",
        colbert_embedding_model_revision="test",
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


def add_product_trace(
    session: Session,
    *,
    user_id: int,
    product_id: int,
    query: str | None = None,
) -> None:
    if query:
        session.add(
            UserBehaviorLog(
                user_id=user_id,
                behavior_type="search",
                target_type="search",
                ext_json={"query": query},
            )
        )
    session.add(
        UserBehaviorLog(
            user_id=user_id,
            behavior_type="view_product",
            target_type="product",
            target_id=product_id,
        )
    )
    session.add(
        UserBehaviorLog(
            user_id=user_id,
            behavior_type="add_to_cart",
            target_type="product",
            target_id=product_id,
        )
    )


def test_recommendation_pipeline_returns_multi_channel_candidates_for_engaged_user(
    seeded_session: Session,
) -> None:
    settings = build_settings(f"shiyige_products_pipeline_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for recommendation pipeline test")

    primary_user = create_user(
        seeded_session,
        email="pipeline-primary@example.com",
        username="pipeline-primary",
    )
    similar_user = create_user(
        seeded_session,
        email="pipeline-similar@example.com",
        username="pipeline-similar",
    )

    add_product_trace(
        seeded_session,
        user_id=primary_user.id,
        product_id=1,
        query="春日汉服",
    )
    add_product_trace(
        seeded_session,
        user_id=similar_user.id,
        product_id=1,
    )
    add_product_trace(
        seeded_session,
        user_id=similar_user.id,
        product_id=4,
    )
    seeded_session.commit()

    client = create_qdrant_client(settings)
    bundle = get_embedding_bundle(settings)
    try:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)

        sync_products_to_qdrant(
            seeded_session,
            mode="full",
            settings=settings,
            client=client,
            bundle=bundle,
        )

        pipeline_run = run_recommendation_pipeline(
            seeded_session,
            user_id=primary_user.id,
            limit=6,
            settings=settings,
            client=client,
            bundle=bundle,
        )
        public_results = recommend_products_for_user(
            seeded_session,
            user_id=primary_user.id,
            limit=6,
            settings=settings,
            client=client,
            bundle=bundle,
        )

        assert pipeline_run.cold_start is False
        assert pipeline_run.candidates
        assert public_results
        assert public_results[0].product.id != 1
        assert any(
            "content_profile" in candidate.recall_channels
            or "sparse_interest" in candidate.recall_channels
            for candidate in pipeline_run.candidates
        )
        assert any(
            "collaborative_user" in candidate.recall_channels
            or "item_cooccurrence" in candidate.recall_channels
            for candidate in pipeline_run.candidates
        )
        assert pipeline_run.candidates[0].reason
        assert pipeline_run.candidates[0].ranking_features
        assert pipeline_run.candidates[0].feature_summary
        assert pipeline_run.active_ranker
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()


def test_recommendation_pipeline_returns_cold_start_candidates_for_new_user(
    seeded_session: Session,
) -> None:
    settings = build_settings(f"shiyige_products_pipeline_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for recommendation pipeline test")

    new_user = create_user(
        seeded_session,
        email="pipeline-cold@example.com",
        username="pipeline-cold",
    )
    seeded_session.commit()

    client = create_qdrant_client(settings)
    bundle = get_embedding_bundle(settings)
    try:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)

        sync_products_to_qdrant(
            seeded_session,
            mode="full",
            settings=settings,
            client=client,
            bundle=bundle,
        )

        pipeline_run = run_recommendation_pipeline(
            seeded_session,
            user_id=new_user.id,
            limit=6,
            settings=settings,
            client=client,
            bundle=bundle,
        )

        assert pipeline_run.cold_start is True
        assert pipeline_run.candidates
        assert pipeline_run.recall_results["cold_start"]
        assert any(
            "cold_start" in candidate.recall_channels
            or "trending" in candidate.recall_channels
            or "new_arrival" in candidate.recall_channels
            for candidate in pipeline_run.candidates
        )
        assert pipeline_run.candidates[0].score_breakdown
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()

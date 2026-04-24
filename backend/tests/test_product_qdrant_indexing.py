from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings
from backend.app.models.base import Base
from backend.app.models.product import Product, ProductTag
from backend.app.models.recommendation import ProductEmbedding
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.embedding_registry import get_embedding_bundle
from backend.app.services.qdrant_client import create_qdrant_client, get_qdrant_connection_status
from backend.app.services.recommendations import recommend_products_for_user
from backend.app.services.vector_search import semantic_search_products
from backend.app.tasks.qdrant_index_tasks import (
    INDEX_STATUS_FAILED,
    get_product_index_status,
    retry_failed_product_indexing,
    sync_products_to_qdrant,
)
from backend.scripts.seed_base_data import seed_base_data


def build_settings(collection_name: str) -> AppSettings:
    return AppSettings(
        vector_db_provider="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection_products=collection_name,
        qdrant_collection_users="index-test-users",
        qdrant_collection_cf="index-test-cf",
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
        colbert_embedding_dimension=4,
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


def test_full_sync_writes_named_vectors_and_payloads(seeded_session: Session) -> None:
    settings = build_settings(f"shiyige_products_index_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for product indexing test")

    client = create_qdrant_client(settings)
    bundle = get_embedding_bundle(settings)
    try:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)

        result = sync_products_to_qdrant(
            seeded_session,
            mode="full",
            settings=settings,
            client=client,
            bundle=bundle,
        )

        point_count = client.count(settings.qdrant_collection_products, exact=True).count
        point = client.retrieve(
            settings.qdrant_collection_products,
            ids=[1],
            with_payload=True,
            with_vectors=True,
        )[0]

        assert result["indexed"] == 20
        assert result["failed"] == 0
        assert point_count == 20
        assert sorted(point.vector.keys()) == ["colbert", "dense", "sparse"]
        assert len(point.vector["dense"]) == 8
        assert len(point.vector["colbert"][0]) == 4
        assert point.payload["status"] == "active"
        assert point.payload["stock_available"] is True
        assert point.payload["embedding_model_version"] == "dense-test|sparse-test|colbert-test"
        assert point.payload["semantic_text"]
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()


def test_incremental_sync_updates_payload_and_inactive_products_are_removed(
    seeded_session: Session,
) -> None:
    settings = build_settings(f"shiyige_products_incremental_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for product indexing test")

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

        tagged_product = seeded_session.get(Product, 1)
        assert tagged_product is not None
        tagged_product.tags.append(ProductTag(tag="茶器"))
        seeded_session.add(tagged_product)
        seeded_session.commit()

        increment_result = sync_products_to_qdrant(
            seeded_session,
            mode="incremental",
            product_ids=[1],
            settings=settings,
            client=client,
            bundle=bundle,
        )
        updated_point = client.retrieve(
            settings.qdrant_collection_products,
            ids=[1],
            with_payload=True,
            with_vectors=True,
        )[0]

        assert increment_result["indexed"] == 1
        assert "茶器" in updated_point.payload["tags"]

        inactive_product = seeded_session.get(Product, 2)
        assert inactive_product is not None
        inactive_product.status = 0
        seeded_session.add(inactive_product)
        seeded_session.commit()

        removal_result = sync_products_to_qdrant(
            seeded_session,
            mode="incremental",
            product_ids=[2],
            settings=settings,
            client=client,
            bundle=bundle,
        )
        removed_point = client.retrieve(
            settings.qdrant_collection_products,
            ids=[2],
            with_payload=True,
            with_vectors=True,
        )

        assert removal_result["deleted"] == 1
        assert removed_point == []
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()


def test_out_of_stock_products_are_filtered_from_search_and_recommendation(
    seeded_session: Session,
) -> None:
    product = seeded_session.get(Product, 2)
    assert product is not None
    assert product.default_sku is not None
    assert product.default_sku.inventory is not None
    product.default_sku.inventory.quantity = 0
    seeded_session.add(product)

    user = User(
        email="vector-index-user@example.com",
        username="vector-index-user",
        password_hash="hashed-password",
        role="user",
        is_active=True,
    )
    user.profile = UserProfile(display_name="vector-index-user")
    seeded_session.add(user)
    seeded_session.flush()
    seeded_session.add(
        UserBehaviorLog(
            user_id=user.id,
            behavior_type="search",
            target_type="search",
            ext_json={"query": "香囊"},
        )
    )
    seeded_session.commit()

    search_ids = [
        result.product.id
        for result in semantic_search_products(seeded_session, query="香囊", limit=10)
    ]
    recommendation_ids = [
        result.product.id
        for result in recommend_products_for_user(seeded_session, user_id=user.id, limit=10)
    ]

    assert product.id not in search_ids
    assert product.id not in recommendation_ids


def test_failed_points_are_recorded_and_can_be_retried(seeded_session: Session) -> None:
    settings = build_settings(f"shiyige_products_retry_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for product indexing test")

    bundle = get_embedding_bundle(settings)
    client = create_qdrant_client(settings)

    class FailingUpsertClient:
        def __init__(self, delegate) -> None:
            self._delegate = delegate

        def upsert(self, *args, **kwargs):
            raise RuntimeError("simulated qdrant upsert failure")

        def __getattr__(self, name: str):
            return getattr(self._delegate, name)

    try:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)

        failed_result = sync_products_to_qdrant(
            seeded_session,
            mode="full",
            settings=settings,
            client=FailingUpsertClient(client),
            bundle=bundle,
        )
        failed_rows = seeded_session.scalars(
            select(ProductEmbedding).where(ProductEmbedding.index_status == INDEX_STATUS_FAILED)
        ).all()

        assert failed_result["failed"] == 20
        assert len(failed_rows) == 20
        assert all(
            "simulated qdrant upsert failure" in (row.index_error or "")
            for row in failed_rows
        )

        retry_result = retry_failed_product_indexing(
            seeded_session,
            settings=settings,
            client=client,
            bundle=bundle,
        )
        status_payload = get_product_index_status(
            seeded_session,
            settings=settings,
            client=client,
        )

        assert retry_result["indexed"] == 20
        assert retry_result["failed"] == 0
        assert status_payload["failed_products"] == []
        assert status_payload["qdrant_point_count"] == 20
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()

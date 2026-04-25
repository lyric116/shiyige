from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.config import AppSettings
from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.services.embedding import (
    EmbeddingModelDescriptor,
    LocalHashColbertEmbeddingProvider,
)
from backend.app.services.embedding_registry import get_embedding_bundle
from backend.app.services.hybrid_search import RecallCandidate, fuse_recall_candidates
from backend.app.services.qdrant_client import create_qdrant_client, get_qdrant_connection_status
from backend.app.services.search_reranker import reciprocal_rank_score, score_colbert_maxsim
from backend.app.services.vector_search import find_related_products, semantic_search_products
from backend.app.tasks.qdrant_index_tasks import sync_products_to_qdrant
from backend.scripts.seed_base_data import seed_base_data


def build_settings(collection_name: str) -> AppSettings:
    return AppSettings(
        vector_db_provider="qdrant",
        qdrant_url="http://127.0.0.1:6333",
        qdrant_collection_products=collection_name,
        qdrant_collection_users="hybrid-test-users",
        qdrant_collection_cf="hybrid-test-cf",
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


def test_fuse_recall_candidates_applies_rrf_across_dense_and_sparse() -> None:
    dense_hits = [
        RecallCandidate(
            product_id=1,
            payload={"product_id": 1},
            dense_rank=1,
            dense_score=0.91,
            fusion_score=reciprocal_rank_score(1),
        ),
        RecallCandidate(
            product_id=2,
            payload={"product_id": 2},
            dense_rank=2,
            dense_score=0.82,
            fusion_score=reciprocal_rank_score(2),
        ),
    ]
    sparse_hits = [
        RecallCandidate(
            product_id=2,
            payload={"product_id": 2},
            sparse_rank=1,
            sparse_score=0.97,
            fusion_score=reciprocal_rank_score(1),
        ),
        RecallCandidate(
            product_id=3,
            payload={"product_id": 3},
            sparse_rank=2,
            sparse_score=0.74,
            fusion_score=reciprocal_rank_score(2),
        ),
    ]

    fused = fuse_recall_candidates(dense_hits=dense_hits, sparse_hits=sparse_hits)

    assert [candidate.product_id for candidate in fused[:3]] == [2, 1, 3]
    assert fused[0].dense_rank == 2
    assert fused[0].sparse_rank == 1
    assert fused[0].fusion_score > fused[1].fusion_score


def test_colbert_reranker_prefers_exact_term_overlap() -> None:
    provider = LocalHashColbertEmbeddingProvider(
        EmbeddingModelDescriptor(
            provider="local_hash",
            model_name="colbert-test",
            dimension=8,
            source="test",
            revision="test",
            device="cpu",
            normalize=True,
        )
    )

    query_vectors = provider.embed_query("香囊")
    exact_vectors = provider.embed_query("故宫宫廷香囊 端午送礼")
    off_topic_vectors = provider.embed_query("景泰蓝花瓶 家居陈设")

    assert score_colbert_maxsim(query_vectors, exact_vectors) > score_colbert_maxsim(
        query_vectors,
        off_topic_vectors,
    )


def test_semantic_search_uses_qdrant_hybrid_and_respects_stock_filters(
    seeded_session: Session,
) -> None:
    settings = build_settings(f"shiyige_products_hybrid_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for hybrid search test")

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

        initial_results = semantic_search_products(
            seeded_session,
            query="香囊",
            limit=5,
            settings=settings,
            client=client,
            bundle=bundle,
        )
        filtered_results = semantic_search_products(
            seeded_session,
            query="端午送礼",
            limit=5,
            max_price=Decimal("200"),
            festival_tag="端午",
            settings=settings,
            client=client,
            bundle=bundle,
        )

        assert initial_results[0].product.name == "故宫宫廷香囊"
        assert "关键词命中" in initial_results[0].reason
        assert all(
            (result.product.lowest_price or Decimal("0")) <= Decimal("200")
            for result in filtered_results
        )
        assert all(result.product.festival_tag == "端午" for result in filtered_results)

        product = seeded_session.scalar(
            select(Product).where(Product.name == "故宫宫廷香囊")
        )
        assert product is not None
        assert product.default_sku is not None
        assert product.default_sku.inventory is not None
        product.default_sku.inventory.quantity = 0
        seeded_session.add(product)
        seeded_session.commit()

        sync_products_to_qdrant(
            seeded_session,
            mode="incremental",
            product_ids=[product.id],
            settings=settings,
            client=client,
            bundle=bundle,
        )

        stock_only_results = semantic_search_products(
            seeded_session,
            query="香囊",
            limit=5,
            stock_only=True,
            settings=settings,
            client=client,
            bundle=bundle,
        )
        include_oos_results = semantic_search_products(
            seeded_session,
            query="香囊",
            limit=5,
            stock_only=False,
            settings=settings,
            client=client,
            bundle=bundle,
        )

        stock_only_ids = [result.product.id for result in stock_only_results]
        include_oos_ids = [result.product.id for result in include_oos_results]

        assert product.id not in stock_only_ids
        assert product.id in include_oos_ids
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()


def test_related_products_use_qdrant_candidates_when_vector_store_is_ready(
    seeded_session: Session,
) -> None:
    settings = build_settings(f"shiyige_products_related_{uuid.uuid4().hex[:8]}")
    status = get_qdrant_connection_status(settings)
    if not status.available:
        pytest.skip("Qdrant is not reachable for related-products test")

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

        source_product = seeded_session.scalar(
            select(Product).where(Product.name == "点翠发簪")
        )
        assert source_product is not None

        results = find_related_products(
            seeded_session,
            product_id=source_product.id,
            limit=3,
            settings=settings,
            client=client,
        )

        assert results
        assert results[0].product.id != source_product.id
        assert results[0].pipeline_version == "qdrant_related"
        assert results[0].dense_score is not None
        assert results[0].source_breakdown["dense_similarity"]["score"] > 0
    finally:
        if client.collection_exists(settings.qdrant_collection_products):
            client.delete_collection(settings.qdrant_collection_products)
        client.close()

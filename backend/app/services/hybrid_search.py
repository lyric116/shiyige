from __future__ import annotations

from dataclasses import dataclass, field

from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.models.product import Product, ProductSku
from backend.app.services.embedding import get_embedding_bundle
from backend.app.services.product_index_document import build_sparse_vector
from backend.app.services.qdrant_client import create_qdrant_client
from backend.app.services.search_filters import (
    SearchFilters,
    build_qdrant_search_filter,
    product_matches_search_filters,
)
from backend.app.services.search_reranker import (
    build_hybrid_search_reason,
    compute_business_rerank_bonus,
    compute_payload_semantic_bonus,
    reciprocal_rank_score,
    score_colbert_maxsim,
)

RECALL_LIMIT = 100
RERANK_LIMIT = 50


@dataclass(slots=True)
class HybridSearchHit:
    product: Product
    score: float
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None
    pipeline_version: str = "qdrant_hybrid"


@dataclass(slots=True)
class RecallCandidate:
    product_id: int
    payload: dict[str, object]
    dense_rank: int | None = None
    dense_score: float | None = None
    sparse_rank: int | None = None
    sparse_score: float | None = None
    fusion_score: float = 0.0
    fusion_rank: int = 0
    colbert_score: float = 0.0
    semantic_bonus: float = 0.0
    business_bonus: float = 0.0
    matched_terms: list[str] = field(default_factory=list)
    final_score: float = 0.0

    @property
    def has_dense_match(self) -> bool:
        return self.dense_rank is not None

    @property
    def has_sparse_match(self) -> bool:
        return self.sparse_rank is not None


def hybrid_search_products(
    db: Session,
    *,
    query: str,
    limit: int,
    filters: SearchFilters,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
    bundle=None,
) -> list[HybridSearchHit]:
    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    embedding_bundle = bundle or get_embedding_bundle(app_settings)

    try:
        query_filter = build_qdrant_search_filter(filters)
        dense_query = embedding_bundle.dense.embed_query(query)
        sparse_query = build_sparse_vector(embedding_bundle.sparse.embed_query(query))
        colbert_query = embedding_bundle.colbert.embed_query(query)

        dense_hits = query_recall_channel(
            qdrant_client,
            collection_name=app_settings.qdrant_collection_products,
            query_vector=dense_query,
            using="dense",
            query_filter=query_filter,
            limit=RECALL_LIMIT,
        )
        sparse_hits = query_recall_channel(
            qdrant_client,
            collection_name=app_settings.qdrant_collection_products,
            query_vector=sparse_query,
            using="sparse",
            query_filter=query_filter,
            limit=RECALL_LIMIT,
        )

        candidates = fuse_recall_candidates(dense_hits=dense_hits, sparse_hits=sparse_hits)
        if not candidates:
            return []

        rerank_candidates = candidates[:RERANK_LIMIT]
        hydrate_colbert_vectors(
            rerank_candidates,
            client=qdrant_client,
            collection_name=app_settings.qdrant_collection_products,
            query_colbert=colbert_query,
        )
        score_reranked_candidates(rerank_candidates, query=query, filters=filters)

        ranked_candidates = sorted(
            rerank_candidates,
            key=lambda item: (-item.final_score, item.fusion_rank, -item.product_id),
        )
        products_by_id = load_products_by_id(
            db,
            product_ids=[candidate.product_id for candidate in ranked_candidates],
        )

        results: list[HybridSearchHit] = []
        for final_rank, candidate in enumerate(ranked_candidates, start=1):
            product = products_by_id.get(candidate.product_id)
            if product is None or not product_matches_search_filters(product, filters):
                continue

            results.append(
                HybridSearchHit(
                    product=product,
                    score=candidate.final_score,
                    reason=build_hybrid_search_reason(
                        query=query,
                        matched_terms=candidate.matched_terms,
                        has_dense_match=candidate.has_dense_match,
                        has_sparse_match=candidate.has_sparse_match,
                        colbert_promoted=final_rank < candidate.fusion_rank,
                    ),
                    matched_terms=list(candidate.matched_terms),
                    dense_score=candidate.dense_score,
                    sparse_score=candidate.sparse_score,
                    rerank_score=candidate.colbert_score,
                    pipeline_version="qdrant_hybrid",
                )
            )
            if len(results) >= limit:
                break

        return results
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()


def query_recall_channel(
    client: QdrantClient,
    *,
    collection_name: str,
    query_vector,
    using: str,
    query_filter,
    limit: int,
) -> list[RecallCandidate]:
    response = client.query_points(
        collection_name=collection_name,
        query=query_vector,
        using=using,
        query_filter=query_filter,
        limit=limit,
        with_payload=True,
        with_vectors=False,
    )

    results: list[RecallCandidate] = []
    for rank, point in enumerate(response.points, start=1):
        payload = dict(point.payload or {})
        product_id = int(payload.get("product_id") or point.id)
        results.append(
            RecallCandidate(
                product_id=product_id,
                payload=payload,
                dense_rank=rank if using == "dense" else None,
                dense_score=float(point.score) if using == "dense" else None,
                sparse_rank=rank if using == "sparse" else None,
                sparse_score=float(point.score) if using == "sparse" else None,
                fusion_score=reciprocal_rank_score(rank),
            )
        )
    return results


def fuse_recall_candidates(
    *,
    dense_hits: list[RecallCandidate],
    sparse_hits: list[RecallCandidate],
) -> list[RecallCandidate]:
    candidates_by_id: dict[int, RecallCandidate] = {}

    for hit in dense_hits:
        candidate = candidates_by_id.get(hit.product_id)
        if candidate is None:
            candidates_by_id[hit.product_id] = hit
            continue
        candidate.payload = hit.payload or candidate.payload
        candidate.dense_rank = hit.dense_rank
        candidate.dense_score = hit.dense_score
        candidate.fusion_score += hit.fusion_score

    for hit in sparse_hits:
        candidate = candidates_by_id.get(hit.product_id)
        if candidate is None:
            candidates_by_id[hit.product_id] = hit
            continue
        candidate.payload = candidate.payload or hit.payload
        candidate.sparse_rank = hit.sparse_rank
        candidate.sparse_score = hit.sparse_score
        candidate.fusion_score += hit.fusion_score

    ranked_candidates = sorted(
        candidates_by_id.values(),
        key=lambda item: (
            -item.fusion_score,
            item.sparse_rank or RECALL_LIMIT + 1,
            item.dense_rank or RECALL_LIMIT + 1,
            -item.product_id,
        ),
    )
    for fusion_rank, candidate in enumerate(ranked_candidates, start=1):
        candidate.fusion_rank = fusion_rank
    return ranked_candidates


def hydrate_colbert_vectors(
    candidates: list[RecallCandidate],
    *,
    client: QdrantClient,
    collection_name: str,
    query_colbert,
) -> None:
    if not candidates:
        return

    records = client.retrieve(
        collection_name,
        ids=[candidate.product_id for candidate in candidates],
        with_payload=True,
        with_vectors=["colbert"],
    )
    records_by_id = {int(record.id): record for record in records}

    for candidate in candidates:
        record = records_by_id.get(candidate.product_id)
        if record is None:
            continue

        record_payload = dict(record.payload or {})
        if record_payload:
            candidate.payload = record_payload

        colbert_vectors = None
        if isinstance(record.vector, dict):
            colbert_vectors = record.vector.get("colbert")
        if isinstance(colbert_vectors, list):
            candidate.colbert_score = score_colbert_maxsim(query_colbert, colbert_vectors)


def score_reranked_candidates(
    candidates: list[RecallCandidate],
    *,
    query: str,
    filters: SearchFilters,
) -> None:
    for candidate in candidates:
        semantic_bonus, matched_terms = compute_payload_semantic_bonus(candidate.payload, query)
        business_bonus = compute_business_rerank_bonus(candidate.payload, filters=filters)
        channel_bonus = 0.12 if candidate.has_dense_match else 0.0
        channel_bonus += 0.18 if candidate.has_sparse_match else 0.0

        candidate.semantic_bonus = semantic_bonus
        candidate.business_bonus = business_bonus
        candidate.matched_terms = matched_terms
        candidate.final_score = (
            candidate.fusion_score * 12.0
            + candidate.colbert_score * 0.55
            + candidate.semantic_bonus
            + candidate.business_bonus
            + channel_bonus
        )


def load_products_by_id(db: Session, *, product_ids: list[int]) -> dict[int, Product]:
    if not product_ids:
        return {}

    products = db.scalars(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
        )
        .where(Product.id.in_(product_ids))
    ).unique().all()
    return {product.id: product for product in products}

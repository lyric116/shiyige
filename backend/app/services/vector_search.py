from __future__ import annotations

import math
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Sequence

from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.core.logger import get_logger
from backend.app.models.product import Product, ProductSku
from backend.app.services.collaborative_filtering import load_item_cooccurrence_map
from backend.app.services.embedding import EmbeddingProvider, get_embedding_provider
from backend.app.services.embedding_text import normalize_text_piece
from backend.app.services.hybrid_search import hybrid_search_products
from backend.app.services.product_index_document import product_has_available_stock
from backend.app.services.search_filters import (
    SearchFilters,
    build_search_filters,
    product_matches_search_filters,
)
from backend.app.services.vector_store import probe_vector_store_runtime
from backend.app.tasks.embedding_tasks import reindex_changed_product_embeddings

logger = get_logger(__name__)


@dataclass
class VectorSearchResult:
    product: Product
    score: float
    reason: str
    matched_terms: list[str] = field(default_factory=list)
    dense_score: float | None = None
    sparse_score: float | None = None
    rerank_score: float | None = None
    pipeline_version: str = "baseline"
    source_breakdown: dict[str, object] = field(default_factory=dict)
    diversity_result: dict[str, object] = field(default_factory=dict)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def ensure_product_embeddings(db: Session, provider: EmbeddingProvider) -> None:
    reindex_changed_product_embeddings(db, provider=provider)


def collect_semantic_matches(product: Product, query: str) -> list[str]:
    normalized_query = normalize_text_piece(query) or ""
    matched_terms: list[str] = []

    candidate_values = [
        product.category.name if product.category else None,
        product.name,
        product.subtitle,
        product.dynasty_style,
        product.scene_tag,
        product.craft_type,
        product.festival_tag,
    ]
    candidate_values.extend(tag.tag for tag in product.tags)

    for raw_value in candidate_values:
        normalized_value = normalize_text_piece(raw_value)
        if not normalized_value:
            continue
        if normalized_value in normalized_query and normalized_value not in matched_terms:
            matched_terms.append(normalized_value)

    return matched_terms


def compute_semantic_bonus(product: Product, query: str) -> tuple[float, list[str]]:
    matched_terms = collect_semantic_matches(product, query)
    bonus = 0.0

    if product.category and product.category.name in matched_terms:
        bonus += 0.25
    if product.dynasty_style and product.dynasty_style in matched_terms:
        bonus += 0.2
    if product.scene_tag and product.scene_tag in matched_terms:
        bonus += 0.2
    if product.craft_type and product.craft_type in matched_terms:
        bonus += 0.15
    if product.festival_tag and product.festival_tag in matched_terms:
        bonus += 0.1

    tag_matches = sum(1 for tag in product.tags if tag.tag in matched_terms)
    bonus += min(tag_matches * 0.12, 0.36)

    if normalize_text_piece(product.name) in matched_terms:
        bonus += 0.12
    elif normalize_text_piece(product.subtitle) in matched_terms:
        bonus += 0.08

    return bonus, matched_terms


def build_semantic_reason(product: Product, query: str, matched_terms: list[str]) -> str:
    if matched_terms:
        reason_terms = "/".join(matched_terms[:3])
        return f"与“{query}”语义相近，命中“{reason_terms}”特征"
    return f"与“{query}”语义相近"


def collect_related_matches(source: Product, candidate: Product) -> list[str]:
    matched_terms: list[str] = []

    if source.category and candidate.category and source.category_id == candidate.category_id:
        matched_terms.append(source.category.name)
    if source.dynasty_style and source.dynasty_style == candidate.dynasty_style:
        matched_terms.append(source.dynasty_style)
    if source.scene_tag and source.scene_tag == candidate.scene_tag:
        matched_terms.append(source.scene_tag)
    if source.craft_type and source.craft_type == candidate.craft_type:
        matched_terms.append(source.craft_type)

    source_tags = {tag.tag for tag in source.tags}
    candidate_tags = {tag.tag for tag in candidate.tags}
    for tag in sorted(source_tags & candidate_tags):
        if tag not in matched_terms:
            matched_terms.append(tag)

    return matched_terms


def build_related_reason(source: Product, candidate: Product, matched_terms: list[str]) -> str:
    if matched_terms:
        reason_terms = "/".join(matched_terms[:3])
        return f"与当前商品在“{reason_terms}”特征上相近"
    return "与当前商品向量相似"


def build_related_source_breakdown(
    *,
    matched_terms: list[str],
    dense_similarity: float,
    cooccurrence_score: float,
    cultural_match_score: float,
) -> dict[str, object]:
    return {
        "dense_similarity": {
            "score": round(dense_similarity, 6),
            "source": "dense vector similarity",
        },
        "co_view_co_buy": {
            "score": round(cooccurrence_score, 6),
            "source": "item_cooccurrence",
            "matched": cooccurrence_score > 0,
        },
        "cultural_match": {
            "score": round(cultural_match_score, 6),
            "matched_terms": list(matched_terms),
        },
    }


def select_diverse_related_results(
    results: list[VectorSearchResult],
    *,
    limit: int,
    max_per_category: int = 2,
) -> list[VectorSearchResult]:
    selected: list[VectorSearchResult] = []
    overflow: list[VectorSearchResult] = []
    category_counts: dict[int | None, int] = {}

    for candidate in results:
        category_id = candidate.product.category_id
        current_count = category_counts.get(category_id, 0)
        if category_id is not None and current_count >= max_per_category:
            candidate.diversity_result = {
                "applied": True,
                "fallback_used": False,
                "category_count_before": current_count,
                "note": "首轮多样性筛选暂缓同类目候选",
            }
            overflow.append(candidate)
            continue

        candidate.diversity_result = {
            "applied": current_count > 0,
            "fallback_used": False,
            "category_count_before": current_count,
            "note": "通过多样性筛选保留",
        }
        selected.append(candidate)
        category_counts[category_id] = current_count + 1
        if len(selected) >= limit:
            return selected

    for candidate in overflow:
        if len(selected) >= limit:
            break
        category_id = candidate.product.category_id
        current_count = category_counts.get(category_id, 0)
        candidate.diversity_result = {
            "applied": True,
            "fallback_used": True,
            "category_count_before": current_count,
            "note": "多样性筛选后用于补足结果数",
        }
        selected.append(candidate)
        category_counts[category_id] = current_count + 1

    return selected[:limit]


def baseline_semantic_search_products(
    db: Session,
    *,
    query: str,
    limit: int,
    filters: SearchFilters,
    provider: EmbeddingProvider | None = None,
    settings: AppSettings | None = None,
) -> list[VectorSearchResult]:
    app_settings = settings or get_app_settings()
    embedding_provider = provider or get_embedding_provider(app_settings)
    normalized_query = normalize_text_piece(query)
    if not normalized_query:
        return []

    ensure_product_embeddings(db, embedding_provider)
    db.expire_all()
    query_vector = embedding_provider.embed_query(normalized_query)

    products = db.scalars(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
            selectinload(Product.embedding),
        )
        .where(Product.status == 1)
    ).unique().all()

    results: list[VectorSearchResult] = []
    for product in products:
        if not product_matches_search_filters(product, filters):
            continue

        if product.embedding is None or not product.embedding.embedding_vector:
            continue

        similarity = cosine_similarity(query_vector, product.embedding.embedding_vector)
        similarity_score = (similarity + 1) / 2
        semantic_bonus, matched_terms = compute_semantic_bonus(product, normalized_query)
        final_score = similarity_score + semantic_bonus

        results.append(
            VectorSearchResult(
                product=product,
                score=final_score,
                reason=build_semantic_reason(product, normalized_query, matched_terms),
                matched_terms=matched_terms,
                dense_score=similarity_score,
                pipeline_version="baseline_semantic",
            )
        )

    results.sort(
        key=lambda item: (
            item.score,
            len(collect_semantic_matches(item.product, normalized_query)),
            item.product.id,
        ),
        reverse=True,
    )
    return results[:limit]


def semantic_search_products(
    db: Session,
    *,
    query: str,
    limit: int = 10,
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    dynasty_style: str | None = None,
    craft_type: str | None = None,
    scene_tag: str | None = None,
    festival_tag: str | None = None,
    stock_only: bool = True,
    provider: EmbeddingProvider | None = None,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
    bundle: Any | None = None,
    force_baseline: bool = False,
) -> list[VectorSearchResult]:
    app_settings = settings or get_app_settings()
    normalized_query = normalize_text_piece(query)
    if not normalized_query:
        return []

    filters = build_search_filters(
        category_id=category_id,
        min_price=min_price,
        max_price=max_price,
        dynasty_style=dynasty_style,
        craft_type=craft_type,
        scene_tag=scene_tag,
        festival_tag=festival_tag,
        stock_only=stock_only,
    )

    if not force_baseline and provider is None:
        runtime = probe_vector_store_runtime(app_settings)
        if runtime.active_search_backend == "qdrant_hybrid":
            try:
                hybrid_results = hybrid_search_products(
                    db,
                    query=normalized_query,
                    limit=limit,
                    filters=filters,
                    settings=app_settings,
                    client=client,
                    bundle=bundle,
                )
                return [
                    VectorSearchResult(
                        product=result.product,
                        score=result.score,
                        reason=result.reason,
                        matched_terms=list(result.matched_terms),
                        dense_score=result.dense_score,
                        sparse_score=result.sparse_score,
                        rerank_score=result.rerank_score,
                        pipeline_version=result.pipeline_version,
                    )
                    for result in hybrid_results
                ]
            except Exception as exc:  # pragma: no cover - fallback protection
                logger.warning(
                    "Hybrid semantic search failed, falling back to baseline. query=%s error=%s",
                    normalized_query,
                    exc,
                )

    return baseline_semantic_search_products(
        db,
        query=normalized_query,
        limit=limit,
        filters=filters,
        provider=provider,
        settings=app_settings,
    )


def find_related_products(
    db: Session,
    *,
    product_id: int,
    limit: int = 4,
    provider: EmbeddingProvider | None = None,
) -> list[VectorSearchResult]:
    embedding_provider = provider or get_embedding_provider()
    ensure_product_embeddings(db, embedding_provider)
    db.expire_all()

    products = db.scalars(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
            selectinload(Product.embedding),
        )
        .where(Product.status == 1)
    ).unique().all()

    source_product = next((product for product in products if product.id == product_id), None)
    if (
        source_product is None
        or source_product.embedding is None
        or not source_product.embedding.embedding_vector
    ):
        return []

    cooccurrence_scores = {
        int(item["product_id"]): float(item["score"])
        for item in load_item_cooccurrence_map(db).get(str(product_id), [])
    }

    results: list[VectorSearchResult] = []
    for candidate in products:
        if candidate.id == source_product.id:
            continue
        if not product_has_available_stock(candidate):
            continue
        if candidate.embedding is None or not candidate.embedding.embedding_vector:
            continue

        similarity = cosine_similarity(
            source_product.embedding.embedding_vector,
            candidate.embedding.embedding_vector,
        )
        similarity_score = (similarity + 1) / 2
        matched_terms = collect_related_matches(source_product, candidate)
        cultural_match_score = 0.0
        if source_product.category_id == candidate.category_id:
            cultural_match_score += 0.25
        if source_product.dynasty_style and source_product.dynasty_style == candidate.dynasty_style:
            cultural_match_score += 0.12
        if source_product.scene_tag and source_product.scene_tag == candidate.scene_tag:
            cultural_match_score += 0.12
        if source_product.craft_type and source_product.craft_type == candidate.craft_type:
            cultural_match_score += 0.1
        cultural_match_score += min(len(set(matched_terms)) * 0.08, 0.24)
        cooccurrence_score = cooccurrence_scores.get(candidate.id, 0.0)
        cooccurrence_boost = min(cooccurrence_score * 0.05, 0.2)
        final_score = similarity_score + cultural_match_score + cooccurrence_boost

        results.append(
            VectorSearchResult(
                product=candidate,
                score=final_score,
                reason=build_related_reason(source_product, candidate, matched_terms),
                matched_terms=matched_terms,
                dense_score=similarity_score,
                pipeline_version="baseline_related",
                source_breakdown=build_related_source_breakdown(
                    matched_terms=matched_terms,
                    dense_similarity=similarity_score,
                    cooccurrence_score=cooccurrence_score,
                    cultural_match_score=cultural_match_score,
                ),
            )
        )

    results.sort(
        key=lambda item: (
            item.score,
            item.product.id,
        ),
        reverse=True,
    )
    return select_diverse_related_results(results, limit=limit)

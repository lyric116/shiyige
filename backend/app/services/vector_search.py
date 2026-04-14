from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import math
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.product import Product
from backend.app.services.embedding import EmbeddingProvider, get_embedding_provider
from backend.app.services.embedding_text import normalize_text_piece
from backend.app.tasks.embedding_tasks import reindex_changed_product_embeddings


@dataclass
class VectorSearchResult:
    product: Product
    score: float
    reason: str


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


def semantic_search_products(
    db: Session,
    *,
    query: str,
    limit: int = 10,
    category_id: int | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    provider: EmbeddingProvider | None = None,
) -> list[VectorSearchResult]:
    embedding_provider = provider or get_embedding_provider()
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
            selectinload(Product.skus),
            selectinload(Product.embedding),
        )
        .where(Product.status == 1)
    ).unique().all()

    results: list[VectorSearchResult] = []
    for product in products:
        if category_id is not None and product.category_id != category_id:
            continue

        lowest_price = product.lowest_price
        if min_price is not None and (lowest_price is None or lowest_price < min_price):
            continue
        if max_price is not None and (lowest_price is None or lowest_price > max_price):
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
            selectinload(Product.skus),
            selectinload(Product.embedding),
        )
        .where(Product.status == 1)
    ).unique().all()

    source_product = next((product for product in products if product.id == product_id), None)
    if source_product is None or source_product.embedding is None or not source_product.embedding.embedding_vector:
        return []

    results: list[VectorSearchResult] = []
    for candidate in products:
        if candidate.id == source_product.id:
            continue
        if candidate.embedding is None or not candidate.embedding.embedding_vector:
            continue

        similarity = cosine_similarity(
            source_product.embedding.embedding_vector,
            candidate.embedding.embedding_vector,
        )
        similarity_score = (similarity + 1) / 2
        matched_terms = collect_related_matches(source_product, candidate)
        bonus = 0.0
        if source_product.category_id == candidate.category_id:
            bonus += 0.25
        if source_product.dynasty_style and source_product.dynasty_style == candidate.dynasty_style:
            bonus += 0.12
        if source_product.scene_tag and source_product.scene_tag == candidate.scene_tag:
            bonus += 0.12
        if source_product.craft_type and source_product.craft_type == candidate.craft_type:
            bonus += 0.1
        bonus += min(len(set(matched_terms)) * 0.08, 0.24)

        results.append(
            VectorSearchResult(
                product=candidate,
                score=similarity_score + bonus,
                reason=build_related_reason(source_product, candidate, matched_terms),
            )
        )

    results.sort(
        key=lambda item: (
            item.score,
            item.product.id,
        ),
        reverse=True,
    )
    return results[:limit]

from __future__ import annotations

from collections.abc import Sequence

from backend.app.services.embedding import tokenize_embedding_terms
from backend.app.services.embedding_text import normalize_text_piece
from backend.app.services.search_filters import SearchFilters


def reciprocal_rank_score(rank: int, *, k: int = 60) -> float:
    return 1.0 / float(k + rank)


def score_colbert_maxsim(
    query_vectors: Sequence[Sequence[float]],
    document_vectors: Sequence[Sequence[float]],
) -> float:
    if not query_vectors or not document_vectors:
        return 0.0

    total_score = 0.0
    for query_vector in query_vectors:
        max_score = max(
            dot_product(query_vector, document_vector) for document_vector in document_vectors
        )
        total_score += max_score

    average_score = total_score / float(len(query_vectors))
    return max(0.0, min((average_score + 1.0) / 2.0, 1.0))


def dot_product(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right):
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=False))


def collect_payload_matches(payload: dict[str, object], query: str) -> list[str]:
    normalized_query = normalize_text_piece(query) or ""
    if not normalized_query:
        return []

    query_tokens = set(tokenize_embedding_terms(normalized_query))
    matched_terms: list[str] = []
    candidate_values = [
        payload.get("category_name"),
        payload.get("product_name"),
        payload.get("dynasty_style"),
        payload.get("craft_type"),
        payload.get("scene_tag"),
        payload.get("festival_tag"),
    ]
    candidate_values.extend(payload.get("tags") or [])

    for raw_value in candidate_values:
        normalized_value = normalize_filterable_payload_value(raw_value)
        if not normalized_value:
            continue
        if normalized_value in normalized_query or normalized_value in query_tokens:
            if normalized_value not in matched_terms:
                matched_terms.append(normalized_value)

    return matched_terms


def compute_payload_semantic_bonus(
    payload: dict[str, object],
    query: str,
) -> tuple[float, list[str]]:
    matched_terms = collect_payload_matches(payload, query)
    bonus = 0.0

    if normalize_filterable_payload_value(payload.get("category_name")) in matched_terms:
        bonus += 0.25
    if normalize_filterable_payload_value(payload.get("dynasty_style")) in matched_terms:
        bonus += 0.2
    if normalize_filterable_payload_value(payload.get("scene_tag")) in matched_terms:
        bonus += 0.2
    if normalize_filterable_payload_value(payload.get("craft_type")) in matched_terms:
        bonus += 0.15
    if normalize_filterable_payload_value(payload.get("festival_tag")) in matched_terms:
        bonus += 0.1

    tag_matches = sum(
        1
        for tag in payload.get("tags") or []
        if normalize_filterable_payload_value(tag) in matched_terms
    )
    bonus += min(tag_matches * 0.12, 0.36)

    if normalize_filterable_payload_value(payload.get("product_name")) in matched_terms:
        bonus += 0.12

    return bonus, matched_terms


def compute_business_rerank_bonus(
    payload: dict[str, object],
    *,
    filters: SearchFilters,
) -> float:
    bonus = 0.0

    if payload.get("status") == "active":
        bonus += 0.03
    if payload.get("stock_available") is True:
        bonus += 0.05
    if filters.category_id is not None and payload.get("category_id") == filters.category_id:
        bonus += 0.02

    price_value = payload.get("price_min")
    if isinstance(price_value, (int, float)):
        if filters.min_price is not None and float(price_value) >= float(filters.min_price):
            bonus += 0.01
        if filters.max_price is not None and float(price_value) <= float(filters.max_price):
            bonus += 0.01

    return bonus


def build_hybrid_search_reason(
    *,
    query: str,
    matched_terms: list[str],
    has_dense_match: bool,
    has_sparse_match: bool,
    colbert_promoted: bool,
) -> str:
    reason_parts: list[str] = []
    if has_dense_match:
        reason_parts.append(f"与“{query}”语义相关")
    if has_sparse_match:
        if matched_terms:
            reason_parts.append(f"关键词命中“{'/'.join(matched_terms[:2])}”")
        else:
            reason_parts.append("关键词命中")
    if matched_terms:
        reason_parts.append(f"文化特征匹配“{'/'.join(matched_terms[:3])}”")
    if colbert_promoted:
        reason_parts.append("ColBERT 重排提升")
    elif has_dense_match or has_sparse_match:
        reason_parts.append("经混合检索精排")

    return "，".join(reason_parts) if reason_parts else f"与“{query}”相关"


def normalize_filterable_payload_value(value: object) -> str | None:
    return normalize_text_piece(str(value)) if value is not None else None

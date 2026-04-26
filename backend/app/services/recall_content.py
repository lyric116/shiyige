from __future__ import annotations

from collections import defaultdict

from qdrant_client import QdrantClient, models

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.models.recommendation import UserInterestProfile
from backend.app.services.candidate_fusion import RecallItem
from backend.app.services.qdrant_client import create_qdrant_client


def recall_profile_content_candidates(
    profile: UserInterestProfile,
    *,
    top_terms: list[str],
    consumed_product_ids: set[int],
    limit: int = 24,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
) -> list[RecallItem]:
    if not profile.embedding_vector:
        return []

    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    try:
        response = qdrant_client.query_points(
            collection_name=app_settings.qdrant_collection_products,
            query=profile.embedding_vector,
            using="dense",
            query_filter=build_recommendation_filter(),
            limit=limit + len(consumed_product_ids),
            with_payload=True,
            with_vectors=False,
        )

        results: list[RecallItem] = []
        rank = 0
        for point in response.points:
            payload = dict(point.payload or {})
            product_id = int(payload.get("product_id") or point.id)
            if product_id in consumed_product_ids:
                continue

            rank += 1
            results.append(
                RecallItem(
                    product_id=product_id,
                    recall_channel="content_profile",
                    recall_score=float(point.score),
                    rank_in_channel=rank,
                    matched_terms=match_terms_against_payload(payload, top_terms),
                    reason_parts=["内容语义召回", "基于近期行为画像"],
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


def recall_related_product_candidates(
    recent_product_ids: list[int],
    *,
    consumed_product_ids: set[int],
    limit: int = 18,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
) -> list[RecallItem]:
    if not recent_product_ids:
        return []

    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    try:
        seed_records = qdrant_client.retrieve(
            app_settings.qdrant_collection_products,
            ids=recent_product_ids[:3],
            with_payload=True,
            with_vectors=["dense"],
        )

        aggregated_items: dict[int, RecallItem] = {}
        for seed_rank, seed_record in enumerate(seed_records, start=1):
            if not isinstance(seed_record.vector, dict):
                continue

            dense_vector = seed_record.vector.get("dense")
            if not isinstance(dense_vector, list):
                continue

            seed_payload = dict(seed_record.payload or {})
            seed_product_id = int(seed_payload.get("product_id") or seed_record.id)
            seed_name = str(seed_payload.get("product_name") or f"商品{seed_product_id}")

            response = qdrant_client.query_points(
                collection_name=app_settings.qdrant_collection_products,
                query=dense_vector,
                using="dense",
                query_filter=build_recommendation_filter(),
                limit=8,
                with_payload=True,
                with_vectors=False,
            )
            for point in response.points:
                payload = dict(point.payload or {})
                product_id = int(payload.get("product_id") or point.id)
                if product_id in consumed_product_ids or product_id == seed_product_id:
                    continue

                existing = aggregated_items.get(product_id)
                matched_terms = collect_shared_payload_terms(seed_payload, payload)
                recall_item = RecallItem(
                    product_id=product_id,
                    recall_channel="related_products",
                    recall_score=float(point.score),
                    rank_in_channel=seed_rank,
                    matched_terms=matched_terms,
                    reason_parts=["相似商品召回", f"延展自最近浏览的“{seed_name}”"],
                    metadata={"seed_product_id": seed_product_id, "seed_name": seed_name},
                )
                if existing is None or recall_item.recall_score > existing.recall_score:
                    aggregated_items[product_id] = recall_item

        results = sorted(
            aggregated_items.values(),
            key=lambda item: (-item.recall_score, item.rank_in_channel, -item.product_id),
        )
        for rank, item in enumerate(results, start=1):
            item.rank_in_channel = rank
        return results[:limit]
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()


def build_recommendation_filter() -> models.Filter:
    return models.Filter(
        must=[
            models.FieldCondition(
                key="status",
                match=models.MatchValue(value="active"),
            ),
            models.FieldCondition(
                key="stock_available",
                match=models.MatchValue(value=True),
            ),
        ]
    )


def match_terms_against_payload(payload: dict[str, object], top_terms: list[str]) -> list[str]:
    payload_terms = {
        str(value)
        for value in [
            payload.get("category_name"),
            payload.get("dynasty_style"),
            payload.get("craft_type"),
            payload.get("scene_tag"),
            payload.get("festival_tag"),
            *(payload.get("tags") or []),
        ]
        if value
    }
    return [term for term in top_terms if term in payload_terms][:4]


def collect_shared_payload_terms(
    seed_payload: dict[str, object],
    candidate_payload: dict[str, object],
) -> list[str]:
    shared_terms: list[str] = []
    seed_values = defaultdict(set)
    for key in ("category_name", "dynasty_style", "craft_type", "scene_tag", "festival_tag"):
        value = seed_payload.get(key)
        if value:
            seed_values[key].add(str(value))

    for tag in seed_payload.get("tags") or []:
        seed_values["tags"].add(str(tag))

    for key, values in seed_values.items():
        candidate_values = (
            candidate_payload.get("tags") or [] if key == "tags" else [candidate_payload.get(key)]
        )
        for candidate_value in candidate_values:
            if (
                candidate_value
                and str(candidate_value) in values
                and str(candidate_value) not in shared_terms
            ):
                shared_terms.append(str(candidate_value))

    return shared_terms[:4]

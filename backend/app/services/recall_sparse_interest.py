from __future__ import annotations

from qdrant_client import QdrantClient, models

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.services.candidate_fusion import RecallItem
from backend.app.services.embedding import get_embedding_bundle
from backend.app.services.product_index_document import build_sparse_vector
from backend.app.services.qdrant_client import create_qdrant_client


def recall_sparse_interest_candidates(
    *,
    top_terms: list[str],
    consumed_product_ids: set[int],
    limit: int = 24,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
    bundle=None,
) -> list[RecallItem]:
    if not top_terms:
        return []

    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    embedding_bundle = bundle or get_embedding_bundle(app_settings)
    try:
        sparse_query = build_sparse_vector(
            embedding_bundle.sparse.embed_query(" | ".join(top_terms[:8]))
        )
        response = qdrant_client.query_points(
            collection_name=app_settings.qdrant_collection_products,
            query=sparse_query,
            using="sparse",
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

            matched_terms = [
                term
                for term in top_terms
                if term in build_payload_term_set(payload)
            ][:4]
            rank += 1
            results.append(
                RecallItem(
                    product_id=product_id,
                    recall_channel="sparse_interest",
                    recall_score=float(point.score),
                    rank_in_channel=rank,
                    matched_terms=matched_terms,
                    reason_parts=["关键词兴趣召回", "命中长期兴趣词"],
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


def build_payload_term_set(payload: dict[str, object]) -> set[str]:
    terms = {
        str(value)
        for value in [
            payload.get("category_name"),
            payload.get("dynasty_style"),
            payload.get("craft_type"),
            payload.get("scene_tag"),
            payload.get("festival_tag"),
        ]
        if value
    }
    for tag in payload.get("tags") or []:
        terms.add(str(tag))
    return terms

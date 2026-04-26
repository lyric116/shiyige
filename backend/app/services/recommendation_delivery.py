from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.app.models.product import Product
from backend.app.services.recommendation_pipeline import run_recommendation_pipeline
from backend.app.services.recommendations import recommend_products_for_user
from backend.app.services.vector_store import build_runtime_marker

RECOMMENDATION_SOURCE_LABELS = {
    "personalized": "个性化",
    "similar": "相似商品",
    "hot": "热门",
    "new": "新品探索",
    "seasonal": "节令主题",
}


@dataclass(frozen=True, slots=True)
class RecommendationPayload:
    items: list[dict[str, object]]
    pipeline: dict[str, object]


def serialize_category_for_recommendation(product: Product) -> dict[str, object] | None:
    category = product.category
    if category is None:
        return None
    return {
        "id": category.id,
        "name": category.name,
        "slug": category.slug,
        "description": category.description,
    }


def serialize_product_list_item_for_recommendation(product: Product) -> dict[str, object]:
    default_sku = product.default_sku
    return {
        "id": product.id,
        "name": product.name,
        "subtitle": product.subtitle,
        "cover_url": product.cover_url,
        "culture_summary": product.culture_summary,
        "category": serialize_category_for_recommendation(product),
        "price": product.lowest_price,
        "member_price": default_sku.member_price if default_sku else None,
        "tags": [tag.tag for tag in product.tags],
    }


def build_recommendation_source_meta(result, *, slot: str) -> dict[str, str]:
    recall_channels = list(getattr(result, "recall_channels", []))
    reason = str(getattr(result, "reason", ""))

    if slot in {"related", "cart", "order_complete"} or "related_products" in recall_channels:
        source_type = "similar"
    elif "collaborative_user" in recall_channels or "item_cooccurrence" in recall_channels:
        source_type = "personalized"
    elif "content_profile" in recall_channels or "sparse_interest" in recall_channels:
        source_type = "personalized"
    elif "trending" in recall_channels and ("节" in reason or "节令" in reason):
        source_type = "seasonal"
    elif "trending" in recall_channels:
        source_type = "hot"
    elif "new_arrival" in recall_channels or "cold_start" in recall_channels:
        source_type = "new"
    elif "节" in reason or "节令" in reason:
        source_type = "seasonal"
    elif slot == "home":
        source_type = "personalized"
    else:
        source_type = "similar"

    return {
        "source_type": source_type,
        "source_label": RECOMMENDATION_SOURCE_LABELS[source_type],
    }


def serialize_recommendation_item(
    result,
    *,
    debug: bool = False,
    slot: str = "home",
) -> dict[str, object]:
    feature_summary = dict(getattr(result, "feature_summary", {}))
    ranking_features = dict(getattr(result, "ranking_features", {}))
    business_summary = feature_summary.get("business", {})
    is_exploration = bool(
        business_summary.get("exploration_candidate")
        if isinstance(business_summary, dict)
        else ranking_features.get("exploration_candidate", 0.0)
    )
    item = {
        **serialize_product_list_item_for_recommendation(result.product),
        "score": round(result.score, 6),
        "final_score": round(result.score, 6),
        "reason": result.reason,
        "recall_channels": list(getattr(result, "recall_channels", [])),
        "is_exploration": is_exploration,
        **build_recommendation_source_meta(result, slot=slot),
    }
    if debug:
        item.update(
            {
                "matched_terms": list(getattr(result, "matched_terms", [])),
                "feature_highlights": list(getattr(result, "feature_highlights", [])),
                "ranking_features": ranking_features,
                "rank_features": ranking_features,
                "feature_summary": feature_summary,
                "score_breakdown": dict(getattr(result, "score_breakdown", {})),
                "ranker_name": getattr(result, "ranker_name", "baseline"),
                "ranker_model_version": getattr(result, "ranker_model_version", "baseline"),
                "ltr_fallback_used": bool(getattr(result, "ltr_fallback_used", False)),
            }
        )
    return item


def resolve_recommendation_payload(
    db: Session,
    *,
    user_id: int,
    limit: int,
    slot: str,
    debug: bool = False,
) -> RecommendationPayload:
    pipeline = build_runtime_marker()
    if pipeline["active_recommendation_backend"] == "multi_recall":
        pipeline_run = run_recommendation_pipeline(
            db,
            user_id=user_id,
            limit=limit,
        )
        items = [
            serialize_recommendation_item(candidate, debug=debug, slot=slot)
            for candidate in pipeline_run.candidates[:limit]
        ]
        pipeline.update(
            {
                "active_ranker": pipeline_run.active_ranker,
                "ranker_model_version": pipeline_run.ranker_model_version,
                "ltr_fallback_used": pipeline_run.ltr_fallback_used,
            }
        )
    else:
        results = recommend_products_for_user(
            db,
            user_id=user_id,
            limit=limit,
            force_baseline=True,
        )
        items = [
            serialize_recommendation_item(result, debug=debug, slot=slot) for result in results
        ]
        pipeline.update(
            {
                "active_ranker": "baseline",
                "ranker_model_version": "baseline",
                "ltr_fallback_used": False,
            }
        )

    return RecommendationPayload(items=items, pipeline={**pipeline, "slot": slot})

from __future__ import annotations

from backend.app.services.business_rules import RecommendationBusinessRules
from backend.app.services.ranking_features import RecommendationRankingFeatures


def build_feature_summary(
    features: RecommendationRankingFeatures,
    *,
    business_rules: RecommendationBusinessRules,
) -> dict[str, object]:
    return {
        "recall": {
            "dense_recall_score": round(features.dense_recall_score, 6),
            "sparse_recall_score": round(features.sparse_recall_score, 6),
            "colbert_rerank_score": round(features.colbert_rerank_score, 6),
            "collaborative_score": round(features.collaborative_score, 6),
            "item_cooccurrence_score": round(features.item_cooccurrence_score, 6),
            "rrf_fusion_score": round(features.rrf_fusion_score, 6),
            "recall_channel_count": int(features.recall_channel_count),
            "best_channel_rank": (
                int(features.best_channel_rank) if features.best_channel_rank else 0
            ),
        },
        "interest": {
            "category_match": round(features.category_match, 6),
            "tag_match_count": int(features.tag_match_count),
            "dynasty_match": round(features.dynasty_match, 6),
            "craft_match": round(features.craft_match, 6),
            "scene_match": round(features.scene_match, 6),
            "festival_match": round(features.festival_match, 6),
            "price_affinity": round(features.price_affinity, 6),
            "user_recent_interest_score": round(features.user_recent_interest_score, 6),
            "user_long_term_interest_score": round(features.user_long_term_interest_score, 6),
        },
        "quality": {
            "sales_count": int(features.sales_count),
            "conversion_rate": round(features.conversion_rate, 6),
            "add_to_cart_rate": round(features.add_to_cart_rate, 6),
            "rating_avg": round(features.rating_avg, 6),
            "review_count": int(features.review_count),
            "stock_available": bool(features.stock_available),
            "return_rate": round(features.return_rate, 6),
            "freshness_score": round(features.freshness_score, 6),
            "content_quality_score": round(features.content_quality_score, 6),
        },
        "business": {
            "is_listed": business_rules.is_listed,
            "has_stock": business_rules.has_stock,
            "price_filter_pass": business_rules.price_filter_pass,
            "recently_exposed": business_rules.recently_exposed,
            "already_purchased": business_rules.already_purchased,
            "is_editorial_pick": business_rules.is_editorial_pick,
            "festival_theme_match": business_rules.festival_theme_match,
            "exploration_candidate": business_rules.exploration_candidate,
        },
    }


def build_feature_highlights(features: RecommendationRankingFeatures) -> list[str]:
    highlights: list[str] = []
    if features.collaborative_score > 0:
        highlights.append("协同过滤信号强")
    if features.item_cooccurrence_score > 0:
        highlights.append("与近期行为商品共现")
    if features.category_match or features.tag_match_count > 0:
        highlights.append("用户兴趣匹配")
    if features.price_affinity >= 0.75:
        highlights.append("价格带贴近偏好")
    if features.rating_avg >= 4.5 and features.review_count > 0:
        highlights.append("口碑稳定")
    if features.freshness_score >= 0.7:
        highlights.append("新品探索位")
    return highlights[:4]


def build_ranker_reason(
    *,
    recall_channels: list[str],
    matched_terms: list[str],
    features: RecommendationRankingFeatures,
) -> str:
    reason_parts: list[str] = []
    if features.collaborative_score > 0:
        reason_parts.append("相似用户偏好")
    if features.item_cooccurrence_score > 0:
        reason_parts.append("近期行为商品共现")
    if features.category_match or features.tag_match_count > 0:
        reason_parts.append("文化兴趣匹配")
    if features.freshness_score >= 0.7:
        reason_parts.append("新品探索")
    if not reason_parts and recall_channels:
        reason_parts.append("多路召回融合")

    if matched_terms:
        return f"{'、'.join(reason_parts[:3])}，命中“{'/'.join(matched_terms[:3])}”"
    return "、".join(reason_parts[:3]) or "多路召回综合排序"

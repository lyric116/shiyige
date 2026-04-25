from __future__ import annotations

from dataclasses import dataclass

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.models.product import Product
from backend.app.services.business_rules import (
    RecommendationBusinessRules,
    apply_post_ranking_rules,
    build_business_rules,
    compute_business_adjustments,
)
from backend.app.services.candidate_fusion import FusedRecommendationCandidate
from backend.app.services.ltr_ranker import load_ltr_ranker
from backend.app.services.ranking_features import (
    RankingFeatureContext,
    RecommendationRankingFeatures,
    build_candidate_ranking_features,
)
from backend.app.services.recommendation_explainer import (
    build_feature_highlights,
    build_feature_summary,
    build_ranker_reason,
)

WEIGHTED_RANKER_MODEL_VERSION = "weighted-ranker-v1"
WEIGHTED_RANKER_GROUP_WEIGHTS = {
    "hybrid_retrieval_score": 0.25,
    "colbert_rerank_score": 0.20,
    "collaborative_group_score": 0.15,
    "user_interest_score": 0.15,
    "product_quality_score": 0.10,
    "trend_freshness_score": 0.05,
    "business_constraints_score": 0.05,
    "diversity_exploration_score": 0.05,
}


@dataclass(slots=True)
class RankedRecommendationCandidate:
    product: Product
    fused_candidate: FusedRecommendationCandidate
    features: RecommendationRankingFeatures
    business_rules: RecommendationBusinessRules
    feature_summary: dict[str, object]
    feature_highlights: list[str]
    score_breakdown: dict[str, float]
    ranker_name: str
    ranker_model_version: str
    ltr_fallback_used: bool
    base_score: float
    final_score: float
    reason: str


def rank_fused_candidates(
    fused_candidates: list[FusedRecommendationCandidate],
    *,
    products_by_id: dict[int, Product],
    context: RankingFeatureContext,
    limit: int,
    settings: AppSettings | None = None,
) -> list[RankedRecommendationCandidate]:
    app_settings = settings or get_app_settings()
    requested_ranker = app_settings.recommendation_ranker
    ltr_ranker = load_ltr_ranker(app_settings) if requested_ranker == "ltr_ranker" else None

    ranked_candidates: list[RankedRecommendationCandidate] = []
    for fused_candidate in fused_candidates:
        product = products_by_id.get(fused_candidate.product_id)
        if product is None:
            continue

        features = build_candidate_ranking_features(
            fused_candidate,
            product,
            context=context,
        )
        business_rules = build_business_rules(features)
        if not business_rules.is_listed or not business_rules.has_stock:
            continue
        weighted_breakdown = score_weighted_candidate(features, business_rules)

        ranker_name = "weighted_ranker"
        ranker_model_version = WEIGHTED_RANKER_MODEL_VERSION
        ltr_fallback_used = False
        base_score = weighted_breakdown["base_score"]
        final_score = weighted_breakdown["final_score"]
        score_breakdown = dict(weighted_breakdown)

        if requested_ranker == "ltr_ranker":
            if ltr_ranker is not None:
                ltr_score = float(ltr_ranker.score(features))
                base_score = ltr_score
                final_score = ltr_score + weighted_breakdown["business_total"]
                ranker_name = "ltr_ranker"
                ranker_model_version = ltr_ranker.model_version
                score_breakdown.update(
                    {
                        "ltr_model_score": round(ltr_score, 6),
                        "base_score": round(base_score, 6),
                        "final_score": round(final_score, 6),
                    }
                )
            else:
                ltr_fallback_used = True
                score_breakdown["ltr_model_score"] = 0.0

        feature_summary = build_feature_summary(features, business_rules=business_rules)
        feature_highlights = build_feature_highlights(features)
        reason = build_ranker_reason(
            recall_channels=fused_candidate.recall_channels,
            matched_terms=fused_candidate.matched_terms,
            features=features,
        )
        ranked_candidates.append(
            RankedRecommendationCandidate(
                product=product,
                fused_candidate=fused_candidate,
                features=features,
                business_rules=business_rules,
                feature_summary=feature_summary,
                feature_highlights=feature_highlights,
                score_breakdown=score_breakdown,
                ranker_name=ranker_name,
                ranker_model_version=ranker_model_version,
                ltr_fallback_used=ltr_fallback_used,
                base_score=base_score,
                final_score=final_score,
                reason=reason,
            )
        )

    ranked_candidates.sort(key=lambda item: (-item.final_score, -item.product.id))
    return apply_post_ranking_rules(
        ranked_candidates,
        limit=limit,
        max_consecutive_category=app_settings.recommendation_max_consecutive_category,
        exploration_ratio=app_settings.recommendation_exploration_ratio,
    )


def score_weighted_candidate(
    features: RecommendationRankingFeatures,
    business_rules: RecommendationBusinessRules,
) -> dict[str, float]:
    normalized = features.to_normalized_dict()

    hybrid_retrieval_score = bound_score(
        normalized["dense_recall_score"] * 0.34
        + normalized["sparse_recall_score"] * 0.24
        + normalized["rrf_fusion_score"] * 0.24
        + normalized["recall_channel_count"] * 0.12
        + normalized["best_channel_rank"] * 0.06
    )
    colbert_rerank_score = bound_score(normalized["colbert_rerank_score"])
    collaborative_group_score = bound_score(
        normalized["collaborative_score"] * 0.65
        + normalized["item_cooccurrence_score"] * 0.35
    )
    user_interest_score = bound_score(
        normalized["category_match"] * 0.12
        + normalized["tag_match_count"] * 0.14
        + normalized["dynasty_match"] * 0.08
        + normalized["craft_match"] * 0.06
        + normalized["scene_match"] * 0.06
        + normalized["festival_match"] * 0.06
        + normalized["price_affinity"] * 0.08
        + normalized["user_recent_interest_score"] * 0.18
        + normalized["user_long_term_interest_score"] * 0.22
    )
    product_quality_score = bound_score(
        normalized["sales_count"] * 0.18
        + normalized["conversion_rate"] * 0.18
        + normalized["add_to_cart_rate"] * 0.14
        + normalized["rating_avg"] * 0.12
        + normalized["review_count"] * 0.08
        + normalized["stock_available"] * 0.10
        + normalized["content_quality_score"] * 0.12
        - normalized["return_rate"] * 0.08
    )
    trend_freshness_score = bound_score(
        normalized["freshness_score"] * 0.65
        + normalized["festival_theme_match"] * 0.15
        + normalized["is_editorial_pick"] * 0.20
    )
    business_constraints_score = bound_score(
        normalized["is_listed"] * 0.35
        + normalized["has_stock"] * 0.35
        + normalized["price_filter_pass"] * 0.10
        + (1.0 - normalized["recently_exposed"]) * 0.10
        + (1.0 - normalized["already_purchased"]) * 0.10
    )
    diversity_exploration_score = bound_score(
        normalized["exploration_candidate"] * 0.65
        + (1.0 - normalized["recently_exposed"]) * 0.35
    )

    hybrid_retrieval_contribution = (
        hybrid_retrieval_score * WEIGHTED_RANKER_GROUP_WEIGHTS["hybrid_retrieval_score"]
    )
    colbert_contribution = (
        colbert_rerank_score * WEIGHTED_RANKER_GROUP_WEIGHTS["colbert_rerank_score"]
    )
    collaborative_contribution = (
        collaborative_group_score * WEIGHTED_RANKER_GROUP_WEIGHTS["collaborative_group_score"]
    )
    interest_contribution = (
        user_interest_score * WEIGHTED_RANKER_GROUP_WEIGHTS["user_interest_score"]
    )
    quality_contribution = (
        product_quality_score * WEIGHTED_RANKER_GROUP_WEIGHTS["product_quality_score"]
    )
    trend_contribution = (
        trend_freshness_score * WEIGHTED_RANKER_GROUP_WEIGHTS["trend_freshness_score"]
    )
    business_constraints_contribution = (
        business_constraints_score
        * WEIGHTED_RANKER_GROUP_WEIGHTS["business_constraints_score"]
    )
    diversity_contribution = (
        diversity_exploration_score
        * WEIGHTED_RANKER_GROUP_WEIGHTS["diversity_exploration_score"]
    )

    recall_score = (
        hybrid_retrieval_contribution + colbert_contribution + collaborative_contribution
    )
    interest_score = interest_contribution
    quality_score = quality_contribution + trend_contribution

    business_adjustments = compute_business_adjustments(
        features,
        rules=business_rules,
    )
    base_score = (
        recall_score
        + interest_score
        + quality_score
        + business_constraints_contribution
        + diversity_contribution
    )
    final_score = base_score + business_adjustments["business_total"]

    return {
        "hybrid_retrieval_score": round(hybrid_retrieval_score, 6),
        "colbert_rerank_score": round(colbert_rerank_score, 6),
        "collaborative_group_score": round(collaborative_group_score, 6),
        "user_interest_score": round(user_interest_score, 6),
        "product_quality_score": round(product_quality_score, 6),
        "trend_freshness_score": round(trend_freshness_score, 6),
        "business_constraints_score": round(business_constraints_score, 6),
        "diversity_exploration_score": round(diversity_exploration_score, 6),
        "hybrid_retrieval_contribution": round(hybrid_retrieval_contribution, 6),
        "colbert_contribution": round(colbert_contribution, 6),
        "collaborative_contribution": round(collaborative_contribution, 6),
        "interest_contribution": round(interest_contribution, 6),
        "quality_contribution": round(quality_contribution, 6),
        "trend_contribution": round(trend_contribution, 6),
        "business_constraints_contribution": round(business_constraints_contribution, 6),
        "diversity_contribution": round(diversity_contribution, 6),
        "recall_score": round(recall_score, 6),
        "interest_score": round(interest_score, 6),
        "quality_score": round(quality_score, 6),
        "business_boost": business_adjustments["business_boost"],
        "business_penalty": business_adjustments["business_penalty"],
        "exploration_boost": business_adjustments["exploration_boost"],
        "business_total": business_adjustments["business_total"],
        "base_score": round(base_score, 6),
        "final_score": round(final_score, 6),
    }


def bound_score(value: float) -> float:
    return max(0.0, min(float(value), 1.0))

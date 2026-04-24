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

    recall_score = (
        normalized["dense_recall_score"] * 0.16
        + normalized["sparse_recall_score"] * 0.12
        + normalized["colbert_rerank_score"] * 0.08
        + normalized["collaborative_score"] * 0.10
        + normalized["item_cooccurrence_score"] * 0.06
        + normalized["rrf_fusion_score"] * 0.16
        + normalized["recall_channel_count"] * 0.06
        + normalized["best_channel_rank"] * 0.04
    )
    interest_score = (
        normalized["category_match"] * 0.08
        + normalized["tag_match_count"] * 0.07
        + normalized["dynasty_match"] * 0.04
        + normalized["craft_match"] * 0.03
        + normalized["scene_match"] * 0.03
        + normalized["festival_match"] * 0.03
        + normalized["price_affinity"] * 0.04
        + normalized["user_recent_interest_score"] * 0.06
        + normalized["user_long_term_interest_score"] * 0.08
    )
    quality_score = (
        normalized["sales_count"] * 0.05
        + normalized["conversion_rate"] * 0.04
        + normalized["add_to_cart_rate"] * 0.03
        + normalized["rating_avg"] * 0.03
        + normalized["review_count"] * 0.02
        + normalized["stock_available"] * 0.03
        + normalized["freshness_score"] * 0.03
        + normalized["content_quality_score"] * 0.03
        - normalized["return_rate"] * 0.03
    )

    business_adjustments = compute_business_adjustments(
        features,
        rules=business_rules,
    )
    base_score = recall_score + interest_score + quality_score
    final_score = base_score + business_adjustments["business_total"]

    return {
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

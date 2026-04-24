from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import Protocol

from backend.app.services.ranking_features import RecommendationRankingFeatures


@dataclass(slots=True)
class RecommendationBusinessRules:
    is_listed: bool
    has_stock: bool
    price_filter_pass: bool
    recently_exposed: bool
    already_purchased: bool
    is_editorial_pick: bool
    festival_theme_match: bool
    exploration_candidate: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class RankedCandidateLike(Protocol):
    product: object
    final_score: float
    features: RecommendationRankingFeatures
    business_rules: RecommendationBusinessRules


def build_business_rules(features: RecommendationRankingFeatures) -> RecommendationBusinessRules:
    return RecommendationBusinessRules(
        is_listed=bool(features.is_listed),
        has_stock=bool(features.has_stock),
        price_filter_pass=bool(features.price_filter_pass),
        recently_exposed=features.recently_exposed >= 0.34,
        already_purchased=bool(features.already_purchased),
        is_editorial_pick=bool(features.is_editorial_pick),
        festival_theme_match=bool(features.festival_theme_match),
        exploration_candidate=bool(features.exploration_candidate),
    )


def compute_business_adjustments(
    features: RecommendationRankingFeatures,
    *,
    rules: RecommendationBusinessRules | None = None,
) -> dict[str, float]:
    business_rules = rules or build_business_rules(features)
    boost = 0.0
    penalty = 0.0

    if business_rules.is_listed:
        boost += 0.08
    else:
        penalty += 2.0

    if business_rules.has_stock:
        boost += 0.08
    else:
        penalty += 2.0

    if business_rules.price_filter_pass:
        boost += 0.01

    if business_rules.is_editorial_pick:
        boost += 0.04
    if business_rules.festival_theme_match:
        boost += 0.04

    penalty += features.recently_exposed * 0.12
    penalty += features.return_rate * 0.08
    if business_rules.already_purchased:
        penalty += 3.0

    exploration_boost = features.exploration_candidate * max(features.freshness_score, 0.35) * 0.08
    return {
        "business_boost": round(boost, 6),
        "business_penalty": round(penalty, 6),
        "exploration_boost": round(exploration_boost, 6),
        "business_total": round(boost + exploration_boost - penalty, 6),
    }


def apply_post_ranking_rules(
    candidates: list[RankedCandidateLike],
    *,
    limit: int,
    max_consecutive_category: int,
    exploration_ratio: float,
) -> list[RankedCandidateLike]:
    ordered = sorted(candidates, key=lambda item: (-item.final_score, -item.product.id))
    selected: list[RankedCandidateLike] = []

    for candidate in ordered:
        if len(selected) >= limit:
            break
        if violates_diversity_constraints(
            candidate,
            selected,
            limit=limit,
            max_consecutive_category=max_consecutive_category,
        ):
            continue
        selected.append(candidate)

    if len(selected) < limit:
        selected_ids = {item.product.id for item in selected}
        for candidate in ordered:
            if len(selected) >= limit:
                break
            if candidate.product.id in selected_ids:
                continue
            selected.append(candidate)
            selected_ids.add(candidate.product.id)

    inject_exploration_candidates(
        selected,
        ordered,
        limit=limit,
        exploration_ratio=exploration_ratio,
    )
    return selected[:limit]


def violates_diversity_constraints(
    candidate: RankedCandidateLike,
    selected: list[RankedCandidateLike],
    *,
    limit: int,
    max_consecutive_category: int,
) -> bool:
    if not selected:
        return False

    category_id = getattr(candidate.product, "category_id", None)
    if category_id is not None:
        same_tail = 0
        for selected_candidate in reversed(selected):
            if getattr(selected_candidate.product, "category_id", None) != category_id:
                break
            same_tail += 1
        if same_tail >= max_consecutive_category:
            return True

    dynasty_counts = Counter(
        getattr(selected_candidate.product, "dynasty_style", None)
        for selected_candidate in selected
        if getattr(selected_candidate.product, "dynasty_style", None)
    )
    craft_counts = Counter(
        getattr(selected_candidate.product, "craft_type", None)
        for selected_candidate in selected
        if getattr(selected_candidate.product, "craft_type", None)
    )

    max_cluster = max(2, limit // 2)
    dynasty_style = getattr(candidate.product, "dynasty_style", None)
    if dynasty_style and dynasty_counts[dynasty_style] >= max_cluster:
        return True
    craft_type = getattr(candidate.product, "craft_type", None)
    if craft_type and craft_counts[craft_type] >= max_cluster:
        return True
    return False


def inject_exploration_candidates(
    selected: list[RankedCandidateLike],
    ordered: list[RankedCandidateLike],
    *,
    limit: int,
    exploration_ratio: float,
) -> None:
    available_exploration = [
        candidate
        for candidate in ordered
        if candidate.business_rules.exploration_candidate
    ]
    if not available_exploration or not selected:
        return

    target_count = min(
        len(available_exploration),
        max(1 if limit >= 5 else 0, round(limit * exploration_ratio)),
    )
    current_count = sum(
        1 for candidate in selected if candidate.business_rules.exploration_candidate
    )
    if current_count >= target_count:
        return

    selected_ids = {candidate.product.id for candidate in selected}
    for exploration_candidate in available_exploration:
        if current_count >= target_count:
            break
        if exploration_candidate.product.id in selected_ids:
            continue

        replacement_index = find_replaceable_index(selected)
        if replacement_index is None:
            break

        selected_ids.discard(selected[replacement_index].product.id)
        selected[replacement_index] = exploration_candidate
        selected_ids.add(exploration_candidate.product.id)
        current_count += 1


def find_replaceable_index(selected: list[RankedCandidateLike]) -> int | None:
    for index in range(len(selected) - 1, 1, -1):
        if not selected[index].business_rules.exploration_candidate:
            return index
    return None

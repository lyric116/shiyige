from __future__ import annotations

from backend.app.models.product import Product
from backend.app.services.candidate_fusion import FusedRecommendationCandidate


def diversify_candidates(
    candidates: list[FusedRecommendationCandidate],
    *,
    products_by_id: dict[int, Product],
    limit: int,
) -> list[FusedRecommendationCandidate]:
    remaining_candidates = list(candidates)
    diversified: list[FusedRecommendationCandidate] = []
    category_counts: dict[int, int] = {}
    dynasty_counts: dict[str, int] = {}
    craft_counts: dict[str, int] = {}

    while remaining_candidates and len(diversified) < limit:
        best_index = 0
        best_score = float("-inf")

        for index, candidate in enumerate(remaining_candidates):
            product = products_by_id.get(candidate.product_id)
            if product is None:
                continue

            adjusted_score = candidate.score
            adjusted_score -= category_counts.get(product.category_id, 0) * 0.08
            if product.dynasty_style:
                adjusted_score -= dynasty_counts.get(product.dynasty_style, 0) * 0.04
            if product.craft_type:
                adjusted_score -= craft_counts.get(product.craft_type, 0) * 0.03

            if adjusted_score > best_score:
                best_index = index
                best_score = adjusted_score

        selected = remaining_candidates.pop(best_index)
        diversified.append(selected)

        product = products_by_id.get(selected.product_id)
        if product is None:
            continue

        category_counts[product.category_id] = category_counts.get(product.category_id, 0) + 1
        if product.dynasty_style:
            dynasty_counts[product.dynasty_style] = (
                dynasty_counts.get(product.dynasty_style, 0) + 1
            )
        if product.craft_type:
            craft_counts[product.craft_type] = craft_counts.get(product.craft_type, 0) + 1

    return diversified

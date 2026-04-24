from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.services.search_reranker import reciprocal_rank_score

CHANNEL_WEIGHTS = {
    "content_profile": 1.2,
    "sparse_interest": 1.1,
    "collaborative": 1.1,
    "related_products": 1.0,
    "trending": 0.75,
    "new_arrival": 0.65,
    "cold_start": 0.8,
}

CHANNEL_LABELS = {
    "content_profile": "内容语义召回",
    "sparse_interest": "关键词兴趣召回",
    "collaborative": "协同过滤召回",
    "related_products": "相似商品召回",
    "trending": "热门趋势召回",
    "new_arrival": "新品探索召回",
    "cold_start": "冷启动兜底",
}


@dataclass(slots=True)
class RecallItem:
    product_id: int
    recall_channel: str
    recall_score: float
    rank_in_channel: int
    matched_terms: list[str] = field(default_factory=list)
    reason_parts: list[str] = field(default_factory=list)
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class FusedRecommendationCandidate:
    product_id: int
    score: float = 0.0
    fusion_score: float = 0.0
    vector_similarity: float = 0.0
    vector_score: float = 0.0
    term_bonus: float = 0.0
    matched_terms: list[str] = field(default_factory=list)
    reason_parts: list[str] = field(default_factory=list)
    recall_channels: list[str] = field(default_factory=list)
    channel_details: list[RecallItem] = field(default_factory=list)


def fuse_recall_results(
    recall_results: dict[str, list[RecallItem]],
    *,
    max_candidates: int = 200,
) -> list[FusedRecommendationCandidate]:
    candidates_by_id: dict[int, FusedRecommendationCandidate] = {}

    for channel_name, items in recall_results.items():
        weight = CHANNEL_WEIGHTS.get(channel_name, 1.0)
        for item in items:
            candidate = candidates_by_id.get(item.product_id)
            if candidate is None:
                candidate = FusedRecommendationCandidate(product_id=item.product_id)
                candidates_by_id[item.product_id] = candidate

            contribution = reciprocal_rank_score(item.rank_in_channel) * weight
            candidate.fusion_score += contribution
            candidate.vector_score += contribution
            candidate.score += contribution + (item.recall_score * 0.05 * weight)
            candidate.vector_similarity = max(candidate.vector_similarity, item.recall_score)
            merge_unique(candidate.matched_terms, item.matched_terms)
            merge_unique(candidate.reason_parts, item.reason_parts)
            if item.recall_channel not in candidate.recall_channels:
                candidate.recall_channels.append(item.recall_channel)
            candidate.channel_details.append(item)

    fused_candidates = list(candidates_by_id.values())
    for candidate in fused_candidates:
        source_bonus = min((len(candidate.recall_channels) - 1) * 0.05, 0.15)
        matched_term_bonus = min(len(candidate.matched_terms) * 0.04, 0.16)
        candidate.term_bonus = source_bonus + matched_term_bonus
        candidate.score += candidate.term_bonus

    fused_candidates.sort(
        key=lambda item: (-item.score, -item.fusion_score, -item.product_id),
    )
    return fused_candidates[:max_candidates]


def build_fused_reason(candidate: FusedRecommendationCandidate) -> str:
    reason_labels = [
        CHANNEL_LABELS.get(channel, channel)
        for channel in candidate.recall_channels[:3]
    ]
    if candidate.matched_terms:
        return (
            f"来自{'、'.join(reason_labels)}，匹配“{'/'.join(candidate.matched_terms[:3])}”"
        )
    if reason_labels:
        return f"来自{'、'.join(reason_labels)}"
    return "基于你的近期兴趣推荐"


def merge_unique(target: list[str], values: list[str]) -> None:
    for value in values:
        if value not in target:
            target.append(value)

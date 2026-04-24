from __future__ import annotations

from dataclasses import dataclass

from qdrant_client import QdrantClient
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.core.logger import get_logger
from backend.app.models.product import Product, ProductSku
from backend.app.models.recommendation import UserInterestProfile
from backend.app.models.user import UserBehaviorLog
from backend.app.services.candidate_fusion import (
    FusedRecommendationCandidate,
    RecallItem,
    build_fused_reason,
    fuse_recall_results,
)
from backend.app.services.diversity import diversify_candidates
from backend.app.services.embedding import (
    EmbeddingProvider,
    get_embedding_bundle,
    get_embedding_provider,
)
from backend.app.services.product_index_document import product_has_available_stock
from backend.app.services.recall_collaborative import recall_collaborative_candidates
from backend.app.services.recall_content import (
    recall_profile_content_candidates,
    recall_related_product_candidates,
)
from backend.app.services.recall_new_arrival import recall_new_arrival_candidates
from backend.app.services.recall_sparse_interest import recall_sparse_interest_candidates
from backend.app.services.recall_trending import recall_trending_candidates

logger = get_logger(__name__)


@dataclass(slots=True)
class PipelineRecommendationCandidate:
    product: Product
    score: float
    reason: str
    matched_terms: list[str]
    recall_channels: list[str]
    channel_details: list[RecallItem]
    vector_similarity: float
    vector_score: float
    term_bonus: float


@dataclass(slots=True)
class RecommendationPipelineRun:
    profile: UserInterestProfile
    candidates: list[PipelineRecommendationCandidate]
    recall_results: dict[str, list[RecallItem]]
    top_terms: list[str]
    consumed_product_ids: set[int]
    recent_product_ids: list[int]
    cold_start: bool


def run_recommendation_pipeline(
    db: Session,
    *,
    user_id: int,
    limit: int = 6,
    provider: EmbeddingProvider | None = None,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
    bundle=None,
    candidate_limit: int | None = None,
) -> RecommendationPipelineRun:
    from backend.app.services.recommendations import (
        build_user_interest_profile,
        collect_product_ids_from_log,
        extract_profile_terms,
        load_user_behavior_logs,
    )

    app_settings = settings or get_app_settings()
    embedding_provider = provider or get_embedding_provider(app_settings)
    embedding_bundle = bundle or get_embedding_bundle(app_settings)
    profile = build_user_interest_profile(db, user_id=user_id, provider=embedding_provider)
    db.expire_all()

    logs = load_user_behavior_logs(db, user_id)
    top_terms, consumed_product_ids = extract_profile_terms(profile)
    recent_product_ids = extract_recent_product_ids(logs, collect_product_ids_from_log)
    cold_start = profile.behavior_count < 2 or not top_terms

    recall_results: dict[str, list[RecallItem]] = {}
    if not cold_start:
        try:
            recall_results["content_profile"] = recall_profile_content_candidates(
                profile,
                top_terms=top_terms,
                consumed_product_ids=consumed_product_ids,
                settings=app_settings,
                client=client,
            )
            recall_results["sparse_interest"] = recall_sparse_interest_candidates(
                top_terms=top_terms,
                consumed_product_ids=consumed_product_ids,
                settings=app_settings,
                client=client,
                bundle=embedding_bundle,
            )
            recall_results["related_products"] = recall_related_product_candidates(
                recent_product_ids,
                consumed_product_ids=consumed_product_ids,
                settings=app_settings,
                client=client,
            )
        except Exception as exc:  # pragma: no cover - runtime fallback protection
            logger.warning(
                "Qdrant-dependent recommendation recalls failed. user_id=%s error=%s",
                user_id,
                exc,
            )

        recall_results["collaborative"] = recall_collaborative_candidates(
            db,
            user_id=user_id,
            consumed_product_ids=consumed_product_ids,
            recent_product_ids=recent_product_ids,
            top_terms=top_terms,
        )

    recall_results["trending"] = recall_trending_candidates(
        db,
        consumed_product_ids=consumed_product_ids,
    )
    recall_results["new_arrival"] = recall_new_arrival_candidates(
        db,
        consumed_product_ids=consumed_product_ids,
    )
    if cold_start:
        recall_results["cold_start"] = build_cold_start_candidates(
            trending_items=recall_results["trending"],
            new_arrival_items=recall_results["new_arrival"],
        )

    fused_candidates = fuse_recall_results(recall_results)
    products_by_id = load_pipeline_products(
        db,
        product_ids=[candidate.product_id for candidate in fused_candidates],
    )
    filtered_candidates = [
        candidate
        for candidate in fused_candidates
        if (
            candidate.product_id not in consumed_product_ids
            and candidate.product_id in products_by_id
        )
    ]
    diversified_candidates = diversify_candidates(
        filtered_candidates,
        products_by_id=products_by_id,
        limit=candidate_limit or max(limit * 4, 24),
    )

    pipeline_candidates = [
        build_pipeline_candidate(candidate, products_by_id[candidate.product_id])
        for candidate in diversified_candidates
        if candidate.product_id in products_by_id
    ]

    return RecommendationPipelineRun(
        profile=profile,
        candidates=pipeline_candidates,
        recall_results=recall_results,
        top_terms=top_terms,
        consumed_product_ids=consumed_product_ids,
        recent_product_ids=recent_product_ids,
        cold_start=cold_start,
    )


def extract_recent_product_ids(
    logs: list[UserBehaviorLog],
    collect_product_ids_from_log,
) -> list[int]:
    recent_ids: list[int] = []
    for log in reversed(logs):
        for product_id in collect_product_ids_from_log(log):
            if product_id not in recent_ids:
                recent_ids.append(product_id)
        if len(recent_ids) >= 3:
            break
    return recent_ids[:3]


def build_cold_start_candidates(
    *,
    trending_items: list[RecallItem],
    new_arrival_items: list[RecallItem],
) -> list[RecallItem]:
    items_by_id: dict[int, RecallItem] = {}
    for rank, item in enumerate([*trending_items[:6], *new_arrival_items[:6]], start=1):
        if item.product_id in items_by_id:
            continue
        items_by_id[item.product_id] = RecallItem(
            product_id=item.product_id,
            recall_channel="cold_start",
            recall_score=item.recall_score,
            rank_in_channel=rank,
            matched_terms=item.matched_terms,
            reason_parts=["冷启动兜底", *item.reason_parts],
        )
    return list(items_by_id.values())


def load_pipeline_products(
    db: Session,
    *,
    product_ids: list[int],
) -> dict[int, Product]:
    if not product_ids:
        return {}

    products = db.scalars(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
            selectinload(Product.embedding),
        )
        .where(Product.id.in_(product_ids), Product.status == 1)
    ).unique().all()

    return {
        product.id: product
        for product in products
        if product_has_available_stock(product)
    }


def build_pipeline_candidate(
    fused_candidate: FusedRecommendationCandidate,
    product: Product,
) -> PipelineRecommendationCandidate:
    return PipelineRecommendationCandidate(
        product=product,
        score=fused_candidate.score,
        reason=build_fused_reason(fused_candidate),
        matched_terms=list(fused_candidate.matched_terms),
        recall_channels=list(fused_candidate.recall_channels),
        channel_details=list(fused_candidate.channel_details),
        vector_similarity=fused_candidate.vector_similarity,
        vector_score=fused_candidate.vector_score,
        term_bonus=fused_candidate.term_bonus,
    )

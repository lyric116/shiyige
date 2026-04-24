from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import get_app_settings
from backend.app.models.product import Product
from backend.app.models.recommendation import UserInterestProfile
from backend.app.models.user import UserBehaviorLog
from backend.app.services.embedding import EmbeddingProvider, get_embedding_provider
from backend.app.services.embedding_text import build_embedding_content_hash, normalize_text_piece
from backend.app.services.vector_search import (
    VectorSearchResult,
    cosine_similarity,
    ensure_product_embeddings,
)

BEHAVIOR_WEIGHTS = {
    "view_product": 1,
    "search": 2,
    "add_to_cart": 3,
    "create_order": 5,
    "pay_order": 5,
}


@dataclass
class RecommendationCandidate:
    product: Product
    score: float
    reason: str
    matched_terms: list[str]
    similarity: float
    vector_score: float
    term_bonus: float


def load_user_behavior_logs(db: Session, user_id: int) -> list[UserBehaviorLog]:
    return db.scalars(
        select(UserBehaviorLog)
        .where(UserBehaviorLog.user_id == user_id)
        .order_by(UserBehaviorLog.created_at.asc(), UserBehaviorLog.id.asc())
    ).all()


def collect_product_ids_from_log(log: UserBehaviorLog) -> list[int]:
    if log.target_type == "product" and log.target_id is not None:
        return [log.target_id]
    if log.target_type == "order":
        product_ids = log.ext_json.get("product_ids") if log.ext_json else []
        return [int(product_id) for product_id in product_ids]
    return []


def load_products_for_interest_profile(db: Session, product_ids: set[int]) -> dict[int, Product]:
    if not product_ids:
        return {}

    products = db.scalars(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.embedding),
            selectinload(Product.skus),
        )
        .where(Product.id.in_(sorted(product_ids)))
    ).unique().all()
    return {product.id: product for product in products}


def load_active_products_for_recommendations(db: Session) -> list[Product]:
    return db.scalars(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.skus),
            selectinload(Product.embedding),
        )
        .where(Product.status == 1)
    ).unique().all()


def build_profile_segments(
    logs: list[UserBehaviorLog],
    products_by_id: dict[int, Product],
) -> tuple[list[str], dict[str, float], set[int], datetime | None]:
    segments: list[str] = []
    weighted_terms: dict[str, float] = defaultdict(float)
    consumed_product_ids: set[int] = set()
    last_event_at: datetime | None = None

    for log in logs:
        weight = BEHAVIOR_WEIGHTS.get(log.behavior_type, 0)
        if weight <= 0:
            continue

        last_event_at = log.created_at
        query = normalize_text_piece(log.ext_json.get("query") if log.ext_json else None)
        if query:
            segments.extend([query] * weight)
            weighted_terms[query] += weight

        for product_id in collect_product_ids_from_log(log):
            consumed_product_ids.add(product_id)
            product = products_by_id.get(product_id)
            if product is None or product.embedding is None:
                continue

            segments.extend([product.embedding.embedding_text] * weight)
            for raw_term in [
                product.category.name if product.category else None,
                product.dynasty_style,
                product.scene_tag,
                product.craft_type,
            ]:
                term = normalize_text_piece(raw_term)
                if term:
                    weighted_terms[term] += weight

            for tag in product.tags:
                term = normalize_text_piece(tag.tag)
                if term:
                    weighted_terms[term] += weight

    return segments, weighted_terms, consumed_product_ids, last_event_at


def build_user_interest_profile(
    db: Session,
    *,
    user_id: int,
    provider: EmbeddingProvider | None = None,
) -> UserInterestProfile:
    settings = get_app_settings()
    embedding_provider = provider or get_embedding_provider()
    ensure_product_embeddings(db, embedding_provider)
    db.expire_all()

    logs = load_user_behavior_logs(db, user_id)
    product_ids: set[int] = set()
    for log in logs:
        product_ids.update(collect_product_ids_from_log(log))

    products_by_id = load_products_for_interest_profile(db, product_ids)
    segments, weighted_terms, consumed_product_ids, last_event_at = build_profile_segments(
        logs,
        products_by_id,
    )

    profile_text = "\n".join(segments) if segments else None
    content_hash = build_embedding_content_hash(profile_text) if profile_text else None
    profile = db.scalar(select(UserInterestProfile).where(UserInterestProfile.user_id == user_id))

    if profile is None:
        profile = UserInterestProfile(
            user_id=user_id,
            model_name=embedding_provider.descriptor.model_name,
        )

    profile.model_name = embedding_provider.descriptor.model_name
    profile.profile_text = profile_text
    profile.behavior_count = len(logs)
    profile.last_event_at = last_event_at
    profile.qdrant_user_point_id = str(user_id)
    profile.profile_version = settings.recommendation_pipeline_version
    profile.ext_json = {
        "top_terms": [
            term
            for term, _weight in sorted(
                weighted_terms.items(),
                key=lambda item: (item[1], item[0]),
                reverse=True,
            )[:8]
        ],
        "consumed_product_ids": sorted(consumed_product_ids),
    }

    if not profile_text:
        profile.embedding_vector = None
        profile.content_hash = None
        profile.last_synced_at = None
        profile.last_built_at = datetime.utcnow()
    elif (
        profile.content_hash != content_hash
        or profile.model_name != embedding_provider.descriptor.model_name
        or not profile.embedding_vector
    ):
        profile.embedding_vector = embedding_provider.embed_query(profile_text)
        profile.content_hash = content_hash
        profile.last_synced_at = None
        profile.last_built_at = datetime.utcnow()

    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def build_recommendation_reason(matched_terms: list[str]) -> str:
    if matched_terms:
        return f"基于你近期关注的“{'/'.join(matched_terms[:3])}”偏好推荐"
    return "基于你近期兴趣偏好推荐"


def extract_profile_terms(profile: UserInterestProfile) -> tuple[list[str], set[int]]:
    if not profile.ext_json:
        return [], set()

    top_terms = list(profile.ext_json.get("top_terms", []))
    consumed_product_ids = {
        int(product_id)
        for product_id in profile.ext_json.get("consumed_product_ids", [])
    }
    return top_terms, consumed_product_ids


def score_recommendation_candidate(
    profile: UserInterestProfile,
    product: Product,
    *,
    top_terms: list[str],
    consumed_product_ids: set[int],
) -> RecommendationCandidate | None:
    if product.id in consumed_product_ids:
        return None
    if product.embedding is None or not product.embedding.embedding_vector:
        return None

    if profile.embedding_vector:
        similarity = cosine_similarity(profile.embedding_vector, product.embedding.embedding_vector)
        vector_score = ((similarity + 1) / 2) * 0.35
    else:
        similarity = 0.0
        vector_score = product.id / 1000

    product_tags = {tag.tag for tag in product.tags}
    matched_terms: list[str] = []
    for term in top_terms:
        if product.category and product.category.name == term and term not in matched_terms:
            matched_terms.append(term)
        if term in product_tags and term not in matched_terms:
            matched_terms.append(term)
        if term == product.dynasty_style and term not in matched_terms:
            matched_terms.append(term)
        if term == product.scene_tag and term not in matched_terms:
            matched_terms.append(term)
        if term == product.craft_type and term not in matched_terms:
            matched_terms.append(term)

    term_bonus = min(len(matched_terms) * 0.18, 0.54)
    return RecommendationCandidate(
        product=product,
        score=vector_score + term_bonus,
        reason=build_recommendation_reason(matched_terms),
        matched_terms=matched_terms,
        similarity=similarity,
        vector_score=vector_score,
        term_bonus=term_bonus,
    )


def rank_recommendation_candidates(
    products: list[Product],
    profile: UserInterestProfile,
) -> list[RecommendationCandidate]:
    top_terms, consumed_product_ids = extract_profile_terms(profile)

    results: list[RecommendationCandidate] = []
    for product in products:
        scored_candidate = score_recommendation_candidate(
            profile,
            product,
            top_terms=top_terms,
            consumed_product_ids=consumed_product_ids,
        )
        if scored_candidate is not None:
            results.append(scored_candidate)

    results.sort(key=lambda item: (item.score, item.product.id), reverse=True)
    return results


def recommend_products_for_user(
    db: Session,
    *,
    user_id: int,
    limit: int = 6,
    provider: EmbeddingProvider | None = None,
) -> list[VectorSearchResult]:
    embedding_provider = provider or get_embedding_provider()
    profile = build_user_interest_profile(db, user_id=user_id, provider=embedding_provider)
    db.expire_all()

    products = load_active_products_for_recommendations(db)
    candidates = rank_recommendation_candidates(products, profile)
    return [
        VectorSearchResult(
            product=candidate.product,
            score=candidate.score,
            reason=candidate.reason,
        )
        for candidate in candidates[:limit]
    ]

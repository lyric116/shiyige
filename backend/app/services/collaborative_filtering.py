from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from qdrant_client import QdrantClient, models
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.core.logger import get_logger
from backend.app.models.product import Product, ProductSku
from backend.app.models.recommendation_experiment import RecommendationExperiment
from backend.app.models.user import UserBehaviorLog
from backend.app.services.candidate_fusion import RecallItem
from backend.app.services.product_index_document import product_has_available_stock
from backend.app.services.qdrant_client import create_qdrant_client

COLLABORATIVE_BEHAVIOR_WEIGHTS = {
    "impression": -0.1,
    "view_product": 1.0,
    "search_click": 2.0,
    "favorite": 3.0,
    "add_to_cart": 4.0,
    "create_order": 5.0,
    "pay_order": 6.0,
    "refund_order": -2.0,
    "cancel_order": -2.0,
}

COLLABORATIVE_ITEM_EXPERIMENT_KEY = "collaborative_item_cooccurrence_v1"
logger = get_logger(__name__)


def build_user_sparse_vector(
    logs: list[UserBehaviorLog],
    *,
    now: datetime | None = None,
) -> models.SparseVector:
    interaction_weights = build_user_interaction_weights(logs, now=now)
    ordered_items = sorted(interaction_weights.items(), key=lambda item: item[0])
    return models.SparseVector(
        indices=[product_id for product_id, _score in ordered_items],
        values=[score for _product_id, score in ordered_items],
    )


def build_user_interaction_weights(
    logs: list[UserBehaviorLog],
    *,
    now: datetime | None = None,
) -> dict[int, float]:
    reference_time = now or datetime.utcnow()
    product_scores: dict[int, float] = defaultdict(float)
    for log in logs:
        product_ids = collect_product_ids_from_log(log)
        if not product_ids:
            continue

        weight = COLLABORATIVE_BEHAVIOR_WEIGHTS.get(log.behavior_type, 0.0)
        if weight == 0.0:
            continue
        decay = compute_time_decay(
            log.created_at,
            behavior_type=log.behavior_type,
            now=reference_time,
        )
        for product_id in product_ids:
            product_scores[product_id] += weight * decay
    return product_scores


def compute_time_decay(
    created_at: datetime,
    *,
    behavior_type: str,
    now: datetime,
) -> float:
    age_days = max((now - created_at).days, 0)
    if age_days <= 7:
        decay = 1.0
    elif age_days <= 30:
        decay = 0.72
    elif age_days <= 90:
        decay = 0.42
    else:
        decay = 0.2

    if behavior_type in {"favorite", "add_to_cart"}:
        decay += 0.08
    elif behavior_type in {"create_order", "pay_order"}:
        decay += 0.15
    return max(decay, 0.05)


def query_similar_users(
    sparse_vector: models.SparseVector,
    *,
    user_id: int,
    limit: int = 6,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
) -> list[tuple[int, float]]:
    if not sparse_vector.indices:
        return []

    app_settings = settings or get_app_settings()
    qdrant_client = client or create_qdrant_client(app_settings)
    owns_client = client is None
    try:
        try:
            response = qdrant_client.query_points(
                collection_name=app_settings.qdrant_collection_cf,
                query=sparse_vector,
                using="interactions",
                limit=limit + 1,
                with_payload=True,
                with_vectors=False,
            )
        except Exception as exc:  # pragma: no cover - runtime fallback protection
            logger.warning(
                "Collaborative user vector search is unavailable. user_id=%s error=%s",
                user_id,
                exc,
            )
            return []

        similar_users: list[tuple[int, float]] = []
        for point in response.points:
            payload = dict(point.payload or {})
            candidate_user_id = int(payload.get("user_id") or point.id)
            if candidate_user_id == user_id:
                continue
            similar_users.append((candidate_user_id, float(point.score)))
            if len(similar_users) >= limit:
                break
        return similar_users
    finally:
        if owns_client:
            close = getattr(qdrant_client, "close", None)
            if callable(close):
                close()


def recall_collaborative_user_candidates(
    db: Session,
    *,
    user_id: int,
    consumed_product_ids: set[int],
    top_terms: list[str],
    limit: int = 16,
    settings: AppSettings | None = None,
    client: QdrantClient | None = None,
) -> list[RecallItem]:
    user_logs = load_user_logs(db, user_id)
    sparse_vector = build_user_sparse_vector(user_logs)
    similar_users = query_similar_users(
        sparse_vector,
        user_id=user_id,
        limit=6,
        settings=settings,
        client=client,
    )
    if not similar_users:
        return []

    similar_user_scores = {candidate_user_id: score for candidate_user_id, score in similar_users}
    candidate_logs = db.scalars(
        select(UserBehaviorLog)
        .where(
            UserBehaviorLog.user_id.in_(sorted(similar_user_scores)),
            UserBehaviorLog.target_type == "product",
        )
        .order_by(UserBehaviorLog.created_at.desc(), UserBehaviorLog.id.desc())
    ).all()

    candidate_scores: dict[int, float] = defaultdict(float)
    support_users: dict[int, set[int]] = defaultdict(set)
    for log in candidate_logs:
        product_ids = collect_product_ids_from_log(log)
        if not product_ids:
            continue
        weight = COLLABORATIVE_BEHAVIOR_WEIGHTS.get(log.behavior_type, 0.0)
        if weight == 0.0:
            continue
        decay = compute_time_decay(
            log.created_at,
            behavior_type=log.behavior_type,
            now=datetime.utcnow(),
        )
        for product_id in product_ids:
            if product_id in consumed_product_ids:
                continue
            candidate_scores[product_id] += (
                similar_user_scores.get(log.user_id, 0.0) * weight * decay
            )
            support_users[product_id].add(log.user_id)

    ranked_product_ids = [
        product_id
        for product_id, _score in sorted(
            candidate_scores.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )[: limit * 2]
    ]
    products_by_id = load_active_products_by_id(db, ranked_product_ids)

    results: list[RecallItem] = []
    for rank, product_id in enumerate(ranked_product_ids, start=1):
        product = products_by_id.get(product_id)
        if product is None:
            continue
        results.append(
            RecallItem(
                product_id=product_id,
                recall_channel="collaborative_user",
                recall_score=float(candidate_scores[product_id]),
                rank_in_channel=rank,
                matched_terms=match_product_terms(product, top_terms),
                reason_parts=[
                    "协同过滤召回",
                    f"来自{len(support_users[product_id])}位相似用户的行为偏好",
                ],
                metadata={"support_users": len(support_users[product_id])},
            )
        )
        if len(results) >= limit:
            break
    return results


def recall_item_cooccurrence_candidates(
    db: Session,
    *,
    seed_product_ids: list[int],
    consumed_product_ids: set[int],
    top_terms: list[str],
    limit: int = 16,
) -> list[RecallItem]:
    if not seed_product_ids:
        return []

    cooccurrence_map = load_item_cooccurrence_map(db)
    if not cooccurrence_map:
        cooccurrence_map = build_item_cooccurrence_map(db)

    candidate_scores: dict[int, float] = defaultdict(float)
    support_seed_ids: dict[int, set[int]] = defaultdict(set)
    for seed_product_id in seed_product_ids[:3]:
        for item in cooccurrence_map.get(str(seed_product_id), []):
            product_id = int(item["product_id"])
            if product_id in consumed_product_ids or product_id == seed_product_id:
                continue
            candidate_scores[product_id] += float(item["score"])
            support_seed_ids[product_id].add(seed_product_id)

    ranked_product_ids = [
        product_id
        for product_id, _score in sorted(
            candidate_scores.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )[: limit * 2]
    ]
    products_by_id = load_active_products_by_id(db, ranked_product_ids)

    results: list[RecallItem] = []
    for rank, product_id in enumerate(ranked_product_ids, start=1):
        product = products_by_id.get(product_id)
        if product is None:
            continue
        results.append(
            RecallItem(
                product_id=product_id,
                recall_channel="item_cooccurrence",
                recall_score=float(candidate_scores[product_id]),
                rank_in_channel=rank,
                matched_terms=match_product_terms(product, top_terms),
                reason_parts=["商品共现召回", "与最近行为商品存在共看/共购关系"],
                metadata={"seed_product_ids": sorted(support_seed_ids[product_id])},
            )
        )
        if len(results) >= limit:
            break
    return results


def build_item_cooccurrence_map(
    db: Session,
    *,
    top_k: int = 12,
) -> dict[str, list[dict[str, float | int]]]:
    logs = db.scalars(
        select(UserBehaviorLog)
        .where(
            UserBehaviorLog.target_type == "product",
            UserBehaviorLog.target_id.is_not(None),
        )
        .order_by(
            UserBehaviorLog.user_id.asc(),
            UserBehaviorLog.created_at.asc(),
            UserBehaviorLog.id.asc(),
        )
    ).all()

    user_vectors: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for log in logs:
        product_ids = collect_product_ids_from_log(log)
        if not product_ids:
            continue
        weight = COLLABORATIVE_BEHAVIOR_WEIGHTS.get(log.behavior_type, 0.0)
        if weight <= 0:
            continue
        decay = compute_time_decay(
            log.created_at,
            behavior_type=log.behavior_type,
            now=datetime.utcnow(),
        )
        for product_id in product_ids:
            user_vectors[log.user_id][product_id] += weight * decay

    cooccurrence_scores: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    for product_scores in user_vectors.values():
        product_ids = sorted(product_scores)
        for index, left_product_id in enumerate(product_ids):
            for right_product_id in product_ids[index + 1 :]:
                score = min(product_scores[left_product_id], product_scores[right_product_id])
                cooccurrence_scores[left_product_id][right_product_id] += score
                cooccurrence_scores[right_product_id][left_product_id] += score

    return {
        str(product_id): [
            {"product_id": related_product_id, "score": round(score, 6)}
            for related_product_id, score in sorted(
                related_scores.items(),
                key=lambda item: (item[1], item[0]),
                reverse=True,
            )[:top_k]
        ]
        for product_id, related_scores in cooccurrence_scores.items()
    }


def load_item_cooccurrence_map(db: Session) -> dict[str, list[dict[str, float | int]]]:
    experiment = db.scalar(
        select(RecommendationExperiment).where(
            RecommendationExperiment.experiment_key == COLLABORATIVE_ITEM_EXPERIMENT_KEY
        )
    )
    if experiment is None or not experiment.artifact_json:
        return {}
    return dict(experiment.artifact_json.get("item_cooccurrence") or {})


def load_user_logs(db: Session, user_id: int) -> list[UserBehaviorLog]:
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


def load_active_products_by_id(
    db: Session,
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
        )
        .where(Product.id.in_(product_ids), Product.status == 1)
    ).unique().all()
    return {
        product.id: product
        for product in products
        if product_has_available_stock(product)
    }


def match_product_terms(product: Product, top_terms: list[str]) -> list[str]:
    product_terms = {
        value
        for value in [
            product.category.name if product.category else None,
            product.dynasty_style,
            product.craft_type,
            product.scene_tag,
            product.festival_tag,
            *(tag.tag for tag in product.tags),
        ]
        if value
    }
    return [term for term in top_terms if term in product_terms][:4]

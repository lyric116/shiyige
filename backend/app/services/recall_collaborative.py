from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.product import Product, ProductSku
from backend.app.models.user import UserBehaviorLog
from backend.app.services.candidate_fusion import RecallItem
from backend.app.services.product_index_document import product_has_available_stock

COLLABORATIVE_BEHAVIOR_WEIGHTS = {
    "view_product": 1.0,
    "search": 0.8,
    "add_to_cart": 2.5,
    "create_order": 3.0,
    "pay_order": 3.5,
}


def recall_collaborative_candidates(
    db: Session,
    *,
    user_id: int,
    consumed_product_ids: set[int],
    recent_product_ids: list[int],
    top_terms: list[str],
    limit: int = 24,
) -> list[RecallItem]:
    seed_product_ids = list(dict.fromkeys(recent_product_ids + sorted(consumed_product_ids)))[:5]
    if not seed_product_ids:
        return []

    overlap_logs = db.scalars(
        select(UserBehaviorLog)
        .where(
            UserBehaviorLog.user_id != user_id,
            UserBehaviorLog.target_type == "product",
            UserBehaviorLog.target_id.in_(seed_product_ids),
        )
        .order_by(UserBehaviorLog.created_at.desc(), UserBehaviorLog.id.desc())
    ).all()

    similar_user_scores: dict[int, float] = defaultdict(float)
    for log in overlap_logs:
        similar_user_scores[log.user_id] += COLLABORATIVE_BEHAVIOR_WEIGHTS.get(
            log.behavior_type,
            0.5,
        )

    if not similar_user_scores:
        return []

    similar_user_ids = [
        user_id
        for user_id, _score in sorted(
            similar_user_scores.items(),
            key=lambda item: (item[1], item[0]),
            reverse=True,
        )[:8]
    ]

    candidate_logs = db.scalars(
        select(UserBehaviorLog)
        .where(
            UserBehaviorLog.user_id.in_(similar_user_ids),
            UserBehaviorLog.target_type == "product",
        )
        .order_by(UserBehaviorLog.created_at.desc(), UserBehaviorLog.id.desc())
    ).all()

    candidate_scores: dict[int, float] = defaultdict(float)
    candidate_users: dict[int, set[int]] = defaultdict(set)
    for log in candidate_logs:
        if log.target_id is None or log.target_id in consumed_product_ids:
            continue

        behavior_weight = COLLABORATIVE_BEHAVIOR_WEIGHTS.get(log.behavior_type, 0.5)
        candidate_scores[log.target_id] += (
            similar_user_scores.get(log.user_id, 0.0) * behavior_weight
        )
        candidate_users[log.target_id].add(log.user_id)

    if not candidate_scores:
        return []

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

        matched_terms = match_product_against_terms(product, top_terms)
        results.append(
            RecallItem(
                product_id=product_id,
                recall_channel="collaborative",
                recall_score=float(candidate_scores[product_id]),
                rank_in_channel=rank,
                matched_terms=matched_terms,
                reason_parts=[
                    "协同过滤召回",
                    f"来自{len(candidate_users[product_id])}位相似用户的共同行为",
                ],
                metadata={"support_users": len(candidate_users[product_id])},
            )
        )
        if len(results) >= limit:
            break

    return results


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


def match_product_against_terms(product: Product, top_terms: list[str]) -> list[str]:
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

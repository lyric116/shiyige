from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.product import Product, ProductSku
from backend.app.models.user import UserBehaviorLog
from backend.app.services.candidate_fusion import RecallItem
from backend.app.services.product_index_document import product_has_available_stock

TRENDING_BEHAVIOR_WEIGHTS = {
    "view_product": 1.0,
    "search": 0.6,
    "add_to_cart": 2.0,
    "create_order": 2.5,
    "pay_order": 3.0,
}


def recall_trending_candidates(
    db: Session,
    *,
    consumed_product_ids: set[int],
    limit: int = 18,
    now: datetime | None = None,
) -> list[RecallItem]:
    reference_time = now or datetime.utcnow()
    recent_logs = db.scalars(
        select(UserBehaviorLog)
        .where(
            UserBehaviorLog.target_type == "product",
            UserBehaviorLog.target_id.is_not(None),
            UserBehaviorLog.created_at >= reference_time - timedelta(days=7),
        )
        .order_by(UserBehaviorLog.created_at.desc(), UserBehaviorLog.id.desc())
    ).all()
    if not recent_logs:
        recent_logs = db.scalars(
            select(UserBehaviorLog)
            .where(
                UserBehaviorLog.target_type == "product",
                UserBehaviorLog.target_id.is_not(None),
            )
            .order_by(UserBehaviorLog.created_at.desc(), UserBehaviorLog.id.desc())
            .limit(500)
        ).all()

    product_scores: dict[int, float] = defaultdict(float)
    for log in recent_logs:
        if log.target_id is None or log.target_id in consumed_product_ids:
            continue
        product_scores[log.target_id] += TRENDING_BEHAVIOR_WEIGHTS.get(log.behavior_type, 0.5)

    if not product_scores:
        return []

    ranked_product_ids = [
        product_id
        for product_id, _score in sorted(
            product_scores.items(),
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
                recall_channel="trending",
                recall_score=float(product_scores[product_id]),
                rank_in_channel=rank,
                matched_terms=[
                    term
                    for term in [product.festival_tag, product.scene_tag]
                    if term
                ][:2],
                reason_parts=["热门趋势召回", "来自近 7 天站内热度"],
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

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.product import Product, ProductSku
from backend.app.services.candidate_fusion import RecallItem
from backend.app.services.product_index_document import product_has_available_stock


def recall_new_arrival_candidates(
    db: Session,
    *,
    consumed_product_ids: set[int],
    limit: int = 18,
) -> list[RecallItem]:
    products = (
        db.scalars(
            select(Product)
            .options(
                selectinload(Product.tags),
                selectinload(Product.skus).selectinload(ProductSku.inventory),
            )
            .where(Product.status == 1)
            .order_by(Product.created_at.desc(), Product.id.desc())
            .limit(limit * 3)
        )
        .unique()
        .all()
    )

    results: list[RecallItem] = []
    for rank, product in enumerate(products, start=1):
        if product.id in consumed_product_ids or not product_has_available_stock(product):
            continue

        results.append(
            RecallItem(
                product_id=product.id,
                recall_channel="new_arrival",
                recall_score=float(max(limit * 3 - rank, 1)),
                rank_in_channel=rank,
                matched_terms=[term for term in [product.festival_tag, product.scene_tag] if term][
                    :2
                ],
                reason_parts=["新品探索召回", "补充低曝光新商品"],
            )
        )
        if len(results) >= limit:
            break

    return results

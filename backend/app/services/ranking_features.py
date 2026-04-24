from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from math import log1p

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.order import Order, OrderItem
from backend.app.models.product import Product, ProductSku
from backend.app.models.review import Review
from backend.app.models.user import UserBehaviorLog
from backend.app.services.candidate_fusion import FusedRecommendationCandidate


@dataclass(slots=True)
class ProductRankingMetrics:
    sales_count: int = 0
    view_count: int = 0
    add_to_cart_count: int = 0
    cancel_count: int = 0
    rating_avg: float = 0.0
    review_count: int = 0


@dataclass(slots=True)
class RankingFeatureContext:
    user_id: int
    top_terms: list[str]
    consumed_product_ids: set[int]
    recent_product_ids: list[int]
    current_time: datetime
    recent_categories: set[int]
    recent_tags: set[str]
    recent_dynasties: set[str]
    recent_crafts: set[str]
    recent_scenes: set[str]
    recent_festivals: set[str]
    preferred_price: float | None
    product_metrics: dict[int, ProductRankingMetrics]
    user_recent_view_counts: dict[int, int]
    user_recent_positive_counts: dict[int, int]


@dataclass(slots=True)
class RecommendationRankingFeatures:
    dense_recall_score: float = 0.0
    sparse_recall_score: float = 0.0
    colbert_rerank_score: float = 0.0
    collaborative_score: float = 0.0
    item_cooccurrence_score: float = 0.0
    rrf_fusion_score: float = 0.0
    recall_channel_count: float = 0.0
    best_channel_rank: float = 0.0
    category_match: float = 0.0
    tag_match_count: float = 0.0
    dynasty_match: float = 0.0
    craft_match: float = 0.0
    scene_match: float = 0.0
    festival_match: float = 0.0
    price_affinity: float = 0.0
    user_recent_interest_score: float = 0.0
    user_long_term_interest_score: float = 0.0
    sales_count: float = 0.0
    conversion_rate: float = 0.0
    add_to_cart_rate: float = 0.0
    rating_avg: float = 0.0
    review_count: float = 0.0
    stock_available: float = 0.0
    return_rate: float = 0.0
    freshness_score: float = 0.0
    content_quality_score: float = 0.0
    is_listed: float = 0.0
    has_stock: float = 0.0
    price_filter_pass: float = 0.0
    recently_exposed: float = 0.0
    already_purchased: float = 0.0
    is_editorial_pick: float = 0.0
    festival_theme_match: float = 0.0
    exploration_candidate: float = 0.0

    def to_dict(self) -> dict[str, float]:
        return asdict(self)

    def to_normalized_dict(self) -> dict[str, float]:
        best_channel_rank = 0.0
        if self.best_channel_rank > 0:
            best_channel_rank = 1.0 / float(self.best_channel_rank)

        return {
            "dense_recall_score": normalize_positive_score(self.dense_recall_score),
            "sparse_recall_score": normalize_positive_score(self.sparse_recall_score),
            "colbert_rerank_score": clamp_score(self.colbert_rerank_score),
            "collaborative_score": normalize_positive_score(self.collaborative_score),
            "item_cooccurrence_score": normalize_positive_score(self.item_cooccurrence_score),
            "rrf_fusion_score": min(self.rrf_fusion_score * 24.0, 1.0),
            "recall_channel_count": min(self.recall_channel_count / 6.0, 1.0),
            "best_channel_rank": best_channel_rank,
            "category_match": clamp_score(self.category_match),
            "tag_match_count": min(self.tag_match_count / 3.0, 1.0),
            "dynasty_match": clamp_score(self.dynasty_match),
            "craft_match": clamp_score(self.craft_match),
            "scene_match": clamp_score(self.scene_match),
            "festival_match": clamp_score(self.festival_match),
            "price_affinity": clamp_score(self.price_affinity),
            "user_recent_interest_score": clamp_score(self.user_recent_interest_score),
            "user_long_term_interest_score": clamp_score(self.user_long_term_interest_score),
            "sales_count": min(log1p(self.sales_count) / 3.5, 1.0),
            "conversion_rate": clamp_score(self.conversion_rate),
            "add_to_cart_rate": clamp_score(self.add_to_cart_rate),
            "rating_avg": min(self.rating_avg / 5.0, 1.0),
            "review_count": min(log1p(self.review_count) / 3.0, 1.0),
            "stock_available": clamp_score(self.stock_available),
            "return_rate": clamp_score(self.return_rate),
            "freshness_score": clamp_score(self.freshness_score),
            "content_quality_score": clamp_score(self.content_quality_score),
            "is_listed": clamp_score(self.is_listed),
            "has_stock": clamp_score(self.has_stock),
            "price_filter_pass": clamp_score(self.price_filter_pass),
            "recently_exposed": clamp_score(self.recently_exposed),
            "already_purchased": clamp_score(self.already_purchased),
            "is_editorial_pick": clamp_score(self.is_editorial_pick),
            "festival_theme_match": clamp_score(self.festival_theme_match),
            "exploration_candidate": clamp_score(self.exploration_candidate),
        }


def clamp_score(value: float) -> float:
    return max(0.0, min(float(value), 1.0))


def normalize_positive_score(value: float) -> float:
    if value <= 0:
        return 0.0
    return float(value) / (float(value) + 1.0)


def build_ranking_feature_context(
    db: Session,
    *,
    user_id: int,
    top_terms: list[str],
    consumed_product_ids: set[int],
    recent_product_ids: list[int],
    logs: list[UserBehaviorLog],
    candidate_product_ids: list[int],
    now: datetime | None = None,
) -> RankingFeatureContext:
    reference_time = now or datetime.utcnow()
    context_product_ids = sorted(
        set(consumed_product_ids) | set(recent_product_ids) | set(candidate_product_ids)
    )
    context_products = load_context_products(db, context_product_ids)

    recent_products = [
        context_products[product_id]
        for product_id in recent_product_ids
        if product_id in context_products
    ]
    positive_price_samples = [
        resolve_product_price(context_products[product_id])
        for product_id in recent_product_ids
        if (
            product_id in context_products
            and resolve_product_price(context_products[product_id]) is not None
        )
    ]
    if not positive_price_samples:
        positive_price_samples = [
            resolve_product_price(context_products[product_id])
            for product_id in consumed_product_ids
            if (
                product_id in context_products
                and resolve_product_price(context_products[product_id]) is not None
            )
        ]
    preferred_price = None
    if positive_price_samples:
        preferred_price = sum(positive_price_samples) / float(len(positive_price_samples))

    recent_categories = {product.category_id for product in recent_products}
    recent_tags = {
        tag.tag
        for product in recent_products
        for tag in product.tags
    }
    recent_dynasties = {
        product.dynasty_style
        for product in recent_products
        if product.dynasty_style
    }
    recent_crafts = {
        product.craft_type
        for product in recent_products
        if product.craft_type
    }
    recent_scenes = {
        product.scene_tag
        for product in recent_products
        if product.scene_tag
    }
    recent_festivals = {
        product.festival_tag
        for product in recent_products
        if product.festival_tag
    }

    recent_cutoff = reference_time - timedelta(days=14)
    user_recent_view_counts: dict[int, int] = {}
    user_recent_positive_counts: dict[int, int] = {}
    for log in logs:
        if log.target_type != "product" or log.target_id is None:
            continue
        if log.created_at < recent_cutoff:
            continue
        if log.behavior_type == "view_product":
            user_recent_view_counts[log.target_id] = (
                user_recent_view_counts.get(log.target_id, 0) + 1
            )
        if log.behavior_type in {"add_to_cart", "create_order", "pay_order"}:
            user_recent_positive_counts[log.target_id] = (
                user_recent_positive_counts.get(log.target_id, 0) + 1
            )

    product_metrics = load_product_metrics(db, candidate_product_ids)
    return RankingFeatureContext(
        user_id=user_id,
        top_terms=list(top_terms),
        consumed_product_ids=set(consumed_product_ids),
        recent_product_ids=list(recent_product_ids),
        current_time=reference_time,
        recent_categories=recent_categories,
        recent_tags=recent_tags,
        recent_dynasties=recent_dynasties,
        recent_crafts=recent_crafts,
        recent_scenes=recent_scenes,
        recent_festivals=recent_festivals,
        preferred_price=preferred_price,
        product_metrics=product_metrics,
        user_recent_view_counts=user_recent_view_counts,
        user_recent_positive_counts=user_recent_positive_counts,
    )


def load_context_products(db: Session, product_ids: list[int]) -> dict[int, Product]:
    if not product_ids:
        return {}

    products = db.scalars(
        select(Product)
        .options(
            selectinload(Product.category),
            selectinload(Product.tags),
            selectinload(Product.skus).selectinload(ProductSku.inventory),
            selectinload(Product.media_items),
        )
        .where(Product.id.in_(product_ids))
    ).unique().all()
    return {product.id: product for product in products}


def load_product_metrics(
    db: Session,
    product_ids: list[int],
) -> dict[int, ProductRankingMetrics]:
    metrics = {
        product_id: ProductRankingMetrics()
        for product_id in set(product_ids)
    }
    if not metrics:
        return {}

    sales_rows = db.execute(
        select(
            OrderItem.product_id,
            func.coalesce(func.sum(OrderItem.quantity), 0),
            func.count(OrderItem.id),
        )
        .join(Order, Order.id == OrderItem.order_id)
        .where(
            OrderItem.product_id.in_(sorted(metrics)),
            Order.status == "PAID",
        )
        .group_by(OrderItem.product_id)
    ).all()
    for product_id, sales_count, _paid_orders in sales_rows:
        metric = metrics[int(product_id)]
        metric.sales_count = int(sales_count or 0)

    behavior_rows = db.execute(
        select(
            UserBehaviorLog.target_id,
            func.count().filter(UserBehaviorLog.behavior_type == "view_product"),
            func.count().filter(UserBehaviorLog.behavior_type == "add_to_cart"),
            func.count().filter(
                UserBehaviorLog.behavior_type.in_(("cancel_order", "refund_order"))
            ),
        )
        .where(
            UserBehaviorLog.target_type == "product",
            UserBehaviorLog.target_id.in_(sorted(metrics)),
        )
        .group_by(UserBehaviorLog.target_id)
    ).all()
    for product_id, view_count, add_to_cart_count, cancel_count in behavior_rows:
        metric = metrics[int(product_id)]
        metric.view_count = int(view_count or 0)
        metric.add_to_cart_count = int(add_to_cart_count or 0)
        metric.cancel_count = int(cancel_count or 0)

    review_rows = db.execute(
        select(
            Review.product_id,
            func.count(Review.id),
            func.coalesce(func.avg(Review.rating), 0.0),
        )
        .where(Review.product_id.in_(sorted(metrics)))
        .group_by(Review.product_id)
    ).all()
    for product_id, review_count, rating_avg in review_rows:
        metric = metrics[int(product_id)]
        metric.review_count = int(review_count or 0)
        metric.rating_avg = float(rating_avg or 0.0)

    return metrics


def build_candidate_ranking_features(
    candidate: FusedRecommendationCandidate,
    product: Product,
    *,
    context: RankingFeatureContext,
) -> RecommendationRankingFeatures:
    channel_scores: dict[str, float] = {}
    best_channel_rank = 0
    colbert_rerank_score = 0.0
    for detail in candidate.channel_details:
        channel_scores[detail.recall_channel] = max(
            channel_scores.get(detail.recall_channel, 0.0),
            float(detail.recall_score),
        )
        if best_channel_rank == 0 or detail.rank_in_channel < best_channel_rank:
            best_channel_rank = detail.rank_in_channel
        colbert_rerank_score = max(
            colbert_rerank_score,
            float(detail.metadata.get("colbert_score", 0.0)),
        )

    top_term_set = set(context.top_terms)
    product_tag_set = {tag.tag for tag in product.tags}
    category_match = float(
        (product.category is not None and product.category.name in top_term_set)
        or product.category_id in context.recent_categories
    )
    tag_match_count = float(len(product_tag_set & (top_term_set | context.recent_tags)))
    dynasty_match = float(
        bool(product.dynasty_style)
        and (
            product.dynasty_style in top_term_set
            or product.dynasty_style in context.recent_dynasties
        )
    )
    craft_match = float(
        bool(product.craft_type)
        and (
            product.craft_type in top_term_set
            or product.craft_type in context.recent_crafts
        )
    )
    scene_match = float(
        bool(product.scene_tag)
        and (
            product.scene_tag in top_term_set
            or product.scene_tag in context.recent_scenes
        )
    )
    festival_match = float(
        bool(product.festival_tag)
        and (
            product.festival_tag in top_term_set
            or product.festival_tag in context.recent_festivals
        )
    )

    recent_interest_score = (
        category_match * 0.28
        + min(tag_match_count / 3.0, 1.0) * 0.22
        + dynasty_match * 0.15
        + craft_match * 0.12
        + scene_match * 0.12
        + festival_match * 0.11
    )
    long_term_interest_score = min(
        (
            category_match
            + min(tag_match_count / 3.0, 1.0)
            + dynasty_match
            + craft_match
            + scene_match
            + festival_match
        )
        / 4.0,
        1.0,
    )

    estimated_alignment = min(
        (
            category_match
            + dynasty_match
            + craft_match
            + scene_match
            + festival_match
            + min(tag_match_count / 2.0, 1.0)
        )
        / 4.0,
        1.0,
    )
    colbert_rerank_score = max(colbert_rerank_score, estimated_alignment)

    price_affinity = 0.5
    product_price = resolve_product_price(product)
    if context.preferred_price is not None and product_price is not None:
        baseline = max(context.preferred_price, 1.0)
        price_affinity = max(0.0, 1.0 - abs(product_price - context.preferred_price) / baseline)

    metrics = context.product_metrics.get(product.id, ProductRankingMetrics())
    conversion_rate = 0.0
    add_to_cart_rate = 0.0
    return_rate = 0.0
    if metrics.view_count > 0:
        conversion_rate = min(metrics.sales_count / float(metrics.view_count), 1.0)
        add_to_cart_rate = min(metrics.add_to_cart_count / float(metrics.view_count), 1.0)
        return_rate = min(metrics.cancel_count / float(metrics.view_count), 1.0)

    has_stock = float(product_has_stock(product))
    freshness_score = compute_freshness_score(product, now=context.current_time)
    content_quality_score = compute_content_quality_score(product)
    recently_exposed = float(
        min(context.user_recent_view_counts.get(product.id, 0) / 3.0, 1.0)
    )
    already_purchased = float(product.id in context.consumed_product_ids)
    exploration_candidate = float(
        "new_arrival" in candidate.recall_channels
        or "cold_start" in candidate.recall_channels
        or freshness_score >= 0.7
    )
    editorial_pick = float(
        content_quality_score >= 0.75
        and (metrics.review_count > 0 or metrics.sales_count > 0 or freshness_score >= 0.55)
    )

    return RecommendationRankingFeatures(
        dense_recall_score=max(
            channel_scores.get("content_profile", 0.0),
            channel_scores.get("related_products", 0.0),
        ),
        sparse_recall_score=channel_scores.get("sparse_interest", 0.0),
        colbert_rerank_score=colbert_rerank_score,
        collaborative_score=channel_scores.get("collaborative_user", 0.0),
        item_cooccurrence_score=channel_scores.get("item_cooccurrence", 0.0),
        rrf_fusion_score=candidate.fusion_score,
        recall_channel_count=float(len(candidate.recall_channels)),
        best_channel_rank=float(best_channel_rank),
        category_match=category_match,
        tag_match_count=tag_match_count,
        dynasty_match=dynasty_match,
        craft_match=craft_match,
        scene_match=scene_match,
        festival_match=festival_match,
        price_affinity=price_affinity,
        user_recent_interest_score=min(recent_interest_score, 1.0),
        user_long_term_interest_score=long_term_interest_score,
        sales_count=float(metrics.sales_count),
        conversion_rate=conversion_rate,
        add_to_cart_rate=add_to_cart_rate,
        rating_avg=metrics.rating_avg,
        review_count=float(metrics.review_count),
        stock_available=has_stock,
        return_rate=return_rate,
        freshness_score=freshness_score,
        content_quality_score=content_quality_score,
        is_listed=float(product.status == 1),
        has_stock=has_stock,
        price_filter_pass=1.0,
        recently_exposed=recently_exposed,
        already_purchased=already_purchased,
        is_editorial_pick=editorial_pick,
        festival_theme_match=festival_match,
        exploration_candidate=exploration_candidate,
    )


def resolve_product_price(product: Product) -> float | None:
    sku = product.default_sku
    value = None
    if sku is not None and sku.member_price is not None:
        value = sku.member_price
    elif sku is not None and sku.price is not None:
        value = sku.price
    elif product.lowest_price is not None:
        value = product.lowest_price
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def product_has_stock(product: Product) -> bool:
    default_sku = product.default_sku
    if default_sku is None or default_sku.inventory is None:
        return False
    return default_sku.inventory.quantity > 0


def compute_freshness_score(product: Product, *, now: datetime) -> float:
    age_days = max((now - product.created_at).days, 0)
    if age_days <= 7:
        return 1.0
    if age_days <= 30:
        return 0.82
    if age_days <= 90:
        return 0.52
    return 0.18


def compute_content_quality_score(product: Product) -> float:
    checks = [
        bool(product.cover_url),
        bool(product.subtitle),
        bool(product.description),
        bool(product.culture_summary),
        bool(product.dynasty_style),
        bool(product.craft_type),
        bool(product.scene_tag),
        bool(product.festival_tag),
        len(product.tags) >= 2,
        len(product.media_items) >= 2,
    ]
    return sum(1.0 for check in checks if check) / float(len(checks))

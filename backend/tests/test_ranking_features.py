from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.models.base import Base
from backend.app.models.order import Order, OrderItem
from backend.app.models.product import Product, ProductSku
from backend.app.models.review import Review
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.candidate_fusion import FusedRecommendationCandidate, RecallItem
from backend.app.services.ranking_features import (
    build_candidate_ranking_features,
    build_ranking_feature_context,
)
from backend.scripts.seed_base_data import seed_base_data


def create_user(session: Session, *, email: str, username: str) -> User:
    user = User(
        email=email,
        username=username,
        password_hash="hashed-password",
        role="user",
        is_active=True,
    )
    user.profile = UserProfile(display_name=username)
    session.add(user)
    session.flush()
    return user


def add_user_trace(session: Session, *, user_id: int, product_id: int, query: str) -> None:
    session.add(
        UserBehaviorLog(
            user_id=user_id,
            behavior_type="search",
            target_type="search",
            ext_json={"query": query},
        )
    )
    session.add(
        UserBehaviorLog(
            user_id=user_id,
            behavior_type="view_product",
            target_type="product",
            target_id=product_id,
        )
    )
    session.add(
        UserBehaviorLog(
            user_id=user_id,
            behavior_type="add_to_cart",
            target_type="product",
            target_id=product_id,
        )
    )


def create_paid_order_with_review(
    session: Session,
    *,
    user_id: int,
    product: Product,
) -> None:
    sku = product.default_sku
    assert sku is not None

    order = Order(
        order_no=f"RANKING-{user_id}-{product.id}",
        user_id=user_id,
        status="PAID",
        goods_amount=Decimal("629.00"),
        shipping_amount=Decimal("10.00"),
        payable_amount=Decimal("639.00"),
        recipient_name="测试用户",
        recipient_phone="13800138000",
        recipient_region="北京市 海淀区",
        recipient_detail_address="中关村大街 1 号",
        recipient_postal_code="100000",
        paid_at=product.created_at,
    )
    order.items.append(
        OrderItem(
            product_id=product.id,
            sku_id=sku.id,
            product_name=product.name,
            sku_name=sku.name,
            quantity=1,
            unit_price=sku.price,
            unit_member_price=sku.member_price,
            subtotal_amount=Decimal("629.00"),
        )
    )
    session.add(order)
    session.flush()

    session.add(
        Review(
            user_id=user_id,
            product_id=product.id,
            order_id=order.id,
            rating=5,
            content="很适合春日出游。",
            is_anonymous=False,
        )
    )


def build_fused_candidate(product_id: int) -> FusedRecommendationCandidate:
    channel_details = [
        RecallItem(
            product_id=product_id,
            recall_channel="content_profile",
            recall_score=0.88,
            rank_in_channel=1,
            matched_terms=["汉服"],
        ),
        RecallItem(
            product_id=product_id,
            recall_channel="collaborative_user",
            recall_score=4.6,
            rank_in_channel=1,
            matched_terms=["汉服"],
        ),
        RecallItem(
            product_id=product_id,
            recall_channel="item_cooccurrence",
            recall_score=2.2,
            rank_in_channel=2,
            matched_terms=["宋制"],
        ),
        RecallItem(
            product_id=product_id,
            recall_channel="new_arrival",
            recall_score=6.0,
            rank_in_channel=3,
        ),
    ]
    return FusedRecommendationCandidate(
        product_id=product_id,
        score=0.62,
        fusion_score=0.11,
        vector_similarity=0.88,
        vector_score=0.35,
        term_bonus=0.18,
        matched_terms=["汉服", "宋制"],
        reason_parts=["内容召回", "协同过滤"],
        recall_channels=[detail.recall_channel for detail in channel_details],
        channel_details=channel_details,
    )


def test_build_candidate_ranking_features_exposes_recall_interest_quality_and_business_fields(
    db_engine,
) -> None:
    Base.metadata.create_all(db_engine)
    session = Session(db_engine)
    try:
        seed_base_data(session)

        primary_user = create_user(
            session,
            email="ranking-primary@example.com",
            username="ranking-primary",
        )
        reviewer = create_user(
            session,
            email="ranking-reviewer@example.com",
            username="ranking-reviewer",
        )

        add_user_trace(
            session,
            user_id=primary_user.id,
            product_id=1,
            query="春日汉服",
        )

        candidate_product = session.scalar(
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.tags),
                selectinload(Product.skus).selectinload(ProductSku.inventory),
                selectinload(Product.media_items),
            )
            .where(Product.name == "宋风褙子套装")
        )
        assert candidate_product is not None
        create_paid_order_with_review(
            session,
            user_id=reviewer.id,
            product=candidate_product,
        )
        session.commit()

        context = build_ranking_feature_context(
            session,
            user_id=primary_user.id,
            top_terms=["汉服", "春日", "宋制"],
            consumed_product_ids={1},
            recent_product_ids=[1],
            logs=session.scalars(
                select(UserBehaviorLog)
                .where(UserBehaviorLog.user_id == primary_user.id)
                .order_by(UserBehaviorLog.created_at.asc(), UserBehaviorLog.id.asc())
            ).all(),
            candidate_product_ids=[candidate_product.id],
        )

        features = build_candidate_ranking_features(
            build_fused_candidate(candidate_product.id),
            candidate_product,
            context=context,
        )

        assert features.dense_recall_score > 0
        assert features.collaborative_score > 0
        assert features.item_cooccurrence_score > 0
        assert features.rrf_fusion_score > 0
        assert features.category_match == 1.0
        assert features.tag_match_count >= 0
        assert features.user_recent_interest_score > 0
        assert features.user_long_term_interest_score > 0
        assert features.sales_count == 1.0
        assert features.review_count == 1.0
        assert features.rating_avg == 5.0
        assert features.has_stock == 1.0
        assert features.is_listed == 1.0
        assert features.exploration_candidate == 1.0
        normalized = features.to_normalized_dict()
        assert normalized["collaborative_score"] > 0
        assert normalized["rating_avg"] == 1.0
    finally:
        session.close()

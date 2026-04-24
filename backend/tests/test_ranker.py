from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.config import AppSettings
from backend.app.models.base import Base
from backend.app.models.product import Product, ProductSku
from backend.app.models.user import User, UserBehaviorLog, UserProfile
from backend.app.services.candidate_fusion import FusedRecommendationCandidate, RecallItem
from backend.app.services.ranker import rank_fused_candidates
from backend.app.services.ranking_features import build_ranking_feature_context
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


def add_user_trace(session: Session, *, user_id: int, product_id: int) -> None:
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


def build_candidate(
    *,
    product_id: int,
    recall_items: list[RecallItem],
    matched_terms: list[str],
    fusion_score: float,
    score: float,
) -> FusedRecommendationCandidate:
    return FusedRecommendationCandidate(
        product_id=product_id,
        score=score,
        fusion_score=fusion_score,
        vector_similarity=max((item.recall_score for item in recall_items), default=0.0),
        vector_score=fusion_score,
        term_bonus=0.08,
        matched_terms=matched_terms,
        reason_parts=["测试候选"],
        recall_channels=[item.recall_channel for item in recall_items],
        channel_details=recall_items,
    )


def test_weighted_ranker_prefers_interest_match_and_keeps_exploration_candidate(
    db_engine,
) -> None:
    Base.metadata.create_all(db_engine)
    session = Session(db_engine)
    try:
        seed_base_data(session)
        user = create_user(session, email="ranker@example.com", username="ranker")
        add_user_trace(session, user_id=user.id, product_id=1)

        products = session.scalars(
            select(Product)
            .options(
                selectinload(Product.category),
                selectinload(Product.tags),
                selectinload(Product.skus).selectinload(ProductSku.inventory),
                selectinload(Product.media_items),
            )
            .where(Product.name.in_(["宋风褙子套装", "故宫宫廷香囊", "故宫星空折扇", "景泰蓝花瓶"]))
        ).unique().all()
        products_by_name = {product.name: product for product in products}
        hanfu_candidate = products_by_name["宋风褙子套装"]
        weak_match_candidate = products_by_name["故宫宫廷香囊"]
        exploration_candidate = products_by_name["故宫星空折扇"]
        no_stock_candidate = products_by_name["景泰蓝花瓶"]

        older_time = datetime.utcnow() - timedelta(days=120)
        hanfu_candidate.created_at = older_time
        weak_match_candidate.created_at = older_time
        exploration_candidate.created_at = datetime.utcnow() - timedelta(days=2)
        no_stock_candidate.created_at = older_time
        assert no_stock_candidate.default_sku is not None
        assert no_stock_candidate.default_sku.inventory is not None
        no_stock_candidate.default_sku.inventory.quantity = 0
        session.commit()

        candidates = [
            build_candidate(
                product_id=hanfu_candidate.id,
                recall_items=[
                    RecallItem(
                        product_id=hanfu_candidate.id,
                        recall_channel="content_profile",
                        recall_score=0.76,
                        rank_in_channel=2,
                        matched_terms=["汉服"],
                    ),
                    RecallItem(
                        product_id=hanfu_candidate.id,
                        recall_channel="sparse_interest",
                        recall_score=2.1,
                        rank_in_channel=2,
                        matched_terms=["宋制"],
                    ),
                    RecallItem(
                        product_id=hanfu_candidate.id,
                        recall_channel="collaborative_user",
                        recall_score=5.4,
                        rank_in_channel=1,
                        matched_terms=["汉服"],
                    ),
                ],
                matched_terms=["汉服", "宋制"],
                fusion_score=0.08,
                score=0.52,
            ),
            build_candidate(
                product_id=weak_match_candidate.id,
                recall_items=[
                    RecallItem(
                        product_id=weak_match_candidate.id,
                        recall_channel="content_profile",
                        recall_score=0.96,
                        rank_in_channel=1,
                        matched_terms=[],
                    ),
                ],
                matched_terms=[],
                fusion_score=0.11,
                score=0.61,
            ),
            build_candidate(
                product_id=exploration_candidate.id,
                recall_items=[
                    RecallItem(
                        product_id=exploration_candidate.id,
                        recall_channel="new_arrival",
                        recall_score=8.0,
                        rank_in_channel=1,
                    ),
                    RecallItem(
                        product_id=exploration_candidate.id,
                        recall_channel="trending",
                        recall_score=3.0,
                        rank_in_channel=2,
                    ),
                ],
                matched_terms=["夏日"],
                fusion_score=0.05,
                score=0.4,
            ),
            build_candidate(
                product_id=no_stock_candidate.id,
                recall_items=[
                    RecallItem(
                        product_id=no_stock_candidate.id,
                        recall_channel="content_profile",
                        recall_score=0.93,
                        rank_in_channel=1,
                    ),
                ],
                matched_terms=["陈设"],
                fusion_score=0.12,
                score=0.63,
            ),
        ]

        context = build_ranking_feature_context(
            session,
            user_id=user.id,
            top_terms=["汉服", "宋制", "春日"],
            consumed_product_ids={1},
            recent_product_ids=[1],
            logs=session.scalars(
                select(UserBehaviorLog)
                .where(UserBehaviorLog.user_id == user.id)
                .order_by(UserBehaviorLog.created_at.asc(), UserBehaviorLog.id.asc())
            ).all(),
            candidate_product_ids=[candidate.product_id for candidate in candidates],
        )
        products_by_id = {product.id: product for product in products}

        ranked = rank_fused_candidates(
            candidates,
            products_by_id=products_by_id,
            context=context,
            limit=3,
            settings=AppSettings(
                recommendation_ranker="weighted_ranker",
                recommendation_exploration_ratio=0.2,
                recommendation_max_consecutive_category=1,
            ),
        )

        assert ranked[0].product.id == hanfu_candidate.id
        assert any(candidate.business_rules.exploration_candidate for candidate in ranked)
        assert all(candidate.product.id != no_stock_candidate.id for candidate in ranked)
        assert ranked[0].score_breakdown["recall_score"] > 0
    finally:
        session.close()


def test_ranker_falls_back_to_weighted_when_ltr_model_is_not_available(
    db_engine,
) -> None:
    Base.metadata.create_all(db_engine)
    session = Session(db_engine)
    try:
        seed_base_data(session)
        user = create_user(session, email="ranker-ltr@example.com", username="ranker-ltr")
        add_user_trace(session, user_id=user.id, product_id=1)

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

        candidate = build_candidate(
            product_id=candidate_product.id,
            recall_items=[
                RecallItem(
                    product_id=candidate_product.id,
                    recall_channel="content_profile",
                    recall_score=0.78,
                    rank_in_channel=1,
                    matched_terms=["汉服"],
                ),
            ],
            matched_terms=["汉服"],
            fusion_score=0.08,
            score=0.51,
        )

        context = build_ranking_feature_context(
            session,
            user_id=user.id,
            top_terms=["汉服"],
            consumed_product_ids={1},
            recent_product_ids=[1],
            logs=session.scalars(
                select(UserBehaviorLog)
                .where(UserBehaviorLog.user_id == user.id)
                .order_by(UserBehaviorLog.created_at.asc(), UserBehaviorLog.id.asc())
            ).all(),
            candidate_product_ids=[candidate_product.id],
        )

        ranked = rank_fused_candidates(
            [candidate],
            products_by_id={candidate_product.id: candidate_product},
            context=context,
            limit=1,
            settings=AppSettings(recommendation_ranker="ltr_ranker"),
        )

        assert len(ranked) == 1
        assert ranked[0].ranker_name == "weighted_ranker"
        assert ranked[0].ltr_fallback_used is True
        assert ranked[0].score_breakdown["ltr_model_score"] == 0.0
    finally:
        session.close()

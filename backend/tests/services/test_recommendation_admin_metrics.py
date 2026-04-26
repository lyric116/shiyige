from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.security import hash_password
from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.recommendation_analytics import (
    RecommendationClickLog,
    RecommendationConversionLog,
    RecommendationImpressionLog,
    RecommendationRequestLog,
    SearchRequestLog,
)
from backend.app.models.user import User, UserProfile
from backend.app.services.recommendation_admin import (
    build_experiment_dashboard,
    build_recommendation_metrics,
    build_search_metrics,
)
from backend.scripts.seed_base_data import seed_base_data


def create_session_factory(db_engine) -> sessionmaker[Session]:
    Base.metadata.create_all(db_engine)
    return sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


def create_user(session_factory: sessionmaker[Session], *, email: str, username: str) -> User:
    with session_factory() as session:
        user = User(
            email=email,
            username=username,
            password_hash=hash_password("secret-pass-123"),
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name=username)
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def test_build_recommendation_metrics_includes_channel_and_fallback_breakdowns(
    db_engine,
) -> None:
    session_factory = create_session_factory(db_engine)
    tracked_user = create_user(
        session_factory,
        email="metrics-user@example.com",
        username="metrics-user",
    )

    with session_factory() as session:
        seed_base_data(session)
        product_ids = session.scalars(select(Product.id).order_by(Product.id.asc()).limit(4)).all()
        assert len(product_ids) == 4

        session.add_all(
            [
                RecommendationRequestLog(
                    request_id="metrics-req-1",
                    user_id=tracked_user.id,
                    slot="home",
                    pipeline_version="v1",
                    model_version="weighted-ranker-v1",
                    candidate_count=8,
                    final_product_ids=product_ids[:2],
                    latency_ms=80.0,
                    fallback_used=False,
                ),
                RecommendationRequestLog(
                    request_id="metrics-req-2",
                    user_id=tracked_user.id,
                    slot="cart",
                    pipeline_version="baseline",
                    model_version="baseline",
                    candidate_count=4,
                    final_product_ids=product_ids[2:],
                    latency_ms=120.0,
                    fallback_used=True,
                ),
            ]
        )
        session.add_all(
            [
                RecommendationImpressionLog(
                    request_id="metrics-req-1",
                    user_id=tracked_user.id,
                    product_id=product_ids[0],
                    rank_position=1,
                    recall_channels=["content_profile", "item_cooccurrence"],
                    final_score=0.95,
                    reason="因为你最近浏览了同类商品",
                ),
                RecommendationImpressionLog(
                    request_id="metrics-req-1",
                    user_id=tracked_user.id,
                    product_id=product_ids[1],
                    rank_position=2,
                    recall_channels=["content_profile"],
                    final_score=0.91,
                    reason="因为你最近搜索了相关关键词",
                ),
                RecommendationImpressionLog(
                    request_id="metrics-req-2",
                    user_id=tracked_user.id,
                    product_id=product_ids[2],
                    rank_position=1,
                    recall_channels=["trending", "cold_start"],
                    final_score=0.74,
                    reason="当前节令热门",
                ),
                RecommendationImpressionLog(
                    request_id="metrics-req-2",
                    user_id=tracked_user.id,
                    product_id=product_ids[3],
                    rank_position=2,
                    recall_channels=["item_cooccurrence", "new_arrival"],
                    final_score=0.69,
                    reason="与你购物车商品常被一起浏览",
                ),
            ]
        )
        session.commit()

        metrics = build_recommendation_metrics(session, active_product_count=20)

    assert metrics["request_count"] == 2
    assert metrics["impression_count"] == 4
    assert metrics["unique_user_count"] == 1
    assert metrics["fallback_request_count"] == 1
    assert metrics["fallback_rate"] == 0.5
    assert metrics["cold_start_request_count"] == 1
    assert metrics["exploration_request_count"] == 1
    assert metrics["cold_start_request_rate"] == 0.5
    assert metrics["exploration_hit_rate"] == 0.5
    assert metrics["new_arrival_impression_count"] == 1
    assert metrics["cold_start_impression_count"] == 1
    assert metrics["exploration_impression_count"] == 2
    assert metrics["new_arrival_share"] == 0.25
    assert metrics["exploration_impression_share"] == 0.5
    assert metrics["average_impressions_per_request"] == 2.0
    assert {item["slot"] for item in metrics["slot_breakdown"]} == {"home", "cart"}
    assert any(
        item["pipeline_version"] == "baseline"
        and item["model_version"] == "baseline"
        and item["share"] == 0.5
        for item in metrics["pipeline_breakdown"]
    )
    assert metrics["channel_breakdown"] == [
        {
            "channel": "content_profile",
            "impression_count": 2,
            "appearance_share": 0.5,
        },
        {
            "channel": "item_cooccurrence",
            "impression_count": 2,
            "appearance_share": 0.5,
        },
        {
            "channel": "cold_start",
            "impression_count": 1,
            "appearance_share": 0.25,
        },
        {
            "channel": "new_arrival",
            "impression_count": 1,
            "appearance_share": 0.25,
        },
        {
            "channel": "trending",
            "impression_count": 1,
            "appearance_share": 0.25,
        },
    ]


def test_build_search_metrics_includes_pipeline_breakdown(
    db_engine,
) -> None:
    session_factory = create_session_factory(db_engine)
    tracked_user = create_user(
        session_factory,
        email="metrics-search@example.com",
        username="metrics-search",
    )

    with session_factory() as session:
        session.add_all(
            [
                SearchRequestLog(
                    request_id="search-req-1",
                    user_id=tracked_user.id,
                    query="春日汉服",
                    mode="semantic",
                    pipeline_version="qdrant_hybrid",
                    total_results=6,
                    latency_ms=66.0,
                    filters_json={"category_id": 1},
                ),
                SearchRequestLog(
                    request_id="search-req-2",
                    user_id=tracked_user.id,
                    query="香囊",
                    mode="keyword",
                    pipeline_version="keyword",
                    total_results=4,
                    latency_ms=21.0,
                    filters_json=None,
                ),
                SearchRequestLog(
                    request_id="search-req-3",
                    user_id=tracked_user.id,
                    query="宋代茶具",
                    mode="semantic",
                    pipeline_version="qdrant_hybrid",
                    total_results=5,
                    latency_ms=72.0,
                    filters_json={"craft_type": "茶具"},
                ),
            ]
        )
        session.commit()

        metrics = build_search_metrics(session)

    assert metrics["request_count"] == 3
    assert metrics["semantic_count"] == 2
    assert metrics["keyword_count"] == 1
    assert metrics["average_result_count"] == 5.0
    assert metrics["pipeline_breakdown"] == [
        {
            "mode": "semantic",
            "pipeline_version": "qdrant_hybrid",
            "total": 2,
            "share": 0.6667,
        },
        {
            "mode": "keyword",
            "pipeline_version": "keyword",
            "total": 1,
            "share": 0.3333,
        },
    ]


def test_build_experiment_dashboard_aggregates_variant_traffic_and_effectiveness(
    db_engine,
) -> None:
    session_factory = create_session_factory(db_engine)
    tracked_user = create_user(
        session_factory,
        email="metrics-ab@example.com",
        username="metrics-ab",
    )

    with session_factory() as session:
        seed_base_data(session)
        product_ids = session.scalars(select(Product.id).order_by(Product.id.asc()).limit(3)).all()
        assert len(product_ids) == 3

        session.add_all(
            [
                RecommendationRequestLog(
                    request_id="ab-req-1",
                    user_id=tracked_user.id,
                    slot="home",
                    pipeline_version="baseline",
                    model_version="baseline",
                    candidate_count=6,
                    final_product_ids=product_ids[:2],
                    latency_ms=80.0,
                    fallback_used=True,
                ),
                RecommendationRequestLog(
                    request_id="ab-req-2",
                    user_id=tracked_user.id,
                    slot="home",
                    pipeline_version="v1",
                    model_version="weighted-ranker-v1",
                    candidate_count=6,
                    final_product_ids=product_ids[:2],
                    latency_ms=35.0,
                    fallback_used=False,
                ),
                RecommendationRequestLog(
                    request_id="ab-req-3",
                    user_id=tracked_user.id,
                    slot="cart",
                    pipeline_version="v1",
                    model_version="weighted-ranker-v1",
                    candidate_count=6,
                    final_product_ids=product_ids[1:],
                    latency_ms=30.0,
                    fallback_used=False,
                ),
            ]
        )
        session.add_all(
            [
                RecommendationImpressionLog(
                    request_id="ab-req-1",
                    user_id=tracked_user.id,
                    product_id=product_ids[0],
                    rank_position=1,
                    recall_channels=["cold_start"],
                    final_score=0.6,
                    reason="baseline result",
                ),
                RecommendationImpressionLog(
                    request_id="ab-req-1",
                    user_id=tracked_user.id,
                    product_id=product_ids[1],
                    rank_position=2,
                    recall_channels=["trending"],
                    final_score=0.55,
                    reason="baseline result",
                ),
                RecommendationImpressionLog(
                    request_id="ab-req-2",
                    user_id=tracked_user.id,
                    product_id=product_ids[0],
                    rank_position=1,
                    recall_channels=["content_profile"],
                    final_score=0.92,
                    reason="pipeline result",
                ),
                RecommendationImpressionLog(
                    request_id="ab-req-2",
                    user_id=tracked_user.id,
                    product_id=product_ids[1],
                    rank_position=2,
                    recall_channels=["item_cooccurrence"],
                    final_score=0.88,
                    reason="pipeline result",
                ),
                RecommendationImpressionLog(
                    request_id="ab-req-3",
                    user_id=tracked_user.id,
                    product_id=product_ids[1],
                    rank_position=1,
                    recall_channels=["item_cooccurrence"],
                    final_score=0.9,
                    reason="pipeline result",
                ),
                RecommendationImpressionLog(
                    request_id="ab-req-3",
                    user_id=tracked_user.id,
                    product_id=product_ids[2],
                    rank_position=2,
                    recall_channels=["content_profile"],
                    final_score=0.85,
                    reason="pipeline result",
                ),
            ]
        )
        session.add_all(
            [
                RecommendationClickLog(
                    request_id="ab-req-1",
                    user_id=tracked_user.id,
                    product_id=product_ids[0],
                    action_type="click",
                ),
                RecommendationClickLog(
                    request_id="ab-req-2",
                    user_id=tracked_user.id,
                    product_id=product_ids[0],
                    action_type="click",
                ),
                RecommendationClickLog(
                    request_id="ab-req-3",
                    user_id=tracked_user.id,
                    product_id=product_ids[1],
                    action_type="click",
                ),
                RecommendationConversionLog(
                    request_id="ab-req-2",
                    user_id=tracked_user.id,
                    product_id=product_ids[0],
                    action_type="add_to_cart",
                ),
                RecommendationConversionLog(
                    request_id="ab-req-3",
                    user_id=tracked_user.id,
                    product_id=product_ids[1],
                    action_type="pay_order",
                ),
            ]
        )
        session.commit()

        dashboard = build_experiment_dashboard(session)

    assert dashboard["summary"]["request_count"] == 3
    assert dashboard["summary"]["variant_count"] == 2
    assert dashboard["summary"]["slot_variant_count"] == 3
    assert dashboard["top_variants"][0]["pipeline_version"] == "v1"
    assert dashboard["top_variants"][0]["request_count"] == 2
    assert dashboard["top_variants"][0]["slot_count"] == 2
    assert dashboard["items"][0]["traffic_share"] == 0.3333
    assert any(
        item["pipeline_version"] == "baseline" and item["fallback_rate"] == 1.0
        for item in dashboard["items"]
    )
    assert dashboard["comparison_cards"][0]["baseline"]["pipeline_version"] == "baseline"
    assert dashboard["comparison_cards"][0]["challenger"]["pipeline_version"] == "v1"

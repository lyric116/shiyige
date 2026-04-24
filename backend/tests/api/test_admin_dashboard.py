import pytest
from sqlalchemy import select

from backend.app.models.product import Product
from backend.app.models.recommendation_analytics import (
    RecommendationClickLog,
    RecommendationConversionLog,
    RecommendationImpressionLog,
    RecommendationRequestLog,
    SearchRequestLog,
)
from backend.app.models.recommendation_experiment import RecommendationExperiment
from backend.app.services.vector_store import VectorStoreRuntime


@pytest.mark.asyncio
async def test_admin_dashboard_summary_returns_recommendation_metrics(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    create_user,
    seed_product_catalog,
    monkeypatch,
) -> None:
    admin_user = create_admin_user(
        email="admin-dashboard@example.com",
        username="admin-dashboard",
    )
    tracked_user = create_user(
        email="tracked-dashboard@example.com",
        username="tracked-dashboard",
    )
    headers = admin_auth_headers_factory(admin_user)

    monkeypatch.setattr(
        "backend.app.services.recommendation_admin.probe_vector_store_runtime",
        lambda: VectorStoreRuntime(
            configured_provider="qdrant",
            recommendation_pipeline_version="v1",
            configured_recommendation_ranker="weighted_ranker",
            qdrant_available=True,
            qdrant_url="http://qdrant:6333",
            qdrant_collections=["shiyige_products_v1"],
            qdrant_error=None,
            degraded_to_baseline=False,
            active_search_backend="qdrant_hybrid",
            active_recommendation_backend="multi_recall",
        ),
    )
    monkeypatch.setattr(
        "backend.app.services.recommendation_admin.get_product_index_status",
        lambda db: {
            "qdrant_available": True,
            "collection_name": "shiyige_products_v1",
            "collection_exists": True,
            "active_product_count": 20,
            "indexed_product_count": 20,
            "qdrant_point_count": 20,
            "failed_products": [],
        },
    )

    with api_session_factory() as session:
        product_ids = session.scalars(select(Product.id).order_by(Product.id.asc()).limit(2)).all()
        assert len(product_ids) == 2

        session.add(
            RecommendationRequestLog(
                request_id="dashboard-req-1",
                user_id=tracked_user.id,
                slot="home",
                pipeline_version="v1",
                model_version="weighted-ranker-v1",
                candidate_count=6,
                final_product_ids=product_ids,
                latency_ms=123.456,
                fallback_used=False,
            )
        )
        for index, product_id in enumerate(product_ids, start=1):
            session.add(
                RecommendationImpressionLog(
                    request_id="dashboard-req-1",
                    user_id=tracked_user.id,
                    product_id=product_id,
                    rank_position=index,
                    recall_channels=["content_profile"],
                    final_score=0.91 - index * 0.1,
                    reason="因为你最近浏览了相关商品",
                )
            )
        session.add(
            RecommendationClickLog(
                request_id="dashboard-req-1",
                user_id=tracked_user.id,
                product_id=product_ids[0],
                action_type="click",
            )
        )
        session.add(
            RecommendationConversionLog(
                request_id="dashboard-req-1",
                user_id=tracked_user.id,
                product_id=product_ids[0],
                action_type="add_to_cart",
            )
        )
        session.add(
            RecommendationConversionLog(
                request_id="dashboard-req-1",
                user_id=tracked_user.id,
                product_id=product_ids[0],
                action_type="pay_order",
            )
        )
        session.add(
            SearchRequestLog(
                request_id="dashboard-search-1",
                user_id=tracked_user.id,
                query="春日汉服",
                mode="semantic",
                pipeline_version="qdrant_hybrid",
                total_results=3,
                latency_ms=88.0,
                filters_json={"category_id": 1},
            )
        )
        session.add(
            RecommendationExperiment(
                experiment_key="full_pipeline",
                name="full_pipeline",
                strategy="multi_recall_ranker",
                pipeline_version="v1",
                model_version="weighted_ranker",
                is_active=True,
                config_json={"ranking": "weighted_ranker"},
                artifact_json={"notes": "synthetic benchmark"},
                description="当前全量推荐主链路。",
            )
        )
        session.commit()

    response = await api_client.get("/api/v1/admin/dashboard/summary", headers=headers)
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["users_total"] == 1
    assert body["data"]["products_total"] == 20
    assert body["data"]["vector_index"]["qdrant_point_count"] == 20
    assert body["data"]["runtime"]["active_recommendation_backend"] == "multi_recall"
    assert body["data"]["recommendation_metrics"]["request_count"] == 1
    assert body["data"]["recommendation_metrics"]["impression_count"] == 2
    assert body["data"]["recommendation_metrics"]["click_count"] == 1
    assert body["data"]["recommendation_metrics"]["add_to_cart_count"] == 1
    assert body["data"]["recommendation_metrics"]["pay_order_count"] == 1
    assert body["data"]["recommendation_metrics"]["ctr"] == 0.5
    assert body["data"]["recommendation_metrics"]["coverage_rate"] == 0.1
    assert body["data"]["search_metrics"]["semantic_count"] == 1
    assert body["data"]["search_metrics"]["average_latency_ms"] == 88.0
    assert body["data"]["experiments"]["active_key"] == "full_pipeline"
    full_pipeline = next(
        item for item in body["data"]["experiments"]["items"] if item["key"] == "full_pipeline"
    )
    assert full_pipeline["artifact_json"]["notes"] == "synthetic benchmark"

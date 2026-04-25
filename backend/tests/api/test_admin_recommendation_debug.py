import pytest
from sqlalchemy import select

from backend.app.models.admin import OperationLog
from backend.app.models.product import Product
from backend.app.services.vector_store import VectorStoreRuntime
from backend.tests.api.test_recommendations import create_user_preference_trace


@pytest.mark.asyncio
async def test_admin_recommendation_debug_returns_profile_and_score_breakdown(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    admin_user = create_admin_user(
        email="admin-debug@example.com",
        username="admin-debug",
    )
    user = create_user(
        email="rec-debug@example.com",
        username="rec-debug",
    )
    admin_headers = admin_auth_headers_factory(admin_user)
    user_headers = auth_headers_factory(user)

    with api_session_factory() as session:
        hanfu = session.scalar(select(Product).where(Product.name == "明制襦裙"))
        assert hanfu is not None
        assert hanfu.default_sku is not None
        product_id = hanfu.id
        sku_id = hanfu.default_sku.id

    await create_user_preference_trace(
        api_client,
        user_headers,
        product_id,
        sku_id,
        "春日汉服",
    )

    response = await api_client.get(
        "/api/v1/admin/recommendations/debug",
        headers=admin_headers,
        params={"email": user.email, "limit": 3},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "ok"
    assert body["data"]["user"]["email"] == user.email
    assert body["data"]["provider"]["model_name"]
    assert body["data"]["metrics"]["indexed_products"] == 20
    assert body["data"]["profile"]["behavior_count"] == 3
    assert body["data"]["profile"]["vector_dimension"] > 0
    assert (
        "汉服" in body["data"]["profile"]["top_terms"]
        or "春日" in body["data"]["profile"]["top_terms"]
    )
    assert body["data"]["profile"]["consumed_products"][0]["id"] == product_id
    assert body["data"]["recent_behaviors"][0]["behavior_type"] == "add_to_cart"
    assert len(body["data"]["recommendations"]) == 3
    assert body["data"]["recommendations"][0]["product_id"] != product_id
    assert body["data"]["recommendations"][0]["reason"]
    assert body["data"]["recommendations"][0]["matched_terms"]
    assert body["data"]["recommendations"][0]["recall_channels"]
    assert body["data"]["recommendations"][0]["channel_details"]
    assert body["data"]["recommendations"][0]["ranking_features"]
    assert body["data"]["recommendations"][0]["feature_summary"]
    assert body["data"]["recommendations"][0]["score_breakdown"]
    assert body["data"]["recommendations"][0]["embedding_dimension"] > 0
    assert body["data"]["recommendations"][0]["embedding_vector_preview"]
    assert body["data"]["metrics"]["active_ranker"]

    with api_session_factory() as session:
        operation_log = session.scalar(
            select(OperationLog)
            .where(OperationLog.admin_user_id == admin_user.id)
            .order_by(OperationLog.id.desc())
        )

        assert operation_log is not None
        assert operation_log.action == "admin_debug_recommendations"
        assert operation_log.target_id == user.id


@pytest.mark.asyncio
async def test_admin_recommendation_debug_supports_lookup_by_user_id(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    admin_user = create_admin_user(
        email="admin-debug-id@example.com",
        username="admin-debug-id",
    )
    user = create_user(
        email="rec-debug-id@example.com",
        username="rec-debug-id",
    )
    admin_headers = admin_auth_headers_factory(admin_user)
    user_headers = auth_headers_factory(user)

    with api_session_factory() as session:
        product = session.scalar(select(Product).where(Product.name == "点翠发簪"))
        assert product is not None
        assert product.default_sku is not None
        product_id = product.id
        sku_id = product.default_sku.id

    await create_user_preference_trace(
        api_client,
        user_headers,
        product_id,
        sku_id,
        "古风发簪",
    )

    response = await api_client.get(
        "/api/v1/admin/recommendations/debug",
        headers=admin_headers,
        params={"user_id": user.id, "limit": 2},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["user"]["id"] == user.id
    assert len(body["data"]["recommendations"]) == 2

    alias_response = await api_client.get(
        "/api/v1/admin/recommendation/debug",
        headers=admin_headers,
        params={"user_id": user.id, "limit": 2},
    )
    assert alias_response.status_code == 200
    assert alias_response.json()["data"]["user"]["id"] == user.id


@pytest.mark.asyncio
async def test_admin_recommendation_experiments_endpoint_returns_static_configs(
    api_client,
    create_admin_user,
    admin_auth_headers_factory,
    monkeypatch,
) -> None:
    admin_user = create_admin_user(
        email="admin-exp@example.com",
        username="admin-exp",
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

    response = await api_client.get(
        "/api/v1/admin/recommendations/experiments",
        headers=headers,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["active_key"] == "full_pipeline"
    assert {item["key"] for item in body["data"]["items"]} >= {
        "baseline",
        "hybrid",
        "hybrid_rerank",
        "full_pipeline",
    }
    assert next(
        item for item in body["data"]["items"] if item["key"] == "full_pipeline"
    )["is_active"] is True


@pytest.mark.asyncio
async def test_admin_recommendation_metrics_endpoint_returns_runtime_and_metrics(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    monkeypatch,
) -> None:
    admin_user = create_admin_user(
        email="admin-metrics@example.com",
        username="admin-metrics",
    )
    headers = admin_auth_headers_factory(admin_user)

    monkeypatch.setattr(
        "backend.app.api.v1.admin_recommendations.build_recommendation_dashboard_payload",
        lambda db: {
            "runtime": {
                "active_recommendation_backend": "multi_recall",
                "active_search_backend": "qdrant_hybrid",
            },
            "recommendation_metrics": {
                "request_count": 12,
                "impression_count": 48,
                "click_count": 6,
                "add_to_cart_count": 2,
                "pay_order_count": 1,
                "covered_product_count": 10,
                "ctr": 0.125,
                "add_to_cart_rate": 0.0417,
                "conversion_rate": 0.0208,
                "coverage_rate": 0.5,
                "average_latency_ms": 88.0,
                "average_candidate_count": 6.0,
                "last_request_at": None,
                "slot_breakdown": [],
                "pipeline_breakdown": [],
            },
            "search_metrics": {
                "request_count": 7,
                "keyword_count": 3,
                "semantic_count": 4,
                "average_latency_ms": 66.0,
                "average_result_count": 5.0,
                "last_request_at": None,
            },
        },
    )

    response = await api_client.get(
        "/api/v1/admin/recommendation/metrics",
        headers=headers,
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["runtime"]["active_recommendation_backend"] == "multi_recall"
    assert body["data"]["metrics"]["request_count"] == 12
    assert body["data"]["search_metrics"]["semantic_count"] == 4

    with api_session_factory() as session:
        operation_log = session.scalar(
            select(OperationLog)
            .where(OperationLog.admin_user_id == admin_user.id)
            .order_by(OperationLog.id.desc())
        )
        assert operation_log is not None
        assert operation_log.action == "admin_recommendation_metrics"

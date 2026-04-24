import pytest
from sqlalchemy import select

from backend.app.models.admin import OperationLog
from backend.app.models.product import Product
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

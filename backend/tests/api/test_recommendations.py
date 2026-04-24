import pytest
from sqlalchemy import select

from backend.app.models.product import Product


async def create_user_preference_trace(
    api_client,
    headers,
    product_id: int,
    sku_id: int,
    query: str,
) -> None:
    detail_response = await api_client.get(f"/api/v1/products/{product_id}", headers=headers)
    assert detail_response.status_code == 200

    search_response = await api_client.get("/api/v1/search", params={"q": query}, headers=headers)
    assert search_response.status_code == 200

    add_cart_response = await api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={
            "product_id": product_id,
            "sku_id": sku_id,
            "quantity": 1,
        },
    )
    assert add_cart_response.status_code == 201


@pytest.mark.asyncio
async def test_recommendations_return_different_results_for_different_users(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    first_user = create_user(email="rec-a@example.com", username="rec-a")
    second_user = create_user(email="rec-b@example.com", username="rec-b")
    first_headers = auth_headers_factory(first_user)
    second_headers = auth_headers_factory(second_user)

    with api_session_factory() as session:
        hanfu = session.scalar(select(Product).where(Product.name == "明制襦裙"))
        accessory = session.scalar(select(Product).where(Product.name == "点翠发簪"))
        assert hanfu is not None
        assert accessory is not None
        assert hanfu.default_sku is not None
        assert accessory.default_sku is not None
        hanfu_id = hanfu.id
        hanfu_sku_id = hanfu.default_sku.id
        accessory_id = accessory.id
        accessory_sku_id = accessory.default_sku.id

    await create_user_preference_trace(
        api_client,
        first_headers,
        hanfu_id,
        hanfu_sku_id,
        "春日汉服",
    )
    await create_user_preference_trace(
        api_client,
        second_headers,
        accessory_id,
        accessory_sku_id,
        "古风发簪",
    )

    first_response = await api_client.get(
        "/api/v1/products/recommendations",
        headers=first_headers,
    )
    second_response = await api_client.get(
        "/api/v1/products/recommendations",
        headers=second_headers,
    )

    first_body = first_response.json()
    second_body = second_response.json()

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert first_body["data"]["items"]
    assert second_body["data"]["items"]
    assert first_body["data"]["pipeline"]["active_recommendation_backend"] == "baseline"
    assert first_body["data"]["pipeline"]["degraded_to_baseline"] is True
    assert first_body["data"]["items"][0]["id"] != hanfu_id
    assert second_body["data"]["items"][0]["id"] != accessory_id
    assert [item["id"] for item in first_body["data"]["items"][:3]] != [
        item["id"] for item in second_body["data"]["items"][:3]
    ]
    assert "偏好推荐" in first_body["data"]["items"][0]["reason"]


@pytest.mark.asyncio
async def test_recommendations_debug_alias_returns_pipeline_metadata(
    api_client,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="rec-debug-alias@example.com", username="rec-debug-alias")
    headers = auth_headers_factory(user)

    response = await api_client.get(
        "/api/v1/recommendations",
        headers=headers,
        params={"slot": "home", "debug": True, "limit": 3},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["pipeline"]["slot"] == "home"
    assert "active_ranker" in body["data"]["pipeline"]
    assert "ranker_model_version" in body["data"]["pipeline"]
    assert "ltr_fallback_used" in body["data"]["pipeline"]

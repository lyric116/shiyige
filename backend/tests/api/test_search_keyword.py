import pytest
from sqlalchemy import select

from backend.app.models.product import Category


@pytest.mark.asyncio
async def test_search_endpoint_returns_filtered_products(
    api_client,
    api_session_factory,
    seed_product_catalog,
) -> None:
    with api_session_factory() as session:
        gift_box_category = session.scalar(select(Category).where(Category.slug == "gift-box"))
        assert gift_box_category is not None

    response = await api_client.get(
        "/api/v1/search",
        params={
            "q": "礼盒",
            "category_id": gift_box_category.id,
            "min_price": "300",
            "sort": "price_desc",
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["query"] == "礼盒"
    assert [item["name"] for item in body["data"]["items"]] == ["国风美妆礼盒", "上元灯会礼盒"]
    assert body["data"]["items"][0]["reason"]
    assert "关键词命中" in body["data"]["items"][0]["explanations"]
    assert body["data"]["items"][0]["search_mode"] == "keyword"


@pytest.mark.asyncio
async def test_search_suggestions_returns_matching_product_names(
    api_client,
    seed_product_catalog,
) -> None:
    response = await api_client.get(
        "/api/v1/search/suggestions",
        params={"q": "故宫", "limit": 3},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["query"] == "故宫"
    assert [item["keyword"] for item in body["data"]["items"]] == [
        "故宫宫廷香囊",
        "故宫百喜毯",
        "故宫花神口红",
    ]

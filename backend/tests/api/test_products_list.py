import pytest
from sqlalchemy import select

from backend.app.models.product import Category


@pytest.mark.asyncio
async def test_products_list_returns_paginated_seeded_products(
    api_client,
    seed_product_catalog,
) -> None:
    response = await api_client.get("/api/v1/products", params={"page": 1, "page_size": 5})

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["page"] == 1
    assert body["data"]["page_size"] == 5
    assert body["data"]["total"] == 20
    assert len(body["data"]["items"]) == 5
    assert "category" in body["data"]["items"][0]
    assert "price" in body["data"]["items"][0]


@pytest.mark.asyncio
async def test_products_list_supports_filters_and_sorting(
    api_client,
    api_session_factory,
    seed_product_catalog,
) -> None:
    with api_session_factory() as session:
        hanfu_category = session.scalar(select(Category).where(Category.slug == "hanfu"))
        assert hanfu_category is not None

    response = await api_client.get(
        "/api/v1/products",
        params={
            "category_id": hanfu_category.id,
            "sort": "price_desc",
        },
    )
    body = response.json()
    product_names = [item["name"] for item in body["data"]["items"]]
    assert product_names == ["明制襦裙", "唐制交领袍", "宋风褙子套装", "汉元素对襟"]

    filtered_response = await api_client.get(
        "/api/v1/products",
        params={
            "q": "故宫",
            "max_price": "200",
        },
    )
    filtered_body = filtered_response.json()
    filtered_names = {item["name"] for item in filtered_body["data"]["items"]}
    assert filtered_names == {"故宫宫廷香囊", "故宫花神口红", "故宫星空折扇"}

    tag_response = await api_client.get("/api/v1/products", params={"tag": "星空"})
    tag_body = tag_response.json()
    assert [item["name"] for item in tag_body["data"]["items"]] == ["故宫星空折扇"]

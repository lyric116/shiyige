import pytest


@pytest.mark.asyncio
async def test_list_categories_returns_seeded_categories(api_client, seed_product_catalog) -> None:
    response = await api_client.get("/api/v1/categories")

    body = response.json()
    category_names = [item["name"] for item in body["data"]["items"]]

    assert response.status_code == 200
    assert body["code"] == 0
    assert category_names == ["汉服", "文创", "非遗", "饰品", "礼盒"]

import pytest
from sqlalchemy import select

from backend.app.models.product import Product


@pytest.mark.asyncio
async def test_related_products_excludes_self_and_returns_reason(
    api_client,
    api_session_factory,
    seed_product_catalog,
) -> None:
    with api_session_factory() as session:
        product = session.scalar(select(Product).where(Product.name == "点翠发簪"))
        assert product is not None

    response = await api_client.get(
        f"/api/v1/products/{product.id}/related",
        params={"limit": 3},
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert len(body["data"]["items"]) == 3
    assert all(item["id"] != product.id for item in body["data"]["items"])
    assert all(item["reason"] for item in body["data"]["items"])
    assert body["data"]["items"][0]["category"]["name"] == "饰品"
    assert body["data"]["items"][0]["dense_similarity"]["score"] > 0
    assert "co_view_co_buy" in body["data"]["items"][0]
    assert "cultural_match" in body["data"]["items"][0]
    assert "source_breakdown" in body["data"]["items"][0]
    assert "diversity_result" in body["data"]["items"][0]

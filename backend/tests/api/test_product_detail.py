import pytest
from sqlalchemy import select

from backend.app.models.product import Product


@pytest.mark.asyncio
async def test_product_detail_returns_complete_payload(
    api_client,
    api_session_factory,
    seed_product_catalog,
) -> None:
    with api_session_factory() as session:
        product = session.scalar(select(Product).where(Product.name == "明制襦裙"))
        assert product is not None

    response = await api_client.get(f"/api/v1/products/{product.id}")

    body = response.json()
    product_payload = body["data"]["product"]

    assert response.status_code == 200
    assert body["code"] == 0
    assert product_payload["name"] == "明制襦裙"
    assert product_payload["culture_summary"]
    assert product_payload["member_price"] is not None
    assert len(product_payload["media"]) >= 1
    assert len(product_payload["skus"]) >= 1
    assert any(sku["is_default"] for sku in product_payload["skus"])
    assert product_payload["skus"][0]["inventory"] > 0
    assert "汉服" in product_payload["tags"]


@pytest.mark.asyncio
async def test_product_detail_returns_not_found_for_missing_product(
    api_client,
    seed_product_catalog,
) -> None:
    response = await api_client.get("/api/v1/products/999999")

    body = response.json()
    assert response.status_code == 404
    assert body["code"] == 40001
    assert body["message"] == "product not found"

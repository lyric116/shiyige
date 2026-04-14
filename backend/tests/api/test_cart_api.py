import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.models.product import Product, ProductSku


def get_seed_product(session, name: str) -> Product:
    product = session.scalar(
        select(Product)
        .options(selectinload(Product.skus).selectinload(ProductSku.inventory))
        .where(Product.name == name)
    )
    assert product is not None
    return product


@pytest.mark.asyncio
async def test_get_cart_returns_empty_cart_for_new_user(
    api_client,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="cart-empty@example.com", username="cart-empty")

    response = await api_client.get("/api/v1/cart", headers=auth_headers_factory(user))

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["cart"]["id"] is None
    assert body["data"]["cart"]["items"] == []
    assert body["data"]["cart"]["total_quantity"] == 0
    assert body["data"]["cart"]["total_amount"] == 0.0


@pytest.mark.asyncio
async def test_cart_api_supports_add_update_and_delete_item(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="cart-flow@example.com", username="cart-flow")
    with api_session_factory() as session:
        product = get_seed_product(session, "点翠发簪")
        sku = product.default_sku
        assert sku is not None

    add_response = await api_client.post(
        "/api/v1/cart/items",
        headers=auth_headers_factory(user),
        json={"product_id": product.id, "sku_id": sku.id, "quantity": 2},
    )
    add_body = add_response.json()
    item_id = add_body["data"]["item"]["id"]

    assert add_response.status_code == 201
    assert add_body["data"]["item"]["quantity"] == 2
    assert add_body["data"]["cart"]["total_quantity"] == 2

    update_response = await api_client.put(
        f"/api/v1/cart/items/{item_id}",
        headers=auth_headers_factory(user),
        json={"quantity": 4},
    )
    update_body = update_response.json()

    assert update_response.status_code == 200
    assert update_body["data"]["item"]["quantity"] == 4
    assert update_body["data"]["cart"]["total_quantity"] == 4

    delete_response = await api_client.delete(
        f"/api/v1/cart/items/{item_id}",
        headers=auth_headers_factory(user),
    )
    delete_body = delete_response.json()

    assert delete_response.status_code == 200
    assert delete_body["data"]["cart"]["items"] == []
    assert delete_body["data"]["cart"]["total_quantity"] == 0


@pytest.mark.asyncio
async def test_cart_api_rejects_invalid_product_sku_quantity_and_inventory(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="cart-error@example.com", username="cart-error")
    with api_session_factory() as session:
        normal_product = get_seed_product(session, "点翠发簪")
        normal_sku = normal_product.default_sku
        assert normal_sku is not None

        unavailable_product = get_seed_product(session, "端午祈福礼盒")
        unavailable_product.status = 0

        low_stock_product = get_seed_product(session, "景泰蓝花瓶")
        low_stock_sku = low_stock_product.default_sku
        assert low_stock_sku is not None

        other_product = get_seed_product(session, "故宫星空折扇")
        other_sku = other_product.default_sku
        assert other_sku is not None

        session.commit()

    missing_product_response = await api_client.post(
        "/api/v1/cart/items",
        headers=auth_headers_factory(user),
        json={"product_id": 9999, "sku_id": 9999, "quantity": 1},
    )
    assert missing_product_response.status_code == 404
    assert missing_product_response.json()["message"] == "product not found"

    missing_sku_response = await api_client.post(
        "/api/v1/cart/items",
        headers=auth_headers_factory(user),
        json={"product_id": normal_product.id, "sku_id": other_sku.id, "quantity": 1},
    )
    assert missing_sku_response.status_code == 404
    assert missing_sku_response.json()["message"] == "sku not found"

    invalid_quantity_response = await api_client.post(
        "/api/v1/cart/items",
        headers=auth_headers_factory(user),
        json={"product_id": normal_product.id, "sku_id": normal_sku.id, "quantity": 0},
    )
    assert invalid_quantity_response.status_code == 400
    assert invalid_quantity_response.json()["message"] == "quantity is invalid"

    unavailable_product_response = await api_client.post(
        "/api/v1/cart/items",
        headers=auth_headers_factory(user),
        json={"product_id": unavailable_product.id, "sku_id": unavailable_product.default_sku.id, "quantity": 1},
    )
    assert unavailable_product_response.status_code == 409
    assert unavailable_product_response.json()["message"] == "product unavailable"

    inventory_response = await api_client.post(
        "/api/v1/cart/items",
        headers=auth_headers_factory(user),
        json={"product_id": low_stock_product.id, "sku_id": low_stock_sku.id, "quantity": 99},
    )
    assert inventory_response.status_code == 409
    assert inventory_response.json()["message"] == "inventory insufficient"

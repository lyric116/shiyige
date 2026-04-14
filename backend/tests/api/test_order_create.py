import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.models.product import Product, ProductSku
from backend.app.models.user import UserAddress


def get_seed_product(session, name: str) -> Product:
    product = session.scalar(
        select(Product)
        .options(selectinload(Product.skus).selectinload(ProductSku.inventory))
        .where(Product.name == name)
    )
    assert product is not None
    return product


@pytest.mark.asyncio
async def test_create_order_writes_snapshot_and_clears_cart(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="order-create@example.com", username="order-create")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="张三",
            phone="13800138000",
            region="北京市东城区",
            detail_address="景山前街 4 号",
            postal_code="100010",
            is_default=True,
        )
        session.add(address)
        product = get_seed_product(session, "点翠发簪")
        sku = product.default_sku
        assert sku is not None
        session.commit()
        session.refresh(address)

    add_cart_response = await api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": product.id, "sku_id": sku.id, "quantity": 2},
    )
    assert add_cart_response.status_code == 201

    response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address.id,
            "buyer_note": "周末送达",
            "idempotency_key": "order-create-key",
        },
    )

    body = response.json()
    assert response.status_code == 201
    assert body["message"] == "order created"
    assert body["data"]["order"]["status"] == "PENDING_PAYMENT"
    assert body["data"]["order"]["goods_amount"] == 258.0
    assert body["data"]["order"]["shipping_amount"] == 10.0
    assert body["data"]["order"]["payable_amount"] == 268.0
    assert body["data"]["order"]["buyer_note"] == "周末送达"
    assert body["data"]["order"]["address"]["recipient_name"] == "张三"
    assert body["data"]["order"]["items"][0]["product_name"] == "点翠发簪"
    assert body["data"]["order"]["items"][0]["quantity"] == 2

    cart_response = await api_client.get("/api/v1/cart", headers=headers)
    cart_body = cart_response.json()
    assert cart_body["data"]["cart"]["items"] == []
    assert cart_body["data"]["cart"]["total_quantity"] == 0


@pytest.mark.asyncio
async def test_create_order_rejects_invalid_address_and_empty_cart(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="order-empty@example.com", username="order-empty")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="王五",
            phone="13700137000",
            region="杭州市西湖区",
            detail_address="龙井路 8 号",
            postal_code="310000",
            is_default=True,
        )
        session.add(address)
        session.commit()
        session.refresh(address)

    missing_address_response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": 9999,
            "buyer_note": "",
            "idempotency_key": "order-missing-address",
        },
    )
    assert missing_address_response.status_code == 404
    assert missing_address_response.json()["message"] == "address not found"

    empty_cart_response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address.id,
            "buyer_note": "",
            "idempotency_key": "order-empty-cart",
        },
    )
    assert empty_cart_response.status_code == 400
    assert empty_cart_response.json()["message"] == "cart is empty"

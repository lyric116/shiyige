import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from backend.app.models.order import Order
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
async def test_create_order_with_same_idempotency_key_returns_existing_order(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="order-idem@example.com", username="order-idem")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="李四",
            phone="13900139000",
            region="上海市黄浦区",
            detail_address="南京东路 1 号",
            postal_code="200001",
            is_default=True,
        )
        session.add(address)
        product = get_seed_product(session, "故宫宫廷香囊")
        sku = product.default_sku
        assert sku is not None
        session.commit()
        session.refresh(address)

    add_cart_response = await api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": product.id, "sku_id": sku.id, "quantity": 1},
    )
    assert add_cart_response.status_code == 201

    first_response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address.id,
            "buyer_note": "幂等测试",
            "idempotency_key": "idem-order-key",
        },
    )
    first_body = first_response.json()

    second_response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address.id,
            "buyer_note": "幂等测试",
            "idempotency_key": "idem-order-key",
        },
    )
    second_body = second_response.json()

    assert first_response.status_code == 201
    assert second_response.status_code == 200
    assert second_body["message"] == "order exists"
    assert first_body["data"]["order"]["id"] == second_body["data"]["order"]["id"]
    assert first_body["data"]["order"]["order_no"] == second_body["data"]["order"]["order_no"]

    with api_session_factory() as session:
        order_count = session.scalar(select(func.count(Order.id)).where(Order.user_id == user.id))
        assert order_count == 1

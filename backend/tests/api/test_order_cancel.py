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


async def create_order(
    api_client, headers, address_id, product_id, sku_id, quantity, idempotency_key
):
    add_cart_response = await api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={"product_id": product_id, "sku_id": sku_id, "quantity": quantity},
    )
    assert add_cart_response.status_code == 201

    create_order_response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address_id,
            "buyer_note": "取消测试",
            "idempotency_key": idempotency_key,
        },
    )
    assert create_order_response.status_code == 201
    return create_order_response.json()["data"]["order"]["id"]


@pytest.mark.asyncio
async def test_cancel_pending_order_updates_status(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="cancel@example.com", username="cancel-user")
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
        product = get_seed_product(session, "故宫宫廷香囊")
        sku = product.default_sku
        assert sku is not None
        session.commit()
        session.refresh(address)

    order_id = await create_order(
        api_client,
        headers,
        address.id,
        product.id,
        sku.id,
        1,
        "order-cancel-key",
    )

    response = await api_client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "order cancelled"
    assert body["data"]["order"]["status"] == "CANCELLED"
    assert body["data"]["order"]["cancelled_at"] is not None


@pytest.mark.asyncio
async def test_cancel_paid_order_is_rejected(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="cancel-paid@example.com", username="cancel-paid")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="赵六",
            phone="13600136000",
            region="苏州市姑苏区",
            detail_address="平江路 6 号",
            postal_code="215000",
            is_default=True,
        )
        session.add(address)
        product = get_seed_product(session, "点翠发簪")
        sku = product.default_sku
        assert sku is not None
        session.commit()
        session.refresh(address)

    order_id = await create_order(
        api_client,
        headers,
        address.id,
        product.id,
        sku.id,
        1,
        "order-cancel-paid-key",
    )

    pay_response = await api_client.post(
        f"/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "alipay"},
    )
    assert pay_response.status_code == 200

    cancel_response = await api_client.post(f"/api/v1/orders/{order_id}/cancel", headers=headers)
    assert cancel_response.status_code == 409
    assert cancel_response.json()["message"] == "paid order cannot be cancelled"

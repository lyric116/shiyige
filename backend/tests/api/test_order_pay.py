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


async def create_pending_order(api_client, headers, address_id, product_id, sku_id, quantity, idempotency_key):
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
            "buyer_note": "支付测试",
            "idempotency_key": idempotency_key,
        },
    )
    assert create_order_response.status_code == 201
    return create_order_response.json()["data"]["order"]["id"]


@pytest.mark.asyncio
async def test_order_pay_deducts_inventory_and_writes_payment_record(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="pay@example.com", username="pay-user")
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
        initial_inventory = sku.inventory.quantity
        session.commit()
        session.refresh(address)

    order_id = await create_pending_order(
        api_client,
        headers,
        address.id,
        product.id,
        sku.id,
        2,
        "order-pay-key",
    )

    response = await api_client.post(
        f"/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "alipay"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["message"] == "order paid"
    assert body["data"]["order"]["status"] == "PAID"
    assert body["data"]["order"]["payment_records"][0]["payment_method"] == "alipay"
    assert body["data"]["order"]["payment_records"][0]["status"] == "PAID"

    with api_session_factory() as session:
        refreshed_product = get_seed_product(session, "点翠发簪")
        refreshed_sku = refreshed_product.default_sku
        assert refreshed_sku is not None
        assert refreshed_sku.inventory.quantity == initial_inventory - 2


@pytest.mark.asyncio
async def test_order_pay_revalidates_inventory_before_deducting(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="pay-inventory@example.com", username="pay-inventory")
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
        product = get_seed_product(session, "景泰蓝花瓶")
        sku = product.default_sku
        assert sku is not None
        session.commit()
        session.refresh(address)

    order_id = await create_pending_order(
        api_client,
        headers,
        address.id,
        product.id,
        sku.id,
        2,
        "order-pay-inventory-key",
    )

    with api_session_factory() as session:
        refreshed_product = get_seed_product(session, "景泰蓝花瓶")
        refreshed_sku = refreshed_product.default_sku
        assert refreshed_sku is not None
        refreshed_sku.inventory.quantity = 1
        session.add(refreshed_sku.inventory)
        session.commit()

    response = await api_client.post(
        f"/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "wechat"},
    )

    assert response.status_code == 409
    assert response.json()["message"] == "inventory insufficient"

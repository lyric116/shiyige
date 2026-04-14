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


async def create_order(api_client, headers, address_id, product_id, sku_id, quantity, idempotency_key):
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
            "buyer_note": "查询测试",
            "idempotency_key": idempotency_key,
        },
    )
    assert create_order_response.status_code == 201
    return create_order_response.json()["data"]["order"]["id"]


@pytest.mark.asyncio
async def test_order_query_returns_current_user_orders_and_detail(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="query@example.com", username="query-user")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="陈七",
            phone="13500135000",
            region="广州市越秀区",
            detail_address="北京路 7 号",
            postal_code="510000",
            is_default=True,
        )
        session.add(address)
        first_product = get_seed_product(session, "故宫宫廷香囊")
        second_product = get_seed_product(session, "点翠发簪")
        first_sku = first_product.default_sku
        second_sku = second_product.default_sku
        assert first_sku is not None
        assert second_sku is not None
        session.commit()
        session.refresh(address)

    first_order_id = await create_order(
        api_client,
        headers,
        address.id,
        first_product.id,
        first_sku.id,
        1,
        "order-query-first",
    )
    second_order_id = await create_order(
        api_client,
        headers,
        address.id,
        second_product.id,
        second_sku.id,
        2,
        "order-query-second",
    )

    list_response = await api_client.get("/api/v1/orders", headers=headers)
    list_body = list_response.json()

    assert list_response.status_code == 200
    assert [item["id"] for item in list_body["data"]["items"]] == [second_order_id, first_order_id]

    detail_response = await api_client.get(f"/api/v1/orders/{second_order_id}", headers=headers)
    detail_body = detail_response.json()

    assert detail_response.status_code == 200
    assert detail_body["data"]["order"]["id"] == second_order_id
    assert detail_body["data"]["order"]["items"][0]["product_name"] == "点翠发簪"
    assert detail_body["data"]["order"]["payment_records"] == []


@pytest.mark.asyncio
async def test_order_detail_rejects_other_users_order(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    owner = create_user(email="owner@example.com", username="owner-user")
    viewer = create_user(email="viewer@example.com", username="viewer-user")
    owner_headers = auth_headers_factory(owner)
    viewer_headers = auth_headers_factory(viewer)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=owner.id,
            recipient_name="孙八",
            phone="13400134000",
            region="成都市锦江区",
            detail_address="春熙路 8 号",
            postal_code="610000",
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
        owner_headers,
        address.id,
        product.id,
        sku.id,
        1,
        "order-query-owner",
    )

    response = await api_client.get(f"/api/v1/orders/{order_id}", headers=viewer_headers)
    assert response.status_code == 404
    assert response.json()["message"] == "order not found"

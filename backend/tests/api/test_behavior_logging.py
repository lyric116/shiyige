import pytest
from sqlalchemy import select

from backend.app.models.product import Product
from backend.app.models.user import UserAddress, UserBehaviorLog


def read_user_logs(session, user_id: int) -> list[UserBehaviorLog]:
    return session.scalars(
        select(UserBehaviorLog)
        .where(UserBehaviorLog.user_id == user_id)
        .order_by(UserBehaviorLog.id.asc())
    ).all()


@pytest.mark.asyncio
async def test_browse_and_search_write_behavior_logs_for_authenticated_user(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="behavior-api@example.com", username="behavior-api")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        product = session.scalar(select(Product).where(Product.name == "明制襦裙"))
        assert product is not None

    detail_response = await api_client.get(f"/api/v1/products/{product.id}", headers=headers)
    search_response = await api_client.get("/api/v1/search", params={"q": "明制"}, headers=headers)

    assert detail_response.status_code == 200
    assert search_response.status_code == 200

    with api_session_factory() as session:
        logs = read_user_logs(session, user.id)

    assert [log.behavior_type for log in logs] == ["view_product", "search"]
    assert logs[0].target_id == product.id
    assert logs[0].target_type == "product"
    assert logs[0].ext_json["product_name"] == "明制襦裙"
    assert logs[1].target_type == "search"
    assert logs[1].ext_json["query"] == "明制"
    assert logs[1].ext_json["result_count"] >= 1


@pytest.mark.asyncio
async def test_add_cart_create_order_and_pay_write_behavior_logs(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="behavior-order@example.com", username="behavior-order")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="行为日志用户",
            phone="13800138000",
            region="北京市 东城区",
            detail_address="景山前街 4 号",
            postal_code="100009",
            is_default=True,
        )
        session.add(address)
        product = session.scalar(select(Product).where(Product.name == "点翠发簪"))
        assert product is not None
        default_sku = product.default_sku
        assert default_sku is not None
        session.commit()
        session.refresh(address)

    add_cart_response = await api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={
            "product_id": product.id,
            "sku_id": default_sku.id,
            "quantity": 2,
        },
    )
    assert add_cart_response.status_code == 201

    create_order_response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address.id,
            "buyer_note": "行为日志测试",
            "idempotency_key": "behavior-order-create",
        },
    )
    assert create_order_response.status_code == 201
    order_id = create_order_response.json()["data"]["order"]["id"]

    pay_response = await api_client.post(
        f"/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "alipay"},
    )
    assert pay_response.status_code == 200

    with api_session_factory() as session:
        logs = read_user_logs(session, user.id)

    assert [log.behavior_type for log in logs] == ["add_to_cart", "create_order", "pay_order"]
    assert logs[0].target_id == product.id
    assert logs[0].target_type == "product"
    assert logs[0].ext_json["quantity"] == 2
    assert logs[1].target_id == order_id
    assert logs[1].target_type == "order"
    assert logs[1].ext_json["item_count"] == 1
    assert logs[2].target_id == order_id
    assert logs[2].ext_json["payment_method"] == "alipay"

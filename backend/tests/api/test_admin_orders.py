import pytest
from sqlalchemy import select

from backend.tests.api.test_order_pay import create_pending_order, get_seed_product
from backend.app.models.user import UserAddress


@pytest.mark.asyncio
async def test_admin_orders_list_detail_and_dashboard_summary(
    api_client,
    api_session_factory,
    create_admin_user,
    admin_auth_headers_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    admin_user = create_admin_user(
        email="admin-orders@example.com",
        username="admin-orders",
    )
    order_user = create_user(
        email="order-admin-view@example.com",
        username="order-admin-view",
    )
    user_headers = auth_headers_factory(order_user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=order_user.id,
            recipient_name="管理员查看订单用户",
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

    paid_order_id = await create_pending_order(
        api_client,
        user_headers,
        address.id,
        product.id,
        sku.id,
        1,
        "admin-orders-paid-key",
    )
    pay_response = await api_client.post(
        f"/api/v1/orders/{paid_order_id}/pay",
        headers=user_headers,
        json={"payment_method": "alipay"},
    )
    assert pay_response.status_code == 200

    pending_order_id = await create_pending_order(
        api_client,
        user_headers,
        address.id,
        product.id,
        sku.id,
        1,
        "admin-orders-pending-key",
    )

    admin_headers = admin_auth_headers_factory(admin_user)
    list_response = await api_client.get(
        "/api/v1/admin/orders",
        headers=admin_headers,
        params={"status": "PAID"},
    )
    list_body = list_response.json()

    assert list_response.status_code == 200
    assert list_body["data"]["total"] == 1
    assert list_body["data"]["items"][0]["id"] == paid_order_id
    assert list_body["data"]["items"][0]["user"]["username"] == "order-admin-view"

    detail_response = await api_client.get(
        f"/api/v1/admin/orders/{paid_order_id}",
        headers=admin_headers,
    )
    detail_body = detail_response.json()

    assert detail_response.status_code == 200
    assert detail_body["data"]["order"]["id"] == paid_order_id
    assert detail_body["data"]["order"]["status"] == "PAID"
    assert detail_body["data"]["order"]["items"][0]["product_name"] == "点翠发簪"

    dashboard_response = await api_client.get(
        "/api/v1/admin/dashboard/summary",
        headers=admin_headers,
    )
    dashboard_body = dashboard_response.json()

    assert dashboard_response.status_code == 200
    assert dashboard_body["data"]["users_total"] == 1
    assert dashboard_body["data"]["products_total"] == 20
    assert dashboard_body["data"]["orders_total"] == 2
    assert dashboard_body["data"]["paid_orders"] == 1
    assert dashboard_body["data"]["pending_orders"] == 1
    assert pending_order_id != paid_order_id

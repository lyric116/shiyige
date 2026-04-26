import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.models.membership import PointAccount
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


async def create_pending_order(
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
            "buyer_note": "会员积分累计测试",
            "idempotency_key": idempotency_key,
        },
    )
    assert create_order_response.status_code == 201
    return create_order_response.json()["data"]["order"]["id"]


@pytest.mark.asyncio
async def test_order_payment_accrues_points_and_updates_member_level(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="member-order@example.com", username="member-order")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="王五",
            phone="13700137000",
            region="杭州市西湖区",
            detail_address="灵隐路 18 号",
            postal_code="310013",
            is_default=True,
        )
        session.add(address)
        product = get_seed_product(session, "明制襦裙")
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
        "member-points-order-key",
    )

    pay_response = await api_client.post(
        f"/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "alipay"},
    )
    pay_body = pay_response.json()
    assert pay_response.status_code == 200
    assert pay_body["data"]["order"]["status"] == "PAID"

    profile_response = await api_client.get("/api/v1/member/profile", headers=headers)
    points_response = await api_client.get("/api/v1/member/points", headers=headers)
    profile_body = profile_response.json()
    points_body = points_response.json()

    assert profile_response.status_code == 200
    assert profile_body["data"]["profile"]["points_balance"] == 1808
    assert profile_body["data"]["profile"]["current_level"]["code"] == "silver"
    assert profile_body["data"]["profile"]["next_level"]["code"] == "gold"

    assert points_response.status_code == 200
    assert points_body["data"]["items"][0]["change_type"] == "order_pay"
    assert points_body["data"]["items"][0]["change_amount"] == 1808
    assert points_body["data"]["items"][0]["source_type"] == "order"
    assert points_body["data"]["items"][0]["source_id"] == order_id
    assert points_body["data"]["summary"]["current_level"]["code"] == "silver"

    with api_session_factory() as session:
        account = session.scalar(
            select(PointAccount)
            .options(selectinload(PointAccount.member_level), selectinload(PointAccount.point_logs))
            .where(PointAccount.user_id == user.id)
        )
        assert account is not None
        assert account.points_balance == 1808
        assert account.lifetime_points == 1808
        assert account.total_spent_amount == 1808
        assert account.member_level.code == "silver"
        assert len(account.point_logs) == 1
        assert account.point_logs[0].balance_after == 1808

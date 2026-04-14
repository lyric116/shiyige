import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.security import create_access_token, hash_password
from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.user import User, UserAddress, UserBehaviorLog, UserProfile
from backend.scripts.seed_base_data import seed_base_data


def list_behavior_logs(session, user_id: int) -> list[UserBehaviorLog]:
    return session.scalars(
        select(UserBehaviorLog)
        .where(UserBehaviorLog.user_id == user_id)
        .order_by(UserBehaviorLog.id.asc())
    ).all()


@pytest.mark.asyncio
async def test_behavior_events_preserve_full_user_journey_sequence(
    async_client,
    db_engine,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "integration-behavior-secret")
    Base.metadata.create_all(db_engine)

    with Session(db_engine) as session:
        seed_base_data(session)

        user = User(
            email="journey@example.com",
            username="journey-user",
            password_hash=hash_password("secret-pass-123"),
            role="user",
            is_active=True,
        )
        user.profile = UserProfile(display_name="journey-user")
        session.add(user)
        session.flush()

        address = UserAddress(
            user_id=user.id,
            recipient_name="旅程用户",
            phone="13900139000",
            region="上海市 黄浦区",
            detail_address="南京东路 1 号",
            postal_code="200001",
            is_default=True,
        )
        session.add(address)
        product = session.scalar(select(Product).where(Product.name == "故宫宫廷香囊"))
        assert product is not None
        default_sku = product.default_sku
        assert default_sku is not None
        session.commit()

        user_id = user.id
        product_id = product.id
        sku_id = default_sku.id
        address_id = address.id

    headers = {"Authorization": f"Bearer {create_access_token(subject=str(user_id), role='user')}"}

    view_response = await async_client.get(f"/api/v1/products/{product_id}", headers=headers)
    search_response = await async_client.get("/api/v1/search", params={"q": "故宫"}, headers=headers)
    add_cart_response = await async_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={
            "product_id": product_id,
            "sku_id": sku_id,
            "quantity": 1,
        },
    )
    order_response = await async_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address_id,
            "buyer_note": "完整行为链路",
            "idempotency_key": "behavior-events-sequence",
        },
    )

    assert view_response.status_code == 200
    assert search_response.status_code == 200
    assert add_cart_response.status_code == 201
    assert order_response.status_code == 201

    order_id = order_response.json()["data"]["order"]["id"]
    pay_response = await async_client.post(
        f"/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "wechat"},
    )
    assert pay_response.status_code == 200

    with Session(db_engine) as session:
        logs = list_behavior_logs(session, user_id)

    assert [log.behavior_type for log in logs] == [
        "view_product",
        "search",
        "add_to_cart",
        "create_order",
        "pay_order",
    ]
    assert [log.target_type for log in logs] == [
        "product",
        "search",
        "product",
        "order",
        "order",
    ]
    assert logs[0].target_id == product_id
    assert logs[1].ext_json["query"] == "故宫"
    assert logs[2].ext_json["sku_id"] == sku_id
    assert logs[3].target_id == order_id
    assert logs[4].ext_json["payment_method"] == "wechat"

import pytest
from sqlalchemy import select

from backend.app.models.product import Product
from backend.app.models.review import Review
from backend.app.models.user import UserAddress


def get_product(session, name: str) -> Product:
    product = session.scalar(select(Product).where(Product.name == name))
    assert product is not None
    return product


async def create_paid_order(
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
            "buyer_note": "评价创建测试",
            "idempotency_key": idempotency_key,
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


@pytest.mark.asyncio
async def test_create_review_persists_review_and_images_for_paid_order(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="review-create@example.com", username="review-create")
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
        product = get_product(session, "点翠发簪")
        sku = product.default_sku
        assert sku is not None
        session.commit()
        session.refresh(address)

    await create_paid_order(
        api_client,
        headers,
        address.id,
        product.id,
        sku.id,
        1,
        "reviews-create-key",
    )

    response = await api_client.post(
        f"/api/v1/products/{product.id}/reviews",
        headers=headers,
        json={
            "rating": 5,
            "content": "做工很细致，佩戴效果很好。",
            "image_urls": ["https://example.com/review-1.jpg"],
        },
    )
    body = response.json()

    assert response.status_code == 201
    assert body["message"] == "review created"
    assert body["data"]["review"]["rating"] == 5
    assert body["data"]["review"]["image_urls"] == ["https://example.com/review-1.jpg"]
    assert body["data"]["review"]["reviewer_name"] == "review-create"

    with api_session_factory() as session:
        stored_review = session.scalar(
            select(Review).where(Review.user_id == user.id, Review.product_id == product.id)
        )
        assert stored_review is not None
        assert stored_review.order_id is not None

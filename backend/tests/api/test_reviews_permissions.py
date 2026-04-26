import pytest

from backend.app.models.user import UserAddress
from backend.tests.api.test_reviews_create import create_paid_order, get_product


@pytest.mark.asyncio
async def test_review_creation_requires_paid_purchase(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="review-permission@example.com", username="review-permission")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        product = get_product(session, "点翠发簪")

    response = await api_client.post(
        f"/api/v1/products/{product.id}/reviews",
        headers=headers,
        json={
            "rating": 5,
            "content": "未购买也想评价。",
        },
    )

    assert response.status_code == 403
    assert response.json()["message"] == "review not allowed"


@pytest.mark.asyncio
async def test_review_creation_allows_only_one_review_per_user_and_product(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="review-once@example.com", username="review-once")
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
        "reviews-once-key",
    )

    first_response = await api_client.post(
        f"/api/v1/products/{product.id}/reviews",
        headers=headers,
        json={
            "rating": 5,
            "content": "第一次评价。",
        },
    )
    second_response = await api_client.post(
        f"/api/v1/products/{product.id}/reviews",
        headers=headers,
        json={
            "rating": 4,
            "content": "再次评价。",
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["message"] == "review already exists"

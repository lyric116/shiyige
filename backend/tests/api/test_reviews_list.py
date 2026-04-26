import pytest

from backend.app.models.user import UserAddress
from backend.tests.api.test_reviews_create import create_paid_order, get_product


@pytest.mark.asyncio
async def test_list_reviews_returns_latest_reviews_with_images(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    first_user = create_user(email="review-list-a@example.com", username="review-list-a")
    second_user = create_user(email="review-list-b@example.com", username="review-list-b")
    first_headers = auth_headers_factory(first_user)
    second_headers = auth_headers_factory(second_user)

    with api_session_factory() as session:
        first_address = UserAddress(
            user_id=first_user.id,
            recipient_name="甲",
            phone="13800138001",
            region="北京市朝阳区",
            detail_address="东三环 1 号",
            postal_code="100020",
            is_default=True,
        )
        second_address = UserAddress(
            user_id=second_user.id,
            recipient_name="乙",
            phone="13800138002",
            region="上海市浦东新区",
            detail_address="世纪大道 1 号",
            postal_code="200120",
            is_default=True,
        )
        session.add_all([first_address, second_address])
        product = get_product(session, "点翠发簪")
        sku = product.default_sku
        assert sku is not None
        session.commit()
        session.refresh(first_address)
        session.refresh(second_address)

    await create_paid_order(
        api_client,
        first_headers,
        first_address.id,
        product.id,
        sku.id,
        1,
        "reviews-list-key-a",
    )
    await create_paid_order(
        api_client,
        second_headers,
        second_address.id,
        product.id,
        sku.id,
        1,
        "reviews-list-key-b",
    )

    await api_client.post(
        f"/api/v1/products/{product.id}/reviews",
        headers=first_headers,
        json={
            "rating": 4,
            "content": "细节不错，适合古风搭配。",
            "image_urls": ["https://example.com/review-a.jpg"],
        },
    )
    await api_client.post(
        f"/api/v1/products/{product.id}/reviews",
        headers=second_headers,
        json={
            "rating": 5,
            "content": "非常精致，拍照很出片。",
            "is_anonymous": True,
        },
    )

    list_response = await api_client.get(f"/api/v1/products/{product.id}/reviews")
    stats_response = await api_client.get(f"/api/v1/products/{product.id}/reviews/stats")

    list_body = list_response.json()
    stats_body = stats_response.json()

    assert list_response.status_code == 200
    assert list_body["data"]["total"] == 2
    assert list_body["data"]["items"][0]["content"] == "非常精致，拍照很出片。"
    assert list_body["data"]["items"][0]["reviewer_name"] == "匿名用户"
    assert list_body["data"]["items"][1]["image_urls"] == ["https://example.com/review-a.jpg"]

    assert stats_response.status_code == 200
    assert stats_body["data"]["total"] == 2
    assert stats_body["data"]["average_rating"] == 4.5
    assert stats_body["data"]["rating_counts"]["4"] == 1
    assert stats_body["data"]["rating_counts"]["5"] == 1

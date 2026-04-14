import pytest


@pytest.mark.asyncio
async def test_member_profile_creates_default_point_account_and_returns_progress(
    api_client,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="member-profile@example.com", username="member-profile")
    headers = auth_headers_factory(user)

    response = await api_client.get("/api/v1/member/profile", headers=headers)
    body = response.json()

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["profile"]["user"]["email"] == "member-profile@example.com"
    assert body["data"]["profile"]["points_balance"] == 0
    assert body["data"]["profile"]["lifetime_points"] == 0
    assert body["data"]["profile"]["current_level"]["code"] == "bronze"
    assert body["data"]["profile"]["next_level"]["code"] == "silver"
    assert body["data"]["profile"]["next_level"]["remaining_points"] == 1000
    assert body["data"]["profile"]["progress_percent"] == 0.0


@pytest.mark.asyncio
async def test_member_benefits_and_points_endpoints_return_seeded_levels_and_logs(
    api_client,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="member-benefits@example.com", username="member-benefits")
    headers = auth_headers_factory(user)

    benefits_response = await api_client.get("/api/v1/member/benefits", headers=headers)
    points_response = await api_client.get("/api/v1/member/points", headers=headers)

    benefits_body = benefits_response.json()
    points_body = points_response.json()

    assert benefits_response.status_code == 200
    assert benefits_body["code"] == 0
    assert benefits_body["data"]["current_level"]["code"] == "bronze"
    assert [item["code"] for item in benefits_body["data"]["items"]] == [
        "bronze",
        "silver",
        "gold",
        "platinum",
    ]
    assert benefits_body["data"]["items"][0]["benefits"] == ["购物享98折", "消费享1倍积分"]

    assert points_response.status_code == 200
    assert points_body["code"] == 0
    assert points_body["data"]["summary"]["current_level"]["code"] == "bronze"
    assert points_body["data"]["summary"]["points_balance"] == 0
    assert points_body["data"]["items"] == []

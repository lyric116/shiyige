import pytest


@pytest.mark.asyncio
async def test_address_crud_flow_supports_default_switching(
    api_client,
    auth_headers_factory,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="address@example.com",
        username="address-user",
        password="secret-pass-123",
    )
    headers = auth_headers_factory(user)

    initial_response = await api_client.get("/api/v1/users/addresses", headers=headers)
    assert initial_response.status_code == 200
    assert initial_response.json()["data"]["items"] == []

    first_response = await api_client.post(
        "/api/v1/users/addresses",
        headers=headers,
        json={
            "recipient_name": "张三",
            "phone": "13800138000",
            "region": "北京市 东城区",
            "detail_address": "景山前街 4 号",
            "postal_code": "100009",
            "is_default": False,
        },
    )
    first_body = first_response.json()
    first_address_id = first_body["data"]["address"]["id"]
    assert first_response.status_code == 201
    assert first_body["data"]["address"]["is_default"] is True

    second_response = await api_client.post(
        "/api/v1/users/addresses",
        headers=headers,
        json={
            "recipient_name": "李四",
            "phone": "13900139000",
            "region": "上海市 黄浦区",
            "detail_address": "南京东路 1 号",
            "postal_code": "200001",
            "is_default": True,
        },
    )
    second_body = second_response.json()
    second_address_id = second_body["data"]["address"]["id"]
    assert second_response.status_code == 201
    assert second_body["data"]["address"]["is_default"] is True

    list_response = await api_client.get("/api/v1/users/addresses", headers=headers)
    list_body = list_response.json()
    assert list_response.status_code == 200
    assert [item["id"] for item in list_body["data"]["items"]] == [
        second_address_id,
        first_address_id,
    ]
    assert list_body["data"]["items"][0]["is_default"] is True
    assert list_body["data"]["items"][1]["is_default"] is False

    update_response = await api_client.put(
        f"/api/v1/users/addresses/{second_address_id}",
        headers=headers,
        json={
            "recipient_name": "李四",
            "phone": "13900139000",
            "region": "上海市 黄浦区",
            "detail_address": "外滩 18 号",
            "postal_code": "200001",
            "is_default": True,
        },
    )
    update_body = update_response.json()
    assert update_response.status_code == 200
    assert update_body["message"] == "address updated"
    assert update_body["data"]["address"]["detail_address"] == "外滩 18 号"

    delete_response = await api_client.delete(
        f"/api/v1/users/addresses/{second_address_id}",
        headers=headers,
    )
    delete_body = delete_response.json()
    assert delete_response.status_code == 200
    assert delete_body["message"] == "address deleted"

    final_list_response = await api_client.get("/api/v1/users/addresses", headers=headers)
    final_items = final_list_response.json()["data"]["items"]
    assert len(final_items) == 1
    assert final_items[0]["id"] == first_address_id
    assert final_items[0]["is_default"] is True


@pytest.mark.asyncio
async def test_address_update_rejects_missing_address(
    api_client,
    auth_headers_factory,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="address@example.com",
        username="address-user",
        password="secret-pass-123",
    )

    response = await api_client.put(
        "/api/v1/users/addresses/999",
        headers=auth_headers_factory(user),
        json={
            "recipient_name": "张三",
            "phone": "13800138000",
            "region": "北京市 东城区",
            "detail_address": "景山前街 4 号",
            "postal_code": "100009",
            "is_default": True,
        },
    )

    body = response.json()
    assert response.status_code == 404
    assert body["code"] == 40001
    assert body["message"] == "address not found"

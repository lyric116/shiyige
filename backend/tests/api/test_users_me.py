import pytest


@pytest.mark.asyncio
async def test_get_current_user_returns_profile_payload(
    api_client,
    auth_headers_factory,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="me@example.com",
        username="me-user",
        password="secret-pass-123",
    )

    response = await api_client.get(
        "/api/v1/users/me",
        headers=auth_headers_factory(user),
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["user"]["id"] == user.id
    assert body["data"]["user"]["email"] == "me@example.com"
    assert body["data"]["user"]["profile"]["display_name"] == "me-user"

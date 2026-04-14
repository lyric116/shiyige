import pytest

from backend.app.core.security import decode_token


@pytest.mark.asyncio
async def test_refresh_uses_refresh_cookie_to_issue_new_access_token(
    api_client,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="refresh@example.com",
        username="refresh-user",
        password="secret-pass-123",
    )

    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "refresh@example.com",
            "password": "secret-pass-123",
        },
    )
    assert login_response.status_code == 200

    response = await api_client.post("/api/v1/auth/refresh")

    body = response.json()
    access_payload = decode_token(body["data"]["access_token"])

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "token refreshed"
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["user"]["id"] == user.id
    assert access_payload.sub == str(user.id)
    assert access_payload.token_type == "access"


@pytest.mark.asyncio
async def test_refresh_rejects_missing_cookie(api_client, monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")

    response = await api_client.post("/api/v1/auth/refresh")

    body = response.json()
    assert response.status_code == 401
    assert body["code"] == 40001
    assert body["message"] == "missing refresh token"

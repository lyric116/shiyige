import pytest

from backend.app.core.security import decode_token


@pytest.mark.asyncio
async def test_login_returns_access_token_and_sets_refresh_cookie(
    api_client,
    create_user,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="login@example.com",
        username="login-user",
        password="secret-pass-123",
        role="admin",
    )

    response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "secret-pass-123",
        },
    )

    body = response.json()
    access_payload = decode_token(body["data"]["access_token"])

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "login successful"
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["user"]["id"] == user.id
    assert access_payload.sub == str(user.id)
    assert access_payload.token_type == "access"
    assert access_payload.role == "admin"
    assert api_client.cookies.get("refresh_token") is not None
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()


@pytest.mark.asyncio
async def test_login_rejects_invalid_credentials(api_client, create_user, monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    create_user(
        email="login@example.com",
        username="login-user",
        password="secret-pass-123",
    )

    response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "login@example.com",
            "password": "wrong-password",
        },
    )

    body = response.json()
    assert response.status_code == 401
    assert body["code"] == 40001
    assert body["message"] == "invalid credentials"

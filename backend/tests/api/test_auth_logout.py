import pytest


@pytest.mark.asyncio
async def test_logout_clears_refresh_cookie(api_client, create_user, monkeypatch) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    create_user(
        email="logout@example.com",
        username="logout-user",
        password="secret-pass-123",
    )

    login_response = await api_client.post(
        "/api/v1/auth/login",
        json={
            "email": "logout@example.com",
            "password": "secret-pass-123",
        },
    )
    assert login_response.status_code == 200
    assert api_client.cookies.get("refresh_token") is not None

    response = await api_client.post("/api/v1/auth/logout")

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["message"] == "logout successful"
    assert "max-age=0" in response.headers["set-cookie"].lower()
    assert api_client.cookies.get("refresh_token") is None

    refresh_response = await api_client.post("/api/v1/auth/refresh")
    refresh_body = refresh_response.json()
    assert refresh_response.status_code == 401
    assert refresh_body["message"] == "missing refresh token"

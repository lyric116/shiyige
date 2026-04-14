import pytest


@pytest.mark.asyncio
async def test_login_endpoint_is_rate_limited_per_client_ip(
    api_client,
) -> None:
    headers = {"X-Forwarded-For": "203.0.113.10"}

    for _ in range(5):
        response = await api_client.post(
            "/api/v1/auth/login",
            headers=headers,
            json={
                "email": "missing@example.com",
                "password": "wrong-password",
            },
        )
        assert response.status_code == 401
        assert response.headers["X-RateLimit-Limit"] == "5"

    limited_response = await api_client.post(
        "/api/v1/auth/login",
        headers=headers,
        json={
            "email": "missing@example.com",
            "password": "wrong-password",
        },
    )
    body = limited_response.json()

    assert limited_response.status_code == 429
    assert body["message"] == "rate limit exceeded"
    assert body["request_id"] == limited_response.headers["X-Request-ID"]
    assert limited_response.headers["Retry-After"] != ""
    assert limited_response.headers["X-RateLimit-Limit"] == "5"
    assert limited_response.headers["X-RateLimit-Remaining"] == "0"

import httpx
import pytest

@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == response.json()["request_id"]
    assert response.json()["code"] == 0
    assert response.json()["message"] == "ok"
    assert response.json()["data"] == {"status": "ok"}

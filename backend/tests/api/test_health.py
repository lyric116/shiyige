import httpx
import pytest


@pytest.mark.asyncio
async def test_health_endpoint_returns_ok(async_client: httpx.AsyncClient) -> None:
    response = await async_client.get("/api/v1/health")
    body = response.json()

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert body["code"] == 0
    assert body["message"] == "ok"
    assert body["data"]["status"] == "ok"
    assert body["data"]["vector_store"]["configured_provider"] == "qdrant"
    assert body["data"]["vector_store"]["active_search_backend"] == "baseline"
    assert body["data"]["vector_store"]["active_recommendation_backend"] == "baseline"
    assert body["data"]["vector_store"]["degraded_to_baseline"] is True

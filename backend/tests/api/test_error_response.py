import httpx
import pytest

from backend.app.main import create_app


@pytest.mark.asyncio
async def test_validation_error_uses_unified_response_structure() -> None:
    app = create_app()

    @app.get("/api/v1/test-validation")
    async def test_validation(limit: int):
        return {"limit": limit}

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/test-validation", params={"limit": "bad"})

    body = response.json()
    assert response.status_code == 422
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert body["code"] == 40000
    assert body["message"] == "validation error"
    assert "errors" in body["data"]


@pytest.mark.asyncio
async def test_unhandled_error_uses_unified_response_structure() -> None:
    app = create_app()

    @app.get("/api/v1/test-crash")
    async def test_crash():
        raise RuntimeError("boom")

    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        response = await client.get("/api/v1/test-crash")

    body = response.json()
    assert response.status_code == 500
    assert response.headers["X-Request-ID"] == body["request_id"]
    assert body["code"] == 50000
    assert body["message"] == "internal server error"
    assert body["data"] is None

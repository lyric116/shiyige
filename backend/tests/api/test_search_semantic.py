import pytest


@pytest.mark.asyncio
async def test_semantic_search_returns_ranked_items_with_reason(
    api_client,
    seed_product_catalog,
) -> None:
    response = await api_client.post(
        "/api/v1/search/semantic",
        json={
            "query": "适合春日出游的素雅汉服",
            "limit": 3,
        },
    )

    body = response.json()
    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["query"] == "适合春日出游的素雅汉服"
    assert body["data"]["items"][0]["name"] == "明制襦裙"
    assert "语义相近" in body["data"]["items"][0]["reason"]
    assert "汉服" in body["data"]["items"][0]["reason"]
    assert body["data"]["items"][0]["score"] >= body["data"]["items"][1]["score"]

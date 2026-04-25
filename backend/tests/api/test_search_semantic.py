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
    assert body["data"]["pipeline"]["active_search_backend"] == "baseline"
    assert body["data"]["pipeline"]["degraded_to_baseline"] is True
    assert body["data"]["items"][0]["name"] == "明制襦裙"
    assert "语义相近" in body["data"]["items"][0]["reason"]
    assert "汉服" in body["data"]["items"][0]["reason"]
    assert "语义相关" in body["data"]["items"][0]["explanations"]
    assert "文化标签匹配" in body["data"]["items"][0]["explanations"]
    assert body["data"]["items"][0]["search_mode"] == "semantic"
    assert body["data"]["items"][0]["final_score"] == body["data"]["items"][0]["score"]
    assert body["data"]["items"][0]["dense_score"] is not None
    assert body["data"]["items"][0]["sparse_score"] is None
    assert body["data"]["items"][0]["rerank_score"] is None
    assert body["data"]["items"][0]["matched_terms"]
    assert body["data"]["items"][0]["pipeline_version"] == "baseline_semantic"
    assert body["data"]["items"][0]["score"] >= body["data"]["items"][1]["score"]


@pytest.mark.asyncio
async def test_products_search_alias_exposes_planned_score_fields(
    api_client,
    seed_product_catalog,
) -> None:
    response = await api_client.get(
        "/api/v1/products/search",
        params={
            "q": "端午香囊",
            "festival_tag": "端午",
            "limit": 2,
            "debug": True,
        },
    )

    body = response.json()
    first_item = body["data"]["items"][0]

    assert response.status_code == 200
    assert body["code"] == 0
    assert body["data"]["query"] == "端午香囊"
    assert body["data"]["pipeline"]["pipeline_version"] == "baseline"
    assert body["data"]["pipeline"]["debug"] is True
    assert first_item["final_score"] == first_item["score"]
    assert first_item["dense_score"] is not None
    assert "sparse_score" in first_item
    assert "rerank_score" in first_item
    assert "matched_terms" in first_item
    assert first_item["pipeline_version"] == "baseline_semantic"
    assert first_item["reason"]

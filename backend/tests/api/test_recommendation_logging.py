from __future__ import annotations

import pytest
from sqlalchemy import select

from backend.app.models.product import Product
from backend.app.models.recommendation_analytics import (
    RecommendationClickLog,
    RecommendationConversionLog,
    RecommendationImpressionLog,
    RecommendationRequestLog,
    SearchRequestLog,
    SearchResultLog,
)
from backend.app.models.user import UserAddress


@pytest.mark.asyncio
async def test_recommendation_request_and_impression_logs_are_written(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="rec-log@example.com", username="rec-log")
    headers = auth_headers_factory(user)

    response = await api_client.get(
        "/api/v1/recommendations",
        headers=headers,
        params={"slot": "home", "limit": 4, "debug": True},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["data"]["items"]

    with api_session_factory() as session:
        request_log = session.scalar(
            select(RecommendationRequestLog)
            .where(RecommendationRequestLog.user_id == user.id)
            .order_by(RecommendationRequestLog.id.desc())
        )
        impression_logs = session.scalars(
            select(RecommendationImpressionLog)
            .where(RecommendationImpressionLog.user_id == user.id)
            .order_by(RecommendationImpressionLog.rank_position.asc())
        ).all()

    assert request_log is not None
    assert request_log.slot == "home"
    assert request_log.candidate_count == len(body["data"]["items"])
    assert len(impression_logs) == len(body["data"]["items"])
    assert impression_logs[0].request_id == request_log.request_id
    assert impression_logs[0].rank_position == 1


@pytest.mark.asyncio
async def test_recommendation_click_and_conversion_logs_follow_user_actions(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="rec-convert@example.com", username="rec-convert")
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        address = UserAddress(
            user_id=user.id,
            recipient_name="推荐转化用户",
            phone="13800138000",
            region="北京市 东城区",
            detail_address="景山前街 4 号",
            postal_code="100009",
            is_default=True,
        )
        session.add(address)
        session.commit()
        session.refresh(address)

    recommendation_response = await api_client.get(
        "/api/v1/recommendations",
        headers=headers,
        params={"slot": "home", "limit": 3, "debug": True},
    )
    assert recommendation_response.status_code == 200
    top_product_id = recommendation_response.json()["data"]["items"][0]["id"]

    with api_session_factory() as session:
        product = session.get(Product, top_product_id)
        assert product is not None
        default_sku = product.default_sku
        assert default_sku is not None
        sku_id = default_sku.id

    detail_response = await api_client.get(f"/api/v1/products/{top_product_id}", headers=headers)
    assert detail_response.status_code == 200

    add_cart_response = await api_client.post(
        "/api/v1/cart/items",
        headers=headers,
        json={
            "product_id": top_product_id,
            "sku_id": sku_id,
            "quantity": 1,
        },
    )
    assert add_cart_response.status_code == 201

    create_order_response = await api_client.post(
        "/api/v1/orders",
        headers=headers,
        json={
            "address_id": address.id,
            "buyer_note": "推荐日志测试",
            "idempotency_key": "rec-log-order",
        },
    )
    assert create_order_response.status_code == 201
    order_id = create_order_response.json()["data"]["order"]["id"]

    pay_response = await api_client.post(
        f"/api/v1/orders/{order_id}/pay",
        headers=headers,
        json={"payment_method": "alipay"},
    )
    assert pay_response.status_code == 200

    with api_session_factory() as session:
        click_logs = session.scalars(
            select(RecommendationClickLog)
            .where(RecommendationClickLog.user_id == user.id)
            .order_by(RecommendationClickLog.id.asc())
        ).all()
        conversion_logs = session.scalars(
            select(RecommendationConversionLog)
            .where(RecommendationConversionLog.user_id == user.id)
            .order_by(RecommendationConversionLog.id.asc())
        ).all()

    assert len(click_logs) == 1
    assert click_logs[0].product_id == top_product_id
    assert click_logs[0].action_type == "click"
    assert {log.action_type for log in conversion_logs} == {
        "add_to_cart",
        "create_order",
        "pay_order",
    }
    assert all(log.product_id == top_product_id for log in conversion_logs)
    assert any(
        log.order_id == order_id for log in conversion_logs if log.action_type == "pay_order"
    )


@pytest.mark.asyncio
async def test_search_request_and_result_logs_are_written(
    api_client,
    api_session_factory,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    user = create_user(email="search-log@example.com", username="search-log")
    headers = auth_headers_factory(user)

    keyword_response = await api_client.get(
        "/api/v1/search",
        headers=headers,
        params={"q": "明制", "page_size": 3},
    )
    semantic_response = await api_client.post(
        "/api/v1/search/semantic",
        headers=headers,
        json={"query": "春日汉服", "limit": 3},
    )

    assert keyword_response.status_code == 200
    assert semantic_response.status_code == 200

    with api_session_factory() as session:
        request_logs = session.scalars(
            select(SearchRequestLog)
            .where(SearchRequestLog.user_id == user.id)
            .order_by(SearchRequestLog.id.asc())
        ).all()
        result_logs = session.scalars(
            select(SearchResultLog).order_by(SearchResultLog.id.asc())
        ).all()

    assert [log.mode for log in request_logs] == ["keyword", "semantic"]
    assert request_logs[0].query == "明制"
    assert request_logs[1].query == "春日汉服"
    assert request_logs[0].latency_ms >= 0
    assert request_logs[1].latency_ms >= 0
    assert result_logs

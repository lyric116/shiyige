from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
from uuid import uuid4

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.recommendation_analytics import (
    RecommendationClickLog,
    RecommendationConversionLog,
    RecommendationImpressionLog,
    RecommendationRequestLog,
    SearchRequestLog,
    SearchResultLog,
)


@dataclass(slots=True)
class RequestTimer:
    started_at: float

    @classmethod
    def start(cls) -> "RequestTimer":
        return cls(started_at=perf_counter())

    def elapsed_ms(self) -> float:
        return round((perf_counter() - self.started_at) * 1000, 3)


def resolve_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str) and request_id:
        return request_id
    return uuid4().hex


def log_recommendation_request(
    db: Session,
    *,
    request: Request,
    user_id: int | None,
    slot: str,
    pipeline_version: str,
    model_version: str,
    candidate_count: int,
    final_items: list[dict[str, Any]],
    latency_ms: float,
    fallback_used: bool,
) -> None:
    request_id = resolve_request_id(request)
    db.add(
        RecommendationRequestLog(
            request_id=request_id,
            user_id=user_id,
            slot=slot,
            pipeline_version=pipeline_version,
            model_version=model_version,
            candidate_count=candidate_count,
            final_product_ids=[int(item["product_id"]) for item in final_items],
            latency_ms=latency_ms,
            fallback_used=fallback_used,
        )
    )
    for index, item in enumerate(final_items, start=1):
        db.add(
            RecommendationImpressionLog(
                request_id=request_id,
                user_id=user_id,
                product_id=int(item["product_id"]),
                rank_position=index,
                recall_channels=list(item.get("recall_channels", [])),
                final_score=float(item.get("score", 0.0)),
                reason=str(item.get("reason", "")),
            )
        )


def log_search_request(
    db: Session,
    *,
    request: Request,
    user_id: int | None,
    query: str,
    mode: str,
    pipeline_version: str,
    total_results: int,
    latency_ms: float,
    filters_json: dict[str, Any] | None,
    items: list[dict[str, Any]],
) -> None:
    request_id = resolve_request_id(request)
    db.add(
        SearchRequestLog(
            request_id=request_id,
            user_id=user_id,
            query=query,
            mode=mode,
            pipeline_version=pipeline_version,
            total_results=total_results,
            latency_ms=latency_ms,
            filters_json=filters_json,
        )
    )
    for index, item in enumerate(items, start=1):
        db.add(
            SearchResultLog(
                request_id=request_id,
                product_id=int(item["product_id"]),
                rank_position=index,
                score=float(item.get("score", 0.0)),
                reason=str(item.get("reason", "")),
            )
        )


def log_recommendation_action(
    db: Session,
    *,
    user_id: int,
    product_id: int,
    action_type: str,
    order_id: int | None = None,
) -> None:
    impression = db.scalar(
        select(RecommendationImpressionLog)
        .where(
            RecommendationImpressionLog.user_id == user_id,
            RecommendationImpressionLog.product_id == product_id,
        )
        .order_by(
            RecommendationImpressionLog.created_at.desc(),
            RecommendationImpressionLog.id.desc(),
        )
    )
    if impression is None:
        return

    if action_type in {"click", "view_product"}:
        if not has_existing_action(
            db,
            model=RecommendationClickLog,
            request_id=impression.request_id,
            user_id=user_id,
            product_id=product_id,
            action_type="click",
        ):
            db.add(
                RecommendationClickLog(
                    request_id=impression.request_id,
                    user_id=user_id,
                    product_id=product_id,
                    action_type="click",
                )
            )
        return

    if action_type not in {"add_to_cart", "create_order", "pay_order"}:
        return

    if has_existing_action(
        db,
        model=RecommendationConversionLog,
        request_id=impression.request_id,
        user_id=user_id,
        product_id=product_id,
        action_type=action_type,
    ):
        return

    db.add(
        RecommendationConversionLog(
            request_id=impression.request_id,
            user_id=user_id,
            product_id=product_id,
            order_id=order_id,
            action_type=action_type,
        )
    )


def has_existing_action(
    db: Session,
    *,
    model,
    request_id: str,
    user_id: int,
    product_id: int,
    action_type: str,
) -> bool:
    record = db.scalar(
        select(model)
        .where(
            model.request_id == request_id,
            model.user_id == user_id,
            model.product_id == product_id,
            model.action_type == action_type,
        )
        .limit(1)
    )
    return record is not None

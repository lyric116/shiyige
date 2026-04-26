from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from time import monotonic
from typing import Deque

from fastapi import FastAPI, Request

from backend.app.core.exceptions import ensure_request_id
from backend.app.core.responses import build_response

RATE_LIMIT_RULES = {
    ("POST", "/api/v1/auth/login"): (5, 60),
    ("POST", "/api/v1/admin/auth/login"): (5, 60),
    ("POST", "/api/v1/media/reviews"): (10, 60),
    ("POST", "/api/v1/admin/media/products"): (10, 60),
}


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    retry_after: int


class InMemoryRateLimiter:
    def __init__(self):
        self.events: dict[str, Deque[float]] = defaultdict(deque)

    def check(self, key: str, *, limit: int, window_seconds: int) -> RateLimitDecision:
        now = monotonic()
        queue = self.events[key]
        threshold = now - window_seconds

        while queue and queue[0] <= threshold:
            queue.popleft()

        if len(queue) >= limit:
            retry_after = max(1, int(window_seconds - (now - queue[0])) + 1)
            return RateLimitDecision(
                allowed=False,
                remaining=0,
                retry_after=retry_after,
            )

        queue.append(now)
        return RateLimitDecision(
            allowed=True,
            remaining=max(0, limit - len(queue)),
            retry_after=0,
        )


def get_rate_limiter(app: FastAPI) -> InMemoryRateLimiter:
    rate_limiter = getattr(app.state, "rate_limiter", None)
    if rate_limiter is None:
        rate_limiter = InMemoryRateLimiter()
        app.state.rate_limiter = rate_limiter
    return rate_limiter


def resolve_client_identifier(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    client = request.client
    if client is not None and client.host:
        return client.host

    return "anonymous"


def register_rate_limit_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def rate_limit_middleware(request: Request, call_next):
        limit_config = RATE_LIMIT_RULES.get((request.method.upper(), request.url.path))
        if limit_config is None:
            return await call_next(request)

        limit, window_seconds = limit_config
        decision = get_rate_limiter(app).check(
            f"{request.method.upper()}:{request.url.path}:{resolve_client_identifier(request)}",
            limit=limit,
            window_seconds=window_seconds,
        )

        if not decision.allowed:
            ensure_request_id(request)
            response = build_response(
                request=request,
                code=40001,
                message="rate limit exceeded",
                data=None,
                status_code=429,
            )
            response.headers["Retry-After"] = str(decision.retry_after)
            response.headers["X-RateLimit-Limit"] = str(limit)
            response.headers["X-RateLimit-Remaining"] = "0"
            return response

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(decision.remaining)
        return response

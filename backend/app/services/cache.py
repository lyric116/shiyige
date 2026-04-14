from __future__ import annotations

import json
from typing import Protocol

from fastapi.encoders import jsonable_encoder

from backend.app.core.redis import get_redis_client


PRODUCT_DETAIL_CACHE_TTL = 120
RECOMMENDATIONS_CACHE_TTL = 90
SEARCH_SUGGESTIONS_CACHE_TTL = 180
MAX_RECOMMENDATION_CACHE_LIMIT = 20


class CacheBackend(Protocol):
    def get(self, key: str) -> str | None: ...

    def setex(self, key: str, ttl_seconds: int, value: str) -> object: ...

    def delete(self, key: str) -> object: ...


def get_cache_backend() -> CacheBackend:
    return get_redis_client()


def get_cached_json(key: str) -> dict[str, object] | list[object] | None:
    raw_value = get_cache_backend().get(key)
    if raw_value is None:
        return None
    return json.loads(raw_value)


def set_cached_json(
    key: str,
    value: dict[str, object] | list[object],
    *,
    ttl_seconds: int,
) -> None:
    encoded_value = json.dumps(
        jsonable_encoder(value),
        ensure_ascii=False,
        separators=(",", ":"),
    )
    get_cache_backend().setex(key, ttl_seconds, encoded_value)


def delete_cache_key(key: str) -> None:
    get_cache_backend().delete(key)


def build_cache_key(*parts: object) -> str:
    return ":".join(str(part) for part in parts)


def invalidate_recommendation_cache_for_user(user_id: int) -> None:
    for limit in range(1, MAX_RECOMMENDATION_CACHE_LIMIT + 1):
        delete_cache_key(build_cache_key("products", "recommendations", user_id, limit))

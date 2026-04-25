from __future__ import annotations

import hashlib
import json
import os
from typing import Protocol

from fastapi.encoders import jsonable_encoder

from backend.app.core.redis import get_redis_client

PRODUCT_DETAIL_CACHE_TTL = 120
RECOMMENDATIONS_CACHE_TTL = 90
PRECOMPUTED_RECOMMENDATION_CACHE_TTL = 900
PRECOMPUTED_RECOMMENDATION_STATUS_TTL = 60 * 60 * 24 * 30
RELATED_PRODUCTS_CACHE_TTL = 120
SEMANTIC_SEARCH_CACHE_TTL = 60
SEARCH_SUGGESTIONS_CACHE_TTL = 180
USER_PROFILE_CACHE_TTL = 180
MAX_RECOMMENDATION_CACHE_LIMIT = 20
RECOMMENDATION_CACHE_SLOTS = ("home", "cart", "order_complete", "related")
RECOMMENDATION_CACHE_BACKENDS = ("baseline", "multi_recall")


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


def get_cache_namespace() -> str:
    database_url = os.getenv("DATABASE_URL", "")
    if not database_url:
        return "default"
    return hashlib.sha1(database_url.encode("utf-8")).hexdigest()[:12]


def build_cache_key(*parts: object) -> str:
    return ":".join([get_cache_namespace(), *(str(part) for part in parts)])


def build_recommendation_cache_key(
    *,
    user_id: int,
    slot: str,
    limit: int,
    backend: str | None = None,
) -> str:
    if backend:
        return build_cache_key("products", "recommendations", user_id, slot, backend, limit)
    return build_cache_key("products", "recommendations", user_id, slot, limit)


def build_precomputed_recommendation_cache_key(
    *,
    user_id: int,
    slot: str,
    limit: int,
    backend: str,
) -> str:
    return build_cache_key("recommendation", "precomputed", user_id, slot, backend, limit)


def build_precomputed_recommendation_status_key() -> str:
    return build_cache_key("recommendation", "precomputed", "status")


def build_user_profile_cache_key(user_id: int) -> str:
    return build_cache_key("recommendation", "profile", user_id)


def invalidate_recommendation_cache_for_user(user_id: int) -> None:
    for limit in range(1, MAX_RECOMMENDATION_CACHE_LIMIT + 1):
        delete_cache_key(build_cache_key("products", "recommendations", user_id, limit))
        for slot in RECOMMENDATION_CACHE_SLOTS:
            delete_cache_key(
                build_recommendation_cache_key(
                    user_id=user_id,
                    slot=slot,
                    limit=limit,
                )
            )
            for backend in RECOMMENDATION_CACHE_BACKENDS:
                delete_cache_key(
                    build_recommendation_cache_key(
                        user_id=user_id,
                        slot=slot,
                        limit=limit,
                        backend=backend,
                    )
                )
                delete_cache_key(
                    build_precomputed_recommendation_cache_key(
                        user_id=user_id,
                        slot=slot,
                        limit=limit,
                        backend=backend,
                    )
                )
    delete_cache_key(build_user_profile_cache_key(user_id))

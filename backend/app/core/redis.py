import os
from functools import lru_cache

from redis import Redis

DEFAULT_REDIS_URL = "redis://127.0.0.1:6379/0"


def get_redis_url() -> str:
    return os.getenv("REDIS_URL", DEFAULT_REDIS_URL)


@lru_cache
def get_redis_client() -> Redis:
    return Redis.from_url(get_redis_url(), decode_responses=True)


def check_redis_connection() -> bool:
    return bool(get_redis_client().ping())


def reset_redis_state() -> None:
    get_redis_client.cache_clear()

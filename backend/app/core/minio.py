from functools import lru_cache
import os

from minio import Minio


DEFAULT_MINIO_ENDPOINT = "127.0.0.1:9000"
DEFAULT_MINIO_ACCESS_KEY = "minioadmin"
DEFAULT_MINIO_SECRET_KEY = "minioadmin"


def get_minio_settings() -> tuple[str, str, str, bool]:
    endpoint = os.getenv("MINIO_ENDPOINT", DEFAULT_MINIO_ENDPOINT)
    access_key = os.getenv("MINIO_ACCESS_KEY", DEFAULT_MINIO_ACCESS_KEY)
    secret_key = os.getenv("MINIO_SECRET_KEY", DEFAULT_MINIO_SECRET_KEY)
    secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
    return endpoint, access_key, secret_key, secure


@lru_cache
def get_minio_client() -> Minio:
    endpoint, access_key, secret_key, secure = get_minio_settings()
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=secure,
    )


def check_minio_connection() -> bool:
    client = get_minio_client()
    list(client.list_buckets())
    return True


def reset_minio_state() -> None:
    get_minio_client.cache_clear()

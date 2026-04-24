from __future__ import annotations

from dataclasses import asdict, dataclass
from time import monotonic

from qdrant_client import QdrantClient

from backend.app.core.config import AppSettings, get_app_settings


@dataclass(frozen=True)
class QdrantConnectionStatus:
    url: str
    available: bool
    collections: list[str]
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


_STATUS_CACHE_TTL_SECONDS = 3.0
_status_cache: dict[str, tuple[float, QdrantConnectionStatus]] = {}


def create_qdrant_client(settings: AppSettings | None = None) -> QdrantClient:
    app_settings = settings or get_app_settings()
    return QdrantClient(
        url=app_settings.qdrant_url,
        api_key=app_settings.qdrant_api_key or None,
        timeout=app_settings.qdrant_timeout_seconds,
        check_compatibility=False,
    )


def get_qdrant_connection_status(
    settings: AppSettings | None = None,
) -> QdrantConnectionStatus:
    app_settings = settings or get_app_settings()
    cache_key = app_settings.qdrant_url
    cached = _status_cache.get(cache_key)
    now = monotonic()
    if cached is not None and now - cached[0] <= _STATUS_CACHE_TTL_SECONDS:
        return cached[1]

    client = create_qdrant_client(app_settings)
    try:
        collections = client.get_collections()
        collection_names = sorted(collection.name for collection in collections.collections)
        status = QdrantConnectionStatus(
            url=app_settings.qdrant_url,
            available=True,
            collections=collection_names,
        )
        _status_cache[cache_key] = (now, status)
        return status
    except Exception as exc:  # pragma: no cover - provider exceptions vary by transport
        status = QdrantConnectionStatus(
            url=app_settings.qdrant_url,
            available=False,
            collections=[],
            error=f"{exc.__class__.__name__}: {exc}",
        )
        _status_cache[cache_key] = (now, status)
        return status
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def collection_exists(
    collection_name: str,
    *,
    settings: AppSettings | None = None,
) -> bool:
    status = get_qdrant_connection_status(settings)
    return collection_name in status.collections

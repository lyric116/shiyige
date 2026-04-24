from __future__ import annotations

from dataclasses import asdict, dataclass

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.core.logger import get_logger
from backend.app.services.qdrant_client import (
    QdrantConnectionStatus,
    create_qdrant_client,
    get_qdrant_connection_status,
)
from backend.app.services.vector_schema import build_product_collection_schema
from backend.app.tasks.qdrant_schema_tasks import collection_has_schema_drift

logger = get_logger(__name__)


@dataclass(frozen=True)
class VectorStoreRuntime:
    configured_provider: str
    recommendation_pipeline_version: str
    configured_recommendation_ranker: str
    qdrant_available: bool
    qdrant_url: str
    qdrant_collections: list[str]
    qdrant_error: str | None
    degraded_to_baseline: bool
    active_search_backend: str
    active_recommendation_backend: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def is_qdrant_search_ready(
    settings: AppSettings | None = None,
    *,
    qdrant_status: QdrantConnectionStatus | None = None,
) -> tuple[bool, str | None]:
    app_settings = settings or get_app_settings()
    if app_settings.vector_db_provider != "qdrant":
        return False, None

    status = qdrant_status or get_qdrant_connection_status(app_settings)
    if not status.available:
        return False, status.error
    if app_settings.qdrant_collection_products not in status.collections:
        return False, "Qdrant product collection is not initialized"

    client = create_qdrant_client(app_settings)
    try:
        collection_info = client.get_collection(app_settings.qdrant_collection_products)
        if collection_has_schema_drift(
            collection_info,
            build_product_collection_schema(app_settings),
        ):
            return False, "Qdrant product collection schema drift detected"

        point_count = int(collection_info.points_count or 0)
        if point_count <= 0:
            return False, "Qdrant product collection has no indexed points"
        return True, None
    except Exception as exc:  # pragma: no cover - provider exceptions vary by transport
        return False, f"{exc.__class__.__name__}: {exc}"
    finally:
        close = getattr(client, "close", None)
        if callable(close):
            close()


def probe_vector_store_runtime(
    settings: AppSettings | None = None,
    *,
    log_on_degrade: bool = False,
) -> VectorStoreRuntime:
    app_settings = settings or get_app_settings()
    qdrant_status = get_qdrant_connection_status(app_settings)
    search_ready, search_error = is_qdrant_search_ready(
        app_settings,
        qdrant_status=qdrant_status,
    )
    degraded = app_settings.vector_db_provider == "qdrant" and not search_ready

    runtime = VectorStoreRuntime(
        configured_provider=app_settings.vector_db_provider,
        recommendation_pipeline_version=app_settings.recommendation_pipeline_version,
        configured_recommendation_ranker=app_settings.recommendation_ranker,
        qdrant_available=qdrant_status.available,
        qdrant_url=qdrant_status.url,
        qdrant_collections=qdrant_status.collections,
        qdrant_error=qdrant_status.error or search_error,
        degraded_to_baseline=degraded,
        active_search_backend="qdrant_hybrid" if search_ready else "baseline",
        active_recommendation_backend="multi_recall" if search_ready else "baseline",
    )
    if degraded and log_on_degrade:
        logger.warning(
            "Qdrant search is not ready, keeping baseline recommendation runtime. error=%s",
            runtime.qdrant_error,
        )
    return runtime


def describe_vector_store_runtime(settings: AppSettings | None = None) -> dict[str, object]:
    return probe_vector_store_runtime(settings).to_dict()


def build_runtime_marker(settings: AppSettings | None = None) -> dict[str, object]:
    runtime = probe_vector_store_runtime(settings)
    return {
        "configured_provider": runtime.configured_provider,
        "recommendation_pipeline_version": runtime.recommendation_pipeline_version,
        "configured_recommendation_ranker": runtime.configured_recommendation_ranker,
        "qdrant_available": runtime.qdrant_available,
        "degraded_to_baseline": runtime.degraded_to_baseline,
        "active_search_backend": runtime.active_search_backend,
        "active_recommendation_backend": runtime.active_recommendation_backend,
    }

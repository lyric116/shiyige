from __future__ import annotations

from dataclasses import asdict, dataclass

from backend.app.core.config import AppSettings, get_app_settings
from backend.app.core.logger import get_logger
from backend.app.services.qdrant_client import get_qdrant_connection_status

logger = get_logger(__name__)


@dataclass(frozen=True)
class VectorStoreRuntime:
    configured_provider: str
    recommendation_pipeline_version: str
    qdrant_available: bool
    qdrant_url: str
    qdrant_collections: list[str]
    qdrant_error: str | None
    degraded_to_baseline: bool
    active_search_backend: str
    active_recommendation_backend: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def probe_vector_store_runtime(
    settings: AppSettings | None = None,
    *,
    log_on_degrade: bool = False,
) -> VectorStoreRuntime:
    app_settings = settings or get_app_settings()
    qdrant_status = get_qdrant_connection_status(app_settings)
    degraded = app_settings.vector_db_provider == "qdrant" and not qdrant_status.available

    runtime = VectorStoreRuntime(
        configured_provider=app_settings.vector_db_provider,
        recommendation_pipeline_version=app_settings.recommendation_pipeline_version,
        qdrant_available=qdrant_status.available,
        qdrant_url=qdrant_status.url,
        qdrant_collections=qdrant_status.collections,
        qdrant_error=qdrant_status.error,
        degraded_to_baseline=degraded,
        active_search_backend="baseline",
        active_recommendation_backend="baseline",
    )
    if degraded and log_on_degrade:
        logger.warning(
            "Qdrant is unavailable, keeping baseline recommendation runtime. error=%s",
            qdrant_status.error,
        )
    return runtime


def describe_vector_store_runtime(settings: AppSettings | None = None) -> dict[str, object]:
    return probe_vector_store_runtime(settings).to_dict()


def build_runtime_marker(settings: AppSettings | None = None) -> dict[str, object]:
    runtime = probe_vector_store_runtime(settings)
    return {
        "configured_provider": runtime.configured_provider,
        "recommendation_pipeline_version": runtime.recommendation_pipeline_version,
        "qdrant_available": runtime.qdrant_available,
        "degraded_to_baseline": runtime.degraded_to_baseline,
        "active_search_backend": runtime.active_search_backend,
        "active_recommendation_backend": runtime.active_recommendation_backend,
    }

from backend.app.core.config import AppSettings
from backend.app.services.qdrant_client import collection_exists, get_qdrant_connection_status
from backend.app.services.vector_store import probe_vector_store_runtime


def build_settings(qdrant_url: str) -> AppSettings:
    return AppSettings(
        qdrant_url=qdrant_url,
        vector_db_provider="qdrant",
        qdrant_collection_products="shiyige_products_v1",
        qdrant_collection_users="shiyige_users_v1",
        qdrant_collection_cf="shiyige_collaborative_v1",
    )


def test_qdrant_connection_status_reports_live_service_when_available() -> None:
    settings = build_settings("http://127.0.0.1:6333")
    status = get_qdrant_connection_status(settings)

    if not status.available:
        assert status.error is not None
        return

    assert status.url == "http://127.0.0.1:6333"
    assert isinstance(status.collections, list)
    assert collection_exists("shiyige_products_v1", settings=settings) is False


def test_vector_store_runtime_degrades_to_baseline_when_qdrant_is_unreachable() -> None:
    settings = build_settings("http://127.0.0.1:65535")
    runtime = probe_vector_store_runtime(settings)

    assert runtime.configured_provider == "qdrant"
    assert runtime.qdrant_available is False
    assert runtime.degraded_to_baseline is True
    assert runtime.active_search_backend == "baseline"
    assert runtime.active_recommendation_backend == "baseline"

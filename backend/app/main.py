from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.router import api_router
from backend.app.core.config import get_app_settings
from backend.app.core.exceptions import register_exception_handlers
from backend.app.core.logger import configure_logging, get_logger
from backend.app.core.minio import check_minio_connection
from backend.app.core.rate_limit import register_rate_limit_middleware
from backend.app.core.redis import check_redis_connection
from backend.app.core.request_id import register_request_id_middleware
from backend.app.services.vector_store import probe_vector_store_runtime
from backend.app.tasks.qdrant_schema_tasks import ensure_product_collection

logger = get_logger(__name__)


def create_app() -> FastAPI:
    settings = get_app_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime = probe_vector_store_runtime(log_on_degrade=True)
        app.state.vector_store_runtime = runtime
        if runtime.qdrant_available:
            try:
                app.state.qdrant_schema = ensure_product_collection()
            except Exception as exc:  # pragma: no cover - startup protection
                logger.warning("Failed to ensure Qdrant schema on startup. error=%s", exc)
        if settings.enable_startup_checks:
            check_redis_connection()
            check_minio_connection()
        yield

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        docs_url=settings.docs_url,
        redoc_url=settings.redoc_url,
        lifespan=lifespan,
    )
    app.state.settings = settings

    register_request_id_middleware(app)
    register_rate_limit_middleware(app)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.config import AppSettings, get_app_settings  # noqa: E402
from backend.app.core.database import get_session_factory, reset_database_state  # noqa: E402
from backend.app.models.base import Base  # noqa: E402
from backend.app.services.qdrant_client import get_qdrant_connection_status  # noqa: E402
from backend.app.tasks.collaborative_index_tasks import build_collaborative_index  # noqa: E402


def resolve_app_settings() -> AppSettings:
    settings = get_app_settings()
    if get_qdrant_connection_status(settings).available:
        return settings

    localhost_settings = settings.model_copy(update={"qdrant_url": "http://127.0.0.1:6333"})
    if get_qdrant_connection_status(localhost_settings).available:
        return localhost_settings
    return settings


def main() -> None:
    session = get_session_factory()()
    try:
        Base.metadata.create_all(bind=session.get_bind())
        result = build_collaborative_index(session, settings=resolve_app_settings())
        print(result)
    finally:
        session.close()


if __name__ == "__main__":
    reset_database_state()
    main()

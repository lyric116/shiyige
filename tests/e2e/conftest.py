import os
import socket
import threading
import time
from pathlib import Path

import pytest
import uvicorn
from fastapi.staticfiles import StaticFiles
from playwright.sync_api import Browser, sync_playwright
from sqlalchemy.orm import Session

os.environ.setdefault("EMBEDDING_PROVIDER", "local_hash")
os.environ.setdefault("EMBEDDING_MODEL_NAME", "shiyige-local-hash-zh")
os.environ.setdefault("EMBEDDING_DIMENSION", "64")
os.environ.setdefault("EMBEDDING_MODEL_SOURCE", "Deterministic local hash fallback for tests")
os.environ.setdefault("EMBEDDING_MODEL_REVISION", "test")
os.environ.setdefault("SPARSE_EMBEDDING_PROVIDER", "local_hash")
os.environ.setdefault("SPARSE_EMBEDDING_MODEL_NAME", "shiyige-local-sparse")
os.environ.setdefault("SPARSE_EMBEDDING_DIMENSION", "0")
os.environ.setdefault("COLBERT_EMBEDDING_PROVIDER", "local_hash")
os.environ.setdefault("COLBERT_EMBEDDING_MODEL_NAME", "shiyige-local-colbert")
os.environ.setdefault("COLBERT_EMBEDDING_DIMENSION", "16")

from backend.app.core.database import create_app_engine, reset_database_state
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.scripts.seed_base_data import seed_base_data

ROOT = Path(__file__).resolve().parents[2]


def get_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def browser() -> Browser:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        yield browser
        browser.close()


@pytest.fixture
def live_server(monkeypatch, tmp_path):
    database_file = tmp_path / "e2e.db"
    database_url = f"sqlite:///{database_file}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("SECRET_KEY", "e2e-secret-key")
    reset_database_state()

    engine = create_app_engine(database_url)
    Base.metadata.create_all(bind=engine)
    with Session(engine) as session:
        seed_base_data(session)
    app = create_app()
    app.mount("/admin", StaticFiles(directory=ROOT / "admin", html=True), name="admin")
    app.mount("/", StaticFiles(directory=ROOT / "front", html=True), name="front")

    port = get_free_port()
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    deadline = time.time() + 10
    while not server.started and time.time() < deadline:
        time.sleep(0.05)

    if not server.started:
        raise RuntimeError("E2E server failed to start")

    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=5)
        engine.dispose()
        reset_database_state()

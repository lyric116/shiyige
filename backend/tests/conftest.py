import sys
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.database import create_app_engine, reset_database_state
from backend.app.main import create_app

ROOT = Path(__file__).resolve().parents[2]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def app():
    return create_app()


@pytest_asyncio.fixture
async def async_client(app):
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
    ) as client:
        yield client


@pytest.fixture
def temp_database_url(monkeypatch, tmp_path):
    database_file = tmp_path / "test.db"
    database_url = f"sqlite:///{database_file}"
    monkeypatch.setenv("DATABASE_URL", database_url)
    reset_database_state()
    yield database_url
    reset_database_state()


@pytest.fixture
def db_engine(temp_database_url):
    engine = create_app_engine(temp_database_url)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    session_factory = sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user_identity():
    return {
        "id": 1,
        "email": "tester@example.com",
        "username": "tester",
        "role": "user",
    }


@pytest.fixture
def auth_headers():
    return {"Authorization": "Bearer test-token"}


@pytest.fixture
def seed_catalog():
    return {
        "categories": [
            {"id": 1, "name": "汉服"},
            {"id": 2, "name": "文创产品"},
        ],
        "products": [
            {"id": 1, "name": "明制襦裙", "category_id": 1},
            {"id": 2, "name": "故宫宫廷香囊", "category_id": 2},
        ],
    }

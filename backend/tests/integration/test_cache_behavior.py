from collections.abc import Callable, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import create_app
from backend.app.models.base import Base
from backend.app.models.product import Product
from backend.app.models.user import User, UserProfile
from backend.app.services import cache as cache_service
from backend.scripts.seed_base_data import seed_base_data
from backend.tests.api.test_recommendations import create_user_preference_trace


class FakeCacheBackend:
    def __init__(self):
        self.store: dict[str, str] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self.store[key] = value
        return True

    def delete(self, key: str) -> int:
        return int(self.store.pop(key, None) is not None)


@pytest.fixture
def api_session_factory(db_engine) -> sessionmaker[Session]:
    Base.metadata.create_all(db_engine)
    return sessionmaker(
        bind=db_engine,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )


@pytest.fixture
def api_app(api_session_factory) -> Generator:
    app = create_app()

    def override_get_db():
        session = api_session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    yield app
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def api_client(api_app):
    transport = ASGITransport(app=api_app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture
def create_user(api_session_factory) -> Callable[..., User]:
    def factory(
        *,
        email: str = "tester@example.com",
        username: str = "tester",
        password: str = "secret-pass-123",
        role: str = "user",
        is_active: bool = True,
    ) -> User:
        with api_session_factory() as session:
            user = User(
                email=email,
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=is_active,
            )
            user.profile = UserProfile(display_name=username)
            session.add(user)
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user

    return factory


@pytest.fixture
def auth_headers_factory() -> Callable[[User], dict[str, str]]:
    def factory(user: User) -> dict[str, str]:
        token = create_access_token(subject=str(user.id), role=user.role)
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture
def seed_product_catalog(api_session_factory) -> None:
    with api_session_factory() as session:
        seed_base_data(session)


@pytest.mark.asyncio
async def test_product_detail_search_suggestions_and_recommendations_are_cached(
    monkeypatch,
    api_session_factory,
    api_client,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    fake_cache = FakeCacheBackend()
    monkeypatch.setattr(cache_service, "get_cache_backend", lambda: fake_cache)

    with api_session_factory() as session:
        product = session.scalar(select(Product).where(Product.name == "明制襦裙"))
        accessory = session.scalar(select(Product).where(Product.name == "点翠发簪"))
        assert product is not None
        assert accessory is not None
        assert accessory.default_sku is not None
        product_id = product.id
        accessory_id = accessory.id
        accessory_sku_id = accessory.default_sku.id

    first_detail_response = await api_client.get(f"/api/v1/products/{product_id}")
    assert first_detail_response.status_code == 200
    assert first_detail_response.json()["data"]["product"]["name"] == "明制襦裙"

    with api_session_factory() as session:
        stored_product = session.get(Product, product_id)
        assert stored_product is not None
        stored_product.name = "缓存后被修改的商品名"
        session.add(stored_product)
        session.commit()

    second_detail_response = await api_client.get(f"/api/v1/products/{product_id}")
    assert second_detail_response.status_code == 200
    assert second_detail_response.json()["data"]["product"]["name"] == "明制襦裙"

    first_suggestion_response = await api_client.get(
        "/api/v1/search/suggestions",
        params={"q": "故宫", "limit": 3},
    )
    assert first_suggestion_response.status_code == 200
    assert first_suggestion_response.json()["data"]["items"][0]["keyword"] == "故宫宫廷香囊"

    with api_session_factory() as session:
        renamed_product = session.scalar(select(Product).where(Product.name == "故宫宫廷香囊"))
        assert renamed_product is not None
        renamed_product.name = "缓存后改名的香囊"
        session.add(renamed_product)
        session.commit()

    second_suggestion_response = await api_client.get(
        "/api/v1/search/suggestions",
        params={"q": "故宫", "limit": 3},
    )
    assert second_suggestion_response.status_code == 200
    assert second_suggestion_response.json()["data"]["items"][0]["keyword"] == "故宫宫廷香囊"

    user = create_user(
        email="cache-rec@example.com",
        username="cache-rec",
    )
    headers = auth_headers_factory(user)
    await create_user_preference_trace(
        api_client,
        headers,
        accessory_id,
        accessory_sku_id,
        "古风发簪",
    )

    first_recommendation_response = await api_client.get(
        "/api/v1/products/recommendations",
        headers=headers,
    )
    first_items = first_recommendation_response.json()["data"]["items"]
    assert first_recommendation_response.status_code == 200
    assert first_items

    cached_product_id = first_items[0]["id"]
    cached_product_name = first_items[0]["name"]

    with api_session_factory() as session:
        cached_product = session.get(Product, cached_product_id)
        assert cached_product is not None
        cached_product.name = "缓存后改名的推荐商品"
        session.add(cached_product)
        session.commit()

    second_recommendation_response = await api_client.get(
        "/api/v1/products/recommendations",
        headers=headers,
    )
    second_items = second_recommendation_response.json()["data"]["items"]

    assert second_recommendation_response.status_code == 200
    assert second_items[0]["id"] == cached_product_id
    assert second_items[0]["name"] == cached_product_name


@pytest.mark.asyncio
async def test_recommendation_cache_is_invalidated_after_user_behavior(
    monkeypatch,
    api_session_factory,
    api_client,
    create_user,
    auth_headers_factory,
    seed_product_catalog,
) -> None:
    fake_cache = FakeCacheBackend()
    monkeypatch.setattr(cache_service, "get_cache_backend", lambda: fake_cache)

    user = create_user(
        email="cache-rec-invalidate@example.com",
        username="cache-rec-invalidate",
    )
    headers = auth_headers_factory(user)

    with api_session_factory() as session:
        hanfu = session.scalar(select(Product).where(Product.name == "明制襦裙"))
        assert hanfu is not None
        assert hanfu.default_sku is not None
        hanfu_id = hanfu.id
        hanfu_sku_id = hanfu.default_sku.id

    first_response = await api_client.get(
        "/api/v1/products/recommendations",
        headers=headers,
    )
    assert first_response.status_code == 200
    first_ids = [item["id"] for item in first_response.json()["data"]["items"][:3]]

    await create_user_preference_trace(
        api_client,
        headers,
        hanfu_id,
        hanfu_sku_id,
        "春日汉服",
    )

    second_response = await api_client.get(
        "/api/v1/products/recommendations",
        headers=headers,
    )
    assert second_response.status_code == 200
    second_ids = [item["id"] for item in second_response.json()["data"]["items"][:3]]

    assert first_ids != second_ids

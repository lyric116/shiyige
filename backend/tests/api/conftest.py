import os
from collections.abc import Callable, Generator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.orm import Session, sessionmaker

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

from backend.app.core.database import get_db
from backend.app.core.security import create_access_token, hash_password
from backend.app.main import create_app
from backend.app.models.admin import AdminUser
from backend.app.models.base import Base
from backend.app.models.user import User, UserProfile
from backend.scripts.seed_base_data import seed_base_data


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
def create_admin_user(api_session_factory) -> Callable[..., AdminUser]:
    def factory(
        *,
        email: str = "admin@example.com",
        username: str = "admin",
        password: str = "secret-pass-123",
        role: str = "super_admin",
        is_active: bool = True,
    ) -> AdminUser:
        with api_session_factory() as session:
            admin_user = AdminUser(
                email=email,
                username=username,
                password_hash=hash_password(password),
                role=role,
                is_active=is_active,
            )
            session.add(admin_user)
            session.commit()
            session.refresh(admin_user)
            session.expunge(admin_user)
            return admin_user

    return factory


@pytest.fixture
def admin_auth_headers_factory() -> Callable[[AdminUser], dict[str, str]]:
    def factory(admin_user: AdminUser) -> dict[str, str]:
        token = create_access_token(
            subject=f"admin:{admin_user.id}",
            role=admin_user.role,
        )
        return {"Authorization": f"Bearer {token}"}

    return factory


@pytest.fixture
def seed_product_catalog(api_session_factory) -> None:
    with api_session_factory() as session:
        seed_base_data(session)

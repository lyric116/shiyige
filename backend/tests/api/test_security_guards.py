import pytest

from backend.app.core.security import create_access_token
from backend.app.services.media import StoredObject, get_media_storage


class FakeMediaStorage:
    def __init__(self):
        self.uploads: list[dict[str, object]] = []

    def upload_bytes(
        self, *, bucket: str, object_name: str, data: bytes, content_type: str
    ) -> StoredObject:
        self.uploads.append(
            {
                "bucket": bucket,
                "object_name": object_name,
                "data": data,
                "content_type": content_type,
            }
        )
        return StoredObject(
            bucket=bucket,
            object_name=object_name,
            url=f"https://media.example.com/{bucket}/{object_name}",
        )


@pytest.fixture
def fake_media_storage(api_app):
    storage = FakeMediaStorage()
    api_app.dependency_overrides[get_media_storage] = lambda: storage
    yield storage
    api_app.dependency_overrides.pop(get_media_storage, None)


@pytest.mark.asyncio
async def test_admin_media_upload_rejects_frontend_user_token(
    api_client,
    create_user,
    auth_headers_factory,
    fake_media_storage,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="guard-user@example.com",
        username="guard-user",
    )

    response = await api_client.post(
        "/api/v1/admin/media/products",
        headers=auth_headers_factory(user),
        files={"file": ("product.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 403
    assert response.json()["message"] == "permission denied"
    assert fake_media_storage.uploads == []


@pytest.mark.asyncio
async def test_admin_media_upload_rejects_access_token_without_admin_subject_prefix(
    api_client,
    create_admin_user,
    fake_media_storage,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    admin_user = create_admin_user(
        email="guard-admin@example.com",
        username="guard-admin",
    )
    forged_token = create_access_token(
        subject=str(admin_user.id),
        role=admin_user.role,
    )

    response = await api_client.post(
        "/api/v1/admin/media/products",
        headers={"Authorization": f"Bearer {forged_token}"},
        files={"file": ("product.png", b"fake-image", "image/png")},
    )

    assert response.status_code == 401
    assert response.json()["message"] == "invalid admin token"
    assert fake_media_storage.uploads == []


@pytest.mark.asyncio
async def test_review_media_upload_rejects_empty_file(
    api_client,
    create_user,
    auth_headers_factory,
    fake_media_storage,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="guard-review@example.com",
        username="guard-review",
    )

    response = await api_client.post(
        "/api/v1/media/reviews",
        headers=auth_headers_factory(user),
        files={"file": ("empty.png", b"", "image/png")},
    )

    assert response.status_code == 400
    assert response.json()["message"] == "empty file"
    assert fake_media_storage.uploads == []

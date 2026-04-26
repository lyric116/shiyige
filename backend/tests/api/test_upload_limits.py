import pytest

from backend.app.services.media import MAX_REVIEW_MEDIA_BYTES, StoredObject, get_media_storage


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
async def test_product_media_upload_rejects_unsupported_content_type(
    api_client,
    create_admin_user,
    admin_auth_headers_factory,
    fake_media_storage,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    admin_user = create_admin_user(
        email="admin-upload-limit@example.com",
        username="admin-upload-limit",
    )

    response = await api_client.post(
        "/api/v1/admin/media/products",
        headers=admin_auth_headers_factory(admin_user),
        files={"file": ("notes.txt", b"not-an-image", "text/plain")},
    )

    assert response.status_code == 415
    assert response.json()["message"] == "unsupported media type"
    assert fake_media_storage.uploads == []


@pytest.mark.asyncio
async def test_review_media_upload_rejects_oversized_file(
    api_client,
    create_user,
    auth_headers_factory,
    fake_media_storage,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="review-upload-limit@example.com",
        username="review-upload-limit",
    )

    response = await api_client.post(
        "/api/v1/media/reviews",
        headers=auth_headers_factory(user),
        files={
            "file": (
                "too-large.png",
                b"x" * (MAX_REVIEW_MEDIA_BYTES + 1),
                "image/png",
            )
        },
    )

    assert response.status_code == 413
    assert response.json()["message"] == "file too large"
    assert fake_media_storage.uploads == []

import pytest

from backend.app.services.media import PRODUCT_MEDIA_BUCKET, REVIEW_MEDIA_BUCKET, StoredObject, get_media_storage


class FakeMediaStorage:
    def __init__(self):
        self.uploads: list[dict[str, object]] = []

    def upload_bytes(self, *, bucket: str, object_name: str, data: bytes, content_type: str) -> StoredObject:
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
async def test_admin_product_media_upload_returns_stored_file_url(
    api_client,
    create_admin_user,
    admin_auth_headers_factory,
    fake_media_storage,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    admin_user = create_admin_user(
        email="admin-media@example.com",
        username="admin-media",
    )

    response = await api_client.post(
        "/api/v1/admin/media/products",
        headers=admin_auth_headers_factory(admin_user),
        files={"file": ("product.png", b"fake-product-image", "image/png")},
    )
    body = response.json()

    assert response.status_code == 201
    assert body["message"] == "upload successful"
    assert body["data"]["file"]["bucket"] == PRODUCT_MEDIA_BUCKET
    assert body["data"]["file"]["content_type"] == "image/png"
    assert body["data"]["file"]["size"] == len(b"fake-product-image")
    assert fake_media_storage.uploads[0]["bucket"] == PRODUCT_MEDIA_BUCKET
    assert fake_media_storage.uploads[0]["content_type"] == "image/png"


@pytest.mark.asyncio
async def test_review_media_upload_returns_user_scoped_file_url(
    api_client,
    create_user,
    auth_headers_factory,
    fake_media_storage,
    monkeypatch,
) -> None:
    monkeypatch.setenv("SECRET_KEY", "unit-test-secret")
    user = create_user(
        email="review-upload@example.com",
        username="review-upload",
    )

    response = await api_client.post(
        "/api/v1/media/reviews",
        headers=auth_headers_factory(user),
        files={"file": ("review.webp", b"fake-review-image", "image/webp")},
    )
    body = response.json()

    assert response.status_code == 201
    assert body["message"] == "upload successful"
    assert body["data"]["file"]["bucket"] == REVIEW_MEDIA_BUCKET
    assert body["data"]["file"]["content_type"] == "image/webp"
    assert f"reviews/user-{user.id}/" in body["data"]["file"]["object_name"]
    assert fake_media_storage.uploads[0]["bucket"] == REVIEW_MEDIA_BUCKET
    assert fake_media_storage.uploads[0]["content_type"] == "image/webp"

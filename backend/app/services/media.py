from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from io import BytesIO
from typing import Protocol
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status

from backend.app.core.minio import get_minio_client, get_minio_settings


ALLOWED_IMAGE_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}

MAX_PRODUCT_MEDIA_BYTES = 5 * 1024 * 1024
MAX_REVIEW_MEDIA_BYTES = 3 * 1024 * 1024
PRODUCT_MEDIA_BUCKET = "product-media"
REVIEW_MEDIA_BUCKET = "review-media"


@dataclass
class StoredObject:
    bucket: str
    object_name: str
    url: str


class MediaStorage(Protocol):
    def upload_bytes(
        self,
        *,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject: ...


class MinioMediaStorage:
    def __init__(self):
        self.client = get_minio_client()
        endpoint, _, _, secure = get_minio_settings()
        self.endpoint = endpoint
        self.secure = secure

    def ensure_bucket(self, bucket: str) -> None:
        if not self.client.bucket_exists(bucket):
            self.client.make_bucket(bucket)

    def build_public_url(self, bucket: str, object_name: str) -> str:
        scheme = "https" if self.secure else "http"
        return f"{scheme}://{self.endpoint}/{bucket}/{quote(object_name, safe='/')}"

    def upload_bytes(
        self,
        *,
        bucket: str,
        object_name: str,
        data: bytes,
        content_type: str,
    ) -> StoredObject:
        self.ensure_bucket(bucket)
        self.client.put_object(
            bucket,
            object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return StoredObject(
            bucket=bucket,
            object_name=object_name,
            url=self.build_public_url(bucket, object_name),
        )


@lru_cache
def get_media_storage_instance() -> MinioMediaStorage:
    return MinioMediaStorage()


def get_media_storage() -> MediaStorage:
    return get_media_storage_instance()


def reset_media_storage_state() -> None:
    get_media_storage_instance.cache_clear()


def read_and_validate_image(file: UploadFile, *, max_bytes: int) -> tuple[bytes, str]:
    content_type = file.content_type or ""
    if content_type not in ALLOWED_IMAGE_CONTENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="unsupported media type",
        )

    content = file.file.read(max_bytes + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="empty file")

    if len(content) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="file too large",
        )

    return content, content_type


def build_object_name(scope: str, content_type: str) -> str:
    extension = ALLOWED_IMAGE_CONTENT_TYPES[content_type]
    date_path = datetime.now(UTC).strftime("%Y/%m/%d")
    return f"{scope}/{date_path}/{uuid4().hex}{extension}"

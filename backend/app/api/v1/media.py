from fastapi import APIRouter, Depends, File, Request, UploadFile, status

from backend.app.api.v1.users import get_current_user
from backend.app.core.responses import build_response
from backend.app.models.user import User
from backend.app.services.media import (
    MAX_REVIEW_MEDIA_BYTES,
    REVIEW_MEDIA_BUCKET,
    MediaStorage,
    build_object_name,
    get_media_storage,
    read_and_validate_image,
)


router = APIRouter(prefix="/media", tags=["media"])


@router.post("/reviews")
def upload_review_media(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    media_storage: MediaStorage = Depends(get_media_storage),
):
    content, content_type = read_and_validate_image(file, max_bytes=MAX_REVIEW_MEDIA_BYTES)
    stored_object = media_storage.upload_bytes(
        bucket=REVIEW_MEDIA_BUCKET,
        object_name=build_object_name(f"reviews/user-{current_user.id}", content_type),
        data=content,
        content_type=content_type,
    )

    return build_response(
        request=request,
        code=0,
        message="upload successful",
        data={
            "file": {
                "bucket": stored_object.bucket,
                "object_name": stored_object.object_name,
                "url": stored_object.url,
                "content_type": content_type,
                "size": len(content),
            }
        },
        status_code=status.HTTP_201_CREATED,
    )

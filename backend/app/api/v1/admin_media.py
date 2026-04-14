from fastapi import APIRouter, Depends, File, Request, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.api.v1.admin_auth import create_operation_log, get_current_admin
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.admin import AdminUser
from backend.app.services.media import (
    MAX_PRODUCT_MEDIA_BYTES,
    PRODUCT_MEDIA_BUCKET,
    MediaStorage,
    build_object_name,
    get_media_storage,
    read_and_validate_image,
)


router = APIRouter(prefix="/admin/media", tags=["admin-media"])


@router.post("/products")
def upload_product_media(
    request: Request,
    file: UploadFile = File(...),
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
    media_storage: MediaStorage = Depends(get_media_storage),
):
    content, content_type = read_and_validate_image(file, max_bytes=MAX_PRODUCT_MEDIA_BYTES)
    stored_object = media_storage.upload_bytes(
        bucket=PRODUCT_MEDIA_BUCKET,
        object_name=build_object_name("products", content_type),
        data=content,
        content_type=content_type,
    )
    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_product_media_upload",
        target_type="product_media",
        detail_json={
            "bucket": stored_object.bucket,
            "object_name": stored_object.object_name,
            "content_type": content_type,
            "size": len(content),
        },
    )
    db.commit()

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

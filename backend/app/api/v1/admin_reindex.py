from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.v1.admin_auth import create_operation_log, get_current_admin
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.admin import AdminUser
from backend.app.schemas.admin import AdminReindexRequest
from backend.app.tasks.embedding_tasks import (
    rebuild_all_product_embeddings,
    reindex_changed_product_embeddings,
)

router = APIRouter(prefix="/admin/reindex", tags=["admin-reindex"])


@router.post("/products")
def reindex_products(
    payload: AdminReindexRequest,
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.force:
        result = rebuild_all_product_embeddings(db)
    else:
        result = reindex_changed_product_embeddings(db, product_ids=payload.product_ids)

    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_reindex_products",
        target_type="product_embedding",
        detail_json={
            "force": payload.force,
            "product_ids": payload.product_ids,
            "indexed": result["indexed"],
            "skipped": result["skipped"],
        },
    )
    db.commit()

    return build_response(
        request=request,
        code=0,
        message="reindex completed",
        data={"result": result},
        status_code=200,
    )

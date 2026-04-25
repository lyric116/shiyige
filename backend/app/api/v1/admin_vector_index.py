from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.api.v1.admin_auth import create_operation_log, get_current_admin
from backend.app.core.database import get_db
from backend.app.core.responses import build_response
from backend.app.models.admin import AdminUser
from backend.app.schemas.admin import AdminVectorIndexRequest
from backend.app.tasks.qdrant_index_tasks import (
    delete_product_points,
    get_product_index_status,
    retry_failed_product_indexing,
    sync_products_to_qdrant,
)

router = APIRouter(prefix="/admin/vector-index", tags=["admin-vector-index"])


@router.get("/status")
@router.get("/products/status")
def get_vector_index_status(
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    status_payload = get_product_index_status(db)
    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_vector_index_status",
        target_type="product_embedding",
        detail_json={"collection_name": status_payload["collection_name"]},
    )
    db.commit()
    return build_response(
        request=request,
        code=0,
        message="ok",
        data={"status": status_payload},
        status_code=200,
    )


@router.post("/rebuild")
def rebuild_vector_index(
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    result = sync_products_to_qdrant(
        db,
        mode="full",
        product_ids=None,
    )

    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_vector_index_rebuild",
        target_type="product_embedding",
        detail_json={
            "mode": "full",
            "result": result,
        },
    )
    db.commit()
    return build_response(
        request=request,
        code=0,
        message="vector index rebuild completed",
        data={"result": result},
        status_code=200,
    )


@router.post("/products/sync")
def sync_vector_index(
    payload: AdminVectorIndexRequest,
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.mode == "retry_failed":
        result = retry_failed_product_indexing(db)
    elif payload.mode == "delete":
        result = delete_product_points(db, product_ids=payload.product_ids or [])
    else:
        result = sync_products_to_qdrant(
            db,
            mode=payload.mode,
            product_ids=payload.product_ids,
        )

    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_vector_index_sync",
        target_type="product_embedding",
        detail_json={
            "mode": payload.mode,
            "product_ids": payload.product_ids,
            "result": result,
        },
    )
    db.commit()
    return build_response(
        request=request,
        code=0,
        message="vector index sync completed",
        data={"result": result},
        status_code=200,
    )


@router.post("/products/{product_id}/reindex")
def reindex_single_product(
    product_id: int,
    request: Request,
    current_admin: AdminUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    result = sync_products_to_qdrant(
        db,
        mode="incremental",
        product_ids=[product_id],
    )

    create_operation_log(
        db,
        admin_user=current_admin,
        request=request,
        action="admin_vector_index_reindex_product",
        target_type="product_embedding",
        target_id=product_id,
        detail_json={
            "mode": "incremental",
            "product_ids": [product_id],
            "result": result,
        },
    )
    db.commit()
    return build_response(
        request=request,
        code=0,
        message="product reindex completed",
        data={"result": result},
        status_code=200,
    )

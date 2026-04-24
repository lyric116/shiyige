from fastapi import APIRouter, Request

from backend.app.core.responses import success_response
from backend.app.services.vector_store import describe_vector_store_runtime

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request):
    return success_response(
        request=request,
        data={
            "status": "ok",
            "vector_store": describe_vector_store_runtime(),
        },
    )

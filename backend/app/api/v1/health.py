from fastapi import APIRouter, Request

from backend.app.core.responses import success_response

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check(request: Request):
    return success_response(request=request, data={"status": "ok"})

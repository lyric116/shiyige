from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError

from backend.app.core.error_codes import HTTP_ERROR, INTERNAL_ERROR, VALIDATION_ERROR
from backend.app.core.logger import get_logger
from backend.app.core.responses import build_response

logger = get_logger("backend.api")


def ensure_request_id(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    if request_id is None:
        request_id = uuid4().hex
        request.state.request_id = request_id
    return request_id


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        ensure_request_id(request)
        return build_response(
            request=request,
            code=VALIDATION_ERROR,
            message="validation error",
            data={"errors": exc.errors()},
            status_code=422,
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        ensure_request_id(request)
        return build_response(
            request=request,
            code=HTTP_ERROR,
            message=str(exc.detail),
            data=None,
            status_code=exc.status_code,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        request_id = ensure_request_id(request)
        logger.exception("Unhandled exception raised. request_id=%s", request_id, exc_info=exc)
        return build_response(
            request=request,
            code=INTERNAL_ERROR,
            message="internal server error",
            data=None,
            status_code=500,
        )

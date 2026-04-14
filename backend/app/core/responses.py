from typing import Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def build_response(
    *,
    request: Request,
    code: int,
    message: str,
    data: Any,
    status_code: int = 200,
) -> JSONResponse:
    request_id = get_request_id(request)
    response = JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "code": code,
                "message": message,
                "data": data,
                "request_id": request_id,
            }
        ),
    )
    if request_id is not None:
        response.headers["X-Request-ID"] = request_id
    return response


def success_response(request: Request, data: Any = None, message: str = "ok") -> JSONResponse:
    return build_response(request=request, code=0, message=message, data=data, status_code=200)

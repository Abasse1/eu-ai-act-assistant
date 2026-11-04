from collections.abc import Mapping
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from opentelemetry import trace
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


def _get_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()

    if not span_context.is_valid:
        return None

    return format(span_context.trace_id, "032x")


def _problem_response(
    request: Request,
    status: int,
    title: str,
    details: str,
    errors: list[dict[str, object]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:

    content: dict[str, object] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": details,
        "instance": request.url.path,
    }

    trace_id = _get_trace_id()
    if trace_id:
        content["traceId"] = trace_id

    if errors:
        content["errors"] = errors

    return JSONResponse(
        status_code=status, content=content, headers=headers, media_type="application/problem+json"
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):
        raise TypeError("Unexpected exception type.")
    title = {
        400: "Bad Request",
        401: "Unauthorized",
        403: "Forbidden",
        404: "Not Found",
        405: "Method Not Allowed",
        409: "Conflict",
        422: "Unprocessable Entity",
        429: "Too Many Requests",
    }

    return _problem_response(
        request=request,
        status=exc.status_code,
        title=title.get(exc.status_code, "HTTP Error"),
        details=exc.detail,
        headers=exc.headers,
    )


async def validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:

    if not isinstance(exc, RequestValidationError):
        raise TypeError("Unexpected exception type.")

    errors: list[dict[str, object]] = [
        {
            "location": list(error["loc"]),
            "message": error["msg"],
            "code": error["type"],
        }
        for error in exc.errors()
    ]

    return _problem_response(
        request=request,
        status=422,
        title="Validation error",
        details="The request contains invalid data.",
        errors=errors,
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:

    logger.exception(
        "Unhandled exception occurred while processing request",
        extra={"request_path": request.url.path, "exception": exc},
    )

    return _problem_response(
        request=request,
        status=500,
        title="Internal Server Error",
        details="An unexpected error occurred.",
    )


def configure_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)

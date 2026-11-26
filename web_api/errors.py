"""Canonical error response va exception mapping."""

from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


def error_response(
    request_id: str,
    status_code: int,
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    """Tao canonical error response khong lo internal detail."""
    return JSONResponse(
        status_code=status_code,
        content={"error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id,
        }},
    )


async def validation_error_handler(
    request: Request, error: RequestValidationError
) -> JSONResponse:
    """Chuyen loi validation sang schema cong khai."""
    malformed = any(item.get("type") == "json_invalid" for item in error.errors())
    details = []
    for item in error.errors():
        location = [str(part) for part in item.get("loc", ()) if part != "body"]
        details.append({
            "field": ".".join(location) or "body",
            "reason": item.get("msg", "invalid value"),
        })
    return error_response(
        request.state.request_id,
        400 if malformed else 422,
        "MALFORMED_JSON" if malformed else "VALIDATION_ERROR",
        "Malformed JSON" if malformed else "Request validation failed",
        details,
    )


async def internal_error_handler(request: Request, error: Exception) -> JSONResponse:
    """An exception detail va tra loi noi bo canonical."""
    return error_response(
        request.state.request_id,
        500,
        "INTERNAL_ERROR",
        "Internal server error",
    )

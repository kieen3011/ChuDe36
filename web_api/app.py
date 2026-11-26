"""FastAPI application factory va middleware bao mat."""

import re
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import HTMLResponse

from web_api.config import MAX_REQUEST_BODY_BYTES, cors_origins, docs_enabled
from web_api.errors import (
    error_response,
    internal_error_handler,
    validation_error_handler,
)
from web_api.routers.health import router as health_router
from web_api.routers.simulations import router as simulation_router


class RequestGuardMiddleware(BaseHTTPMiddleware):
    """Gan request ID va gioi han HTTP body truoc route."""

    @staticmethod
    def _add_response_headers(request: Request, response):
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path == "/api/simulations/run":
            response.headers["Cache-Control"] = "no-store"
        return response

    async def dispatch(self, request: Request, call_next):
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request.state.request_id = supplied_request_id if re.fullmatch(
            r"[A-Za-z0-9._:-]{1,128}", supplied_request_id
        ) else str(uuid4())
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > MAX_REQUEST_BODY_BYTES:
                    response = error_response(
                        request.state.request_id,
                        413,
                        "PAYLOAD_TOO_LARGE",
                        "Request body exceeds 64 KiB",
                    )
                    return self._add_response_headers(request, response)
            except ValueError:
                response = error_response(
                    request.state.request_id,
                    400,
                    "MALFORMED_REQUEST",
                    "Invalid Content-Length",
                )
                return self._add_response_headers(request, response)
        chunks = []
        body_size = 0
        async for chunk in request.stream():
            body_size += len(chunk)
            if body_size > MAX_REQUEST_BODY_BYTES:
                response = error_response(
                    request.state.request_id,
                    413,
                    "PAYLOAD_TOO_LARGE",
                    "Request body exceeds 64 KiB",
                )
                return self._add_response_headers(request, response)
            chunks.append(chunk)
        request._body = b"".join(chunks)
        response = await call_next(request)
        return self._add_response_headers(request, response)


def create_app() -> FastAPI:
    """Tao app moi de test va deployment khong chia se mutable state."""
    enabled = docs_enabled()
    app = FastAPI(
        title="CHUDE36 IoT Warehouse API",
        version="1",
        docs_url="/docs" if enabled else None,
        redoc_url="/redoc" if enabled else None,
        openapi_url="/openapi.json" if enabled else None,
    )
    app.add_middleware(RequestGuardMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=False,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Accept", "Content-Type", "X-Request-ID"],
    )
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(Exception, internal_error_handler)
    app.include_router(health_router)
    app.include_router(simulation_router)

    @app.get("/", include_in_schema=False, response_class=HTMLResponse)
    def frontend_index() -> HTMLResponse:
        """Tra trang frontend hien co ma khong them vao OpenAPI."""
        frontend_path = Path(__file__).resolve().parents[1] / "frontend" / "index.html"
        return HTMLResponse(frontend_path.read_text(encoding="utf-8"))

    return app


app = create_app()

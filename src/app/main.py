"""FastAPI factory for the owner surface and separately authenticated agent API."""

import os
import sqlite3
from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response

from app.routes import router
from services.authorization import Denied, Runtime


def create_app(data_dir: Path | None = None, testing: bool = False) -> FastAPI:
    """Create an isolated runtime; test-only faults are never exposed as HTTP controls."""
    runtime = Runtime(data_dir or Path(os.environ.get("LEDGER_DATA", "/data")), testing)
    app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
    app.state.runtime = runtime
    app.state.origin = os.environ.get("LEDGER_ORIGIN", "")
    app.mount("/static", StaticFiles(directory=Path(__file__).parent / "static"), name="static")
    app.include_router(router)

    @app.exception_handler(Denied)
    async def denied(request: Request, error: Denied) -> JSONResponse:
        return JSONResponse({"reason": error.reason}, status_code=error.status)

    @app.exception_handler(sqlite3.Error)
    async def unavailable(request: Request, error: sqlite3.Error) -> JSONResponse:
        return JSONResponse({"reason": "STORAGE_UNAVAILABLE"}, status_code=503)

    @app.middleware("http")
    async def security(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        )
        return response

    return app

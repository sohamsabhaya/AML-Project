"""Shared exceptions and the JSON error format ``{"detail": "..."}``."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ModelUnavailableError(Exception):
    """Raised when TensorFlow or a model file is missing / cannot be loaded (HTTP 503)."""


def _json(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": message})


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ModelUnavailableError)
    async def _model_unavailable(_: Request, exc: ModelUnavailableError) -> JSONResponse:
        return _json(503, str(exc))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Turn FastAPI's list-style 422 into the contract's single-string 400.
        parts = []
        for err in exc.errors():
            where = ".".join(str(p) for p in err.get("loc", ()) if p not in ("query", "body"))
            msg = str(err.get("msg", "invalid value"))
            parts.append(f"{where}: {msg}" if where else msg)
        return _json(400, "Invalid request: " + "; ".join(parts))

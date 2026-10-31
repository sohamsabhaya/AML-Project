"""App factory. Run with ``uvicorn app.main:app`` from the backend folder.

Run a single worker process: the rate limiter and the model cache are in memory.
"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import config
from .errors import register_error_handlers
from .model_service import ModelService, ModelServiceProtocol
from .observability import RequestIdMiddleware, setup_logging
from .routers import analyses, health, stats
from .security import AnalyzeGuardMiddleware
from .storage import Storage

log = logging.getLogger("brainscan.app")


def run_startup_tasks(storage: Storage) -> None:
    """Retention purge and orphan clean-up (runs before requests are served)."""
    purged = storage.purge_older_than(config.RETENTION_DAYS)
    if purged:
        log.info("retention: removed %d analyses older than %d days", purged, config.RETENTION_DAYS)
    orphans = storage.cleanup_orphans()
    if orphans:
        log.info("clean-up: removed %d orphaned files/rows", orphans)


def create_app(
    storage: Storage | None = None, model_service: ModelServiceProtocol | None = None
) -> FastAPI:
    """Build the app. Tests pass a temp-dir ``Storage`` and a fake model service."""
    setup_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        await asyncio.to_thread(run_startup_tasks, app.state.storage)
        warmup = getattr(app.state.model_service, "warmup", None)
        task = None
        if config.WARMUP and callable(warmup):
            # In the background: the API answers immediately while the models load.
            task = asyncio.create_task(asyncio.to_thread(warmup))
        yield
        if task is not None and not task.done():
            task.cancel()

    app = FastAPI(title="BrainScan AI API", version="1.1.0", lifespan=lifespan)
    # Added innermost-first: the request-id middleware is outermost, so even the
    # guard's 401/413/429 answers carry CORS headers and an X-Request-ID.
    app.add_middleware(AnalyzeGuardMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "X-API-Key", "X-Request-ID"],
        expose_headers=["X-Request-ID", "Retry-After"],
    )
    app.add_middleware(RequestIdMiddleware)
    app.state.storage = storage or Storage()  # creates folders + tables
    app.state.model_service = model_service or ModelService()  # models load lazily
    register_error_handlers(app)
    for module in (health, analyses, stats):
        for name in ("public_router", "router"):
            router = getattr(module, name, None)
            if router is not None:
                app.include_router(router)
    return app


app = create_app()

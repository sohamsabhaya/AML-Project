"""FastAPI dependencies: the storage and model service live on ``app.state``."""
from __future__ import annotations

from fastapi import Request

from .model_service import ModelServiceProtocol
from .storage import Storage


def get_storage(request: Request) -> Storage:
    return request.app.state.storage


def get_model_service(request: Request) -> ModelServiceProtocol:
    return request.app.state.model_service

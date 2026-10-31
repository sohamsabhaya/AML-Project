"""GET /api/stats."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from ..deps import get_storage
from ..security import require_api_key
from ..storage import Storage

router = APIRouter(prefix="/api", tags=["stats"], dependencies=[Depends(require_api_key)])


@router.get("/stats")
def stats(storage: Storage = Depends(get_storage)) -> dict[str, Any]:
    return storage.stats()

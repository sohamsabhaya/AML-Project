"""GET /api/health, GET /api/models and GET /api/models/insights."""
from __future__ import annotations

import csv
import json
import logging
import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException

from .. import config
from ..deps import get_model_service
from ..model_service import ModelServiceProtocol
from ..security import require_api_key

log = logging.getLogger("brainscan.api")

# /api/health is public (used by container health checks); the rest needs the API key when set.
public_router = APIRouter(prefix="/api", tags=["health"])
router = APIRouter(prefix="/api", tags=["models"], dependencies=[Depends(require_api_key)])

# CSV column header keyword -> model id / display name
_MODEL_COLUMNS = {"custom": "custom_cnn", "resnet": "resnet50"}
# CSV row label (lower case) -> (field name, is_percentage)
_METRIC_ROWS = {
    "test accuracy": ("accuracy", True),
    "macro precision": ("precision", True),
    "macro recall": ("recall", True),
    "macro f1-score": ("f1", True),
    "total parameters": ("parameters", False),
    "trainable parameters": ("trainable_parameters", False),
}


@public_router.get("/health")
def health(service: ModelServiceProtocol = Depends(get_model_service)) -> dict[str, Any]:
    """Cheap: no model is loaded and TensorFlow is not imported to answer this."""
    return {
        "status": "ok",
        "model_loaded": service.is_loaded(),
        "model_version": config.MODEL_VERSIONS[config.DEFAULT_MODEL],
        "classes": config.CLASSES,
        "models": service.status(),
        "tensorflow_available": service.tensorflow_available(),
        "demo": False,
    }


def _number(text: str, percentage: bool) -> float | int:
    cleaned = re.sub(r"[,%\s]", "", text)
    value = float(cleaned)
    return round(value / 100, 6) if percentage else int(value)


def read_model_metrics(csv_path: Path) -> list[dict[str, Any]]:
    """Parse model_comparison_results.csv (metrics as rows, one column per model).

    Percentages become fractions (74.31% -> 0.7431).
    """
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        return []
    header = rows[0]
    models: list[dict[str, Any]] = []
    for col, title in enumerate(header[1:], start=1):
        key = next((mid for word, mid in _MODEL_COLUMNS.items() if word in title.lower()), None)
        if key is None:
            continue
        entry: dict[str, Any] = {"id": key, "name": title.strip()}
        for row in rows[1:]:
            if len(row) <= col:
                continue
            spec = _METRIC_ROWS.get(row[0].strip().lower())
            if spec:
                entry[spec[0]] = _number(row[col], spec[1])
        models.append(entry)
    return models


@router.get("/models")
def models() -> dict[str, Any]:
    if not config.METRICS_CSV.is_file():
        raise HTTPException(404, "Model comparison results file was not found.")
    try:
        return {"models": read_model_metrics(config.METRICS_CSV)}
    except (ValueError, csv.Error):
        raise HTTPException(500, "Model comparison results file could not be read.") from None


@router.get("/models/insights")
def model_insights() -> dict[str, Any]:
    """Verified evaluation numbers from ml/results/model_insights.json, else 'unavailable' (HTTP 200)."""
    path = config.INSIGHTS_JSON
    if path.is_file():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("models"), list):
                return data
            log.warning("Insights file has an unexpected shape")
        except (OSError, ValueError):
            log.warning("Insights file could not be read")
    return {"status": "unavailable", "models": []}

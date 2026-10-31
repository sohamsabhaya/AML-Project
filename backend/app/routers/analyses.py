"""Analyze + analyses CRUD endpoints (see docs/API_CONTRACT.md, v1.1)."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from .. import config
from ..deps import get_model_service, get_storage
from ..errors import ModelUnavailableError
from ..model_service import ModelServiceProtocol
from ..preprocess import (
    preprocess_for_model,
    sanitize_filename,
    to_model_array,
    validate_upload,
)
from ..report import build_report_pdf
from ..security import require_api_key
from ..storage import Storage

log = logging.getLogger("brainscan.api")
router = APIRouter(prefix="/api", tags=["analyses"], dependencies=[Depends(require_api_key)])

# Uploaded medical images must not be cached by browsers/proxies.
_NO_STORE = {"Cache-Control": "private, no-store"}
_MEDIA_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
_ALLOWED_MODELS = (*config.MODEL_IDS, "both")


# -- serialisation ---------------------------------------------------------
def _summary(rec: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": rec["id"],
        "created_at": rec["created_at"],
        "filename": rec["filename"],
        "predicted_class": rec["predicted_class"],
        "predicted_label": config.CLASS_LABELS.get(rec["predicted_class"], rec["predicted_class"]),
        "confidence": rec["confidence"],
        "low_confidence": rec["low_confidence"],
        "confidence_threshold": rec["confidence_threshold"],
        "top2": rec["top2"],
        "entropy": rec["entropy"],
        "model_id": rec["model_id"],
    }


def _full(rec: dict[str, Any], storage: Storage, warning: str | None = None) -> dict[str, Any]:
    base = f"/api/analyses/{rec['id']}"
    data = _summary(rec)
    data.update(
        probabilities=rec["probabilities"],
        model_version=rec["model_version"],
        image_url=f"{base}/image",
        heatmap_url=f"{base}/heatmap" if storage.heatmap_path(rec) else None,
        comparison=rec["comparison"],
        warning=warning,
        disclaimer=config.DISCLAIMER,
    )
    return data


def _require(storage: Storage, analysis_id: str) -> dict[str, Any]:
    rec = storage.get(analysis_id)
    if rec is None:
        raise HTTPException(404, "Analysis not found.")
    return rec


def _compare_entry(probabilities: dict[str, float]) -> dict[str, Any]:
    best = max(probabilities, key=lambda c: probabilities[c])
    return {"predicted_class": best, "confidence": probabilities[best], "probabilities": probabilities}


# -- analyze ---------------------------------------------------------------
@router.post("/analyze")
def analyze(
    file: UploadFile = File(...),
    model: str = Query(config.DEFAULT_MODEL),
    heatmap: bool = Query(True),
    storage: Storage = Depends(get_storage),
    service: ModelServiceProtocol = Depends(get_model_service),
) -> dict[str, Any]:
    if model not in _ALLOWED_MODELS:
        raise HTTPException(400, f"Unknown model '{model}'. Use one of: {', '.join(_ALLOWED_MODELS)}.")

    # Read at most limit+1 bytes so a huge upload cannot exhaust memory.
    data = file.file.read(config.MAX_UPLOAD_BYTES + 1)
    validated = validate_upload(file.filename, data)
    # Base array for general compatibility and fallback
    array = to_model_array(validated.image)

    wanted = list(config.MODEL_IDS) if model == "both" else [model]
    results: dict[str, dict[str, float]] = {}
    failures: dict[str, str] = {}
    model_arrays: dict[str, np.ndarray] = {}
    for name in wanted:  # one failing model must not take the other down
        try:
            arr = preprocess_for_model(validated.image, name)
            model_arrays[name] = arr
            probs = service.predict(arr, name)
            results[name] = {cls: round(float(p), 6) for cls, p in zip(config.CLASSES, probs)}
        except ModelUnavailableError as exc:
            failures[name] = str(exc)
        except Exception:  # noqa: BLE001
            log.exception("Prediction failed for model %s", name)
            failures[name] = "Prediction failed."
    if not results:
        raise ModelUnavailableError(next(iter(failures.values())))

    primary = next(name for name in wanted if name in results)  # resnet50 first
    probabilities = results[primary]
    predicted = max(probabilities, key=lambda c: probabilities[c])
    primary_array = model_arrays.get(primary, array)

    warnings: list[str] = [f"Model '{n}' was not used: {msg}" for n, msg in failures.items()]
    comparison: dict[str, Any] | None = None
    if model == "both":
        comparison = {
            name: _compare_entry(results[name]) if name in results else None
            for name in config.MODEL_IDS
        }
        comparison["agree"] = (
            comparison["resnet50"]["predicted_class"] == comparison["custom_cnn"]["predicted_class"]
            if len(results) == 2 else None
        )

    heatmap_png: bytes | None = None
    if heatmap:
        try:
            heatmap_png = service.heatmap(primary_array, primary, config.CLASSES.index(predicted))
        except Exception:  # noqa: BLE001 - heatmap is optional; the prediction still stands
            log.exception("Grad-CAM failed for model %s", primary)
            warnings.append("The Grad-CAM heatmap could not be generated.")

    rec = storage.create(
        filename=sanitize_filename(file.filename),
        predicted_class=predicted,
        confidence=probabilities[predicted],
        probabilities=probabilities,
        model_version=config.MODEL_VERSIONS[primary],
        model_id=primary,
        image_bytes=data,
        image_ext=validated.extension,
        heatmap_png=heatmap_png,
        comparison=comparison,
    )
    log.info(
        "analysis stored: class=%s confidence=%.3f model=%s%s", predicted, rec["confidence"],
        primary, " (low confidence)" if rec["low_confidence"] else "",
    )
    return _full(rec, storage, warning=" ".join(warnings) or None)


# -- list / get / delete ---------------------------------------------------
@router.get("/analyses")
def list_analyses(
    search: str | None = Query(None, max_length=100),
    label: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    storage: Storage = Depends(get_storage),
) -> dict[str, Any]:
    if label and label not in config.CLASSES:
        raise HTTPException(400, f"Unknown label '{label}'. Use one of: {', '.join(config.CLASSES)}.")
    items, total = storage.list_analyses(search=search, label=label, page=page, page_size=page_size)
    return {"items": [_summary(r) for r in items], "total": total, "page": page, "page_size": page_size}


@router.delete("/analyses")
def purge_analyses(
    confirm: bool = Query(False), storage: Storage = Depends(get_storage)
) -> dict[str, Any]:
    """Delete every analysis and file. Requires ``confirm=true``."""
    if not confirm:
        raise HTTPException(400, "This deletes ALL analyses. Repeat the request with confirm=true.")
    deleted = storage.purge_all()
    log.info("purged all analyses: %d removed", deleted)
    return {"deleted": deleted}


@router.get("/analyses/{analysis_id}")
def get_analysis(analysis_id: str, storage: Storage = Depends(get_storage)) -> dict[str, Any]:
    return _full(_require(storage, analysis_id), storage)


@router.delete("/analyses/{analysis_id}")
def delete_analysis(analysis_id: str, storage: Storage = Depends(get_storage)) -> dict[str, Any]:
    if not storage.delete(analysis_id):
        raise HTTPException(404, "Analysis not found.")
    return {"deleted": True, "id": analysis_id}


# -- files -----------------------------------------------------------------
@router.get("/analyses/{analysis_id}/image")
def get_image(analysis_id: str, storage: Storage = Depends(get_storage)) -> FileResponse:
    path = storage.image_path(_require(storage, analysis_id))
    if not path.is_file():
        raise HTTPException(404, "Image file not found.")
    return FileResponse(path, media_type=_MEDIA_TYPES.get(Path(path).suffix.lower(), "image/png"),
                        headers=_NO_STORE)


@router.get("/analyses/{analysis_id}/heatmap")
def get_heatmap(analysis_id: str, storage: Storage = Depends(get_storage)) -> FileResponse:
    path = storage.heatmap_path(_require(storage, analysis_id))
    if path is None:
        raise HTTPException(404, "No heatmap available for this analysis.")
    return FileResponse(path, media_type="image/png", headers=_NO_STORE)


@router.get("/analyses/{analysis_id}/report")
def get_report(analysis_id: str, storage: Storage = Depends(get_storage)) -> Response:
    rec = _require(storage, analysis_id)
    image_path = storage.image_path(rec)
    if not image_path.is_file():
        raise HTTPException(404, "Image file not found.")
    pdf = build_report_pdf(rec, image_path, storage.heatmap_path(rec))
    headers = {**_NO_STORE, "Content-Disposition": f'inline; filename="brainscan-report-{rec["id"]}.pdf"'}
    return Response(content=pdf, media_type="application/pdf", headers=headers)

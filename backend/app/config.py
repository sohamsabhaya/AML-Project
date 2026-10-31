"""Central configuration. Every setting can be overridden by an environment variable.

Values are read once at import time. Code reads them as ``config.NAME`` at call
time, so tests can monkeypatch individual attributes. Invalid values fall back
to the default instead of crashing the server. See ``backend/.env.example`` for
the full list (the app itself does not load ``.env`` files; export the variables
or pass them to Docker with ``--env-file``).
"""
from __future__ import annotations

import os
from pathlib import Path

BACKEND_DIR: Path = Path(__file__).resolve().parent.parent
REPO_ROOT: Path = BACKEND_DIR.parent


def _str(name: str, default: str) -> str:
    value = os.environ.get(name)
    return value.strip() if value and value.strip() else default


def _int(name: str, default: int, minimum: int = 0) -> int:
    try:
        return max(minimum, int(os.environ[name]))
    except (KeyError, ValueError):
        return default


def _float(name: str, default: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    try:
        return min(maximum, max(minimum, float(os.environ[name])))
    except (KeyError, ValueError):
        return default


def _bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path(name: str, default: Path) -> Path:
    value = os.environ.get(name)
    return Path(value).expanduser() if value and value.strip() else default


def _list(name: str, default: list[str]) -> list[str]:
    value = os.environ.get(name)
    if value is None or not value.strip():
        return default
    return [part.strip() for part in value.split(",") if part.strip()]


# --- Storage -----------------------------------------------------------
DATA_DIR: Path = _path("DATA_DIR", BACKEND_DIR / "data")
RETENTION_DAYS: int = _int("RETENTION_DAYS", 0)  # 0 = keep forever

# --- Models ------------------------------------------------------------
DEFAULT_MODEL = "resnet50"
MODEL_IDS: tuple[str, ...] = ("resnet50", "custom_cnn")
MODEL_DIR: Path = _path("MODEL_DIR", REPO_ROOT)
MODEL_PATHS: dict[str, Path] = {
    "resnet50": MODEL_DIR / _str("RESNET50_MODEL_FILE", "resnet50_model.keras"),
    "custom_cnn": MODEL_DIR / _str("CUSTOM_CNN_MODEL_FILE", "custom_cnn_model.keras"),
}
MODEL_VERSIONS: dict[str, str] = {
    "resnet50": "resnet50-v1",
    "custom_cnn": "custom_cnn-v1",
}
# Last convolutional layer used for Grad-CAM (read from config.json of each
# .keras file). Grad-CAM falls back to "the last layer with a 4-D output".
GRADCAM_LAYERS: dict[str, str] = {
    "resnet50": "conv5_block3_out",
    "custom_cnn": "conv2d_2",
}
METRICS_CSV: Path = _path("METRICS_CSV", REPO_ROOT / "model_comparison_results.csv")
INSIGHTS_JSON: Path = _path("INSIGHTS_JSON", REPO_ROOT / "ml" / "results" / "model_insights.json")

# Executing a Lambda layer (ResNet50 preprocess_input) needs safe_mode=False,
# which runs code stored in the model file. Only ever use trusted model files.
ALLOW_UNSAFE_LAMBDA_LOAD: bool = _bool("ALLOW_UNSAFE_LAMBDA_LOAD", True)
WARMUP: bool = _bool("WARMUP", False)
MAX_CONCURRENT_INFERENCES: int = _int("MAX_CONCURRENT_INFERENCES", 1, minimum=1)
INFERENCE_WAIT_SECONDS: int = _int("INFERENCE_WAIT_SECONDS", 60, minimum=1)

# --- Safety ------------------------------------------------------------
CONFIDENCE_THRESHOLD: float = _float("CONFIDENCE_THRESHOLD", 0.6)

# --- Classes (alphabetical, as produced by image_dataset_from_directory) --
CLASSES: list[str] = ["glioma", "meningioma", "notumor", "pituitary"]
CLASS_LABELS: dict[str, str] = {
    "glioma": "Glioma",
    "meningioma": "Meningioma",
    "notumor": "No Tumor",
    "pituitary": "Pituitary Tumor",
}
IMG_SIZE: tuple[int, int] = (224, 224)

# --- Upload limits / abuse protection ----------------------------------
MAX_UPLOAD_MB: int = _int("MAX_UPLOAD_MB", 10, minimum=1)
MAX_UPLOAD_BYTES: int = MAX_UPLOAD_MB * 1024 * 1024
MULTIPART_OVERHEAD_BYTES = 64 * 1024  # allowance for multipart boundaries/headers
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({".png", ".jpg", ".jpeg"})
# Pillow format name -> (stored extension, media type)
ALLOWED_FORMATS: dict[str, tuple[str, str]] = {
    "PNG": (".png", "image/png"),
    "JPEG": (".jpg", "image/jpeg"),
}
MAX_IMAGE_PIXELS: int = _int("MAX_IMAGE_PIXELS", 25_000_000, minimum=1)  # decompression bombs
RATE_LIMIT_PER_MIN: int = _int("RATE_LIMIT_PER_MIN", 30)  # per client IP, /api/analyze; 0 = off

# --- Access control ----------------------------------------------------
# Empty = open (local demo). When set, every /api route except /api/health
# requires the header X-API-Key with this value.
API_KEY: str = os.environ.get("API_KEY", "").strip()

# --- HTTP / logging ----------------------------------------------------
CORS_ORIGINS: list[str] = _list("CORS_ORIGINS", ["http://localhost:5173", "http://127.0.0.1:5173"])
LOG_LEVEL: str = _str("LOG_LEVEL", "INFO").upper()
LOG_FORMAT: str = _str("LOG_FORMAT", "json").lower()  # json | text

DISCLAIMER = (
    "AI-generated prediction for educational and research use only. It is not a "
    "medical diagnosis and must not replace review by a qualified clinician."
)

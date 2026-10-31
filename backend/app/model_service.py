"""Lazy-loading, caching, concurrency-limited model service.

Models are loaded on first use (or by the optional warm-up) so the API starts
fast and /api/health works even without TensorFlow. Missing TensorFlow or
model files raise ``ModelUnavailableError`` -> HTTP 503.

Concurrency: loading happens under a lock (a model is loaded once even if
several requests arrive together) and prediction / Grad-CAM run inside a global
semaphore (``MAX_CONCURRENT_INFERENCES``, default 1) so parallel requests
cannot exhaust memory or CPU.
"""
from __future__ import annotations

import importlib.util
import logging
import threading
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from . import config
from .errors import ModelUnavailableError
from .gradcam import GradCam, overlay_heatmap

log = logging.getLogger("brainscan.models")


class ModelServiceProtocol(Protocol):
    """Interface used by the routers (tests provide a fake implementation)."""

    def predict(self, array: np.ndarray, model_name: str) -> list[float]: ...

    def heatmap(self, array: np.ndarray, model_name: str, class_index: int) -> bytes: ...

    def is_loaded(self) -> bool: ...

    def status(self) -> dict[str, dict[str, bool]]: ...

    def tensorflow_available(self) -> bool: ...


def _is_lambda_deserialization_error(exc: BaseException) -> bool:
    """True for Keras' refusal to deserialize a Lambda layer or custom code in safe mode."""
    text = str(exc).lower()
    return any(k in text for k in ("lambda", "safe_mode", "deserializ", "custom_objects", "opcode"))


class ModelService:
    def __init__(self, model_paths: dict[str, Path] | None = None) -> None:
        self._paths = model_paths or config.MODEL_PATHS
        self._models: dict[str, Any] = {}
        self._cams: dict[str, GradCam] = {}
        self._load_lock = threading.RLock()
        self._inference = threading.BoundedSemaphore(config.MAX_CONCURRENT_INFERENCES)

    # -- introspection (cheap, never imports TensorFlow) -------------------
    def tensorflow_available(self) -> bool:
        try:
            return importlib.util.find_spec("tensorflow") is not None
        except (ImportError, ValueError):
            return False

    def is_loaded(self) -> bool:
        return bool(self._models)

    def status(self) -> dict[str, dict[str, bool]]:
        tf_ok = self.tensorflow_available()
        return {
            name: {
                "available": tf_ok and path.is_file(),
                "loaded": name in self._models,
            }
            for name, path in self._paths.items()
        }

    # -- loading -------------------------------------------------------------
    def _load(self, name: str) -> Any:
        """Return the cached model, loading it on first use."""
        with self._load_lock:
            if name in self._models:
                return self._models[name]
            path = self._paths.get(name)
            if path is None:
                raise ModelUnavailableError(f"Unknown model '{name}'.")
            if not path.is_file():
                raise ModelUnavailableError(f"Model file for '{name}' was not found ({path.name}).")
            try:
                import tensorflow as tf  # lazy import
            except ImportError:
                raise ModelUnavailableError(
                    "TensorFlow is not installed, so the model cannot run. "
                    "Install it with: pip install tensorflow"
                ) from None
            model = self._load_keras(tf, name, path)
            self._models[name] = model
            log.info("Loaded model %s", name)
            return model

    @staticmethod
    def _load_keras(tf: Any, name: str, path: Path) -> Any:
        try:
            return tf.keras.models.load_model(str(path), compile=False)
        except Exception as exc:  # noqa: BLE001
            log.warning("Plain load of model %s failed: %s: %s", name, type(exc).__name__, exc)
            if not (config.ALLOW_UNSAFE_LAMBDA_LOAD and _is_lambda_deserialization_error(exc)):
                raise ModelUnavailableError(
                    f"Model '{name}' could not be loaded ({type(exc).__name__}). Check that the "
                    "TensorFlow/Keras version matches the one the model was saved with."
                ) from None
        # Known case: the ResNet50 model contains a Lambda(preprocess_input) layer.
        log.warning(
            "Retrying load of model %s with safe_mode=False. This executes code stored in the "
            "local model file; only use it with model files you trust.", name,
        )
        try:
            return tf.keras.models.load_model(str(path), compile=False, safe_mode=False)
        except Exception as exc:  # noqa: BLE001
            log.error("Unsafe-mode load of model %s failed: %s: %s", name, type(exc).__name__, exc)
            raise ModelUnavailableError(
                f"Model '{name}' could not be loaded ({type(exc).__name__})."
            ) from None

    def warmup(self) -> None:
        """Load every available model and run one dummy prediction (never raises)."""
        dummy = np.zeros((*config.IMG_SIZE, 3), dtype=np.float32)
        for name, state in self.status().items():
            if not state["available"]:
                continue
            try:
                self.predict(dummy, name)
                log.info("Warm-up finished for %s", name)
            except Exception as exc:  # noqa: BLE001
                log.warning("Warm-up failed for %s: %s", name, type(exc).__name__)

    # -- inference -----------------------------------------------------------
    def _acquire(self) -> None:
        if not self._inference.acquire(timeout=config.INFERENCE_WAIT_SECONDS):
            raise ModelUnavailableError("The server is busy with other analyses. Please retry shortly.")

    def predict(self, array: np.ndarray, model_name: str) -> list[float]:
        """Class probabilities for one (224, 224, 3) raw-RGB [0, 255] array."""
        if not isinstance(array, np.ndarray):
            raise ValueError(f"Input tensor must be a numpy ndarray, got {type(array).__name__}")
        expected_shape = (*config.IMG_SIZE, 3)
        if array.shape != expected_shape:
            raise ValueError(f"Expected input shape {expected_shape}, got {array.shape}")
        if not np.isfinite(array).all():
            raise ValueError("Input array contains NaN or infinite values")

        model = self._load(model_name)
        self._acquire()
        try:
            batch = array[None, ...]
            try:
                preds = model(batch, training=False)
                probs = preds.numpy()[0] if hasattr(preds, "numpy") else np.asarray(preds)[0]
            except Exception:
                probs = model.predict(batch, verbose=0)[0]
        finally:
            self._inference.release()

        if len(probs) != len(config.CLASSES):
            raise ModelUnavailableError(
                f"Model '{model_name}' output dimension {len(probs)} does not match expected {len(config.CLASSES)} classes."
            )
        if not np.isfinite(probs).all():
            raise RuntimeError(f"Model '{model_name}' generated non-finite (NaN/Inf) probabilities.")

        # Ensure valid probability distribution: clip to [0, 1] and renormalize
        probs = np.clip(probs, 0.0, 1.0)
        total = float(np.sum(probs))
        if total > 0:
            probs = probs / total
        return [float(p) for p in probs]

    def heatmap(self, array: np.ndarray, model_name: str, class_index: int) -> bytes:
        """Grad-CAM overlay PNG for ``class_index``."""
        if not (0 <= class_index < len(config.CLASSES)):
            raise ValueError(f"class_index {class_index} is out of bounds for classes {config.CLASSES}")
        model = self._load(model_name)
        with self._load_lock:
            cam = self._cams.get(model_name)
            if cam is None:
                cam = GradCam(model, config.GRADCAM_LAYERS.get(model_name))
                self._cams[model_name] = cam
        self._acquire()
        try:
            cam_map = cam.heatmap(array[None, ...], class_index)
        finally:
            self._inference.release()
        return overlay_heatmap(array, cam_map)

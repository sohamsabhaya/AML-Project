"""Shared fixtures: temp storage + a fake model service (no TensorFlow needed)."""
from __future__ import annotations

import io
import sys
from pathlib import Path

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.errors import ModelUnavailableError  # noqa: E402
from app.gradcam import overlay_heatmap  # noqa: E402
from app.main import create_app  # noqa: E402
from app.storage import Storage  # noqa: E402


class FakeModelService:
    """Returns fixed probabilities; ``probs`` can be changed per test."""

    def __init__(self) -> None:
        self.probs = [0.05, 0.85, 0.06, 0.04]
        self.probs_by_model: dict[str, list[float]] = {}  # optional per-model override
        self.available = True
        self.heatmap_fails = False
        self.loaded = False
        self.last_array: np.ndarray | None = None

    def is_loaded(self) -> bool:
        return self.loaded

    def status(self) -> dict[str, dict[str, bool]]:
        return {m: {"available": self.available, "loaded": self.loaded} for m in ("resnet50", "custom_cnn")}

    def tensorflow_available(self) -> bool:
        return self.available

    def predict(self, array: np.ndarray, model_name: str) -> list[float]:
        if not self.available:
            raise ModelUnavailableError("TensorFlow is not installed.")
        assert array.shape == (224, 224, 3) and array.dtype == np.float32
        self.last_array = array
        self.loaded = True
        return list(self.probs_by_model.get(model_name, self.probs))

    def heatmap(self, array: np.ndarray, model_name: str, class_index: int) -> bytes:
        if self.heatmap_fails:
            raise RuntimeError("boom")
        return overlay_heatmap(array, np.random.default_rng(0).random((7, 7)))


@pytest.fixture()
def fake_service() -> FakeModelService:
    return FakeModelService()


@pytest.fixture()
def client(tmp_path: Path, fake_service: FakeModelService) -> TestClient:
    app = create_app(storage=Storage(tmp_path / "data"), model_service=fake_service)
    return TestClient(app)


def make_image_bytes(fmt: str = "PNG", size: tuple[int, int] = (64, 48), mode: str = "L") -> bytes:
    arr = (np.random.default_rng(1).random((size[1], size[0])) * 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr, mode="L").convert(mode).save(buf, format=fmt)
    return buf.getvalue()


@pytest.fixture()
def png_bytes() -> bytes:
    return make_image_bytes("PNG")


def upload(client: TestClient, data: bytes, name: str = "scan.png", ctype: str = "image/png", **params):
    return client.post("/api/analyze", params=params, files={"file": (name, data, ctype)})

"""End-to-end and independent validation tests for both AI models (Custom CNN and ResNet50).

Tests real model loading, preprocessing, tensor shapes, inference, postprocessing,
error handling, and API integration without mocks.
"""
from __future__ import annotations

import io
import sys
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config  # noqa: E402
from app.main import create_app  # noqa: E402
from app.model_service import ModelService  # noqa: E402
from app.preprocess import (  # noqa: E402
    preprocess_custom_cnn,
    preprocess_for_model,
    preprocess_resnet50,
    validate_model_tensor,
    validate_upload,
)
from app.storage import Storage  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def real_service() -> ModelService:
    service = ModelService()
    return service


@pytest.fixture(scope="module")
def real_app(real_service: ModelService, tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    tmp_data = tmp_path_factory.mktemp("real_data")
    storage = Storage(tmp_data)
    app = create_app(storage=storage, model_service=real_service)
    return TestClient(app)


def make_test_image_bytes(
    fmt: str = "JPEG",
    size: tuple[int, int] = (224, 224),
    mode: str = "RGB",
    color: tuple[int, ...] | int = (128, 128, 128),
) -> bytes:
    img = Image.new(mode, size, color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Model Loading and Architecture Inspection
# ---------------------------------------------------------------------------
def test_both_models_available_and_files_exist(real_service: ModelService):
    status = real_service.status()
    assert "resnet50" in status, "resnet50 must be in status"
    assert "custom_cnn" in status, "custom_cnn must be in status"
    assert status["resnet50"]["available"] is True, "ResNet50 model file must exist"
    assert status["custom_cnn"]["available"] is True, "Custom CNN model file must exist"


def test_independent_model_loading(real_service: ModelService):
    m_resnet = real_service._load("resnet50")
    assert m_resnet is not None
    assert m_resnet.input_shape == (None, 224, 224, 3)
    assert m_resnet.output_shape == (None, 4)

    m_cnn = real_service._load("custom_cnn")
    assert m_cnn is not None
    assert m_cnn.input_shape == (None, 224, 224, 3)
    assert m_cnn.output_shape == (None, 4)


# ---------------------------------------------------------------------------
# 2. Preprocessing Validation for Both Models
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("model_name,prep_fn", [
    ("custom_cnn", preprocess_custom_cnn),
    ("resnet50", preprocess_resnet50),
])
def test_preprocessing_various_image_types(model_name: str, prep_fn):
    # Valid RGB JPG
    jpg_bytes = make_test_image_bytes("JPEG", (300, 400), "RGB", (100, 150, 200))
    val_jpg = validate_upload("scan.jpg", jpg_bytes)
    arr_jpg = prep_fn(val_jpg.image)
    assert arr_jpg.shape == (224, 224, 3)
    assert arr_jpg.dtype == np.float32
    assert np.isfinite(arr_jpg).all()
    assert 0.0 <= arr_jpg.min() and arr_jpg.max() <= 255.0

    # Valid PNG
    png_bytes = make_test_image_bytes("PNG", (224, 224), "RGB", (50, 100, 150))
    val_png = validate_upload("scan.png", png_bytes)
    arr_png = prep_fn(val_png.image)
    assert arr_png.shape == (224, 224, 3)
    assert arr_png.dtype == np.float32

    # Grayscale image (L)
    gray_bytes = make_test_image_bytes("PNG", (128, 128), "L", 120)
    val_gray = validate_upload("gray.png", gray_bytes)
    arr_gray = prep_fn(val_gray.image)
    assert arr_gray.shape == (224, 224, 3)
    # Check that channels are identical for grayscale input
    assert np.allclose(arr_gray[..., 0], arr_gray[..., 1])
    assert np.allclose(arr_gray[..., 1], arr_gray[..., 2])

    # Transparent image (RGBA)
    rgba_bytes = make_test_image_bytes("PNG", (250, 250), "RGBA", (255, 0, 0, 0))
    val_rgba = validate_upload("transparent.png", rgba_bytes)
    arr_rgba = prep_fn(val_rgba.image)
    assert arr_rgba.shape == (224, 224, 3)
    # Fully transparent pixels composited over black background must be 0
    assert np.allclose(arr_rgba, 0.0)

    # Dispatcher function matches dedicated pipeline
    arr_dispatched = preprocess_for_model(val_jpg.image, model_name)
    assert np.allclose(arr_jpg, arr_dispatched)


def test_tensor_validation_catches_invalid_inputs():
    with pytest.raises(ValueError, match="numpy ndarray"):
        validate_model_tensor("not_an_array", "test")

    with pytest.raises(ValueError, match="Expected tensor shape"):
        validate_model_tensor(np.zeros((100, 100, 3), dtype=np.float32), "test")

    with pytest.raises(ValueError, match="NaN or infinite"):
        bad_arr = np.zeros((224, 224, 3), dtype=np.float32)
        bad_arr[0, 0, 0] = np.nan
        validate_model_tensor(bad_arr, "test")


# ---------------------------------------------------------------------------
# 3. Independent Model Inference and Calibration
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("model_name", ["resnet50", "custom_cnn"])
def test_independent_inference(real_service: ModelService, model_name: str):
    dummy = np.ones((224, 224, 3), dtype=np.float32) * 128.0
    probs = real_service.predict(dummy, model_name)

    assert isinstance(probs, list)
    assert len(probs) == 4
    assert np.all(np.isfinite(probs))
    assert all(0.0 <= p <= 1.0 for p in probs)
    assert pytest.approx(sum(probs), abs=1e-4) == 1.0


@pytest.mark.parametrize("model_name", ["resnet50", "custom_cnn"])
def test_inference_consistency(real_service: ModelService, model_name: str):
    dummy = (np.indices((224, 224)).sum(axis=0) % 256).astype(np.float32)
    rgb = np.stack([dummy, dummy, dummy], axis=-1)

    p1 = real_service.predict(rgb, model_name)
    p2 = real_service.predict(rgb, model_name)
    assert p1 == p2, f"{model_name} must return identical predictions for identical inputs"


@pytest.mark.parametrize("model_name", ["resnet50", "custom_cnn"])
def test_heatmap_generation(real_service: ModelService, model_name: str):
    dummy = np.ones((224, 224, 3), dtype=np.float32) * 100.0
    cam_bytes = real_service.heatmap(dummy, model_name, class_index=0)

    assert isinstance(cam_bytes, bytes)
    assert len(cam_bytes) > 0
    # Ensure it is a decodable PNG
    with Image.open(io.BytesIO(cam_bytes)) as im:
        assert im.format == "PNG"
        assert im.size == (224, 224)


# ---------------------------------------------------------------------------
# 4. End-to-End API Integration for Both Models
# ---------------------------------------------------------------------------
def test_api_resnet50_analysis(real_app: TestClient):
    img_bytes = make_test_image_bytes("JPEG", (256, 256), "RGB", (80, 80, 80))
    res = real_app.post(
        "/api/analyze",
        params={"model": "resnet50", "heatmap": "true"},
        files={"file": ("brain.jpg", img_bytes, "image/jpeg")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["model_id"] == "resnet50"
    assert data["predicted_class"] in config.CLASSES
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["probabilities"]) == 4
    assert data["heatmap_url"] is not None


def test_api_custom_cnn_analysis(real_app: TestClient):
    img_bytes = make_test_image_bytes("PNG", (224, 224), "RGB", (90, 90, 90))
    res = real_app.post(
        "/api/analyze",
        params={"model": "custom_cnn", "heatmap": "true"},
        files={"file": ("brain.png", img_bytes, "image/png")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["model_id"] == "custom_cnn"
    assert data["predicted_class"] in config.CLASSES
    assert 0.0 <= data["confidence"] <= 1.0
    assert len(data["probabilities"]) == 4


def test_api_both_models_together(real_app: TestClient):
    img_bytes = make_test_image_bytes("JPEG", (300, 300), "RGB", (70, 70, 70))
    res = real_app.post(
        "/api/analyze",
        params={"model": "both", "heatmap": "true"},
        files={"file": ("compare.jpg", img_bytes, "image/jpeg")},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["comparison"] is not None
    cmp = data["comparison"]
    assert "resnet50" in cmp and cmp["resnet50"] is not None
    assert "custom_cnn" in cmp and cmp["custom_cnn"] is not None
    assert isinstance(cmp["agree"], bool)
    assert cmp["resnet50"]["predicted_class"] in config.CLASSES
    assert cmp["custom_cnn"]["predicted_class"] in config.CLASSES


# ---------------------------------------------------------------------------
# 5. Fault Isolation and Edge Cases
# ---------------------------------------------------------------------------
def test_api_invalid_image_rejected(real_app: TestClient):
    res = real_app.post(
        "/api/analyze",
        files={"file": ("bad.png", b"not-an-image-content", "image/png")},
    )
    assert res.status_code == 400


def test_api_empty_file_rejected(real_app: TestClient):
    res = real_app.post(
        "/api/analyze",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert res.status_code == 400


def test_api_unsupported_format_rejected(real_app: TestClient):
    res = real_app.post(
        "/api/analyze",
        files={"file": ("text.txt", b"hello world", "text/plain")},
    )
    assert res.status_code == 415


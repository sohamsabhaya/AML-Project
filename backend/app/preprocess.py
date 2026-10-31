"""Upload validation and image preprocessing.

Preprocessing MUST match training (Brain_Tumor_Classification_AML.ipynb):
  * Training used ``image_dataset_from_directory(image_size=(224, 224),
    label_mode='int')`` -> RGB, resized to 224x224, float32 in [0, 255].
  * Neither model expects pre-normalised input. The normalisation is inside
    the saved models: Custom CNN has a ``Rescaling(1/255)`` layer, ResNet50
    has a ``Lambda(resnet50.preprocess_input)`` layer. The notebook's own
    ``predict_and_visualize_mri`` feeds raw RGB [0, 255] too.
  So: do NOT divide by 255 and do NOT call preprocess_input here.
"""
from __future__ import annotations

import io
import re
import unicodedata
from pathlib import Path

import numpy as np
from fastapi import HTTPException
from PIL import Image, UnidentifiedImageError

from . import config


class ValidatedImage:
    """Result of a successful upload validation."""

    def __init__(self, image: Image.Image, extension: str, media_type: str) -> None:
        self.image = image
        self.extension = extension
        self.media_type = media_type


def sanitize_filename(name: str | None) -> str:
    """Return a safe display name: basename only, no control chars, max 100 chars."""
    base = (name or "").replace("\\", "/").split("/")[-1]
    base = unicodedata.normalize("NFKC", base)
    base = "".join(ch for ch in base if ch.isprintable())
    base = re.sub(r"\s+", " ", base).strip().lstrip(".")
    if len(base) > 100:
        stem, ext = Path(base).stem, Path(base).suffix[:10]
        base = stem[: 100 - len(ext)] + ext
    return base or "upload"


def validate_upload(filename: str | None, data: bytes) -> ValidatedImage:
    """Validate extension, size and real image content.

    400 empty/corrupt/too many pixels, 413 too large, 415 wrong type.
    """
    ext = Path(filename or "").suffix.lower()
    if ext not in config.ALLOWED_EXTENSIONS:
        raise HTTPException(415, "Unsupported file type. Please upload a PNG, JPG or JPEG image.")
    if len(data) == 0:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > config.MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File is too large. The maximum size is {config.MAX_UPLOAD_MB} MB.")
    # Pillow only warns at MAX_IMAGE_PIXELS (errors at 2x), so check the header ourselves.
    Image.MAX_IMAGE_PIXELS = config.MAX_IMAGE_PIXELS
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            width, height = probe.size
            if width * height > config.MAX_IMAGE_PIXELS:
                raise HTTPException(
                    400,
                    f"The image has too many pixels ({width}x{height}). "
                    f"The maximum is {config.MAX_IMAGE_PIXELS // 1_000_000} megapixels.",
                )
            probe.verify()  # cheap integrity check; invalidates this handle
        image = Image.open(io.BytesIO(data))
        image.load()  # full decode catches truncated files
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, Image.DecompressionBombError):
        raise HTTPException(400, "The file is not a valid image or is corrupted.") from None
    if fmt not in config.ALLOWED_FORMATS:
        raise HTTPException(415, "Unsupported image format. Please upload a PNG, JPG or JPEG image.")
    stored_ext, media_type = config.ALLOWED_FORMATS[fmt]
    return ValidatedImage(image, stored_ext, media_type)


def to_model_array(image: Image.Image) -> np.ndarray:
    """Convert to a (224, 224, 3) float32 RGB array with values in [0, 255].

    The notebook used cv2.resize (INTER_LINEAR, no anti-aliasing). An affine
    transform with BILINEAR resampling reproduces that sampling, whereas
    Image.resize would add anti-aliasing and give slightly different pixels.
    """
    rgb = image.convert("RGB")  # grayscale -> 3 channels, alpha dropped (as cv2.imread)
    w, h = rgb.size
    tw, th = config.IMG_SIZE
    if (w, h) != (tw, th):
        rgb = rgb.transform((tw, th), Image.AFFINE, (w / tw, 0, 0, 0, h / th, 0), resample=Image.BILINEAR)
    return np.asarray(rgb, dtype=np.float32)

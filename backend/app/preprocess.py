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
from PIL import Image, ImageOps, UnidentifiedImageError

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


def normalize_image_mode(image: Image.Image) -> Image.Image:
    """Standardise color channels to RGB.
    
    - Handles EXIF orientation tags.
    - Handles alpha/transparency: composites onto a black background (typical MRI background)
      so transparent areas do not become garbage pixel values.
    - Converts grayscale or palette images to 3 identical RGB channels.
    """
    try:
        image = ImageOps.exif_transpose(image)
    except Exception:
        pass

    if image.mode in ("RGBA", "LA") or (image.mode == "P" and "transparency" in image.info):
        rgba = image.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        image = Image.alpha_composite(bg, rgba).convert("RGB")
    elif image.mode != "RGB":
        image = image.convert("RGB")
    return image


def preprocess_image_array(image: Image.Image) -> np.ndarray:
    """Resize image to (224, 224, 3) float32 RGB array with values in [0, 255].
    
    Uses bilinear resampling matching OpenCV / TensorFlow training pipeline.
    """
    rgb = normalize_image_mode(image)
    w, h = rgb.size
    tw, th = config.IMG_SIZE
    if (w, h) != (tw, th):
        rgb = rgb.transform((tw, th), Image.AFFINE, (w / tw, 0, 0, 0, h / th, 0), resample=Image.BILINEAR)
    arr = np.asarray(rgb, dtype=np.float32)
    return validate_model_tensor(arr, "common")


def validate_model_tensor(array: np.ndarray, model_name: str) -> np.ndarray:
    """Validate that preprocessed tensor conforms strictly to model expectations."""
    if array is None or not isinstance(array, np.ndarray):
        raise ValueError(f"Preprocessed tensor for {model_name} must be a numpy ndarray.")
    expected_shape = (*config.IMG_SIZE, 3)
    if array.shape != expected_shape:
        raise ValueError(f"Expected tensor shape {expected_shape} for {model_name}, got {array.shape}.")
    if array.dtype != np.float32:
        array = array.astype(np.float32)
    if not np.isfinite(array).all():
        raise ValueError(f"Input tensor for {model_name} contains NaN or infinite values.")
    return array


def preprocess_custom_cnn(image: Image.Image) -> np.ndarray:
    """Model 1 preprocessing: Custom CNN baseline.
    
    Accepts raw RGB [0, 255] float32 array of shape (224, 224, 3).
    The internal Rescaling(1/255) layer inside Custom CNN maps [0, 255] to [0, 1].
    """
    arr = preprocess_image_array(image)
    return validate_model_tensor(arr, "custom_cnn")


def preprocess_resnet50(image: Image.Image) -> np.ndarray:
    """Model 2 preprocessing: ResNet50 Transfer Learning.
    
    Accepts raw RGB [0, 255] float32 array of shape (224, 224, 3).
    The internal Lambda(resnet50.preprocess_input) layer inside ResNet50 converts RGB
    to BGR and applies ImageNet zero-centering.
    """
    arr = preprocess_image_array(image)
    return validate_model_tensor(arr, "resnet50")


def preprocess_for_model(image: Image.Image, model_name: str) -> np.ndarray:
    """Dispatch to the dedicated preprocessing pipeline for the specified model."""
    if model_name == "custom_cnn":
        return preprocess_custom_cnn(image)
    elif model_name == "resnet50":
        return preprocess_resnet50(image)
    else:
        # Fallback to standard RGB [0, 255] array
        return preprocess_image_array(image)


def to_model_array(image: Image.Image) -> np.ndarray:
    """Backwards-compatible wrapper returning (224, 224, 3) float32 RGB array [0, 255]."""
    return preprocess_image_array(image)

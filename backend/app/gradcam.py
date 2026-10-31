"""Grad-CAM (Selvaraju et al.) for the predicted class.

Both saved models are flat Keras Functional graphs (ResNet50 was built with
``input_tensor=x`` so its layers sit directly in the outer model, which is why
``conv5_block3_out`` is a top-level layer). Nested base models (a ResNet50
inside a Sequential/Functional wrapper) are still supported: the conv layer is
searched recursively and a sequential forward pass is used for that case.

TensorFlow is imported lazily; ``overlay_heatmap`` needs only numpy + Pillow.
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np
from PIL import Image


def find_conv_layer(model: Any, preferred: str | None) -> tuple[Any | None, Any]:
    """Return ``(container, layer)``; container is None for a top-level layer.

    Tries ``preferred`` first (recursively into nested models), then falls back
    to the last layer with a 4-D output (the feature map before pooling/dense).
    """
    if preferred:
        found = _search(model, preferred, None)
        if found:
            return found
    for layer in reversed(model.layers):
        if hasattr(layer, "layers") and layer.layers:  # nested model
            inner = _last_4d(layer)
            if inner is not None:
                return layer, inner
        elif len(tuple(layer.output.shape)) == 4:
            return None, layer
    raise ValueError("No convolutional layer found for Grad-CAM")


def _search(model: Any, name: str, container: Any | None) -> tuple[Any | None, Any] | None:
    for layer in model.layers:
        if layer.name == name:
            return container, layer
        if hasattr(layer, "layers") and layer.layers:
            hit = _search(layer, name, layer)
            if hit:
                return hit
    return None


def _last_4d(model: Any) -> Any | None:
    for layer in reversed(model.layers):
        if len(tuple(layer.output.shape)) == 4:
            return layer
    return None


class GradCam:
    """Computes Grad-CAM maps for one loaded Keras model."""

    def __init__(self, model: Any, layer_name: str | None) -> None:
        import tensorflow as tf  # lazy import

        self._tf = tf
        self._model = model
        self._container, self._layer = find_conv_layer(model, layer_name)
        if self._container is None:
            # Flat graph: one extra model that exposes the conv feature map.
            self._grad_model = tf.keras.Model(model.inputs, [self._layer.output, model.output])
        else:
            # Nested base model: expose the conv map of the nested model only.
            self._feature_model = tf.keras.Model(
                self._container.inputs, [self._layer.output, self._container.output]
            )

    def _forward(self, x: Any) -> tuple[Any, Any]:
        """Return (conv feature map, class probabilities) for input ``x``."""
        if self._container is None:
            conv_out, preds = self._grad_model(x, training=False)
            return conv_out, preds
        # Linear wrapper (Sequential / chain): run layers in order, tapping the nested model.
        h = x
        conv_out = None
        for layer in self._model.layers:
            if layer is self._container:
                conv_out, h = self._feature_model(h, training=False)
            elif layer.__class__.__name__ != "InputLayer":
                h = layer(h, training=False)
        return conv_out, h

    def heatmap(self, batch: np.ndarray, class_index: int) -> np.ndarray:
        """Return a 2-D map in [0, 1] (conv-layer resolution) for ``class_index``.

        ``batch`` is shape (1, 224, 224, 3), float32, raw [0, 255] RGB.
        """
        tf = self._tf
        x = tf.convert_to_tensor(batch, dtype=tf.float32)
        with tf.GradientTape() as tape:
            conv_out, preds = self._forward(x)
            score = preds[:, class_index]
        grads = tape.gradient(score, conv_out)
        if grads is None:
            raise RuntimeError("Gradient is None: conv layer is not connected to the output")
        weights = tf.reduce_mean(grads, axis=(1, 2))  # (1, C): importance per channel
        cam = tf.reduce_sum(conv_out * weights[:, None, None, :], axis=-1)[0]
        cam = tf.nn.relu(cam).numpy()
        peak = float(cam.max())
        return cam / peak if peak > 1e-8 else np.zeros_like(cam)


def _jet(values: np.ndarray) -> np.ndarray:
    """Matplotlib-style 'jet' colormap for values in [0, 1] -> uint8 RGB."""
    v = np.clip(values, 0.0, 1.0)
    r = np.clip(1.5 - np.abs(4.0 * v - 3.0), 0, 1)
    g = np.clip(1.5 - np.abs(4.0 * v - 2.0), 0, 1)
    b = np.clip(1.5 - np.abs(4.0 * v - 1.0), 0, 1)
    return (np.stack([r, g, b], axis=-1) * 255).astype(np.uint8)


def overlay_heatmap(rgb: np.ndarray, cam: np.ndarray, alpha: float = 0.4) -> bytes:
    """Blend a [0, 1] ``cam`` over the RGB image (values 0-255); return PNG bytes."""
    base = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGB")
    cam_img = Image.fromarray((np.clip(cam, 0, 1) * 255).astype(np.uint8)).resize(
        base.size, Image.BICUBIC
    )
    colored = _jet(np.asarray(cam_img, dtype=np.float32) / 255.0)
    blended = Image.blend(base, Image.fromarray(colored), alpha)
    buf = io.BytesIO()
    blended.save(buf, format="PNG")
    return buf.getvalue()

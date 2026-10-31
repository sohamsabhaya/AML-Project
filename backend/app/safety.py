"""Uncertainty measures derived from the class probabilities."""
from __future__ import annotations

import math
from typing import Any

from . import config


def entropy_nats(probs: list[float]) -> float:
    """Shannon entropy in nats (0 = certain, ln(4) = 1.386 = maximally uncertain)."""
    return round(-sum(p * math.log(p) for p in probs if p > 0), 4)


def top2(probabilities: dict[str, float]) -> list[dict[str, Any]]:
    ranked = sorted(probabilities.items(), key=lambda kv: kv[1], reverse=True)[:2]
    return [
        {"class": cls, "label": config.CLASS_LABELS.get(cls, cls), "probability": round(float(p), 6)}
        for cls, p in ranked
    ]


def safety_fields(
    probabilities: dict[str, float], threshold: float | None = None
) -> dict[str, Any]:
    """``low_confidence``, ``confidence_threshold``, ``top2`` and ``entropy`` for one result."""
    limit = config.CONFIDENCE_THRESHOLD if threshold is None else threshold
    values = [float(v) for v in probabilities.values()]
    return {
        "low_confidence": max(values) < limit,
        "confidence_threshold": limit,
        "top2": top2(probabilities),
        "entropy": entropy_nats(values),
    }

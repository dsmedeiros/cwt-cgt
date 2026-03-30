"""Statistical summary helpers for geometric quantities.

Pure utilities — no imports from layers/, orchestrator/, experiments/,
or baselines/ (invariant GEOM-001).
"""

from __future__ import annotations

from typing import Iterable

import numpy as np


def summarize(values: Iterable[float]) -> dict[str, float | int | None]:
    """Min/max/mean/median summary, ignoring non-finite entries."""
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
    }


def summarize_abs(values: Iterable[float]) -> dict[str, float | int | None]:
    """Min/max/mean/median of absolute values, ignoring non-finite entries."""
    arr = np.asarray(list(values), dtype=float)
    arr = np.abs(arr[np.isfinite(arr)])
    if arr.size == 0:
        return {"count": 0, "min": None, "max": None, "mean": None, "median": None}
    return {
        "count": int(arr.size),
        "min": float(np.min(arr)),
        "max": float(np.max(arr)),
        "mean": float(np.mean(arr)),
        "median": float(np.median(arr)),
    }


def fit_through_origin(x: np.ndarray, y: np.ndarray) -> dict[str, float]:
    """Least-squares fit y = slope * x constrained through the origin.

    Returns a dict with ``slope`` and ``r_squared``.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr)
    x_arr = x_arr[mask]
    y_arr = y_arr[mask]
    denom = float(np.dot(x_arr, x_arr))
    if abs(denom) <= 1e-30:
        return {"slope": 0.0, "r_squared": 0.0}
    slope = float(np.dot(x_arr, y_arr)) / denom
    residuals = y_arr - slope * x_arr
    ss_res = float(np.dot(residuals, residuals))
    ss_tot = float(np.dot(y_arr, y_arr))
    r2 = max(0.0, 1.0 - ss_res / max(ss_tot, 1e-30))
    return {"slope": slope, "r_squared": r2}

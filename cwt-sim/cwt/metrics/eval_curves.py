"""Evaluation curve utilities."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

import numpy as np

try:  # pragma: no cover - optional dependency
    import scipy.sparse as sp
except ModuleNotFoundError:  # pragma: no cover - SciPy is optional
    sp = None  # type: ignore[assignment]

from ..geometry.fs_distance import fs_distance
from ..orchestrator.scheduler import RunRecord


@dataclass
class LoopSummary:
    """Compact summary of a single parameter loop run."""

    phi_flux: float
    R_bias: float
    orientation: str
    overlaps_min: float
    fs_stats: dict[str, float]


def _clean_float(value: float) -> float:
    if not math.isfinite(value):
        return float("nan")
    return float(value)


def _infer_orientation(meta: Any, phi_flux: float) -> str:
    """Infer loop orientation from metadata and flux sign."""

    orientation: str | None = None
    if isinstance(meta, dict):
        raw = meta.get("orientation")
        if isinstance(raw, str) and raw.strip():
            orientation = raw.strip().upper()
        elif "meta" in meta and isinstance(meta["meta"], dict):
            raw = meta["meta"].get("orientation")
            if isinstance(raw, str) and raw.strip():
                orientation = raw.strip().upper()
        if orientation is None:
            label = str(meta.get("label", ""))
            lower = label.lower()
            if "ccw" in lower and "cw" not in lower.replace("ccw", ""):
                orientation = "CCW"
            elif "cw" in lower:
                orientation = "CW"
    if orientation:
        if orientation not in {"CW", "CCW"}:
            return orientation
        return orientation

    if phi_flux > 0.0:
        return "CCW"
    if phi_flux < 0.0:
        return "CW"
    return "UNKNOWN"


def _aggregate_bias(
    curvature_biases: Iterable[np.ndarray],
    final_readout: Mapping[str, Any] | None = None,
) -> float:
    arrays = [np.asarray(bias, dtype=float) for bias in curvature_biases if np.size(bias)]
    if not arrays:
        return 0.0

    total = np.sum(arrays, axis=0, dtype=float)
    total = np.asarray(total, dtype=float)
    if total.size == 0:
        return 0.0

    if not np.all(np.isfinite(total)):
        total = np.where(np.isfinite(total), total, 0.0)

    if final_readout and isinstance(final_readout, Mapping):
        memory = final_readout.get("memory")
        if memory is not None:
            chi = np.asarray(memory, dtype=float)
            if chi.shape == total.shape and chi.size:
                if not np.all(np.isfinite(chi)):
                    chi = np.where(np.isfinite(chi), chi, 0.0)
                weighted = float(np.dot(total, chi))
                if math.isfinite(weighted):
                    return weighted

    scalar = float(np.sum(total))
    if not math.isfinite(scalar):
        return 0.0
    return scalar


def _fs_statistics(psi_traj: Iterable[np.ndarray]) -> dict[str, float]:
    psi_list = [np.asarray(vec, dtype=np.complex128) for vec in psi_traj]
    stats = {
        "count": 0.0,
        "mean": float("nan"),
        "max": float("nan"),
        "min": float("nan"),
        "kappa1": float("nan"),
    }
    if len(psi_list) < 2:
        return stats

    distances: list[float] = []
    for a, b in zip(psi_list, psi_list[1:]):
        if a.size == 0 or b.size == 0:
            distances.append(float("nan"))
            continue
        try:
            dist = fs_distance(a, b)
        except ValueError:
            dist = float("nan")
        distances.append(float(dist))

    stats["count"] = float(len(distances))
    if not distances:
        return stats

    finite = [value for value in distances if math.isfinite(value)]
    if finite:
        arr = np.asarray(finite, dtype=float)
        stats["mean"] = float(arr.mean())
        stats["max"] = float(arr.max())
        stats["min"] = float(arr.min())
    first = distances[0]
    stats["kappa1"] = float(first) if math.isfinite(first) else float("nan")
    return stats


def _min_overlap(overlaps: Iterable[float]) -> float:
    values = [float(v) for v in overlaps if math.isfinite(float(v))]
    if not values:
        return float("nan")
    return float(min(values))


def summarize_loop(record: RunRecord) -> LoopSummary:
    """Return a :class:`LoopSummary` for ``record``."""

    if not isinstance(record, RunRecord):
        raise TypeError("record must be a RunRecord instance")

    phi_flux = 0.0
    if record.omega_tiles:
        total_flux = 0.0
        for tile in record.omega_tiles:
            if not isinstance(tile, dict):
                continue
            try:
                omega = float(tile.get("omega", 0.0))
                area = float(tile.get("tile_area", 0.0))
            except (TypeError, ValueError):  # pragma: no cover - defensive
                continue
            if math.isfinite(omega) and math.isfinite(area):
                total_flux += omega * area
        phi_flux = total_flux

    final_readout = record.readouts[-1] if record.readouts else None
    R_bias = _aggregate_bias(record.curvature_biases, final_readout)
    overlaps_min = _min_overlap(record.overlaps_min)
    fs_stats = _fs_statistics(record.psi_traj)
    orientation = _infer_orientation(record.meta, phi_flux)

    fs_stats = {key: _clean_float(value) for key, value in fs_stats.items()}

    return LoopSummary(
        phi_flux=_clean_float(phi_flux),
        R_bias=_clean_float(R_bias),
        orientation=orientation,
        overlaps_min=_clean_float(overlaps_min),
        fs_stats=fs_stats,
    )


def auc_hotspot(score_map: np.ndarray, target_map: np.ndarray) -> float:
    """Compute the ROC AUC for a hotspot detector."""

    scores = np.asarray(score_map, dtype=float).ravel()
    targets = np.asarray(target_map, dtype=float).ravel()

    mask = np.isfinite(scores) & np.isfinite(targets)
    if not mask.any():
        return float("nan")

    scores = scores[mask]
    targets = targets[mask]

    positives = targets > 0.0
    n_pos = int(np.count_nonzero(positives))
    n_neg = int(scores.size - n_pos)
    if n_pos == 0 or n_neg == 0:
        return float("nan")

    order = np.argsort(scores, kind="mergesort")[::-1]
    sorted_pos = positives.astype(int)[order]

    tp = np.cumsum(sorted_pos)
    fp = np.cumsum(1 - sorted_pos)

    tpr = tp / max(n_pos, 1)
    fpr = fp / max(n_neg, 1)

    tpr = np.concatenate([[0.0], tpr, [1.0]])
    fpr = np.concatenate([[0.0], fpr, [1.0]])

    auc = float(np.trapz(tpr, fpr))
    if not math.isfinite(auc):
        return float("nan")
    return float(np.clip(auc, 0.0, 1.0))


def spectral_gap(K: Any) -> float:
    """Return the spectral gap ``1 - |λ₂|`` of ``K``."""

    if sp is not None and sp.issparse(K):  # type: ignore[arg-type]
        matrix = K.toarray()
    else:
        matrix = np.asarray(K, dtype=float)

    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("spectral_gap expects a square matrix")

    n = matrix.shape[0]
    if n <= 1:
        return 0.0

    eigenvalues = np.linalg.eigvals(matrix.T)
    magnitudes = np.sort(np.abs(eigenvalues))
    if magnitudes.size < 2:
        return 0.0

    lambda2 = float(magnitudes[-2])
    lambda2 = min(lambda2, 1.0)
    gap = 1.0 - lambda2
    if gap < 0.0:
        gap = 0.0
    return float(gap)


def kuramoto_order(theta: np.ndarray) -> float:
    """Return the Kuramoto order parameter for ``theta``."""

    angles = np.asarray(theta, dtype=float).ravel()
    if angles.size == 0:
        return float("nan")
    order = np.mean(np.exp(1j * angles))
    return float(np.abs(order))


__all__ = [
    "LoopSummary",
    "summarize_loop",
    "auc_hotspot",
    "spectral_gap",
    "kuramoto_order",
]

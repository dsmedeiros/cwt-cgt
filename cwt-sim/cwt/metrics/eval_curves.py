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

    matrix = _as_square_matrix(K, "spectral_gap")
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


def _as_square_matrix(value: Any, caller: str) -> np.ndarray:
    if sp is not None and sp.issparse(value):  # type: ignore[arg-type]
        matrix = value.toarray()
    else:
        matrix = np.asarray(value, dtype=float)

    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError(f"{caller} expects a square matrix")
    return np.asarray(matrix, dtype=float)


def non_degenerate_spectral_gap(K: Any, eps: float = 1e-8) -> float:
    """Return the dominant spectral gap, treating top degeneracy as zero gap."""

    matrix = _as_square_matrix(K, "non_degenerate_spectral_gap")
    n = matrix.shape[0]
    if n <= 1:
        return 0.0

    tolerance = abs(float(eps))
    magnitudes = np.sort(np.abs(np.linalg.eigvals(matrix)))[::-1]
    dominant = float(magnitudes[0])
    if magnitudes.size > 1 and abs(float(magnitudes[1]) - dominant) <= tolerance:
        return 0.0
    if magnitudes.size < 2:
        return 0.0
    gap = dominant - float(magnitudes[1])
    return float(max(gap, 0.0))


def second_singular_value(K: Any) -> float:
    """Return the second largest singular value of ``K``."""

    matrix = _as_square_matrix(K, "second_singular_value")
    if matrix.shape[0] <= 1:
        return 0.0

    singular_values = np.linalg.svd(matrix, compute_uv=False)
    singular_values = np.sort(np.asarray(singular_values, dtype=float))[::-1]
    if singular_values.size < 2:
        return 0.0
    return float(singular_values[1])


def mixing_time_baseline(K: Any, eps: float = 1e-3) -> float:
    """Estimate a simple SVD-based mixing-time baseline from sigma_2."""

    sigma2 = second_singular_value(K)
    target = float(eps)
    if target <= 0.0 or not math.isfinite(target):
        raise ValueError("eps must be a finite positive scalar")
    if sigma2 <= 0.0:
        return 1.0
    if sigma2 >= 1.0:
        return float("inf")
    return float(math.ceil(math.log(target) / math.log(sigma2)))


def orientation_antisymmetry_statistic(
    ccw: Iterable[float] | np.ndarray,
    cw: Iterable[float] | np.ndarray,
    eps: float = 1e-12,
) -> dict[str, float | int]:
    """Summarize how close paired orientation responses are to antisymmetric."""

    ccw_arr = np.asarray(ccw, dtype=float)
    cw_arr = np.asarray(cw, dtype=float)
    ccw_arr, cw_arr = np.broadcast_arrays(ccw_arr, cw_arr)
    mask = np.isfinite(ccw_arr) & np.isfinite(cw_arr)
    if not mask.any():
        return {
            "count": 0,
            "score": float("nan"),
            "symmetric_residual": float("nan"),
            "orientation_gap": float("nan"),
        }

    left = ccw_arr[mask]
    right = cw_arr[mask]
    symmetric = left + right
    denominator = float(np.sum(np.abs(left) + np.abs(right))) + abs(float(eps))
    residual = float(np.sum(np.abs(symmetric)) / denominator)
    score = float(np.clip(1.0 - residual, 0.0, 1.0))
    return {
        "count": int(left.size),
        "score": score,
        "symmetric_residual": residual,
        "orientation_gap": float(np.mean(left - right)),
    }


def log_log_slope(x: Iterable[float], y: Iterable[float]) -> dict[str, float | int]:
    """Fit ``log(y) = slope * log(x) + intercept`` on positive finite pairs."""

    x_arr = np.asarray(list(x), dtype=float)
    y_arr = np.asarray(list(y), dtype=float)
    x_arr, y_arr = np.broadcast_arrays(x_arr, y_arr)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr) & (x_arr > 0.0) & (y_arr > 0.0)
    count = int(np.count_nonzero(mask))
    if count < 2:
        return {
            "count": count,
            "slope": float("nan"),
            "intercept": float("nan"),
            "r_squared": float("nan"),
        }

    lx = np.log(x_arr[mask])
    ly = np.log(y_arr[mask])
    design = np.column_stack((lx, np.ones_like(lx)))
    slope, intercept = np.linalg.lstsq(design, ly, rcond=None)[0]
    predicted = slope * lx + intercept
    residual = ly - predicted
    ss_res = float(np.dot(residual, residual))
    centered = ly - float(np.mean(ly))
    ss_tot = float(np.dot(centered, centered))
    r_squared = 1.0 if ss_tot <= 1e-30 else 1.0 - ss_res / ss_tot
    return {
        "count": int(lx.size),
        "slope": float(slope),
        "intercept": float(intercept),
        "r_squared": float(np.clip(r_squared, 0.0, 1.0)),
    }


def fs_adiabaticity_guard(
    fs_steps: Iterable[float],
    max_step: float = 0.1,
) -> dict[str, float | int | bool | str | None]:
    """Report whether Fubini-Study step sizes remain adiabatic."""

    values = np.asarray(list(fs_steps), dtype=float)
    values = values[np.isfinite(values)]
    if values.size == 0:
        return {
            "count": 0,
            "passed": False,
            "max_step": float("nan"),
            "mean_step": float("nan"),
            "threshold": float(max_step),
            "excluded_reason": "no_finite_fs_steps",
        }

    max_value = float(np.max(np.abs(values)))
    mean_value = float(np.mean(np.abs(values)))
    threshold = float(max_step)
    passed = bool(max_value <= threshold)
    return {
        "count": int(values.size),
        "passed": passed,
        "max_step": max_value,
        "mean_step": mean_value,
        "threshold": threshold,
        "excluded_reason": None if passed else "non_adiabatic_fs_step",
    }


def overlap_safe_tile_filter(min_overlaps: Any, threshold: float = 0.9) -> np.ndarray:
    """Return a boolean mask for overlap-safe tiles."""

    overlaps = np.asarray(min_overlaps, dtype=float)
    return np.isfinite(overlaps) & (overlaps >= float(threshold))


def metric_only_null_rejection(
    metric_scores: Iterable[float],
    responses: Iterable[float],
    max_abs_correlation: float = 0.25,
    min_count: int = 3,
) -> dict[str, float | int | bool | str | None]:
    """Decide whether a metric-only explanation is weak enough to reject."""

    scores = np.asarray(list(metric_scores), dtype=float)
    values = np.asarray(list(responses), dtype=float)
    scores, values = np.broadcast_arrays(scores, values)
    mask = np.isfinite(scores) & np.isfinite(values)
    count = int(np.count_nonzero(mask))
    if count < int(min_count):
        return {
            "count": count,
            "reject_metric_only": False,
            "correlation": float("nan"),
            "abs_correlation": float("nan"),
            "reason": "insufficient_data",
        }

    x = scores[mask]
    y = values[mask]
    if float(np.std(x)) <= 1e-15 or float(np.std(y)) <= 1e-15:
        correlation = 0.0
    else:
        correlation = float(np.corrcoef(x, y)[0, 1])
    abs_corr = abs(correlation)
    reject = bool(abs_corr <= float(max_abs_correlation))
    return {
        "count": count,
        "reject_metric_only": reject,
        "correlation": correlation,
        "abs_correlation": abs_corr,
        "reason": None if reject else "metric_response_correlation_above_threshold",
    }


def scramble_response_summary(
    baseline_ccw: Iterable[float] | np.ndarray,
    baseline_cw: Iterable[float] | np.ndarray,
    a_zero_ccw: Iterable[float] | np.ndarray,
    a_zero_cw: Iterable[float] | np.ndarray,
    a_signflip_ccw: Iterable[float] | np.ndarray,
    a_signflip_cw: Iterable[float] | np.ndarray,
    collapse_ratio: float = 0.1,
) -> dict[str, float | bool]:
    """Summarize expected `A_zero` collapse and `A_signflip` reversal."""

    base_ccw = np.asarray(baseline_ccw, dtype=float)
    base_cw = np.asarray(baseline_cw, dtype=float)
    zero_ccw = np.asarray(a_zero_ccw, dtype=float)
    zero_cw = np.asarray(a_zero_cw, dtype=float)
    flip_ccw = np.asarray(a_signflip_ccw, dtype=float)
    flip_cw = np.asarray(a_signflip_cw, dtype=float)
    base_ccw, base_cw, zero_ccw, zero_cw, flip_ccw, flip_cw = np.broadcast_arrays(
        base_ccw,
        base_cw,
        zero_ccw,
        zero_cw,
        flip_ccw,
        flip_cw,
    )
    mask = (
        np.isfinite(base_ccw)
        & np.isfinite(base_cw)
        & np.isfinite(zero_ccw)
        & np.isfinite(zero_cw)
        & np.isfinite(flip_ccw)
        & np.isfinite(flip_cw)
    )
    if not mask.any():
        return {
            "baseline_gap": float("nan"),
            "a_zero_gap": float("nan"),
            "a_signflip_alignment": float("nan"),
            "a_zero_collapsed": False,
            "a_signflip_reversed": False,
        }

    baseline_gap = float(np.mean(np.abs(base_ccw[mask] - base_cw[mask])))
    zero_gap = float(np.mean(np.abs(zero_ccw[mask] - zero_cw[mask])))
    baseline_vec = np.concatenate([base_ccw[mask].ravel(), base_cw[mask].ravel()])
    flipped_vec = np.concatenate([flip_ccw[mask].ravel(), flip_cw[mask].ravel()])
    denom = float(np.linalg.norm(baseline_vec) * np.linalg.norm(flipped_vec))
    alignment = 0.0 if denom <= 1e-30 else float(np.dot(baseline_vec, flipped_vec) / denom)
    return {
        "baseline_gap": baseline_gap,
        "a_zero_gap": zero_gap,
        "a_signflip_alignment": alignment,
        "a_zero_collapsed": bool(zero_gap <= float(collapse_ratio) * max(baseline_gap, 1e-30)),
        "a_signflip_reversed": bool(alignment < -0.95),
    }


def noise_threshold_report(
    s_bar_values: Iterable[float],
    responses: Iterable[float],
    mild_s_bar_floor: float = 0.95,
) -> dict[str, float | int | None]:
    """Report the first observed sign-flip threshold in a noise sweep."""

    s_bar = np.asarray(list(s_bar_values), dtype=float)
    response = np.asarray(list(responses), dtype=float)
    s_bar, response = np.broadcast_arrays(s_bar, response)
    mask = np.isfinite(s_bar) & np.isfinite(response)
    if not mask.any():
        return {
            "count": 0,
            "reference_sign": None,
            "sign_flip_s_bar": None,
            "mild_count": 0,
            "high_noise_excluded_count": 0,
        }

    s_clean = s_bar[mask]
    r_clean = response[mask]
    order = np.argsort(-s_clean)
    s_sorted = s_clean[order]
    r_sorted = r_clean[order]
    nonzero = r_sorted[np.abs(r_sorted) > 1e-15]
    if nonzero.size == 0:
        reference_sign: int | None = None
    else:
        reference_sign = 1 if float(nonzero[0]) > 0.0 else -1

    flip_threshold: float | None = None
    if reference_sign is not None:
        for coherence, value in zip(s_sorted, r_sorted):
            if abs(float(value)) <= 1e-15:
                continue
            sign = 1 if float(value) > 0.0 else -1
            if sign != reference_sign:
                flip_threshold = float(coherence)
                break

    if flip_threshold is None:
        excluded = 0
    else:
        excluded = int(np.count_nonzero(s_clean <= flip_threshold))

    return {
        "count": int(s_clean.size),
        "reference_sign": reference_sign,
        "sign_flip_s_bar": flip_threshold,
        "mild_count": int(np.count_nonzero(s_clean >= float(mild_s_bar_floor))),
        "high_noise_excluded_count": excluded,
    }


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
    "non_degenerate_spectral_gap",
    "second_singular_value",
    "mixing_time_baseline",
    "orientation_antisymmetry_statistic",
    "log_log_slope",
    "fs_adiabaticity_guard",
    "overlap_safe_tile_filter",
    "metric_only_null_rejection",
    "scramble_response_summary",
    "noise_threshold_report",
    "kuramoto_order",
]

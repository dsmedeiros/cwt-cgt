"""Frozen real shell-state encoding and small exact percolation controls."""

from itertools import product

import numpy as np

from cwt.geometry.curvature import curvature_tile
from cwt.geometry.metric import metric_tile
from cwt.geometry.psi import build_psi
from experiments.percolation_finite_size.model import Box, sample_shells


def _validate_tile(step: float, min_overlap: float) -> None:
    if not np.isfinite(step) or step <= 0:
        raise ValueError("step must be positive and finite")
    area = float(step) * float(step)
    if not np.isfinite(area) or area <= 0:
        raise ValueError("step squared must give a positive finite representable stencil area")
    if not np.isfinite(min_overlap) or not 0 <= min_overlap <= 1:
        raise ValueError("min_overlap must be finite and in [0, 1]")


def sqrt_state(weights: np.ndarray) -> np.ndarray:
    """Normalize unsmoothed shell weights into a real square-root state."""
    weights = np.asarray(weights, dtype=float)
    if weights.ndim != 1 or not np.all(np.isfinite(weights)) or np.any(weights < 0) or weights.sum() <= 0:
        raise ValueError("weights must be a finite nonnegative vector with positive mass")
    return build_psi(weights / weights.sum(), np.zeros_like(weights))


def histogram_geometry(
    histograms: np.ndarray,
    step: float,
    min_overlap: float = 0.1,
) -> dict[str, object]:
    """Estimate a forward tile ordered 0, u, uv, v; expose support exclusions."""
    _validate_tile(step, min_overlap)
    histograms = np.asarray(histograms)
    if (
        histograms.ndim != 2
        or histograms.shape[0] != 4
        or histograms.shape[1] == 0
        or not np.all(np.isfinite(histograms))
        or np.any(histograms < 0)
        or np.any(histograms.sum(axis=1) <= 0)
    ):
        raise ValueError("histograms must contain four finite nonnegative positive-mass rows")
    result: dict[str, object] = {
        "histograms": histograms.tolist(),
        "support_sizes": np.sum(histograms > 0, axis=1).tolist(),
        "trace_g": None,
        "g_uu": None,
        "g_uv": None,
        "g_vv": None,
        "omega": None,
        "min_overlap": None,
        "excluded_reason": None,
    }
    if np.any(histograms == 0):
        result["excluded_reason"] = "zero_bin"
        return result
    psi0, psi_u, psi_uv, psi_v = [sqrt_state(row) for row in histograms]
    omega, stats = curvature_tile(psi0, psi_u, psi_uv, psi_v, step, step)
    result["min_overlap"] = stats["min_overlap"]
    if stats["min_overlap"] < min_overlap:
        result["excluded_reason"] = "low_overlap"
        return result
    guu = metric_tile(psi0, psi_u, psi_u, step, step)
    gvv = metric_tile(psi0, psi_v, psi_v, step, step)
    guv = metric_tile(psi0, psi_u, psi_v, step, step)
    if not np.all(np.isfinite([guu, gvv, guv, omega])):
        result["excluded_reason"] = "nonfinite_estimator"
        return result
    result.update(trace_g=guu + gvv, g_uu=guu, g_uv=guv, g_vv=gvv, omega=omega)
    return result


def sample_geometry(
    box: Box,
    u: float,
    v: float,
    step: float,
    uniforms: np.ndarray,
    min_overlap: float = 0.1,
) -> dict[str, object]:
    """Reuse geometry-stream uniforms at four chart corners, separate from measurement."""
    _validate_tile(step, min_overlap)
    corners = np.array([(u, v), (u + step, v), (u + step, v + step), (u, v + step)])
    if not np.all(np.isfinite(corners)):
        raise ValueError("chart coordinates must be finite")
    if np.any((corners <= 0) | (corners >= 1)):
        return {
            "excluded_reason": "chart_outside_open_domain",
            "histograms": [],
            "support_sizes": [],
            "trace_g": None,
            "g_uu": None,
            "g_uv": None,
            "g_vv": None,
            "omega": None,
            "min_overlap": None,
            "trials": 0,
        }
    counts = [sample_shells(box, a, b, uniforms) for a, b in corners]
    result = histogram_geometry(np.asarray([row.histogram for row in counts]), step, min_overlap)
    result["trials"] = counts[0].trials
    return result


def chain_probabilities(u: float, v: float) -> np.ndarray:
    """Exact radius 0,1,2 masses on (0,0)-(1,0)-(1,1)-(1,2), weights u,v,v."""
    if not np.all(np.isfinite([u, v])) or not (0 < u < 1 and 0 < v < 1):
        raise ValueError("chain coordinates must lie in open (0, 1)")
    return np.array([1 - u, u * (1 - v * v), u * v * v])


def chain_control(u: float = 0.4, v: float = 0.6, step: float = 1e-4) -> dict[str, object]:
    """Compare actual CGT estimators to the same encoding's exact diagonal tensor."""
    weights = [
        chain_probabilities(a, b) for a, b in [(u, v), (u + step, v), (u + step, v + step), (u, v + step)]
    ]
    result = histogram_geometry(np.asarray(weights), step)
    result["analytic"] = {"g_uu": 1 / (4 * u * (1 - u)), "g_vv": u / (1 - v * v), "g_uv": 0.0, "omega": 0.0}
    return result


def diamond_gluing(weights: np.ndarray) -> dict[str, object]:
    """Enumerate one four-edge independent diamond; this is a finite control, not a proof."""
    weights = np.asarray(weights, dtype=float)
    if weights.shape != (4,) or not np.all(np.isfinite(weights)) or np.any((weights < 0) | (weights > 1)):
        raise ValueError("diamond weights must be four finite probabilities in [0, 1]")
    edges = [(0, 1), (0, 2), (1, 3), (2, 3)]  # o=0, A={1,2}, b=3
    p_o_A, p_o_b, p_a_b = 0.0, 0.0, np.zeros(2)
    for configuration in product([False, True], repeat=4):
        mass = float(np.prod(np.where(configuration, weights, 1 - weights)))
        connected = {3}
        while True:
            before = len(connected)
            for opened, (a, b) in zip(configuration, edges):
                if opened and (a in connected or b in connected):
                    connected.update([a, b])
            if len(connected) == before:
                break
        p_o_A += mass * (configuration[0] or configuration[1])
        p_o_b += mass * (0 in connected)
        p_a_b += mass * np.array([1 in connected, 2 in connected])
    t = float(np.max(1 - p_a_b))
    bound = p_o_A - t
    return {
        "p_o_A": p_o_A,
        "p_o_b": p_o_b,
        "p_a_b": p_a_b.tolist(),
        "t": t,
        "bound": bound,
        "slack": p_o_b - bound,
        "passed": p_o_b + 1e-12 >= bound,
        "configurations": 16,
        "weights": weights.tolist(),
    }


def controls() -> dict[str, object]:
    """Return analytic same-encoding chain and finite additive-gluing checks."""
    return {"chain": chain_control(), "diamond": diamond_gluing(np.array([0.8, 0.6, 0.9, 0.7]))}

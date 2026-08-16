"""Phase-coherence utilities and projective geometry helpers for CGT.

This module provides probability normalisation, phase wrapping, and
projective metric/curvature estimators used by the CGT benchmark
framework.  Functions here must remain pure geometry — no imports from
``layers/``, ``orchestrator/``, ``experiments/``, or ``baselines/``
(invariant GEOM-001).
"""

from __future__ import annotations

import numpy as np


def normalize_probabilities(values: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    """Return a normalised probability vector, clamping entries above *floor*."""
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr
    arr = np.maximum(arr, floor)
    total = float(arr.sum())
    if total <= 0.0:
        arr = np.full(arr.shape, 1.0 / arr.size, dtype=float)
    else:
        arr = arr / total
    return arr


def wrap_phase(values: np.ndarray | float) -> np.ndarray | float:
    """Wrap angles to (-pi, pi]."""
    arr = np.asarray(values, dtype=float)
    wrapped = (arr + np.pi) % (2.0 * np.pi) - np.pi
    if np.isscalar(values):
        return float(wrapped)
    return wrapped


def canonicalize_phase(theta: np.ndarray, p: np.ndarray | None = None) -> np.ndarray:
    """Remove the p-weighted mean phase so the centroid sits at zero."""
    theta_arr = np.asarray(theta, dtype=float)
    if p is None:
        offset = float(np.mean(theta_arr))
    else:
        p_arr = normalize_probabilities(np.asarray(p, dtype=float))
        offset = float(np.dot(p_arr, theta_arr))
    return np.asarray(wrap_phase(theta_arr - offset), dtype=float)


def phase_coherence(state) -> float:
    """Return the magnitude of the p-weighted phase phasor."""
    p = normalize_probabilities(np.asarray(state.p, dtype=float))
    theta = canonicalize_phase(np.asarray(state.theta, dtype=float), p)
    return float(abs(np.sum(p * np.exp(1j * theta))))


def _projective_derivative(psi0: np.ndarray, derivative: np.ndarray) -> np.ndarray:
    """Project *derivative* onto the orthogonal complement of *psi0*."""
    return derivative - psi0 * np.vdot(psi0, derivative)


def projective_metric_trace_and_curvature(
    psi0: np.ndarray,
    psi_u_plus: np.ndarray,
    psi_u_minus: np.ndarray,
    psi_v_plus: np.ndarray,
    psi_v_minus: np.ndarray,
    du: float,
    dv: float,
) -> tuple[float, float]:
    """Five-point central-difference projective metric trace and curvature."""
    dpsi_u = (np.asarray(psi_u_plus, dtype=complex) - np.asarray(psi_u_minus, dtype=complex)) / (2.0 * du)
    dpsi_v = (np.asarray(psi_v_plus, dtype=complex) - np.asarray(psi_v_minus, dtype=complex)) / (2.0 * dv)
    q_u = _projective_derivative(np.asarray(psi0, dtype=complex), dpsi_u)
    q_v = _projective_derivative(np.asarray(psi0, dtype=complex), dpsi_v)
    g_uu = float(np.real(np.vdot(q_u, q_u)))
    g_vv = float(np.real(np.vdot(q_v, q_v)))
    metric_trace = g_uu + g_vv
    c_uv = np.vdot(q_u, q_v)
    curvature = float(2.0 * np.imag(c_uv))
    return metric_trace, curvature

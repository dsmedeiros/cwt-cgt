"""Refinement metrics for ranking candidate runs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

import numpy as np


def refine_score(
    fidelities: Sequence[float],
    *,
    curvature: Sequence[float] | None = None,
    target: float = 0.97,
    stability_weight: float = 0.35,
    curvature_weight: float = 0.25,
) -> float:
    """Aggregate fidelity and curvature statistics into a scalar score.

    The metric rewards improvements over ``target`` while penalising large
    variance and curvature excursions.  Inputs are clipped to sensible bounds
    and the result is constrained to the unit interval for convenient
    downstream consumption.
    """

    fidelity_arr = np.asarray(fidelities, dtype=float)
    if fidelity_arr.ndim != 1:
        raise ValueError("fidelities must be a one-dimensional sequence.")
    if fidelity_arr.size == 0:
        raise ValueError("fidelities must not be empty.")

    fidelity_arr = np.clip(fidelity_arr, 0.0, 1.0)

    mean_gain = np.mean(fidelity_arr) - float(target)
    spread = float(np.std(fidelity_arr))
    stability_term = np.exp(-spread)

    curvature_term = 1.0
    if curvature is not None:
        curvature_arr = np.asarray(curvature, dtype=float)
        if curvature_arr.ndim != 1:
            raise ValueError("curvature must be one-dimensional when provided.")
        if curvature_arr.size not in {0, fidelity_arr.size}:
            raise ValueError("curvature must match fidelities in length.")
        if curvature_arr.size:
            curvature_term = np.exp(-np.mean(np.abs(curvature_arr)))

    improvement_term = 1.0 / (1.0 + np.exp(-8.0 * mean_gain))

    # Combine the contributions.  The remainder of the weight emphasises raw
    # improvement after accounting for the explicit stability and curvature
    # penalties.
    base_weight = 1.0 - float(stability_weight) - float(curvature_weight)
    base_weight = max(base_weight, 0.0)

    score = (
        base_weight * improvement_term
        + float(stability_weight) * stability_term
        + float(curvature_weight) * curvature_term
    )

    return float(np.clip(score, 0.0, 1.0))


def geom_score(
    tr_g: float,
    det_g: float,
    omega: float,
    alpha: float = 1.0,
    beta: float = 0.2,
    gamma: float = 0.5,
) -> float:
    """Return a scalar score summarising geometric diagnostics."""

    from math import sqrt

    det_term = sqrt(max(det_g, 0.0))
    return float(alpha) * float(tr_g) + float(beta) * det_term + float(gamma) * abs(float(omega))


def _normalise_state(state: np.ndarray, *, eps: float = 1e-12) -> np.ndarray:
    """Return ``state`` flattened, complex128, and L2-normalised."""

    arr = np.asarray(state, dtype=np.complex128).reshape(-1)
    norm = float(np.linalg.norm(arr))
    if not np.isfinite(norm) or norm <= eps:
        raise ValueError("State vector must have non-zero finite norm.")
    return arr / norm


def metric_tensor_tile(
    Psi0: np.ndarray,
    Psi_i: np.ndarray,
    Psi_j: np.ndarray,
    *,
    delta_i: float,
    delta_j: float,
    eps: float = 1e-12,
) -> np.ndarray:
    """Estimate the two-parameter metric tensor from a plaquette of states."""

    if delta_i == 0.0 or not np.isfinite(delta_i):
        raise ValueError("delta_i must be a finite, non-zero value.")
    if delta_j == 0.0 or not np.isfinite(delta_j):
        raise ValueError("delta_j must be a finite, non-zero value.")
    if eps <= 0.0:
        raise ValueError("eps must be strictly positive.")

    psi0 = _normalise_state(Psi0, eps=eps)
    psi_i = _normalise_state(Psi_i, eps=eps)
    psi_j = _normalise_state(Psi_j, eps=eps)

    delta_vec_i = (psi_i - psi0) / float(delta_i)
    delta_vec_j = (psi_j - psi0) / float(delta_j)

    proj_i = delta_vec_i - psi0 * np.vdot(psi0, delta_vec_i)
    proj_j = delta_vec_j - psi0 * np.vdot(psi0, delta_vec_j)

    g_ii = float(np.real(np.vdot(proj_i, proj_i)))
    g_jj = float(np.real(np.vdot(proj_j, proj_j)))
    g_ij = float(np.real(np.vdot(proj_i, proj_j)))

    return np.array([[g_ii, g_ij], [g_ij, g_jj]], dtype=float)


def berry_curvature_tile(
    Psi0: np.ndarray,
    Psi_i: np.ndarray,
    Psi_j: np.ndarray,
    Psi_ij: np.ndarray,
    *,
    delta_i: float,
    delta_j: float,
    eps: float = 1e-12,
) -> float:
    """Estimate the Berry-like curvature on a two-parameter plaquette."""

    if delta_i == 0.0 or not np.isfinite(delta_i):
        raise ValueError("delta_i must be a finite, non-zero value.")
    if delta_j == 0.0 or not np.isfinite(delta_j):
        raise ValueError("delta_j must be a finite, non-zero value.")
    if eps <= 0.0:
        raise ValueError("eps must be strictly positive.")

    psi0 = _normalise_state(Psi0, eps=eps)
    psi_i = _normalise_state(Psi_i, eps=eps)
    psi_j = _normalise_state(Psi_j, eps=eps)
    psi_ij = _normalise_state(Psi_ij, eps=eps)

    overlaps: Mapping[str, complex] = {
        "0i": np.vdot(psi0, psi_i),
        "iij": np.vdot(psi_i, psi_ij),
        "ijj": np.vdot(psi_ij, psi_j),
        "j0": np.vdot(psi_j, psi0),
    }

    wilson = 1.0 + 0.0j
    for key, value in overlaps.items():
        if abs(value) <= eps or not np.isfinite(value.real) or not np.isfinite(value.imag):
            return 0.0
        wilson *= value / abs(value)

    plaquette_phase = float(np.angle(wilson))
    return plaquette_phase / (float(delta_i) * float(delta_j))


def placeholder_refine_score(*args, **kwargs) -> float:
    """Compatibility shim delegating to :func:`refine_score`."""

    return refine_score(*args, **kwargs)


__all__ = [
    "berry_curvature_tile",
    "geom_score",
    "metric_tensor_tile",
    "refine_score",
    "placeholder_refine_score",
]

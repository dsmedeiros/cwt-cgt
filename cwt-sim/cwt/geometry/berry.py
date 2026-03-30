"""Berry-phase loop flux and signed-area utilities for CGT.

Pure geometry functions — no imports from layers/, orchestrator/,
experiments/, or baselines/ (invariant GEOM-001).
"""

from __future__ import annotations

from typing import Iterable

import numpy as np

from .coherence import canonicalize_phase, normalize_probabilities


def psi_from_parts(p: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Build a normalised wavefunction from probability and phase arrays."""
    import math

    p_arr = normalize_probabilities(np.asarray(p, dtype=float))
    theta_arr = canonicalize_phase(np.asarray(theta, dtype=float), p_arr)
    psi = np.sqrt(p_arr) * np.exp(1j * theta_arr)
    norm = np.linalg.norm(psi)
    if norm <= 0.0:
        return np.full(p_arr.shape, 1.0 / math.sqrt(p_arr.size), dtype=complex)
    return psi / norm


def psi_from_state(state) -> np.ndarray:
    """Build a normalised wavefunction from a branch state."""
    return psi_from_parts(state.p, state.theta)


def berry_loop_flux(states: Iterable) -> float:
    """Discrete Berry phase around a closed loop of branch states."""
    psi_states = [psi_from_state(state) for state in states]
    if len(psi_states) < 2:
        return 0.0
    prod = 1.0 + 0.0j
    for a, b in zip(psi_states[:-1], psi_states[1:]):
        ov = np.vdot(a, b)
        mag = abs(ov)
        if mag <= 1e-12:
            continue
        prod *= ov / mag
    return float(np.angle(prod))


def polygon_signed_area(path: list[tuple[float, float]]) -> float:
    """Signed area of a polygon given as a list of (x, y) vertices."""
    if len(path) < 3:
        return 0.0
    area = 0.0
    for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
        area += x0 * y1 - x1 * y0
    return 0.5 * area

"""Branch-distance metric in (p, theta, kernel) space.

Pure geometry — no imports from layers/, orchestrator/, experiments/,
or baselines/ (invariant GEOM-001).
"""

from __future__ import annotations

import math

import numpy as np

from .coherence import canonicalize_phase, normalize_probabilities, wrap_phase


def branch_distance(
    state_a,
    state_b,
    p_weight: float = 1.0,
    theta_weight: float = 0.55,
    kernel_weight: float = 0.15,
) -> float:
    """Weighted distance between two branch states."""
    p_a = normalize_probabilities(np.asarray(state_a.p, dtype=float))
    p_b = normalize_probabilities(np.asarray(state_b.p, dtype=float))
    p_term = float(np.linalg.norm(p_a - p_b, ord=1))

    theta_a = canonicalize_phase(np.asarray(state_a.theta, dtype=float), p_a)
    theta_b = canonicalize_phase(np.asarray(state_b.theta, dtype=float), p_b)
    theta_diff = np.asarray(wrap_phase(theta_a - theta_b), dtype=float)
    theta_term = float(
        np.linalg.norm(theta_diff)
        / max(math.sqrt(theta_diff.size) * np.pi, 1e-12)
    )

    kernel_term = 0.0
    if (
        getattr(state_a, "kernel", None) is not None
        and getattr(state_b, "kernel", None) is not None
    ):
        ka = np.asarray(state_a.kernel, dtype=float)
        kb = np.asarray(state_b.kernel, dtype=float)
        kernel_term = float(np.linalg.norm(ka - kb) / max(ka.size, 1))

    return p_weight * p_term + theta_weight * theta_term + kernel_weight * kernel_term

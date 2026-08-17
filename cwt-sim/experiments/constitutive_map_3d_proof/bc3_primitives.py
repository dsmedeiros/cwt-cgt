"""Frozen experiment-local Benchmark-C C0 primitives and readout."""

from __future__ import annotations

import math
from fractions import Fraction

import numpy as np

from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract


def frozen_c0_branch(
    u: float,
    v: float,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate only the reviewed local C0 formulas, with no core helper."""

    if not float(contract.bc3_u_bounds[0]) <= u <= float(contract.bc3_u_bounds[1]):
        raise ValueError("u leaves the frozen C0 box")
    if not float(contract.bc3_v_bounds[0]) <= v <= float(contract.bc3_v_bounds[1]):
        raise ValueError("v leaves the frozen C0 box")
    k_plus = 0.18 + 0.10 * u
    k_minus = 0.18 - 0.10 * u
    kernel = np.zeros((3, 3), dtype=float)
    for node in range(3):
        kernel[node, node] = 1.0 - k_plus - k_minus
        kernel[node, (node + 1) % 3] = k_plus
        kernel[node, (node - 1) % 3] = k_minus
    logits = np.asarray(
        (
            0.85 * u + 0.50 * v,
            -0.70 * u + 0.35 * u * v,
            -0.55 * v - 0.25 * u * v,
        ),
        dtype=float,
    )
    weights = np.exp(logits)
    probability = weights / np.sum(weights)
    phase = 0.70 * v + 0.45 * u * v + 0.15 * u
    theta = np.asarray((phase, 0.0, -phase), dtype=float)
    return probability, theta, kernel


def frozen_circulation_readout(
    probability: np.ndarray,
    theta: np.ndarray,
    kernel: np.ndarray,
    gain: float,
) -> float:
    """Evaluate the exact geometry-blind directed three-node readout."""

    p = np.asarray(probability, dtype=float)
    phase = np.asarray(theta, dtype=float)
    transition = np.asarray(kernel, dtype=float)
    if p.shape != (3,) or phase.shape != (3,) or transition.shape != (3, 3):
        raise ValueError("BC3 primitive readout shapes must be (3,), (3,), and (3,3)")
    phase_factor = 1.0 + float(gain) * np.sin(phase[None, :] - phase[:, None])
    current = p[:, None] * transition * phase_factor
    return float(
        current[0, 1] + current[1, 2] + current[2, 0] - current[1, 0] - current[2, 1] - current[0, 2]
    )


def frozen_phase_and_coefficient_arrays(
    u_values: np.ndarray,
    v_values: np.ndarray,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> tuple[np.ndarray, np.ndarray]:
    """Vectorize the exact local branch phase and centered-readout coefficient."""

    u = np.asarray(u_values, dtype=float)
    v = np.asarray(v_values, dtype=float)
    if u.shape != v.shape or u.ndim != 1:
        raise ValueError("BC3 primitive control arrays must be equal one-dimensional shapes")
    if (
        np.min(u) < float(contract.bc3_u_bounds[0])
        or np.max(u) > float(contract.bc3_u_bounds[1])
        or np.min(v) < float(contract.bc3_v_bounds[0])
        or np.max(v) > float(contract.bc3_v_bounds[1])
    ):
        raise ValueError("BC3 primitive control arrays leave the frozen C0 box")
    logits = np.column_stack(
        (
            0.85 * u + 0.50 * v,
            -0.70 * u + 0.35 * u * v,
            -0.55 * v - 0.25 * u * v,
        )
    )
    weights = np.exp(logits)
    probability = weights / np.sum(weights, axis=1, keepdims=True)
    k_plus = 0.18 + 0.10 * u
    k_minus = 0.18 - 0.10 * u
    coefficient = k_plus * probability[:, 2] + k_minus * probability[:, 0]
    phase = 0.70 * v + 0.45 * u * v + 0.15 * u
    return phase, coefficient


def frozen_centered_readout(
    actual_phase: float,
    branch_phase: float,
    coefficient: float,
    gain: float,
) -> float:
    """Evaluate J(actual)-J(branch) after the equilibrium-independent J0 cancels."""

    return float(
        gain
        * (
            (coefficient - 0.36) * (math.sin(actual_phase) - math.sin(branch_phase))
            + coefficient * (math.sin(2.0 * actual_phase) - math.sin(2.0 * branch_phase))
        )
    )


def analytic_box_certificate(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Prove clip/wrap inactivity over the whole box with exact rationals."""

    u_min, u_max = contract.bc3_u_bounds
    v_min, v_max = contract.bc3_v_bounds
    k_plus_bounds = (
        Fraction(9, 50) + Fraction(1, 10) * u_min,
        Fraction(9, 50) + Fraction(1, 10) * u_max,
    )
    k_minus_bounds = (
        Fraction(9, 50) - Fraction(1, 10) * u_max,
        Fraction(9, 50) - Fraction(1, 10) * u_min,
    )
    clip_lower = Fraction(1, 25)
    clip_upper = Fraction(2, 5)
    clip_margin = min(
        k_plus_bounds[0] - clip_lower,
        k_minus_bounds[0] - clip_lower,
        clip_upper - k_plus_bounds[1],
        clip_upper - k_minus_bounds[1],
    )
    phase_min = Fraction(7, 10) * v_min + Fraction(9, 20) * u_min * v_min + Fraction(3, 20) * u_min
    phase_max = Fraction(7, 10) * v_max + Fraction(9, 20) * u_max * v_max + Fraction(3, 20) * u_max
    pi_lower = Fraction(333, 106)
    wrap_margin_lower = pi_lower - phase_max
    return {
        "proof_kind": "exact_monotone_rational_box_bounds",
        "k_plus_bounds": [str(item) for item in k_plus_bounds],
        "k_minus_bounds": [str(item) for item in k_minus_bounds],
        "clip_interval": [str(clip_lower), str(clip_upper)],
        "clip_margin": str(clip_margin),
        "phase_bounds": [str(phase_min), str(phase_max)],
        "pi_lower_bound": str(pi_lower),
        "wrap_margin_lower_bound": str(wrap_margin_lower),
        "clip_inactive_everywhere": clip_margin > 0,
        "wrap_inactive_everywhere": wrap_margin_lower > 0,
        "branch_construction": "frozen_experiment_local_exact_C0_formulas",
        "auxiliary_or_continuation_branch_present": False,
        "live_core_sample_comparison_is_acceptance": False,
    }

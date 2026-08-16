"""Geometry-blind response calculation for the benchmark-C current trace.

This module deliberately has no curvature, flux, or orientation inputs.  It
implements the same phase-relaxation and circulation-current trace used by the
legacy benchmark-C loop protocol, then exposes both the unchanged legacy mean
and its fixed-tick cycle sum.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np


@dataclass(frozen=True)
class ResponseTrace:
    """Deterministic response trace in fixed current-tick units."""

    q_samples: np.ndarray
    actual_circulation_samples: np.ndarray
    branch_circulation_samples: np.ndarray
    discrete_cycle_sum_surrogate: float
    legacy_mean_response: float
    raw_mean_circulation: float
    branch_mean_circulation: float
    max_lag_recurrence_residual: float
    max_abs_phase_increment: float
    max_abs_lag_error: float
    path_length: int


def _wrap_phase(values: np.ndarray | float) -> np.ndarray | float:
    arr = np.asarray(values, dtype=float)
    wrapped = (arr + np.pi) % (2.0 * np.pi) - np.pi
    if np.isscalar(values):
        return float(wrapped)
    return wrapped


def circulation_current(
    p: np.ndarray,
    theta: np.ndarray,
    kernel: np.ndarray,
    current_phase_gain: float,
) -> float:
    """Return the exact directed three-node circulation used by benchmark C."""

    p_arr = np.asarray(p, dtype=float)
    theta_arr = np.asarray(theta, dtype=float)
    kernel_arr = np.asarray(kernel, dtype=float)
    if p_arr.shape != (3,) or theta_arr.shape != (3,) or kernel_arr.shape != (3, 3):
        raise ValueError("benchmark-C circulation requires p/theta/kernel shapes (3,), (3,), (3, 3)")
    phase_factor = 1.0 + float(current_phase_gain) * np.sin(theta_arr[None, :] - theta_arr[:, None])
    current = p_arr[:, None] * kernel_arr * phase_factor
    return float(
        current[0, 1] + current[1, 2] + current[2, 0] - current[1, 0] - current[2, 1] - current[0, 2]
    )


def circulation_phase_gradient(
    p: np.ndarray,
    theta: np.ndarray,
    kernel: np.ndarray,
    current_phase_gain: float,
) -> np.ndarray:
    """Return the exact gradient of circulation with respect to node phases."""

    p_arr = np.asarray(p, dtype=float)
    theta_arr = np.asarray(theta, dtype=float)
    kernel_arr = np.asarray(kernel, dtype=float)
    if p_arr.shape != (3,) or theta_arr.shape != (3,) or kernel_arr.shape != (3, 3):
        raise ValueError("benchmark-C circulation requires p/theta/kernel shapes (3,), (3,), (3, 3)")

    gradient = np.zeros(3, dtype=float)
    signed_edges = (
        (+1.0, 0, 1),
        (+1.0, 1, 2),
        (+1.0, 2, 0),
        (-1.0, 1, 0),
        (-1.0, 2, 1),
        (-1.0, 0, 2),
    )
    for sign, source, target in signed_edges:
        coefficient = (
            sign
            * p_arr[source]
            * kernel_arr[source, target]
            * float(current_phase_gain)
            * np.cos(theta_arr[target] - theta_arr[source])
        )
        gradient[source] -= coefficient
        gradient[target] += coefficient
    return gradient


def calculate_response_trace(
    branch_states: Sequence[Any],
    path: Sequence[tuple[float, float]],
    phase_relaxation: float,
    current_phase_gain: float,
) -> ResponseTrace:
    """Calculate the fixed-tick current response without geometry metadata.

    The path is accepted only to bind the response samples to the declared
    branch-state sequence and to enforce endpoint accounting.  Curvature,
    Wilson flux, signed area, and orientation labels are intentionally absent.
    """

    alpha = float(phase_relaxation)
    gain = float(current_phase_gain)
    if not 0.0 < alpha <= 1.0:
        raise ValueError("phase_relaxation must lie in (0, 1]")
    if not branch_states:
        raise ValueError("branch_states must not be empty")
    if len(branch_states) != len(path):
        raise ValueError("branch_states and path must have the same length")

    first_theta = np.asarray(branch_states[0].theta, dtype=float)
    theta_actual = first_theta.copy()
    previous_branch_theta = first_theta.copy()
    previous_error = np.zeros_like(first_theta)
    relaxation_memory = 1.0 - alpha

    q_samples: list[float] = []
    actual_samples: list[float] = []
    branch_samples: list[float] = []
    recurrence_residuals: list[float] = []
    phase_increments: list[float] = []
    lag_errors: list[float] = []

    for index, state in enumerate(branch_states):
        theta_branch = np.asarray(state.theta, dtype=float)
        lag_before_update = np.asarray(_wrap_phase(theta_branch - theta_actual), dtype=float)
        theta_actual = np.asarray(
            _wrap_phase(theta_actual + alpha * lag_before_update),
            dtype=float,
        )
        error = np.asarray(_wrap_phase(theta_actual - theta_branch), dtype=float)

        if index > 0:
            delta_theta = np.asarray(
                _wrap_phase(theta_branch - previous_branch_theta),
                dtype=float,
            )
            predicted_error = relaxation_memory * previous_error - relaxation_memory * delta_theta
            recurrence_residual = np.asarray(
                _wrap_phase(error - predicted_error),
                dtype=float,
            )
            recurrence_residuals.append(float(np.max(np.abs(recurrence_residual))))
            phase_increments.append(float(np.max(np.abs(delta_theta))))

        actual = circulation_current(
            state.p,
            theta_actual,
            state.kernel,
            gain,
        )
        branch = circulation_current(
            state.p,
            theta_branch,
            state.kernel,
            gain,
        )
        actual_samples.append(actual)
        branch_samples.append(branch)
        q_samples.append(actual - branch)
        lag_errors.append(float(np.max(np.abs(error))))
        previous_branch_theta = theta_branch
        previous_error = error

    q_array = np.asarray(q_samples, dtype=float)
    actual_array = np.asarray(actual_samples, dtype=float)
    branch_array = np.asarray(branch_samples, dtype=float)
    return ResponseTrace(
        q_samples=q_array,
        actual_circulation_samples=actual_array,
        branch_circulation_samples=branch_array,
        discrete_cycle_sum_surrogate=float(np.sum(q_array)),
        legacy_mean_response=float(np.mean(actual_array) - np.mean(branch_array)),
        raw_mean_circulation=float(np.mean(actual_array)),
        branch_mean_circulation=float(np.mean(branch_array)),
        max_lag_recurrence_residual=max(recurrence_residuals, default=0.0),
        max_abs_phase_increment=max(phase_increments, default=0.0),
        max_abs_lag_error=max(lag_errors, default=0.0),
        path_length=len(path),
    )

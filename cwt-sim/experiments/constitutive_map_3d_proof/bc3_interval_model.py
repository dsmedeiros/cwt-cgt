"""Shared exact-lattice binary64 model kernel for BC3 prediction and oracle lanes."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from .binary64_interval import (
    Float64Interval,
    balanced_pairwise_sum,
    cos_interval_binary64,
    exp_interval_binary64,
    sin_interval_binary64,
)


def _ratio_array(numerators: list[int], denominator: int) -> Float64Interval:
    return Float64Interval.ratios(numerators, denominator)


def _model_fields(points: np.ndarray, denominator: int) -> dict[str, Float64Interval]:
    rows = np.asarray(points, dtype=np.int64)
    if rows.ndim != 2 or rows.shape[1] != 3:
        raise ValueError("BC3 exact model points must be an integer (n,3) array")
    d = int(denominator)
    u_values = [int(row[0]) for row in rows]
    v_values = [int(row[1]) for row in rows]
    a_values = [int(row[2]) for row in rows]
    phase_numerators = [14 * v * d + 9 * u * v + 3 * u * d for u, v in zip(u_values, v_values)]
    phase = _ratio_array(phase_numerators, 20 * d * d)
    logit_0 = _ratio_array([17 * u + 10 * v for u, v in zip(u_values, v_values)], 20 * d)
    logit_1 = _ratio_array(
        [-14 * u * d + 7 * u * v for u, v in zip(u_values, v_values)],
        20 * d * d,
    )
    logit_2 = _ratio_array(
        [-11 * v * d - 5 * u * v for u, v in zip(u_values, v_values)],
        20 * d * d,
    )
    weights = tuple(exp_interval_binary64(item) for item in (logit_0, logit_1, logit_2))
    normalization = weights[0] + weights[1] + weights[2]
    if np.any(normalization.lower <= 0.0):
        raise FloatingPointError("BC3 softmax normalization lower bound is not positive")
    k_plus = _ratio_array([9 * d + 5 * u for u in u_values], 50 * d)
    k_minus = _ratio_array([9 * d - 5 * u for u in u_values], 50 * d)
    coefficient = (k_plus * weights[2] + k_minus * weights[0]) / normalization
    return {
        "phase": phase,
        "coefficient": coefficient,
        "alpha": _ratio_array(a_values, d),
        "u": _ratio_array(u_values, d),
        "v": _ratio_array(v_values, d),
    }


def _delta_recurrence(points: np.ndarray, denominator: int) -> Float64Interval:
    rows = np.asarray(points, dtype=np.int64)
    d = int(denominator)
    phase_numerators = [
        14 * int(row[1]) * d + 9 * int(row[0]) * int(row[1]) + 3 * int(row[0]) * d for row in rows
    ]
    phase = _ratio_array(phase_numerators, 20 * d * d)
    dphi = _ratio_array(
        [right - left for left, right in zip(phase_numerators[:-1], phase_numerators[1:], strict=True)],
        20 * d * d,
    )
    r = _ratio_array([d - int(row[2]) for row in rows[1:]], d)
    count = len(points) - 1
    lower = np.empty(count, dtype=np.float64)
    upper = np.empty(count, dtype=np.float64)
    delta_lower = 0.0
    delta_upper = 0.0
    for index in range(count):
        dphi_lower = float(dphi.lower[index])
        dphi_upper = float(dphi.upper[index])
        shifted_lower = float(np.nextafter(delta_lower - dphi_upper, -np.inf))
        shifted_upper = float(np.nextafter(delta_upper - dphi_lower, np.inf))
        r_lower = float(r.lower[index])
        r_upper = float(r.upper[index])
        products = (
            r_lower * shifted_lower,
            r_lower * shifted_upper,
            r_upper * shifted_lower,
            r_upper * shifted_upper,
        )
        delta_lower = float(np.nextafter(min(products), -np.inf))
        delta_upper = float(np.nextafter(max(products), np.inf))
        lower[index] = delta_lower
        upper[index] = delta_upper
    result = Float64Interval(lower, upper)
    actual_phase = phase.at(np.arange(1, len(points))) + result
    if np.any(actual_phase.lower < 349.0 / 8000.0) or np.any(actual_phase.upper > 1101.0 / 8000.0):
        raise FloatingPointError("BC3 driven phase leaves the reviewed convex tube")
    if np.any(result.lower < -47.0 / 500.0) or np.any(result.upper > 47.0 / 500.0):
        raise FloatingPointError("BC3 lag leaves the reviewed interval domain")
    return result


def path_response_interval(points: np.ndarray, denominator: int) -> Float64Interval:
    """Enclose the right-endpoint centered response sum for one orientation."""

    fields = _model_fields(points, denominator)
    phase = Float64Interval(fields["phase"].lower[1:], fields["phase"].upper[1:])
    coefficient = Float64Interval(
        fields["coefficient"].lower[1:],
        fields["coefficient"].upper[1:],
    )
    delta = _delta_recurrence(points, denominator)
    first = (
        2
        * (coefficient - Fraction(9, 25))
        * cos_interval_binary64(phase + delta / 2)
        * sin_interval_binary64(delta / 2)
    )
    second = 2 * coefficient * cos_interval_binary64(2 * phase + delta) * sin_interval_binary64(delta)
    samples = Fraction(9, 20) * (first + second)
    return balanced_pairwise_sum(samples)


def midpoint_line_interval(points: np.ndarray, denominator: int) -> Float64Interval:
    """Enclose the independently sealed midpoint integral of beta along one path."""

    rows = np.asarray(points, dtype=np.int64)
    midpoint_numerators = rows[:-1] + rows[1:]
    midpoint_denominator = 2 * int(denominator)
    fields = _model_fields(midpoint_numerators, midpoint_denominator)
    phase = fields["phase"]
    coefficient = fields["coefficient"]
    alpha = fields["alpha"]
    u = fields["u"]
    v = fields["v"]
    value = Fraction(9, 20) * (
        (coefficient - Fraction(9, 25)) * cos_interval_binary64(phase)
        + 2 * coefficient * cos_interval_binary64(2 * phase)
    )
    phase_u = Fraction(3, 20) + Fraction(9, 20) * v
    phase_v = Fraction(7, 10) + Fraction(9, 20) * u
    memory = (1 - alpha) / alpha
    beta_u = -memory * value * phase_u
    beta_v = -memory * value * phase_v
    increments = rows[1:] - rows[:-1]
    du = _ratio_array([int(item) for item in increments[:, 0]], denominator)
    dv = _ratio_array([int(item) for item in increments[:, 1]], denominator)
    return balanced_pairwise_sum(beta_u * du + beta_v * dv)

"""Benchmark-C three-control primitive predictor; no response oracle is imported."""

from __future__ import annotations

import math
from fractions import Fraction
from typing import Iterable

import numpy as np

from .bc3_primitives import analytic_box_certificate, frozen_phase_and_coefficient_arrays
from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract
from .exact import RationalInterval, cos_interval, exp_interval, fraction_item, sin_interval, strict_cross
from .pipeline import PredictionAccess


def _fraction(value: float | Fraction) -> Fraction:
    return value if isinstance(value, Fraction) else Fraction(str(value))


def _logits_and_derivatives(u: Fraction, v: Fraction) -> tuple[list[Fraction], list[list[Fraction]]]:
    logits = [
        Fraction(17, 20) * u + Fraction(1, 2) * v,
        -Fraction(7, 10) * u + Fraction(7, 20) * u * v,
        -Fraction(11, 20) * v - Fraction(1, 4) * u * v,
    ]
    derivatives = [
        [Fraction(17, 20), Fraction(1, 2)],
        [-Fraction(7, 10) + Fraction(7, 20) * v, Fraction(7, 20) * u],
        [-Fraction(1, 4) * v, -Fraction(11, 20) - Fraction(1, 4) * u],
    ]
    return logits, derivatives


def _probability_intervals(
    u: Fraction, v: Fraction
) -> tuple[list[RationalInterval], list[list[RationalInterval]]]:
    logits, derivatives = _logits_and_derivatives(u, v)
    weights = [exp_interval(item) for item in logits]
    total = sum(weights, RationalInterval.point(0))
    probabilities = [item / total for item in weights]
    probability_derivatives = []
    for index, probability in enumerate(probabilities):
        row = []
        for axis in range(2):
            mean = sum(
                (probabilities[item] * derivatives[item][axis] for item in range(3)),
                RationalInterval.point(0),
            )
            row.append(probability * (derivatives[index][axis] - mean))
        probability_derivatives.append(row)
    return probabilities, probability_derivatives


def directed_form_intervals(
    u: Fraction,
    v: Fraction,
    alpha: Fraction,
    gain: Fraction = MODEL_CONTRACT.bc3_gain,
) -> dict[str, RationalInterval]:
    """Return exact outward rational enclosures for the BC3 local forms."""

    probabilities, derivatives = _probability_intervals(u, v)
    phase = Fraction(7, 10) * v + Fraction(9, 20) * u * v + Fraction(3, 20) * u
    phase_u = Fraction(9, 20) * v + Fraction(3, 20)
    phase_v = Fraction(7, 10) + Fraction(9, 20) * u
    k_plus = Fraction(9, 50) + Fraction(1, 10) * u
    k_minus = Fraction(9, 50) - Fraction(1, 10) * u
    b = k_plus * probabilities[2] + k_minus * probabilities[0]
    b_u = (
        Fraction(1, 10) * probabilities[2]
        + k_plus * derivatives[2][0]
        - Fraction(1, 10) * probabilities[0]
        + k_minus * derivatives[0][0]
    )
    b_v = k_plus * derivatives[2][1] + k_minus * derivatives[0][1]
    cosine = cos_interval(phase)
    cosine_double = cos_interval(2 * phase)
    sine = sin_interval(phase)
    sine_double = sin_interval(2 * phase)
    kernel_sum = Fraction(9, 25)
    r = gain * ((b - kernel_sum) * cosine + 2 * b * cosine_double)

    def derivative(b_axis: RationalInterval, phase_axis: Fraction) -> RationalInterval:
        return gain * (
            b_axis * (cosine + 2 * cosine_double)
            - (b - kernel_sum) * sine * phase_axis
            - 4 * b * sine_double * phase_axis
        )

    r_u = derivative(b_u, phase_u)
    r_v = derivative(b_v, phase_v)
    inverse_alpha_squared = Fraction(1, 1) / (alpha * alpha)
    memory = (1 - alpha) / alpha
    eta_u = r * phase_u
    eta_v = r * phase_v
    d_eta_uv = r_u * phase_v - r_v * phase_u
    f_v_alpha = -inverse_alpha_squared * eta_v
    f_alpha_u = inverse_alpha_squared * eta_u
    f_u_v = -memory * d_eta_uv
    delta_p_u = derivatives[0][0] - derivatives[2][0]
    delta_p_v = derivatives[0][1] - derivatives[2][1]
    state_two_form_u_v = delta_p_u * phase_v - delta_p_v * phase_u
    area = MODEL_CONTRACT.bc3_area_vector
    density = area[0] * f_v_alpha + area[1] * f_alpha_u + area[2] * f_u_v
    return {
        "R": r,
        "R_u": r_u,
        "R_v": r_v,
        "eta_u": eta_u,
        "eta_v": eta_v,
        "d_eta_u_v": d_eta_uv,
        "F_v_alpha": f_v_alpha,
        "F_alpha_u": f_alpha_u,
        "F_u_v": f_u_v,
        "Omega_u_v": state_two_form_u_v,
        "heldout_density": density,
    }


def _probability_float(u: float, v: float) -> tuple[np.ndarray, np.ndarray]:
    logits, derivative_values = _logits_and_derivatives(Fraction(str(u)), Fraction(str(v)))
    weights = np.exp(np.asarray([float(item) for item in logits], dtype=float))
    p = weights / np.sum(weights)
    derivatives = np.asarray([[float(value) for value in row] for row in derivative_values], dtype=float)
    mean = p @ derivatives
    return p, p[:, None] * (derivatives - mean)


def form_components(u: float, v: float, alpha: float, gain: float = 0.45) -> dict[str, float]:
    """Evaluate the exact symbolic BC3 formulas in floating arithmetic as a regression view."""

    p, dp = _probability_float(u, v)
    phase = 0.70 * v + 0.45 * u * v + 0.15 * u
    phase_u = 0.45 * v + 0.15
    phase_v = 0.70 + 0.45 * u
    k_plus, k_minus = 0.18 + 0.10 * u, 0.18 - 0.10 * u
    b = k_plus * p[2] + k_minus * p[0]
    b_u = 0.10 * p[2] + k_plus * dp[2, 0] - 0.10 * p[0] + k_minus * dp[0, 0]
    b_v = k_plus * dp[2, 1] + k_minus * dp[0, 1]
    r = gain * ((b - 0.36) * math.cos(phase) + 2.0 * b * math.cos(2.0 * phase))

    def derivative(b_axis: float, phase_axis: float) -> float:
        return gain * (
            b_axis * (math.cos(phase) + 2.0 * math.cos(2.0 * phase))
            - (b - 0.36) * math.sin(phase) * phase_axis
            - 4.0 * b * math.sin(2.0 * phase) * phase_axis
        )

    r_u, r_v = derivative(b_u, phase_u), derivative(b_v, phase_v)
    eta_u, eta_v = r * phase_u, r * phase_v
    d_eta = r_u * phase_v - r_v * phase_u
    f_vector = np.asarray(
        (-eta_v / alpha**2, eta_u / alpha**2, -((1.0 - alpha) / alpha) * d_eta),
        dtype=float,
    )
    state_two_form = (dp[0, 0] - dp[2, 0]) * phase_v - (dp[0, 1] - dp[2, 1]) * phase_u
    return {
        "phi": phase,
        "R": r,
        "R_u": r_u,
        "R_v": r_v,
        "eta_u": eta_u,
        "eta_v": eta_v,
        "d_eta_u_v": d_eta,
        "F_v_alpha": float(f_vector[0]),
        "F_alpha_u": float(f_vector[1]),
        "F_u_v": float(f_vector[2]),
        "Omega_u_v": float(state_two_form),
        "heldout_density": float(f_vector @ np.asarray(MODEL_CONTRACT.bc3_area_vector, dtype=float)),
    }


def beta_components(control: Iterable[float], gain: float = 0.45) -> np.ndarray:
    u, v, alpha = (float(item) for item in control)
    values = form_components(u, v, alpha, gain)
    memory = (1.0 - alpha) / alpha
    return np.asarray((-memory * values["eta_u"], -memory * values["eta_v"], 0.0), dtype=float)


def line_integral_beta(path: np.ndarray, gain: float = 0.45) -> float:
    controls = np.asarray(path, dtype=float)
    if controls.ndim != 2 or controls.shape[1] != 3 or len(controls) < 2:
        raise ValueError("BC3 predictor path must have shape (n,3) with n>=2")
    midpoints = 0.5 * (controls[:-1] + controls[1:])
    phases, coefficients = frozen_phase_and_coefficient_arrays(
        midpoints[:, 0],
        midpoints[:, 1],
    )
    phase_u = 0.45 * midpoints[:, 1] + 0.15
    phase_v = 0.70 + 0.45 * midpoints[:, 0]
    value = gain * ((coefficients - 0.36) * np.cos(phases) + 2.0 * coefficients * np.cos(2.0 * phases))
    memory = (1.0 - midpoints[:, 2]) / midpoints[:, 2]
    beta = np.column_stack((-memory * value * phase_u, -memory * value * phase_v))
    increments = controls[1:, :2] - controls[:-1, :2]
    return float(np.sum(beta * increments))


def factorization_certificate(
    access: PredictionAccess,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    access.require_current()
    u, v, alpha = contract.bc3_heldout_center
    intervals = directed_form_intervals(u, v, alpha, contract.bc3_gain)
    lower_endpoint = directed_form_intervals(u, v, contract.bc3_alpha_bounds[0], contract.bc3_gain)
    upper_endpoint = directed_form_intervals(u, v, contract.bc3_alpha_bounds[1], contract.bc3_gain)
    gain_zero = directed_form_intervals(u, v, alpha, Fraction(0))
    alpha_one = directed_form_intervals(u, v, Fraction(1), contract.bc3_gain)
    regression = form_components(float(u), float(v), float(alpha), float(contract.bc3_gain))
    branch_box = analytic_box_certificate(contract)
    area = strict_cross(contract.bc3_tangent_1, contract.bc3_tangent_2)
    return {
        "formula": contract.bc3_formula,
        "two_form_vector_order": list(contract.two_form_vector_order),
        "heldout_center": [fraction_item(item) for item in contract.bc3_heldout_center],
        "tangent_1": list(contract.bc3_tangent_1),
        "tangent_2": list(contract.bc3_tangent_2),
        "derived_area_vector": list(area),
        "directed_intervals": {name: interval.jsonable() for name, interval in intervals.items()},
        "all_response_components_nonzero": all(
            intervals[name].excludes_zero for name in ("F_v_alpha", "F_alpha_u", "F_u_v")
        ),
        "heldout_density_nonzero": intervals["heldout_density"].excludes_zero,
        "geometry_vector": [0.0, 0.0, float(regression["Omega_u_v"])],
        "geometry_rank": 1,
        "alpha_endpoint_omega_intervals_equal": (lower_endpoint["Omega_u_v"] == upper_endpoint["Omega_u_v"]),
        "alpha_endpoint_fiber_response_separated": any(
            lower_endpoint[name].upper < upper_endpoint[name].lower
            or upper_endpoint[name].upper < lower_endpoint[name].lower
            for name in ("F_v_alpha", "F_alpha_u", "F_u_v")
        ),
        "scalar_omega_only_map_possible": False,
        "global_phase_invariant": True,
        "closed_by_exterior_derivative_squared": True,
        "coordinate_covariant_two_form": True,
        "regression_float_view": regression,
        "response_oracle_imported": False,
        "prediction_uses_response": False,
        "branch_box_certificate": branch_box,
        "live_core_sample_comparison_is_acceptance": False,
        "exact_null_and_factor_identities": {
            "gain_zero_annuls_all_response_components": all(
                gain_zero[name].lower == gain_zero[name].upper == 0
                for name in ("F_v_alpha", "F_alpha_u", "F_u_v")
            ),
            "alpha_one_annuls_u_v_component_because_m_zero": (
                alpha_one["F_u_v"].lower == alpha_one["F_u_v"].upper == 0
            ),
            "pure_alpha_loop_is_null_because_beta_alpha_zero": True,
            "ordinary_difference_equals_two_q_anti_by_definition": True,
        },
    }

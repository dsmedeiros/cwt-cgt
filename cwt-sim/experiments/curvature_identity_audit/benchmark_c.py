"""Exact same-primitive Benchmark-C Berry and response connections."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.geometry import psi_from_parts
from cwt.geometry.curvature import curvature_tile
from experiments.independent_response_theorem.theorem import (
    projective_curvature,
    response_curvature,
)

from .contract import MODEL_CONTRACT, CurvatureAuditContract
from .exact import Jet2, fraction_item

EXPECTED_OMEGA_CENTER = Fraction(7, 48)
EXPECTED_RESPONSE_CENTER = Fraction(-222183, 2800000)
EXPECTED_QUOTIENT_CENTER = Fraction(-666549, 1225000)
EXPECTED_RESPONSE_GRADIENT = (Fraction(8541, 175000), Fraction(4561947, 56000000))
EXPECTED_OMEGA_GRADIENT = (Fraction(2933, 12000), Fraction(-581, 72000))
EXPECTED_QUOTIENT_GRADIENT = (
    Fraction(54539433, 43750000),
    Fraction(11560887, 21875000),
)
EXPECTED_J_XP_RESPONSE_CENTER = EXPECTED_RESPONSE_CENTER
EXPECTED_J_XP_RESPONSE_GRADIENT = (Fraction(-1287, 1400000), Fraction(1122147, 56000000))
EXPECTED_J_XK_RESPONSE_CENTER = Fraction(0)
EXPECTED_J_XK_RESPONSE_GRADIENT = (Fraction(1989, 40000), Fraction(2457, 40000))


def analytic_branch(u: float, v: float) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Evaluate the unclipped C0 authored branch on its interior analytic patch."""

    u_float = float(u)
    v_float = float(v)
    logits = np.asarray(
        [
            0.85 * u_float + 0.50 * v_float,
            -0.70 * u_float + 0.35 * u_float * v_float,
            -0.55 * v_float - 0.25 * u_float * v_float,
        ],
        dtype=float,
    )
    weights = np.exp(logits - np.max(logits))
    probability = weights / np.sum(weights)
    phi = 0.70 * v_float + 0.45 * u_float * v_float + 0.15 * u_float
    theta = np.asarray([phi, 0.0, -phi], dtype=float)
    clockwise = 0.18 + 0.10 * u_float
    counterclockwise = 0.18 - 0.10 * u_float
    kernel = np.zeros((3, 3), dtype=float)
    for source in range(3):
        kernel[source, source] = 1.0 - clockwise - counterclockwise
        kernel[source, (source + 1) % 3] = clockwise
        kernel[source, (source - 1) % 3] = counterclockwise
    return probability, theta, kernel


def _exact_branch_jets() -> tuple[list[Jet2], list[Jet2], Jet2, Jet2]:
    degree = 3
    u = Jet2.variable(0, degree)
    v = Jet2.variable(1, degree)
    logits = [
        Fraction(17, 20) * u + Fraction(1, 2) * v,
        Fraction(-7, 10) * u + Fraction(7, 20) * u * v,
        Fraction(-11, 20) * v + Fraction(-1, 4) * u * v,
    ]
    exponentials = [item.exp_zero_constant() for item in logits]
    normalizer = sum(exponentials, Jet2.constant(0, degree))
    probability = [item / normalizer for item in exponentials]
    phi = Fraction(7, 10) * v + Fraction(9, 20) * u * v + Fraction(3, 20) * u
    theta = [phi, Jet2.constant(0, degree), -phi]
    clockwise = Jet2.constant(Fraction(9, 50), degree) + Fraction(1, 10) * u
    counterclockwise = Jet2.constant(Fraction(9, 50), degree) - Fraction(1, 10) * u
    return probability, theta, clockwise, counterclockwise


def _exact_forms(
    alpha: Fraction = Fraction(7, 20),
    gain: Fraction = Fraction(9, 20),
) -> dict[str, Jet2]:
    """Derive A, Omega, beta, and F as exact local Taylor jets."""

    if not 0 < alpha <= 1:
        raise ValueError("alpha must lie in (0,1]")
    probability, theta, clockwise, counterclockwise = _exact_branch_jets()
    theta_u = [item.derivative(0) for item in theta]
    theta_v = [item.derivative(1) for item in theta]
    probability_u = [item.derivative(0) for item in probability]
    probability_v = [item.derivative(1) for item in probability]

    connection_u = sum(
        (probability[index] * theta_u[index] for index in range(3)),
        Jet2.constant(0),
    )
    connection_v = sum(
        (probability[index] * theta_v[index] for index in range(3)),
        Jet2.constant(0),
    )
    omega = connection_v.derivative(0) - connection_u.derivative(1)
    omega_from_tangents = sum(
        (probability_u[index] * theta_v[index] - probability_v[index] * theta_u[index] for index in range(3)),
        Jet2.constant(0),
    )

    phase_gradient = [Jet2.constant(0) for _ in range(3)]
    directional_phase_gradient = {
        component: [[Jet2.constant(0) for _ in range(3)] for _ in range(2)]
        for component in ("J_xp_dp", "J_xx_dtheta", "J_xK_dK")
    }
    edges = (
        (+1, 0, 1, clockwise),
        (+1, 1, 2, clockwise),
        (+1, 2, 0, clockwise),
        (-1, 1, 0, counterclockwise),
        (-1, 2, 1, counterclockwise),
        (-1, 0, 2, counterclockwise),
    )
    for sign, source, target, rate in edges:
        phase_difference = theta[target] - theta[source]
        cosine = phase_difference.cos_zero_constant()
        sine = phase_difference.sin_zero_constant()
        coefficient = sign * gain * probability[source] * rate * cosine
        phase_gradient[source] -= coefficient
        phase_gradient[target] += coefficient
        for axis in range(2):
            component_coefficients = {
                "J_xp_dp": sign * gain * probability[source].derivative(axis) * rate * cosine,
                "J_xx_dtheta": (
                    -sign
                    * gain
                    * probability[source]
                    * rate
                    * sine
                    * (theta[target].derivative(axis) - theta[source].derivative(axis))
                ),
                "J_xK_dK": sign * gain * probability[source] * rate.derivative(axis) * cosine,
            }
            for component, derivative_coefficient in component_coefficients.items():
                directional_phase_gradient[component][axis][source] -= derivative_coefficient
                directional_phase_gradient[component][axis][target] += derivative_coefficient

    memory_factor = (1 - alpha) / alpha
    response_u = -memory_factor * sum(
        (phase_gradient[index] * theta_u[index] for index in range(3)),
        Jet2.constant(0),
    )
    response_v = -memory_factor * sum(
        (phase_gradient[index] * theta_v[index] for index in range(3)),
        Jet2.constant(0),
    )
    response_curvature_jet = response_v.derivative(0) - response_u.derivative(1)

    def response_component(component: str) -> Jet2:
        derivative_u, derivative_v = directional_phase_gradient[component]
        return -memory_factor * (
            sum(
                (derivative_u[index] * theta_v[index] for index in range(3)),
                Jet2.constant(0),
            )
            - sum(
                (derivative_v[index] * theta_u[index] for index in range(3)),
                Jet2.constant(0),
            )
        )

    response_from_p = response_component("J_xp_dp")
    response_from_theta = response_component("J_xx_dtheta")
    response_from_kernel = response_component("J_xK_dK")
    response_from_d2theta = -memory_factor * sum(
        (
            phase_gradient[index] * (theta_v[index].derivative(0) - theta_u[index].derivative(1))
            for index in range(3)
        ),
        Jet2.constant(0),
    )
    decomposition_total = response_from_p + response_from_theta + response_from_kernel + response_from_d2theta
    return {
        "berry_connection_u": connection_u,
        "berry_connection_v": connection_v,
        "omega": omega,
        "omega_from_tangents": omega_from_tangents,
        "response_connection_u": response_u,
        "response_connection_v": response_v,
        "response_curvature": response_curvature_jet,
        "response_curvature_J_xp_dp": response_from_p,
        "response_curvature_J_xx_dtheta": response_from_theta,
        "response_curvature_J_xK_dK": response_from_kernel,
        "response_curvature_d2theta": response_from_d2theta,
        "response_curvature_decomposition_total": decomposition_total,
        "response_curvature_decomposition_residual": response_curvature_jet - decomposition_total,
        "phase_gradient_0": phase_gradient[0],
        "phase_gradient_1": phase_gradient[1],
        "phase_gradient_2": phase_gradient[2],
    }


def exact_center_certificate(
    alpha: Fraction = Fraction(7, 20),
    gain: Fraction = Fraction(9, 20),
) -> dict[str, object]:
    """Recompute the center values and quotient gradient over exact rationals."""

    forms = _exact_forms(alpha=alpha, gain=gain)
    omega = forms["omega"]
    response = forms["response_curvature"]
    omega_center = omega.coefficient(0, 0)
    response_center = response.coefficient(0, 0)
    response_gradient = (response.coefficient(1, 0), response.coefficient(0, 1))
    omega_gradient = (omega.coefficient(1, 0), omega.coefficient(0, 1))
    quotient_center = response_center / omega_center
    quotient_gradient = tuple(
        (response_gradient[index] * omega_center - response_center * omega_gradient[index])
        / (omega_center * omega_center)
        for index in range(2)
    )
    theta_uv = (Fraction(9, 20), Fraction(0), Fraction(-9, 20))
    theta_vu = theta_uv
    component_names = (
        "response_curvature_J_xp_dp",
        "response_curvature_J_xx_dtheta",
        "response_curvature_J_xK_dK",
        "response_curvature_d2theta",
    )
    decomposition = {
        name: {
            "center": fraction_item(forms[name].coefficient(0, 0)),
            "gradient": [
                fraction_item(forms[name].coefficient(1, 0)),
                fraction_item(forms[name].coefficient(0, 1)),
            ],
        }
        for name in component_names
    }
    decomposition_residual = forms["response_curvature_decomposition_residual"]
    return {
        "omega_center": fraction_item(omega_center),
        "response_curvature_center": fraction_item(response_center),
        "quotient_center": fraction_item(quotient_center),
        "response_curvature_gradient": [fraction_item(value) for value in response_gradient],
        "omega_gradient": [fraction_item(value) for value in omega_gradient],
        "quotient_gradient": [fraction_item(value) for value in quotient_gradient],
        "quotient_gradient_nonzero": all(value != 0 for value in quotient_gradient),
        "berry_connection_curvature_identity_error": fraction_item(
            (forms["omega"] - forms["omega_from_tangents"]).coefficient(0, 0)
        ),
        "theta_mixed_hessian_uv": [fraction_item(value) for value in theta_uv],
        "theta_mixed_hessian_vu": [fraction_item(value) for value in theta_vu],
        "theta_hessian_antisymmetric_residual": [
            fraction_item(left - right) for left, right in zip(theta_uv, theta_vu)
        ],
        "response_exterior_derivative_formula": "d beta_R=-m dJ_x wedge dtheta",
        "phase_gradient_total_derivative_formula": "dJ_x=J_xp dp+J_xx dtheta+J_xK dK",
        "J_xx_is_symmetric_hessian": True,
        "decomposition": decomposition,
        "decomposition_residual": {
            "center": fraction_item(decomposition_residual.coefficient(0, 0)),
            "gradient": [
                fraction_item(decomposition_residual.coefficient(1, 0)),
                fraction_item(decomposition_residual.coefficient(0, 1)),
            ],
        },
        "phase_gradient_center": [
            fraction_item(forms[f"phase_gradient_{index}"].coefficient(0, 0)) for index in range(3)
        ],
    }


def _core_branch_regression() -> dict[str, object]:
    benchmark = get_benchmark(MODEL_CONTRACT.benchmark_c_id)
    points = ((-0.3, -0.2), (0.0, 0.0), (0.3, 0.2))
    maximum_probability_error = 0.0
    maximum_phase_error = 0.0
    maximum_kernel_error = 0.0
    for u, v in points:
        candidate = benchmark.resolve_candidate_by_id(u, v, MODEL_CONTRACT.benchmark_c_branch_id)
        if candidate is None:
            raise RuntimeError("Benchmark C C0 branch is unavailable on the frozen patch")
        probability, theta, kernel = analytic_branch(u, v)
        maximum_probability_error = max(
            maximum_probability_error,
            float(np.max(np.abs(candidate.state.p - probability))),
        )
        maximum_phase_error = max(
            maximum_phase_error,
            float(np.max(np.abs(candidate.state.theta - theta))),
        )
        maximum_kernel_error = max(
            maximum_kernel_error,
            float(np.max(np.abs(candidate.state.kernel - kernel))),
        )
    return {
        "points": [list(point) for point in points],
        "maximum_probability_error": maximum_probability_error,
        "maximum_phase_error": maximum_phase_error,
        "maximum_kernel_error": maximum_kernel_error,
    }


def _numerical_regressions() -> dict[str, object]:
    step = 1.0e-5
    response = response_curvature(
        (0.0, 0.0),
        step,
        float(MODEL_CONTRACT.benchmark_c_phase_relaxation),
        float(MODEL_CONTRACT.benchmark_c_current_gain),
    )
    projective = projective_curvature((0.0, 0.0), step)
    half = 5.0e-5
    corners = ((-half, -half), (half, -half), (half, half), (-half, half))
    states = []
    for u, v in corners:
        probability, theta, _ = analytic_branch(u, v)
        states.append(psi_from_parts(probability, theta))
    wilson_density, minimum_overlap = curvature_tile(
        states[0], states[1], states[2], states[3], 2.0 * half, 2.0 * half
    )
    return {
        "role": "finite_difference_and_wilson_implementation_regressions_not_proof",
        "derivative_step": step,
        "response_curvature": response,
        "projective_curvature": projective,
        "wilson_curvature_density": wilson_density,
        "wilson_minimum_overlap": minimum_overlap,
        "response_absolute_error": abs(response - float(EXPECTED_RESPONSE_CENTER)),
        "projective_absolute_error": abs(projective - float(EXPECTED_OMEGA_CENTER)),
        "wilson_absolute_error": abs(wilson_density - float(EXPECTED_OMEGA_CENTER)),
    }


def benchmark_c_certificate(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Return the exact different-connection result on one primitive manifold."""

    center = exact_center_certificate(
        contract.benchmark_c_phase_relaxation,
        contract.benchmark_c_current_gain,
    )
    zero_gain = exact_center_certificate(contract.benchmark_c_phase_relaxation, Fraction(0))
    doubled_gain = exact_center_certificate(
        contract.benchmark_c_phase_relaxation,
        2 * contract.benchmark_c_current_gain,
    )
    unit_relaxation = exact_center_certificate(Fraction(1), contract.benchmark_c_current_gain)
    return {
        "classification": "SAME_PRIMITIVE_MANIFOLD_DIFFERENT_CONNECTIONS_DERIVED_MIXED_HESSIAN",
        "primitive_graph": "lambda=(u,v)->(p(lambda),theta(lambda),K(lambda))",
        "exact_branch": {
            "logits": [
                "17u/20+v/2",
                "-7u/10+7uv/20",
                "-11v/20-uv/4",
            ],
            "probability": "p_j=exp(z_j)/sum_k exp(z_k)",
            "phase": "theta=(phi,0,-phi);phi=7v/10+9uv/20+3u/20",
            "kernel": "k_plus=9/50+u/10;k_minus=9/50-u/10",
        },
        "berry_connection": "A_i=sum_j p_j partial_i theta_j",
        "berry_curvature": (
            "Omega_uv=sum_j[(partial_u p_j)(partial_v theta_j)-" "(partial_v p_j)(partial_u theta_j)]"
        ),
        "response_readout": "J=directed circulation(p,x,K;gain);H=partial_x J|x=theta",
        "response_connection": "beta_i=-(1-alpha)/alpha H_a partial_i theta^a",
        "response_curvature": (
            "F_uv=-(1-alpha)/alpha[(partial_u H_a)(partial_v theta^a)-" "(partial_v H_a)(partial_u theta^a)]"
        ),
        "mixed_hessian_identity": (
            "d beta_R=-m dJ_x wedge dtheta with dJ_x=J_xp dp+J_xx dtheta+J_xK dK; "
            "d^2theta=0 and symmetric J_xx cancel, while mixed J_xp/J_xK terms remain"
        ),
        "alpha": fraction_item(contract.benchmark_c_phase_relaxation),
        "gain": fraction_item(contract.benchmark_c_current_gain),
        "center": center,
        "gain_zero_response": zero_gain["response_curvature_center"],
        "gain_double_response": doubled_gain["response_curvature_center"],
        "alpha_one_response": unit_relaxation["response_curvature_center"],
        "gain_scaling_exact": (
            doubled_gain["response_curvature_center"]["fraction"]
            == fraction_item(2 * EXPECTED_RESPONSE_CENTER)["fraction"]
        ),
        "omega_independent_of_gain_and_alpha": (
            zero_gain["omega_center"]["fraction"]
            == center["omega_center"]["fraction"]
            == unit_relaxation["omega_center"]["fraction"]
        ),
        "core_branch_regression": _core_branch_regression(),
        "numerical_regressions": _numerical_regressions(),
        "response_statistic_scope": contract.benchmark_c_response_statistic,
        "legacy_mean_is_same_curvature_response": False,
        "finite_difference_or_wilson_used_as_analytic_acceptance": False,
    }

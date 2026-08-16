"""Frozen no-go, covariance, and non-implication fixtures."""

from __future__ import annotations

import math

import numpy as np

from .contracts import Array, CaseDisposition
from .forms import (
    bloch_connection,
    bloch_state,
    closed_circle_path,
    exterior_derivative,
    line_integral,
    normalized_area_condition,
    projective_curvature_tensor,
    pullback_two_form,
    rotational_one_form,
    two_form_vector,
)
from .models import realizability_pair, realized_tangent_one_form

EXPECTED_CASE_DISPOSITIONS = {
    "C1": CaseDisposition.COUNTEREXAMPLE.value,
    "C2": CaseDisposition.COUNTEREXAMPLE.value,
    "C3": CaseDisposition.COUNTEREXAMPLE.value,
    "C4": CaseDisposition.COUNTEREXAMPLE.value,
    "C5": CaseDisposition.INELIGIBLE_TAUTOLOGY.value,
    "C6": CaseDisposition.COUNTEREXAMPLE.value,
    "C7": CaseDisposition.PASS_LOCAL_INTERNAL.value,
    "C8": CaseDisposition.OUT_OF_SCOPE.value,
    "P1": CaseDisposition.PASS_LOCAL_INTERNAL.value,
}


def _bloch_2d(point: Array) -> Array:
    polar, azimuth = np.asarray(point, dtype=float)
    return np.asarray(
        [np.cos(0.5 * polar), np.exp(1j * azimuth) * np.sin(0.5 * polar)],
        dtype=complex,
    )


def _constant_state(_point: Array) -> Array:
    return np.asarray((1.0, 0.0), dtype=complex)


def _curl_free_beta(point: Array) -> Array:
    u, v = np.asarray(point, dtype=float)
    return np.asarray((v, u), dtype=float)


def _unit_xy_connection(point: Array) -> Array:
    """Return A=x dy in three coordinates, so Omega=dx wedge dy."""

    x, _y, _z = np.asarray(point, dtype=float)
    return np.asarray((0.0, x, 0.0), dtype=float)


def _unit_xy_projective_state(point: Array) -> Array:
    """Normalized CP1 state with A=q dphi and dA=dx wedge dy on a safe patch."""

    x, y, _z = np.asarray(point, dtype=float)
    population = 0.5 + 0.2 * x
    if not 0.0 < population < 1.0:
        raise ValueError("unit-xy projective fixture left its safe population patch")
    phase = 5.0 * y
    return np.asarray(
        (
            math.sqrt(1.0 - population),
            np.exp(1j * phase) * math.sqrt(population),
        ),
        dtype=complex,
    )


def _sign_changing_response_connection(point: Array) -> Array:
    """Return B=(x^2/2)dy, so dB=x dx wedge dy."""

    x, _y, _z = np.asarray(point, dtype=float)
    return np.asarray((0.0, 0.5 * x**2, 0.0), dtype=float)


def nonnormal_fixed_gap_case() -> dict[str, object]:
    """Return an exact fixed-gap non-normal example outside the pure-state scope."""

    parameter = np.asarray((0.2, -0.3), dtype=float)
    u, v = parameter
    coefficient = 1.0 + 1.0j
    right = np.asarray((1.0, u, v), dtype=complex)
    left = np.asarray((1.0, coefficient * v, -coefficient * u), dtype=complex)
    second = np.asarray((-coefficient * v, 1.0, 0.0), dtype=complex)
    third = np.asarray((coefficient * u, 0.0, 1.0), dtype=complex)
    similarity = np.column_stack((right, second, third))
    operator = similarity @ np.diag((0.0, 1.0, 2.0)) @ np.linalg.inv(similarity)
    commutator_norm = float(np.linalg.norm(operator @ operator.conj().T - operator.conj().T @ operator))
    biorthogonal_curvature = 2.0j * coefficient
    return {
        "case_id": "C8",
        "disposition": CaseDisposition.OUT_OF_SCOPE.value,
        "construction_id": "proof_program_similarity_family_v1",
        "same_as_adversarial_projector_example": False,
        "fixed_eigenvalues": [0.0, 1.0, 2.0],
        "minimum_gap": 1.0,
        "left_right_overlap": [float(np.real(left @ right)), float(np.imag(left @ right))],
        "right_only_curvature": 0.0,
        "biorthogonal_curvature": [
            float(np.real(biorthogonal_curvature)),
            float(np.imag(biorthogonal_curvature)),
        ],
        "nonnormal_commutator_norm": commutator_norm,
    }


def covariance_checks(step: float = 2e-5) -> dict[str, float]:
    """Check projective gauge invariance and coordinate pullback covariance."""

    point = np.asarray((1.1, -0.2, 0.15), dtype=float)
    base_curvature = projective_curvature_tensor(bloch_state, point, step)

    def gauged_state(value: Array) -> Array:
        phase = float(value[0] * value[1] + 0.3 * value[2] ** 2)
        return np.exp(1j * phase) * bloch_state(value)

    gauge_curvature = projective_curvature_tensor(gauged_state, point, step)
    jacobian = np.asarray(
        [
            [1.0, 0.2, 0.0],
            [0.0, 1.0, -0.1],
            [0.15, 0.0, 1.0],
        ],
        dtype=float,
    )
    offset = np.asarray((0.2, -0.1, 0.05), dtype=float)
    mu = np.linalg.solve(jacobian, point - offset)

    def transformed_state(value: Array) -> Array:
        return bloch_state(jacobian @ np.asarray(value, dtype=float) + offset)

    transformed_curvature = projective_curvature_tensor(transformed_state, mu, step)
    expected_curvature = pullback_two_form(base_curvature, jacobian)

    def beta(value: Array) -> Array:
        return 2.0 * bloch_connection(value)

    base_response_curvature = exterior_derivative(beta, point, step)

    def transformed_beta(value: Array) -> Array:
        physical = jacobian @ np.asarray(value, dtype=float) + offset
        return jacobian.T @ beta(physical)

    transformed_response_curvature = exterior_derivative(transformed_beta, mu, step)
    expected_response_curvature = pullback_two_form(base_response_curvature, jacobian)
    return {
        "gauge_curvature_max_error": float(np.max(np.abs(gauge_curvature - base_curvature))),
        "coordinate_geometry_max_error": float(np.max(np.abs(transformed_curvature - expected_curvature))),
        "coordinate_response_max_error": float(
            np.max(np.abs(transformed_response_curvature - expected_response_curvature))
        ),
    }


def positive_control(step: float = 2e-5) -> dict[str, object]:
    """Deliberately aligned 3D oracle/positive implementation control."""

    point = np.asarray((1.1, -0.2, 0.15), dtype=float)
    omega = projective_curvature_tensor(bloch_state, point, step)
    response_curvature = exterior_derivative(lambda value: 2.0 * bloch_connection(value), point, step)
    area_vectors = np.eye(3, dtype=float)
    heldout = np.ones(3, dtype=float) / math.sqrt(3.0)
    omega_vector = two_form_vector(omega)
    response_vector = two_form_vector(response_curvature)
    predicted = 2.0 * float(omega_vector @ heldout)
    observed = float(response_vector @ heldout)
    return {
        "case_id": "P1",
        "disposition": CaseDisposition.PASS_LOCAL_INTERNAL.value,
        "frozen_kappa": 2.0,
        "max_tensor_error": float(np.max(np.abs(response_curvature - 2.0 * omega))),
        "normalized_area_condition": normalized_area_condition(area_vectors),
        "area_rank": int(np.linalg.matrix_rank(area_vectors)),
        "heldout_cosine_max": float(np.max(np.abs(area_vectors @ heldout))),
        "heldout_prediction": predicted,
        "heldout_response": observed,
        "heldout_absolute_error": abs(predicted - observed),
        "control_role": "deliberately_aligned_oracle_positive_implementation_control",
    }


def counterexample_matrix() -> list[dict[str, object]]:
    """Return the frozen C1-C8/P1 matrix with exact expected dispositions."""

    point_2d = np.asarray((1.1, -0.25), dtype=float)
    omega_nonzero = projective_curvature_tensor(_bloch_2d, point_2d)
    curl_free = exterior_derivative(_curl_free_beta, point_2d)
    zero_omega = projective_curvature_tensor(_constant_state, point_2d)
    nonzero_response = exterior_derivative(rotational_one_form(1.0), point_2d)
    coarse_path = closed_circle_path(np.asarray((0.3, -0.2)), 0.2, 16)
    fine_path = closed_circle_path(np.asarray((0.3, -0.2)), 0.2, 512)
    coarse_pair = realizability_pair(rotational_one_form(1.0), coarse_path, 0.65)
    fine_pair = realizability_pair(rotational_one_form(1.0), fine_path, 0.65)
    coarse_speed_target = line_integral(rotational_one_form(1.0), coarse_path)
    fine_speed_target = line_integral(rotational_one_form(1.0), fine_path)
    analytic_circle_target = math.pi * 0.2**2
    c3_points = [np.asarray((x, 0.2, -0.1), dtype=float) for x in (-1.0, 0.0, 1.0)]
    c3_omega = [projective_curvature_tensor(_unit_xy_projective_state, point) for point in c3_points]
    c3_response = [exterior_derivative(_sign_changing_response_connection, point) for point in c3_points]
    c3_kappa = [float(response[0, 1] / omega[0, 1]) for response, omega in zip(c3_response, c3_omega)]
    c4_point = np.asarray((0.4, -0.3, 0.2), dtype=float)
    c4_omega = projective_curvature_tensor(_unit_xy_projective_state, c4_point)
    c4_analytic_omega = exterior_derivative(_unit_xy_connection, c4_point)
    c4_coefficients = (-2.0, 0.0, 3.0)
    c4_responses = [
        exterior_derivative(lambda value, c=c: c * _unit_xy_connection(value), c4_point)
        for c in c4_coefficients
    ]
    c4_errors = [
        float(np.max(np.abs(response - coefficient * c4_omega)))
        for response, coefficient in zip(c4_responses, c4_coefficients)
    ]
    c5_point = np.asarray((0.2, -0.4), dtype=float)
    c5_first = exterior_derivative(rotational_one_form(1.25), c5_point)
    c5_second = exterior_derivative(rotational_one_form(-0.75), c5_point)
    c5_quotient = float(c5_second[0, 1] / c5_first[0, 1])
    c5_identity_error = float(np.max(np.abs(c5_second - c5_quotient * c5_first)))
    c6_zero_omega = projective_curvature_tensor(_constant_state, point_2d)
    covariance = covariance_checks()
    cases: list[dict[str, object]] = [
        {
            "case_id": "C1",
            "disposition": CaseDisposition.COUNTEREXAMPLE.value,
            "description": "nonzero projective curvature with curl-free response",
            "omega_uv": float(omega_nonzero[0, 1]),
            "response_curvature_uv": float(curl_free[0, 1]),
            "implication_refuted": "Omega_nonzero_implies_response",
        },
        {
            "case_id": "C2",
            "disposition": CaseDisposition.COUNTEREXAMPLE.value,
            "description": "zero projective curvature with nonzero response curvature",
            "omega_uv": float(zero_omega[0, 1]),
            "response_curvature_uv": float(nonzero_response[0, 1]),
            "implication_refuted": "response_implies_Omega",
        },
        {
            "case_id": "C3",
            "disposition": CaseDisposition.COUNTEREXAMPLE.value,
            "description": "an aligned coefficient can change sign",
            "sample_coordinates": [-1.0, 0.0, 1.0],
            "omega_xy": [float(form[0, 1]) for form in c3_omega],
            "normalized_state_map": "psi=(sqrt(1-q),exp(i*phi)*sqrt(q)); q=0.5+0.2*x; phi=5*y",
            "response_curvature_xy": [float(form[0, 1]) for form in c3_response],
            "kappa_values": c3_kappa,
            "max_alignment_error": max(
                float(np.max(np.abs(response - kappa * omega)))
                for response, omega, kappa in zip(c3_response, c3_omega, c3_kappa)
            ),
            "kappa_index": "fixture/coupling/readout",
        },
        {
            "case_id": "C4",
            "disposition": CaseDisposition.COUNTEREXAMPLE.value,
            "description": "one state curvature permits multiple authored readout coefficients",
            "same_omega_tensor": c4_omega.tolist(),
            "normalized_state_map": "same CP1 q=0.5+0.2*x, phi=5*y state used for every readout",
            "projective_vs_analytic_connection_error": float(np.max(np.abs(c4_omega - c4_analytic_omega))),
            "readout_coefficients": list(c4_coefficients),
            "response_tensors": [response.tolist() for response in c4_responses],
            "max_coefficient_identity_errors": c4_errors,
            "kappa_index": "fixture/coupling/readout",
        },
        {
            "case_id": "C5",
            "disposition": CaseDisposition.INELIGIBLE_TAUTOLOGY.value,
            "description": "pointwise division of nonzero two-forms in two dimensions",
            "reason": "the two-form space is one-dimensional",
            "first_two_form": c5_first.tolist(),
            "second_two_form": c5_second.tolist(),
            "pointwise_quotient": c5_quotient,
            "quotient_identity_error": c5_identity_error,
        },
        {
            "case_id": "C6",
            "disposition": CaseDisposition.COUNTEREXAMPLE.value,
            "description": "finite-speed lag contains a dynamic remainder",
            "independent_constant_state_omega_uv": float(c6_zero_omega[0, 1]),
            "coarse_sampled_path_line_integral": coarse_speed_target,
            "fine_sampled_path_line_integral": fine_speed_target,
            "analytic_circle_line_integral": analytic_circle_target,
            "coarse_orientation_odd": coarse_pair.anti,
            "fine_orientation_odd": fine_pair.anti,
            "coarse_odd_remainder": abs(coarse_pair.anti - coarse_speed_target),
            "fine_odd_remainder": abs(fine_pair.anti - fine_speed_target),
            "coarse_to_fine_odd_remainder_reduction": (
                abs(coarse_pair.anti - coarse_speed_target) / abs(fine_pair.anti - fine_speed_target)
            ),
            "coarse_orientation_even": coarse_pair.even,
            "fine_orientation_even": fine_pair.even,
            "coarse_to_fine_even_reduction": abs(coarse_pair.even) / abs(fine_pair.even),
        },
        {
            "case_id": "C7",
            "disposition": CaseDisposition.PASS_LOCAL_INTERNAL.value,
            "description": "gauge invariance and coordinate covariance",
            **covariance,
        },
        nonnormal_fixed_gap_case(),
        positive_control(),
    ]
    return cases


def case_dispositions_match(cases: list[dict[str, object]]) -> bool:
    """Require the complete ordered C1-C8/P1 disposition contract."""

    actual = {str(case.get("case_id")): str(case.get("disposition")) for case in cases}
    return actual == EXPECTED_CASE_DISPOSITIONS and len(actual) == len(cases)


def propagator_decay_without_frozen_invertibility(samples: int = 257) -> dict[str, object]:
    """Exhibit driven decay while the frozen Jacobian is singular on the path.

    For f(x,lambda)=(-1+lambda)(x-lambda) and lambda(t)=sin(t), the
    branch-linearized propagator is bounded by exp(2) exp(-(t-u)), while
    J=-1+sin(t) vanishes at pi/2.
    """

    times = np.linspace(0.0, 2.0 * math.pi, samples)
    max_prefactor_ratio = 0.0
    for start_index, start in enumerate(times):
        ratios = np.exp(math.cos(start) - np.cos(times[start_index:]))
        max_prefactor_ratio = max(max_prefactor_ratio, float(np.max(ratios)))
    return {
        "construction": "f(x,lambda)=(-1+lambda)(x-lambda); lambda(t)=sin(t)",
        "branch_linearized_propagator": "U(t,u)=exp(-(t-u)+cos(u)-cos(t))",
        "decay_prefactor_bound": math.exp(2.0),
        "sampled_max_prefactor_ratio": max_prefactor_ratio,
        "decay_time_constant": 1.0,
        "frozen_jacobian_at_pi_over_two": 0.0,
        "uniform_frozen_inverse_exists": False,
        "reason": "driven propagator decay alone does not justify J(lambda)^-1",
    }


def realizability_identity_error() -> float:
    """Return the max B-beta error for a nonlinear arbitrary one-form."""

    def arbitrary_beta(point: Array) -> Array:
        x, y, z = np.asarray(point, dtype=float)
        return np.asarray((y + z**2, np.sin(x) - z, x * y + np.cos(z)), dtype=float)

    points = (
        np.asarray((0.2, -0.1, 0.3)),
        np.asarray((-0.4, 0.5, -0.2)),
        np.asarray((0.0, 0.0, 0.0)),
    )
    errors = [
        float(np.max(np.abs(realized_tangent_one_form(arbitrary_beta, point, 0.63) - arbitrary_beta(point))))
        for point in points
    ]
    return max(errors)

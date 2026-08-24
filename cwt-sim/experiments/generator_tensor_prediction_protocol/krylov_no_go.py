"""Exact response-free closure obstruction for the Krylov3 tensor family."""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from types import MappingProxyType

from .contract import A_CENTERS, MODEL_CONTRACT
from .exact import (
    RationalMatrix,
    canonical_exact_sha256,
    fraction_vector_sha256,
    freeze_exact_record,
    rational_determinant,
    rational_inverse,
)
from .geometry import (
    GeometryJet,
    RationalVector,
    dimensionless_endomorphism,
    geometry_jet,
    normalized_omega,
    normalized_omega_derivatives,
    rational_matrix_add,
    rational_matrix_multiply,
    rational_matrix_scale,
    rational_matrix_vector,
    two_form_pullback,
    two_form_pullback_derivative,
)

EXPECTED_CLOSURE_DETERMINANT_SHA256 = "0d0b3dff9d30fc49c8aef954a3b90aba4fa483c1d70dd2c43366476298bfad63"
EXPECTED_N0_CERTIFICATE_SHA256 = "6e0566cfd47da888358f0af7165bf622e359cdcbf8ac511513e2a0c66e882868"

N0_PAYLOAD_KEYS = (
    "authority",
    "family",
    "target",
    "wedge_action_convention",
    "closure_derivative_convention",
    "closure_row_order",
    "centers",
    "closure_rows",
    "closure_determinant",
    "closure_determinant_positive",
    "closure_determinant_sha256",
    "closure_rank",
    "closure_nullity",
    "only_closed_coefficient_vector",
    "classification",
    "disposition",
    "response_accessed",
    "retrospective_unrestricted_3x3_status",
    "retrospective_diagnostic_used_for_acceptance",
)


def _normalized_tensor_derivative(jet: GeometryJet, axis: int) -> RationalMatrix:
    scales = MODEL_CONTRACT.coordinate_scales
    metric = [[scales[i] * scales[j] * jet.metric[i][j] for j in range(3)] for i in range(3)]
    metric_derivative = [
        [scales[i] * scales[j] * scales[axis] * jet.metric_derivatives[axis][i][j] for j in range(3)]
        for i in range(3)
    ]
    friction_derivative = [
        [scales[i] * scales[j] * scales[axis] * jet.friction_derivatives[axis][i][j] for j in range(3)]
        for i in range(3)
    ]
    inverse_metric = rational_inverse(metric)
    endomorphism = dimensionless_endomorphism(jet)
    return rational_matrix_multiply(
        inverse_metric,
        rational_matrix_add(
            rational_matrix_scale(friction_derivative, MODEL_CONTRACT.depolarizing_rate),
            rational_matrix_scale(
                rational_matrix_multiply(metric_derivative, endomorphism),
                Fraction(-1),
            ),
        ),
    )


def _vector_add(left: RationalVector, right: RationalVector) -> RationalVector:
    return tuple(left[index] + right[index] for index in range(3))  # type: ignore[return-value]


def closure_coefficients(center) -> tuple[Fraction, Fraction, Fraction]:
    live = geometry_jet(center)
    zero_chord = geometry_jet(center, Fraction(0))
    if zero_chord.omega != (0, 0, 0) or any(item != (0, 0, 0) for item in zero_chord.omega_derivatives):
        raise RuntimeError("zero-chord real-gauge geometry is not exactly zero")
    xi = tuple(
        left - right for left, right in zip(normalized_omega(live), normalized_omega(zero_chord), strict=True)
    )
    xi_derivatives = tuple(
        tuple(
            left - right
            for left, right in zip(
                normalized_omega_derivatives(live)[axis],
                normalized_omega_derivatives(zero_chord)[axis],
                strict=True,
            )
        )
        for axis in range(3)
    )
    endomorphism = dimensionless_endomorphism(live)
    pullback = two_form_pullback(endomorphism)
    pullback_derivatives = tuple(
        two_form_pullback_derivative(endomorphism, _normalized_tensor_derivative(live, axis))
        for axis in range(3)
    )
    first_image = rational_matrix_vector(pullback, xi)
    first_derivatives = []
    second_derivatives = []
    for axis in range(3):
        first_derivative = _vector_add(
            rational_matrix_vector(pullback_derivatives[axis], xi),
            rational_matrix_vector(pullback, xi_derivatives[axis]),
        )
        first_derivatives.append(first_derivative)
        second_derivatives.append(
            _vector_add(
                _vector_add(
                    rational_matrix_vector(pullback_derivatives[axis], first_image),
                    rational_matrix_vector(
                        pullback,
                        rational_matrix_vector(pullback_derivatives[axis], xi),
                    ),
                ),
                rational_matrix_vector(
                    pullback,
                    rational_matrix_vector(pullback, xi_derivatives[axis]),
                ),
            )
        )
    return (
        sum(xi_derivatives[axis][axis] for axis in range(3)),
        sum(first_derivatives[axis][axis] for axis in range(3)),
        sum(second_derivatives[axis][axis] for axis in range(3)),
    )


def n0_acceptance_payload(record: object) -> tuple:
    if type(record) not in {dict, MappingProxyType} or tuple(record) != (
        *N0_PAYLOAD_KEYS,
        "certificate_sha256",
        "reviewed_certificate_sha256_matches",
    ):
        raise TypeError("N0 certificate schema refused")
    return tuple((key, record[key]) for key in N0_PAYLOAD_KEYS)


@lru_cache(maxsize=1)
def _cached_krylov_no_go_certificate() -> MappingProxyType:
    centers = A_CENTERS[:3]
    rows = tuple(closure_coefficients(center) for center in centers)
    determinant_value = rational_determinant([list(row) for row in rows])
    if determinant_value == 0:
        raise RuntimeError("reviewed Krylov3 closure system became singular")
    determinant_sha256 = fraction_vector_sha256((determinant_value,))
    record = {
        "authority": "exact_count_blind_geometry_and_full_dA_closure_recompute",
        "family": "K_sigma=sigma*(k0*I+k1*A+k2*A^2)",
        "target": "Xi=Omega_r-Omega_0",
        "wedge_action_convention": "explicit_two_by_two_minors_without_inverse_assumption",
        "closure_derivative_convention": "d(A^m Xi)_axis includes dA and dXi before divergence trace",
        "closure_row_order": ("d_Xi", "d_A_Xi", "d_A2_Xi"),
        "centers": centers,
        "closure_rows": rows,
        "closure_determinant": determinant_value,
        "closure_determinant_positive": determinant_value > 0,
        "closure_determinant_sha256": determinant_sha256,
        "closure_rank": 3,
        "closure_nullity": 0,
        "only_closed_coefficient_vector": (0, 0, 0),
        "classification": "NO_NONTRIVIAL_CLOSED_MEMBER",
        "disposition": "INELIGIBLE_NOT_CLOSED",
        "response_accessed": False,
        "retrospective_unrestricted_3x3_status": ("EXPOSED_INELIGIBLE_DIAGNOSTIC"),
        "retrospective_diagnostic_used_for_acceptance": False,
    }
    payload = tuple((key, record[key]) for key in N0_PAYLOAD_KEYS)
    certificate_sha256 = canonical_exact_sha256(payload)
    record["certificate_sha256"] = certificate_sha256
    record["reviewed_certificate_sha256_matches"] = (
        certificate_sha256 == EXPECTED_N0_CERTIFICATE_SHA256
        and determinant_sha256 == EXPECTED_CLOSURE_DETERMINANT_SHA256
    )
    return freeze_exact_record(record)  # type: ignore[return-value]


def krylov_no_go_certificate() -> MappingProxyType:
    """Return a fresh immutable view over the cached exact algebra result."""

    return freeze_exact_record(dict(_cached_krylov_no_go_certificate()))  # type: ignore[return-value]

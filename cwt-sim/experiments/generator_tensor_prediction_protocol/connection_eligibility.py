"""Response-free geometry eligibility for the closed connection family."""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from types import MappingProxyType

from .contract import (
    A_CENTERS,
    HELDOUT_AREA_VECTOR,
    HELDOUT_CENTER,
    RESERVATION_STATUS,
    V_CENTERS,
)
from .exact import (
    RationalMatrix,
    canonical_exact_sha256,
    fraction_vector_sha256,
    freeze_exact_record,
    rational_determinant,
    rational_inverse,
)
from .geometry import (
    RationalVector,
    normalized_purity_derivative,
    purity_jet,
    wilson_scalar_jet,
)

EXPECTED_GRAM_DETERMINANT_SHA256 = "650243385ad8d2bac5d32b8890b8b0dcb931a2b08611bca995de68eb5f1a650d"
EXPECTED_HELDOUT_DENSITY_SHA256 = "23f59845f3a860ca2823e6c190eaaa4ad94e469d33694a15c5086be9d9201aa6"
EXPECTED_P0_CERTIFICATE_SHA256 = "dd25364e1211a6a671049c51e8ad32a7793e01b38a7a2575dd19747ef57b93a4"

P0_PAYLOAD_KEYS = (
    "authority",
    "connection_family",
    "curvature_family",
    "global_coefficient_count",
    "pointwise_coefficients_forbidden",
    "basis_order",
    "calibration_centers",
    "calibration_basis_matrices",
    "calibration_design_shape",
    "local_basis_determinants",
    "all_local_basis_determinants_positive",
    "gram_determinant",
    "gram_determinant_positive",
    "gram_determinant_sha256",
    "exact_gram_infinity_condition",
    "calibration_rank",
    "calibration_scalar_constraints",
    "calibration_overdetermination",
    "confirmation_centers",
    "confirmation_basis_matrices",
    "confirmation_basis_determinants",
    "confirmation_points_eligible",
    "heldout_center",
    "heldout_area_vector",
    "heldout_basis",
    "heldout_basis_densities",
    "heldout_basis_densities_nonzero",
    "heldout_basis_density_sha256",
    "connection_exterior_derivative_identity",
    "basis_exterior_derivative_is_structurally_closed",
    "gauge_invariant_scalar_inputs",
    "coordinate_covariance_records",
    "coordinate_covariance_exact",
    "units",
    "sigma_predictor_record",
    "count_reversal_rule",
    "zero_current_rule",
    "zero_chord_wilson_jet",
    "zero_chord_Wilson_jet_zero",
    "flux_conjugation_records",
    "conjugate_bases_rank_three",
    "simple_flux_conjugation_parity_holds",
    "simple_flux_conjugation_parity_claimed",
    "flux_conjugation_scope",
    "basis_scope",
    "uniform_purity_bias_derivative_box_proved",
    "reservation_status",
    "response_accessed",
    "coefficients_fitted",
    "confirmation_prediction_run",
    "heldout_prediction_run",
    "disposition",
)


def wedge(left: RationalVector, right: RationalVector) -> RationalVector:
    """Return two-form pseudovector order (dt,tb,bd)."""

    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def connection_basis(center) -> tuple[RationalVector, RationalVector, RationalVector]:
    _, _, du, dv = wilson_scalar_jet(center)
    dp = normalized_purity_derivative(purity_jet(center))
    return wedge(du, dv), wedge(du, dp), wedge(dv, dp)


def connection_one_form_basis(center) -> tuple[RationalVector, RationalVector, RationalVector]:
    u, v, du, dv = wilson_scalar_jet(center)
    dp = normalized_purity_derivative(purity_jet(center))
    return (
        tuple((u * dv[index] - v * du[index]) / 2 for index in range(3)),
        tuple(u * dp[index] for index in range(3)),
        tuple(v * dp[index] for index in range(3)),
    )  # type: ignore[return-value]


def predictor_one_form(center, coefficients, sigma: int) -> RationalVector:
    if type(sigma) is not int or sigma not in {-1, 0, 1}:
        raise TypeError("sigma must be an exact reviewed orientation")
    if (
        type(coefficients) is not tuple
        or len(coefficients) != 3
        or any(type(value) is not Fraction for value in coefficients)
    ):
        raise TypeError("coefficients must be three exact Fractions")
    basis = connection_one_form_basis(center)
    return tuple(
        Fraction(sigma) * sum(coefficients[index] * basis[index][axis] for index in range(3))
        for axis in range(3)
    )  # type: ignore[return-value]


def predictor_curvature(center, coefficients, sigma: int) -> RationalVector:
    if type(sigma) is not int or sigma not in {-1, 0, 1}:
        raise TypeError("sigma must be an exact reviewed orientation")
    if (
        type(coefficients) is not tuple
        or len(coefficients) != 3
        or any(type(value) is not Fraction for value in coefficients)
    ):
        raise TypeError("coefficients must be three exact Fractions")
    basis = connection_basis(center)
    return tuple(
        Fraction(sigma) * sum(coefficients[index] * basis[index][axis] for index in range(3))
        for axis in range(3)
    )  # type: ignore[return-value]


def _basis_matrix(center) -> RationalMatrix:
    basis = connection_basis(center)
    return [list(row) for row in zip(*basis, strict=True)]


def _gram(rows: RationalMatrix) -> RationalMatrix:
    return [[sum(row[i] * row[j] for row in rows) for j in range(3)] for i in range(3)]


def _infinity_norm(matrix: RationalMatrix) -> Fraction:
    return max(sum(abs(value) for value in row) for row in matrix)


def _coordinate_covariance_record(center) -> dict[str, object]:
    """Check the exact two-form pullback under one frozen rational chart map."""

    transform = [
        [Fraction(1), Fraction(1), Fraction(0)],
        [Fraction(0), Fraction(1), Fraction(1)],
        [Fraction(1), Fraction(0), Fraction(1)],
    ]
    determinant_value = rational_determinant(transform)
    inverse = rational_inverse(transform)
    transpose = [list(row) for row in zip(*transform, strict=True)]

    def pull_one_form(values: RationalVector) -> RationalVector:
        return tuple(
            sum(transpose[i][j] * values[j] for j in range(3)) for i in range(3)
        )  # type: ignore[return-value]

    def pull_two_form(values: RationalVector) -> RationalVector:
        return tuple(
            determinant_value * sum(inverse[i][j] * values[j] for j in range(3)) for i in range(3)
        )  # type: ignore[return-value]

    _, _, du, dv = wilson_scalar_jet(center)
    dp = normalized_purity_derivative(purity_jet(center))
    pairs = ((du, dv), (du, dp), (dv, dp))
    direct = tuple(wedge(pull_one_form(left), pull_one_form(right)) for left, right in pairs)
    pulled = tuple(pull_two_form(wedge(left, right)) for left, right in pairs)
    return {
        "center": center,
        "transform": tuple(tuple(row) for row in transform),
        "determinant": determinant_value,
        "direct_wedges": direct,
        "pulled_wedges": pulled,
        "matches": direct == pulled,
    }


def _flux_conjugation_record(center) -> dict[str, object]:
    bias, diffusion, t = center
    positive = connection_basis(center)
    negative = connection_basis((bias, diffusion, -t))

    def pull_back(values: RationalVector) -> RationalVector:
        # For C=diag(1,1,-1), Lambda^2(C*)=diag(-1,-1,1).
        return (-values[0], -values[1], values[2])

    simple_parities = (-1, 1, -1)
    pulled = tuple(pull_back(item) for item in negative)
    simple_parity_holds = all(
        pull_back(negative[index]) == tuple(simple_parities[index] * value for value in positive[index])
        for index in range(3)
    )
    return {
        "center": center,
        "conjugate_center": (bias, diffusion, -t),
        "pulled_conjugate_basis": pulled,
        "pulled_conjugate_determinant": rational_determinant(
            [list(row) for row in zip(*pulled, strict=True)]
        ),
        "simple_parities_tested": simple_parities,
        "simple_parity_holds": simple_parity_holds,
    }


def p0_acceptance_payload(record: object) -> tuple:
    if type(record) not in {dict, MappingProxyType} or tuple(record) != (
        *P0_PAYLOAD_KEYS,
        "certificate_sha256",
        "reviewed_certificate_sha256_matches",
    ):
        raise TypeError("P0 certificate schema refused")
    return tuple((key, record[key]) for key in P0_PAYLOAD_KEYS)


@lru_cache(maxsize=1)
def _cached_connection_eligibility_certificate() -> MappingProxyType:
    calibration_matrices = tuple(tuple(tuple(row) for row in _basis_matrix(center)) for center in A_CENTERS)
    rows = [list(row) for matrix in calibration_matrices for row in matrix]
    gram = _gram(rows)
    gram_determinant = rational_determinant(gram)
    if gram_determinant == 0:
        raise RuntimeError("reviewed connection design became singular")
    gram_condition = _infinity_norm(gram) * _infinity_norm(rational_inverse(gram))
    local_determinants = tuple(
        rational_determinant([list(row) for row in matrix]) for matrix in calibration_matrices
    )
    if any(value == 0 for value in local_determinants):
        raise RuntimeError("reviewed local connection basis became singular")
    confirmation_matrices = tuple(tuple(tuple(row) for row in _basis_matrix(center)) for center in V_CENTERS)
    confirmation_determinants = tuple(
        rational_determinant([list(row) for row in matrix]) for matrix in confirmation_matrices
    )
    if any(value == 0 for value in confirmation_determinants):
        raise RuntimeError("reviewed confirmation connection basis became singular")
    heldout_basis = connection_basis(HELDOUT_CENTER)
    heldout_densities = tuple(
        sum(Fraction(area) * component for area, component in zip(HELDOUT_AREA_VECTOR, basis, strict=True))
        for basis in heldout_basis
    )
    zero_wilson = wilson_scalar_jet(A_CENTERS[0], Fraction(0))
    all_reserved_points = (*A_CENTERS, *V_CENTERS, HELDOUT_CENTER)
    conjugation_records = tuple(_flux_conjugation_record(center) for center in all_reserved_points)
    covariance_records = tuple(_coordinate_covariance_record(center) for center in A_CENTERS)
    coefficients = (Fraction(1), Fraction(2), Fraction(3))
    positive_one_form = predictor_one_form(A_CENTERS[0], coefficients, 1)
    positive_curvature = predictor_curvature(A_CENTERS[0], coefficients, 1)
    sigma_record = {
        "center": A_CENTERS[0],
        "coefficients": coefficients,
        "sigma_values": (-1, 0, 1),
        "positive_one_form": positive_one_form,
        "positive_curvature": positive_curvature,
        "negative_one_form": predictor_one_form(A_CENTERS[0], coefficients, -1),
        "negative_curvature": predictor_curvature(A_CENTERS[0], coefficients, -1),
        "zero_one_form": predictor_one_form(A_CENTERS[0], coefficients, 0),
        "zero_curvature": predictor_curvature(A_CENTERS[0], coefficients, 0),
    }
    record = {
        "authority": "exact_count_blind_Wilson_scalars_and_stationary_purity",
        "connection_family": ("Bhat_sigma=sigma*[k0/2*(u*dv-v*du)+k1*u*dp+k2*v*dp]"),
        "curvature_family": ("Fhat_sigma=sigma*[k0*du^dv+k1*du^dp+k2*dv^dp]"),
        "global_coefficient_count": 3,
        "pointwise_coefficients_forbidden": True,
        "basis_order": ("du_wedge_dv", "du_wedge_dp", "dv_wedge_dp"),
        "calibration_centers": A_CENTERS,
        "calibration_basis_matrices": calibration_matrices,
        "calibration_design_shape": (18, 3),
        "local_basis_determinants": local_determinants,
        "all_local_basis_determinants_positive": all(value > 0 for value in local_determinants),
        "gram_determinant": gram_determinant,
        "gram_determinant_positive": gram_determinant > 0,
        "gram_determinant_sha256": fraction_vector_sha256((gram_determinant,)),
        "exact_gram_infinity_condition": gram_condition,
        "calibration_rank": 3,
        "calibration_scalar_constraints": 18,
        "calibration_overdetermination": 15,
        "confirmation_centers": V_CENTERS,
        "confirmation_basis_matrices": confirmation_matrices,
        "confirmation_basis_determinants": confirmation_determinants,
        "confirmation_points_eligible": all(value != 0 for value in confirmation_determinants),
        "heldout_center": HELDOUT_CENTER,
        "heldout_area_vector": HELDOUT_AREA_VECTOR,
        "heldout_basis": heldout_basis,
        "heldout_basis_densities": heldout_densities,
        "heldout_basis_densities_nonzero": all(value != 0 for value in heldout_densities),
        "heldout_basis_density_sha256": fraction_vector_sha256(heldout_densities),
        "connection_exterior_derivative_identity": (
            "d[k0/2*(u*dv-v*du)+k1*u*dp+k2*v*dp]" "=k0*du^dv+k1*du^dp+k2*dv^dp"
        ),
        "basis_exterior_derivative_is_structurally_closed": True,
        "gauge_invariant_scalar_inputs": ("Re_Wilson", "Im_Wilson", "Tr_rho2"),
        "coordinate_covariance_records": covariance_records,
        "coordinate_covariance_exact": all(record["matches"] is True for record in covariance_records),
        "units": {
            "u_v_p": "dimensionless",
            "basis_two_forms": "dimensionless",
            "kappa": "count",
            "Fhat": "count",
        },
        "sigma_predictor_record": sigma_record,
        "count_reversal_rule": "sigma_to_minus_sigma_negates_Bhat_and_Fhat",
        "zero_current_rule": "sigma_zero_gives_Bhat_zero_and_Fhat_zero",
        "zero_chord_wilson_jet": zero_wilson,
        "zero_chord_Wilson_jet_zero": all(
            value == 0 for item in zero_wilson for value in (item if type(item) is tuple else (item,))
        ),
        "flux_conjugation_records": conjugation_records,
        "conjugate_bases_rank_three": all(
            record["pulled_conjugate_determinant"] != 0 for record in conjugation_records
        ),
        "simple_flux_conjugation_parity_holds": all(
            record["simple_parity_holds"] is True for record in conjugation_records
        ),
        "simple_flux_conjugation_parity_claimed": False,
        "flux_conjugation_scope": ("exact_conjugate_recompute_only; no unproved fixed-parity response law"),
        "basis_scope": "exact_frozen_rational_points_only",
        "uniform_purity_bias_derivative_box_proved": False,
        "reservation_status": RESERVATION_STATUS,
        "response_accessed": False,
        "coefficients_fitted": False,
        "confirmation_prediction_run": False,
        "heldout_prediction_run": False,
        "disposition": "ELIGIBLE_PRE_RESPONSE_ONLY",
    }
    payload = tuple((key, record[key]) for key in P0_PAYLOAD_KEYS)
    certificate_sha256 = canonical_exact_sha256(payload)
    record["certificate_sha256"] = certificate_sha256
    record["reviewed_certificate_sha256_matches"] = (
        certificate_sha256 == EXPECTED_P0_CERTIFICATE_SHA256
        and record["gram_determinant_sha256"] == EXPECTED_GRAM_DETERMINANT_SHA256
        and record["heldout_basis_density_sha256"] == EXPECTED_HELDOUT_DENSITY_SHA256
    )
    return freeze_exact_record(record)  # type: ignore[return-value]


def connection_eligibility_certificate() -> MappingProxyType:
    """Return a fresh immutable view over the cached exact geometry result."""

    return freeze_exact_record(dict(_cached_connection_eligibility_certificate()))  # type: ignore[return-value]

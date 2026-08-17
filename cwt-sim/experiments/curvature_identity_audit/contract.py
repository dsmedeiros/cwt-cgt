"""Frozen contract and fail-closed registry for the curvature identity audit."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class CurvatureAuditContract:
    """Every mathematical convention and claim boundary used by the audit."""

    experiment_id: str = "curvature_identity_audit"
    parameter_orientation: str = "first_coordinate_wedge_second_coordinate"
    berry_connection_convention: str = "A_i=-i<psi|partial_i psi>"
    projective_curvature_convention: str = "Omega_ij=+2 Im<C_i|C_j>=partial_i A_j-partial_j A_i"
    response_curvature_convention: str = "F_ij=partial_i beta_j-partial_j beta_i"
    alignment_coefficient_type: str = "kappa in C^infty(Lambda;R)"
    pullback_condition: str = "sigma^*(d beta_R)-kappa sigma^*(P^*omega_FS)=0"
    local_potential_scope: str = "constant_kappa_contractible_gauge_patch_only"
    global_obstruction_scope: str = "periods_and_nonzero_chern_flux_checked"

    qp1_operator_id: str = "cwt.operator.L_map.qp1_builder"
    qp1_observable_sign: str = "O_i=+partial_i H"
    qp1_conventional_force_sign: str = "O_i=-partial_i H"
    qp1_gap_minimum: Fraction = Fraction(1, 5)
    qp1_chern_number: int = -1
    qp1_scope: str = "same_operator_kubo_qgt_calibration_only"

    benchmark_c_id: str = "benchmark_c"
    benchmark_c_branch_id: str = "C0"
    benchmark_c_phase_relaxation: Fraction = Fraction(7, 20)
    benchmark_c_current_gain: Fraction = Fraction(9, 20)
    benchmark_c_response_statistic: str = "fixed_tick_cycle_sum_not_legacy_mean"

    benchmark_d_id: str = "benchmark_d"
    benchmark_d_branch_id: str = "D0_exact_affine_stationary_branch"
    benchmark_d_generator: str = "A=(1/5)(K^T-I)-(1/25)I"
    benchmark_d_source: str = "c=(1/125)1"
    benchmark_d_observable: str = "O=diag(1,2,3,4,5)"
    benchmark_d_projective_encoding: str = "psi_j=sqrt(xbar_j),theta_j=0"
    benchmark_d_mixed_state_scope: str = "commuting_diagonal_uhlmann_statement_separate"

    future_minimum_full_rank_area_directions: int = 3
    future_heldout_oblique_required: bool = True
    future_pointwise_division_forbidden: bool = True
    future_tensor_map_must_be_frozen: bool = True

    fitted_or_pointwise_normalization_allowed: bool = False
    two_dimensional_quotient_is_predictive: bool = False
    unfrozen_tensor_map_allowed: bool = False
    limit_or_ontology_upgrade_allowed: bool = False
    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    claim_ceiling: str = (
        "internal authored QP-1 calibration and Benchmark-C/Benchmark-D analytic identity audit only; "
        "not universal CWT, physical response, empirical evidence, or a general CGT-response alignment law"
    )

    def jsonable(self) -> dict[str, Any]:
        """Return a strict-JSON representation preserving exact fractions."""

        def convert(value: Any) -> Any:
            if isinstance(value, Fraction):
                return {
                    "fraction": f"{value.numerator}/{value.denominator}",
                    "numerator": value.numerator,
                    "denominator": value.denominator,
                    "float": float(value),
                }
            if isinstance(value, tuple):
                return [convert(item) for item in value]
            if isinstance(value, dict):
                return {str(key): convert(item) for key, item in value.items()}
            return value

        return convert(asdict(self))


MODEL_CONTRACT = CurvatureAuditContract()

CANONICAL_CASE_DISPOSITION_ITEMS = (
    ("T0", "COMMON_ORIGIN_PULLBACK_THEOREM_PASS"),
    ("QP1", "SAME_CURVATURE_CALIBRATION_ONLY"),
    ("BC", "SAME_PRIMITIVE_MANIFOLD_DIFFERENT_CONNECTIONS_DERIVED_MIXED_HESSIAN"),
    ("BD", "SAME_MODEL_ZERO_SET_OBSTRUCTION"),
    ("FUTURE", "ALIGNMENT_TEST_REQUIREMENTS_FROZEN_NO_CURRENT_PASS"),
    ("SCOPE", "PASS_INTERNAL_ANALYTIC_NO_EMPIRICAL_EVIDENCE"),
)

CANONICAL_CASE_GATE_OWNERSHIP = (
    (
        "T0",
        (
            "common_origin_branch_tangent_equivalence",
            "local_exact_potential_scope",
            "global_period_and_chern_obstructions",
            "alignment_refusal_matrix",
        ),
    ),
    (
        "QP1",
        (
            "qp1_same_operator_projector",
            "qp1_exact_connection_curvature_gap",
            "qp1_kubo_sign_and_antisymmetrization",
            "qp1_patch_transition_and_chern",
            "qp1_spectral_regression_only",
        ),
    ),
    (
        "BC",
        (
            "benchmark_c_core_branch_binding",
            "benchmark_c_exact_berry_pullback",
            "benchmark_c_exact_response_pullback",
            "benchmark_c_exact_response_decomposition",
            "benchmark_c_center_oracle_and_nonconstant_quotient",
            "benchmark_c_gain_and_relaxation_nulls",
            "benchmark_c_numerical_regressions_only",
            "benchmark_c_cycle_sum_scope",
        ),
    ),
    (
        "BD",
        (
            "benchmark_d_shared_model_provenance",
            "benchmark_d_exact_stationary_positive_no_floor",
            "benchmark_d_real_projective_lift_zero_curvature",
            "benchmark_d_exact_nonzero_response",
            "benchmark_d_zero_set_obstruction",
            "benchmark_d_mixed_state_scope",
        ),
    ),
    ("FUTURE", ("future_alignment_fail_closed",)),
    ("SCOPE", ("claim_ceiling",)),
)


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def expected_case_dispositions() -> dict[str, str]:
    """Return a fresh mapping derived from the immutable canonical tuple."""

    return dict(CANONICAL_CASE_DISPOSITION_ITEMS)


def case_gate_ownership() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return immutable ordered ownership records."""

    return CANONICAL_CASE_GATE_OWNERSHIP


def canonical_registry_record() -> dict[str, object]:
    """Serialize ownership and dispositions independently with path-stable fingerprints."""

    dispositions = [
        {"case_id": case_id, "disposition": disposition}
        for case_id, disposition in CANONICAL_CASE_DISPOSITION_ITEMS
    ]
    ownership = [
        {"case_id": case_id, "gate_names": list(gate_names)}
        for case_id, gate_names in CANONICAL_CASE_GATE_OWNERSHIP
    ]
    return {
        "schema_version": 1,
        "case_dispositions": dispositions,
        "case_dispositions_sha256": hashlib.sha256(_canonical_json_bytes(dispositions)).hexdigest(),
        "gate_ownership": ownership,
        "gate_ownership_sha256": hashlib.sha256(_canonical_json_bytes(ownership)).hexdigest(),
    }


def contract_issues(contract: CurvatureAuditContract) -> list[str]:
    """Reject every deviation from the reviewed analytic specialization."""

    issues = []
    for field_name in MODEL_CONTRACT.__dataclass_fields__:
        if getattr(contract, field_name) != getattr(MODEL_CONTRACT, field_name):
            issues.append(f"CONTRACT_MISMATCH:{field_name}")
    if contract.future_minimum_full_rank_area_directions < 3:
        issues.append("FUTURE_ALIGNMENT_DIMENSION_BELOW_THREE")
    if not contract.future_heldout_oblique_required:
        issues.append("FUTURE_HELDOUT_OBLIQUE_NOT_REQUIRED")
    if contract.fitted_or_pointwise_normalization_allowed:
        issues.append("FITTED_OR_POINTWISE_NORMALIZATION_ALLOWED")
    if contract.two_dimensional_quotient_is_predictive:
        issues.append("TAUTOLOGICAL_2D_QUOTIENT_TREATED_AS_PREDICTION")
    if contract.unfrozen_tensor_map_allowed:
        issues.append("UNFROZEN_TENSOR_MAP_ALLOWED")
    if contract.limit_or_ontology_upgrade_allowed:
        issues.append("LIMIT_OR_ONTOLOGY_UPGRADE_ALLOWED")
    return sorted(set(issues))

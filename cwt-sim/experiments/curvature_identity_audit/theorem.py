"""Executable analytic program for the curvature identity audit."""

from __future__ import annotations

from fractions import Fraction
from typing import Any, Mapping

from .benchmark_c import (
    EXPECTED_J_XK_RESPONSE_CENTER,
    EXPECTED_J_XK_RESPONSE_GRADIENT,
    EXPECTED_J_XP_RESPONSE_CENTER,
    EXPECTED_J_XP_RESPONSE_GRADIENT,
    EXPECTED_OMEGA_CENTER,
    EXPECTED_OMEGA_GRADIENT,
    EXPECTED_QUOTIENT_CENTER,
    EXPECTED_QUOTIENT_GRADIENT,
    EXPECTED_RESPONSE_CENTER,
    EXPECTED_RESPONSE_GRADIENT,
    benchmark_c_certificate,
)
from .benchmark_d import benchmark_d_certificate
from .classifier import apply_fail_only_overrides, case_dispositions, registry_gate_names
from .common_origin import (
    common_origin_certificate,
    future_alignment_requirements,
    obstruction_certificate,
    refusal_certificate,
)
from .contract import (
    MODEL_CONTRACT,
    CurvatureAuditContract,
    canonical_registry_record,
    contract_issues,
    expected_case_dispositions,
)
from .qp1 import qp1_certificate


def build_certificates(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, dict[str, object]]:
    """Build every case from source primitives without artifact inputs."""

    return {
        "common_origin": common_origin_certificate(contract),
        "obstructions": obstruction_certificate(contract),
        "refusals": refusal_certificate(contract),
        "future": future_alignment_requirements(contract),
        "qp1": qp1_certificate(contract),
        "benchmark_c": benchmark_c_certificate(contract),
        "benchmark_d": benchmark_d_certificate(contract),
    }


def _fraction(value: Mapping[str, object]) -> Fraction:
    return Fraction(int(value["numerator"]), int(value["denominator"]))


def natural_gate_inputs(
    certificates: Mapping[str, Mapping[str, Any]],
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, tuple[bool, str, Any]]:
    """Recompute every live gate from certificate semantics."""

    common = certificates["common_origin"]
    obstructions = certificates["obstructions"]
    refusals = certificates["refusals"]
    future = certificates["future"]
    qp1 = certificates["qp1"]
    benchmark_c = certificates["benchmark_c"]
    benchmark_d = certificates["benchmark_d"]
    c_center = benchmark_c["center"]
    c_decomposition = c_center["decomposition"]
    c_regression = benchmark_c["numerical_regressions"]
    c_core = benchmark_c["core_branch_regression"]
    d_oracle = benchmark_d["response_oracle"]
    d_projective = benchmark_d["projective_regression"]
    q_regression = qp1["regression"]
    issues = contract_issues(contract)

    natural: dict[str, tuple[bool, str, Any]] = {
        "common_origin_branch_tangent_equivalence": (
            common["necessary"] is True
            and common["sufficient"] is True
            and common["alignment_coefficient"] == contract.alignment_coefficient_type
            and common["response_one_form_pullback"] == "B_R=sigma^*beta_R in Omega^1(Lambda)"
            and common["berry_connection_pullback"] == "A_Lambda=sigma^*P^*a_B in Omega^1(U)"
            and common["necessary_and_sufficient_condition"] == contract.pullback_condition
            and common["ambient_equality_not_required"] is True,
            "alignment is exactly equality of the pulled-back two-forms on every branch tangent pair",
            common,
        ),
        "local_exact_potential_scope": (
            obstructions["local_scope_id"] == "constant_kappa_contractible_gauge_patch_only"
            and "d(B_R-kappa*A_Lambda)=0" in obstructions["constant_kappa_local_statement"]
            and "B_R-kappa*A_Lambda=d chi" in obstructions["constant_kappa_local_statement"]
            and "dkappa wedge A_Lambda" in obstructions["variable_kappa_warning"],
            (
                "the local exact-potential statement is restricted to constant kappa on a "
                "contractible gauge patch"
            ),
            obstructions,
        ),
        "global_period_and_chern_obstructions": (
            obstructions["periods_required"] is True
            and obstructions["chern_flux_required"] is True
            and "pulled-back periods" in obstructions["noncontractible_period_condition"]
            and obstructions["global_smooth_connection_claimed"] is False,
            "noncontractible periods and nonzero Chern flux are explicit global obstructions",
            obstructions,
        ),
        "alignment_refusal_matrix": (
            refusals["all_refused"] is True and all(refusals["refused"].values()),
            (
                "pointwise fitting, 2D quotient tautology, unfrozen maps, auxiliary states, and "
                "ontology upgrades are refused"
            ),
            refusals,
        ),
        "qp1_same_operator_projector": (
            qp1["classification"] == "SAME_CURVATURE_CALIBRATION_ONLY"
            and qp1["same_operator_and_projector"] is True
            and qp1["operator_id"] == contract.qp1_operator_id,
            "the state projector and Kubo perturbations derive from the same Hermitian QP-1 operator",
            {"classification": qp1["classification"], "operator_id": qp1["operator_id"]},
        ),
        "qp1_exact_connection_curvature_gap": (
            qp1["connection_north"] == "A_x=2*pi*sin(pi*y/2)^2;A_y=0"
            and qp1["curvature"] == "Omega_xy=-pi^2*sin(pi*y)"
            and qp1["gap_interval"] == ["1/5", "3/5"],
            "A, Omega, and the positive spectral gap are analytic on the declared chart",
            {
                "connection": qp1["connection_north"],
                "curvature": qp1["curvature"],
                "gap": qp1["gap_interval"],
            },
        ),
        "qp1_kubo_sign_and_antisymmetrization": (
            qp1["positive_observable_result"] == "K_[xy]=(K_xy-K_yx)/2=+Omega_xy"
            and qp1["conventional_observable_result"] == "K_[xy]=-Omega_xy"
            and qp1["full_antisymmetrization"] == "K_xy-K_yx=2*K_[xy]",
            "+dH gives +Omega, -dH gives -Omega, and full antisymmetrization is twice the half convention",
            {
                "positive": qp1["positive_observable_result"],
                "conventional": qp1["conventional_observable_result"],
                "factor": qp1["full_antisymmetrization"],
            },
        ),
        "qp1_patch_transition_and_chern": (
            qp1["chern_number"] == -1
            and qp1["global_smooth_connection_exists"] is False
            and qp1["north_south_transition"] == "psi_S=exp(-i*2*pi*x)psi_N;A_S=A_N-2*pi*dx",
            "the north/south transition yields Chern number -1 and forbids a global smooth connection",
            {
                "transition": qp1["north_south_transition"],
                "chern_number": qp1["chern_number"],
            },
        ),
        "qp1_spectral_regression_only": (
            q_regression["role"] == "numerical_spectral_implementation_regression_not_proof"
            and q_regression["maximum_positive_sign_error"] < 1.0e-7
            and q_regression["maximum_conventional_negative_sign_error"] < 1.0e-7
            and q_regression["maximum_projector_error"] < 1.0e-12
            and q_regression["minimum_sampled_gap"] >= 0.199999999,
            "numerical eigensystem evaluation cross-checks but does not establish the exact identity",
            q_regression,
        ),
        "benchmark_c_core_branch_binding": (
            c_core["maximum_probability_error"] < 1.0e-12
            and c_core["maximum_phase_error"] < 1.0e-12
            and c_core["maximum_kernel_error"] < 1.0e-12,
            "the analytic p, theta, and K formulas equal the core Benchmark-C C0 branch on the frozen patch",
            c_core,
        ),
        "benchmark_c_exact_berry_pullback": (
            _fraction(c_center["omega_center"]) == EXPECTED_OMEGA_CENTER
            and _fraction(c_center["berry_connection_curvature_identity_error"]) == 0,
            "A=sum p dtheta and Omega=dA reproduce the exact 7/48 center value",
            {
                "omega": c_center["omega_center"],
                "identity_error": c_center["berry_connection_curvature_identity_error"],
            },
        ),
        "benchmark_c_exact_response_pullback": (
            _fraction(c_center["response_curvature_center"]) == EXPECTED_RESPONSE_CENTER
            and tuple(_fraction(item) for item in c_center["response_curvature_gradient"])
            == EXPECTED_RESPONSE_GRADIENT,
            "beta=-(1-alpha)/alpha H.dtheta and F=d beta reproduce the exact center response jet",
            {
                "response": c_center["response_curvature_center"],
                "gradient": c_center["response_curvature_gradient"],
            },
        ),
        "benchmark_c_exact_response_decomposition": (
            c_center["response_exterior_derivative_formula"] == "d beta_R=-m dJ_x wedge dtheta"
            and c_center["phase_gradient_total_derivative_formula"] == "dJ_x=J_xp dp+J_xx dtheta+J_xK dK"
            and c_center["J_xx_is_symmetric_hessian"] is True
            and _fraction(c_decomposition["response_curvature_J_xp_dp"]["center"])
            == EXPECTED_J_XP_RESPONSE_CENTER
            and tuple(_fraction(item) for item in c_decomposition["response_curvature_J_xp_dp"]["gradient"])
            == EXPECTED_J_XP_RESPONSE_GRADIENT
            and _fraction(c_decomposition["response_curvature_J_xK_dK"]["center"])
            == EXPECTED_J_XK_RESPONSE_CENTER
            and tuple(_fraction(item) for item in c_decomposition["response_curvature_J_xK_dK"]["gradient"])
            == EXPECTED_J_XK_RESPONSE_GRADIENT
            and all(
                _fraction(c_decomposition[name][part]) == 0
                for name in ("response_curvature_J_xx_dtheta", "response_curvature_d2theta")
                for part in ("center",)
            )
            and all(
                _fraction(item) == 0
                for name in ("response_curvature_J_xx_dtheta", "response_curvature_d2theta")
                for item in c_decomposition[name]["gradient"]
            )
            and _fraction(c_center["decomposition_residual"]["center"]) == 0
            and all(_fraction(item) == 0 for item in c_center["decomposition_residual"]["gradient"])
            and all(_fraction(item) == 0 for item in c_center["theta_hessian_antisymmetric_residual"]),
            (
                "d beta_R=-m dJ_x wedge dtheta with dJ_x=J_xp dp+J_xx dtheta+J_xK dK; "
                "d2theta and symmetric J_xx cancel while mixed J_xp/J_xK remain"
            ),
            {
                "decomposition": c_decomposition,
                "residual": c_center["decomposition_residual"],
            },
        ),
        "benchmark_c_center_oracle_and_nonconstant_quotient": (
            _fraction(c_center["quotient_center"]) == EXPECTED_QUOTIENT_CENTER
            and tuple(_fraction(item) for item in c_center["omega_gradient"]) == EXPECTED_OMEGA_GRADIENT
            and tuple(_fraction(item) for item in c_center["quotient_gradient"]) == EXPECTED_QUOTIENT_GRADIENT
            and c_center["quotient_gradient_nonzero"] is True,
            (
                "the exact quotient has the reviewed center value and nonzero exact gradient, so "
                "it is not constant"
            ),
            {
                "quotient": c_center["quotient_center"],
                "gradient": c_center["quotient_gradient"],
            },
        ),
        "benchmark_c_gain_and_relaxation_nulls": (
            _fraction(benchmark_c["gain_zero_response"]) == 0
            and _fraction(benchmark_c["alpha_one_response"]) == 0
            and benchmark_c["gain_scaling_exact"] is True
            and benchmark_c["omega_independent_of_gain_and_alpha"] is True,
            "gain=0 and alpha=1 null response while Omega persists, and response scales exactly with gain",
            {
                "gain_zero": benchmark_c["gain_zero_response"],
                "alpha_one": benchmark_c["alpha_one_response"],
                "gain_scaling": benchmark_c["gain_scaling_exact"],
            },
        ),
        "benchmark_c_numerical_regressions_only": (
            c_regression["role"] == "finite_difference_and_wilson_implementation_regressions_not_proof"
            and c_regression["response_absolute_error"] < 1.0e-9
            and c_regression["projective_absolute_error"] < 1.0e-9
            and c_regression["wilson_absolute_error"] < 1.0e-8,
            "finite differences and Wilson flux cross-check the analytic proof without supplying it",
            c_regression,
        ),
        "benchmark_c_cycle_sum_scope": (
            benchmark_c["response_statistic_scope"] == "fixed_tick_cycle_sum_not_legacy_mean"
            and benchmark_c["legacy_mean_is_same_curvature_response"] is False
            and benchmark_c["finite_difference_or_wilson_used_as_analytic_acceptance"] is False,
            (
                "the theorem uses a fixed-tick cycle sum; the legacy sample mean is not promoted "
                "to the same response"
            ),
            {
                "scope": benchmark_c["response_statistic_scope"],
                "legacy_mean_promoted": benchmark_c["legacy_mean_is_same_curvature_response"],
            },
        ),
        "benchmark_d_shared_model_provenance": (
            benchmark_d["same_A_c_O_provenance"] is True
            and benchmark_d["model_identity_sha256"]
            == benchmark_d["geometry_model_identity_sha256"]
            == benchmark_d["response_model_identity_sha256"]
            and benchmark_d["named_core_observable_error"] == 0.0,
            "geometry and response use the identical exact A, c, and named mean-position O identity",
            {
                "identity": benchmark_d["model_identity_sha256"],
                "observable_error": benchmark_d["named_core_observable_error"],
            },
        ),
        "benchmark_d_exact_stationary_positive_no_floor": (
            all(_fraction(item) == 0 for item in benchmark_d["center_stationary_residual"])
            and _fraction(benchmark_d["center_trace"]) == 1
            and _fraction(benchmark_d["uniform_positive_lower_bound"]) == Fraction(4, 69)
            and benchmark_d["encoding_probability_floor_applied"] is False
            and benchmark_d["encoding_clip_applied"] is False
            and benchmark_d["encoding_projection_or_normalization_repair_applied"] is False,
            "xbar=-A^-1c is exact, normalized, uniformly positive, and encoded without floor/clip/repair",
            {
                "residual": benchmark_d["center_stationary_residual"],
                "trace": benchmark_d["center_trace"],
                "lower_bound": benchmark_d["uniform_positive_lower_bound"],
            },
        ),
        "benchmark_d_real_projective_lift_zero_curvature": (
            benchmark_d["projective_curvature_fraction"] == "0/1"
            and benchmark_d["center_lift_norm_error"] < 1.0e-15
            and benchmark_d["center_lift_maximum_imaginary_component"] == 0.0
            and d_projective["projective_curvature"] == 0.0,
            "the actual smooth positive stationary lift is real and normalized, hence A=Omega=0 exactly",
            {
                "omega": benchmark_d["projective_curvature_fraction"],
                "regression": d_projective,
            },
        ),
        "benchmark_d_exact_nonzero_response": (
            d_oracle["response_curvature_bd"]["fraction"] == "-28888766872100000000000/235345963257301712101"
            and benchmark_d["response_fraction_matches_formal"] is True
            and benchmark_d["response_curvature_nonzero"] is True,
            "the identical exact A,c,O model has the formal nonzero response curvature",
            d_oracle["response_curvature_bd"],
        ),
        "benchmark_d_zero_set_obstruction": (
            benchmark_d["projective_curvature_fraction"] == "0/1"
            and benchmark_d["response_curvature_nonzero"] is True
            and benchmark_d["finite_scalar_kappa_exists_at_center"] is False
            and benchmark_d["zero_preserving_homogeneous_linear_tensor_map_can_match"] is False
            and benchmark_d["arbitrary_nonlinear_or_affine_omega_only_map_ruled_out"] is False
            and benchmark_d["auxiliary_or_authored_constant_state_used"] is False
            and benchmark_d["finite_step_branch_used"] is False,
            (
                "Omega=0 with F!=0 rules out a finite scalar F=kappa*Omega and every frozen "
                "zero-preserving homogeneous linear tensor map for this encoding/readout"
            ),
            {
                "omega": benchmark_d["projective_curvature_fraction"],
                "response": d_oracle["response_curvature_bd"],
            },
        ),
        "benchmark_d_mixed_state_scope": (
            benchmark_d["projective_encoding_is_mixed_density"] is False
            and benchmark_d["mixed_density_used_to_prove_projective_zero"] is False
            and "separate commuting" in benchmark_d["mixed_density_statement"],
            "the diagonal mixed-state Uhlmann-null statement is separate from the projective proof",
            benchmark_d["mixed_density_statement"],
        ),
        "future_alignment_fail_closed": (
            future["minimum_full_rank_area_directions"] >= 3
            and future["heldout_oblique_direction_required"] is True
            and future["pointwise_division_forbidden"] is True
            and future["tensor_map_frozen_before_response"] is True
            and future["current_audit_supplies_future_alignment_pass"] is False,
            (
                "a future positive CWT alignment test needs >=3 full-rank directions and held-out "
                "oblique prediction"
            ),
            future,
        ),
        "claim_ceiling": (
            not issues
            and contract.disposition == "PASS_INTERNAL_ANALYTIC"
            and contract.evidence_status == "NO_EMPIRICAL_EVIDENCE"
            and "not universal CWT" in contract.claim_ceiling
            and qp1["finite_speed_response_claimed"] is False
            and qp1["live_cwt_response_claimed"] is False,
            (
                "the result is internal analytic only, with no empirical, physical, universal-CWT, "
                "or alignment upgrade"
            ),
            {"issues": issues, "claim_ceiling": contract.claim_ceiling},
        ),
    }
    if set(natural) != set(registry_gate_names()):
        raise RuntimeError("natural gate construction does not match the exact registry")
    return natural


def execute_program(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
    gate_overrides: Mapping[str, bool] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute the complete analytic audit with monotone fail-only mutations."""

    certificates = build_certificates(contract)
    gates = apply_fail_only_overrides(
        natural_gate_inputs(certificates, contract),
        overrides=gate_overrides,
    )
    cases = case_dispositions(gates)
    failed = [gate.name for gate in gates if not gate.passed]
    all_cases_match = cases == expected_case_dispositions()
    all_pass = not failed and all_cases_match
    summary = {
        "experiment_id": contract.experiment_id,
        "disposition": "PASS_INTERNAL_ANALYTIC" if all_pass else "FAIL_INTERNAL_ANALYTIC",
        "evidence_status": contract.evidence_status,
        "all_gates_pass": all_pass,
        "failed_gates": failed,
        "case_dispositions": cases,
        "canonical_registry": canonical_registry_record(),
        "claim_ceiling": contract.claim_ceiling,
        "metrics": {
            "qp1_chern_number": certificates["qp1"]["chern_number"],
            "benchmark_c_omega_center": certificates["benchmark_c"]["center"]["omega_center"],
            "benchmark_c_response_center": certificates["benchmark_c"]["center"]["response_curvature_center"],
            "benchmark_c_quotient_gradient": certificates["benchmark_c"]["center"]["quotient_gradient"],
            "benchmark_d_projective_curvature": certificates["benchmark_d"]["projective_curvature_fraction"],
            "benchmark_d_response_curvature": certificates["benchmark_d"]["response_oracle"][
                "response_curvature_bd"
            ],
        },
        "gates": [gate.jsonable() for gate in gates],
    }
    records = [
        {"record_type": "contract", "value": contract.jsonable()},
        *[
            {"record_type": "certificate", "name": name, "value": value}
            for name, value in certificates.items()
        ],
        *[{"record_type": "gate", **gate.jsonable()} for gate in gates],
    ]
    return summary, records

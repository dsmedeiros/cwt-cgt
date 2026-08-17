"""Fail-closed execution of the Benchmark D Lindblad proof certificates."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping

from .certificates import all_certificates
from .contract import (
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    MODEL_CONTRACT,
    LindbladProofContract,
    contract_issues,
)


@dataclass(frozen=True)
class Gate:
    name: str
    passed: bool
    requirement: str
    observed: object

    def jsonable(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": "pass" if self.passed else "fail",
            "requirement": self.requirement,
            "observed": self.observed,
        }


def _gate(name: str, passed: bool, requirement: str, observed: object) -> Gate:
    return Gate(name=name, passed=bool(passed), requirement=requirement, observed=observed)


@lru_cache(maxsize=1)
def _base_certificates() -> dict[str, object]:
    return all_certificates()


def build_gates(
    certificates: Mapping[str, Any],
    contract: LindbladProofContract = MODEL_CONTRACT,
) -> list[Gate]:
    """Build every live analytic gate directly from executable certificate fields."""

    binding = certificates["core_binding"]
    affine = certificates["core_affine_equivalence"]
    stationary = certificates["stationary"]
    contraction = certificates["contraction"]
    response = certificates["exact_response"]
    loop = certificates["loop_convention"]
    dynamic = certificates["dynamic"]
    nulls = certificates["nulls_and_covariance"]
    benchmark_c = certificates["benchmark_c_null"]
    projective = certificates["projective_no_go"]
    invalid = nulls["invalid_contract_issues"]
    primary_dynamic = dynamic["scale_certificates"][0]

    gates = [
        _gate(
            "explicit_contract",
            not contract_issues(contract),
            "all reviewed model, clock, path, readout, and scope fields equal the frozen contract",
            contract_issues(contract),
        ),
        _gate(
            "d0_core_kernel_and_readout",
            binding["maximum_kernel_error"] < 1e-14
            and binding["maximum_phase_error"] == 0.0
            and binding["observable_maximum_absolute_error"] == 0.0
            and binding["observable_hermiticity_error"] == 0.0
            and binding["all_config_fields_explicit_and_equal"] is True
            and binding["clipping_inactive_on_box"] is True,
            "explicit D0 K, named mean_position operator, every config field, and inactive clips match core",
            binding,
        ),
        _gate(
            "affine_population_generator",
            affine["affine_source_required_norm"] == 0.04,
            "the exact diagonal model is A=(1/5)(K^T-I)-(1/25)I with source (1/125)1",
            affine["affine_source_required_norm"],
        ),
        _gate(
            "diagonal_invariant_subspace_core_equivalence",
            max(
                affine["maximum_diagonal_rhs_error"],
                affine["maximum_offdiagonal_rhs_error"],
                affine["maximum_trace_preservation_error"],
                affine["maximum_superoperator_deviation_error"],
                affine["maximum_affine_source_error"],
            )
            < 1e-14
            and affine["semantic_scope"] == "complete_diagonal_invariant_subspace_not_full_superoperator"
            and affine["control_point_count"] == 5
            and affine["diagonal_population_basis_count"] == 5
            and affine["traceless_diagonal_deviation_basis_count"] == 4,
            (
                "core RHS/superoperator agree on the complete diagonal invariant subspace "
                "at four corners and center"
            ),
            affine,
        ),
        _gate(
            "trace_norm_contraction",
            contraction["M"]["fraction"] == "1/1" and contraction["tau"]["fraction"] == "25/1",
            "uniform traceless-Hermitian trace-norm propagator bound has M=1 and tau=25",
            contraction,
        ),
        _gate(
            "frozen_inverse_bound",
            contraction["inverse_bound_KJ"]["fraction"] == "25/1",
            "the branch inverse is uniformly bounded by K_J<=25 in the declared norm",
            contraction["inverse_bound_KJ"],
        ),
        _gate(
            "exact_stationary_branch",
            stationary["maximum_exact_stationary_residual"]["fraction"] == "0/1"
            and stationary["maximum_exact_trace_error"]["fraction"] == "0/1",
            "the exact affine linear solve is normalized and stationary without Euler projection",
            stationary,
        ),
        _gate(
            "uniform_full_rank_floor",
            stationary["uniform_full_rank_floor"]["fraction"] == "4/69"
            and stationary["uniform_floor_below_sampled_minimum"] is True,
            "every fixed population component is at least the analytic floor 4/69 on the box",
            stationary,
        ),
        _gate(
            "exact_center_oracle",
            certificates["formal_fraction_matches"] is True,
            "the center stationary solve, one-form, derivatives, and F_bd reproduce the formal fraction",
            response,
        ),
        _gate(
            "nonzero_response_curvature",
            response["response_curvature_bd"]["numerator"] != 0
            and response["response_curvature_bd"]["float"] < 0.0,
            "F_bd is finite, nonzero, and negative in the frozen orientation",
            response["response_curvature_bd"],
        ),
        _gate(
            "circle_orientation_reversal",
            loop["exact_reverse_maximum_error"] == 0.0
            and loop["duplicate_endpoint_stored"] is False
            and loop["every_sampled_loop_point_inside_box"] is True
            and loop["sampling_role"] == "diagnostic_only_not_domain_acceptance"
            and loop["analytic_extrema_inside_box"] is True
            and all(item["fraction"] == "1/100" for item in loop["exact_face_margins"]),
            (
                "CW is the exact reverse, no endpoint is duplicated, and exact circle extrema "
                "have 1/100 box margins"
            ),
            loop,
        ),
        _gate(
            "qanti_and_did_factor_two",
            loop["qanti_definition"] == "(Q_ccw-Q_cw)/2"
            and loop["ordinary_difference_in_differences"] == "Q_ccw-Q_cw=2*Qanti",
            "orientation-odd Qanti uses the half difference and ordinary DID equals 2 Qanti",
            {
                "qanti": loop["qanti_definition"],
                "did": loop["ordinary_difference_in_differences"],
            },
        ),
        _gate(
            "identity_readout_null",
            nulls["identity_readout_curvature"]["fraction"] == "0/1",
            "the identity readout has exactly zero response curvature",
            nulls["identity_readout_curvature"],
        ),
        _gate(
            "linear_readout_covariance",
            nulls["scaled_covariance_exact"] is True,
            "sign reversal and scaling of the readout scale F_bd exactly",
            nulls["scaled_readout_curvatures"],
        ),
        _gate(
            "zero_depolarization_refused",
            bool(invalid["zero_depolarization"])
            and contract.depolarizing_rate == MODEL_CONTRACT.depolarizing_rate
            and contract.depolarizing_rate > 0,
            "zero depolarization cannot receive the contraction certificate",
            invalid["zero_depolarization"],
        ),
        _gate(
            "coherent_or_gauge_variant_refused",
            bool(invalid["nonzero_coherent"])
            and bool(invalid["nonzero_site_gauge"])
            and contract.coherent_scale == 0
            and contract.site_potential_scale == 0,
            "nonzero coherent or site-potential variants are outside this specialization",
            {
                "coherent": invalid["nonzero_coherent"],
                "site_gauge": invalid["nonzero_site_gauge"],
            },
        ),
        _gate(
            "euler_projection_backend_refused",
            bool(invalid["euler_projection_backend"])
            and contract.flow_backend == MODEL_CONTRACT.flow_backend,
            "Euler plus PSD projection is forbidden on the theorem path",
            invalid["euler_projection_backend"],
        ),
        _gate(
            "clock_reversal_initialization_mutations_refused",
            bool(invalid["wrong_dt"])
            and bool(invalid["wrong_reversal"])
            and bool(invalid["wrong_initialization"])
            and bool(invalid["nonuniform_clock"])
            and contract.dt == MODEL_CONTRACT.dt
            and contract.reversal_convention == MODEL_CONTRACT.reversal_convention
            and contract.initialization == MODEL_CONTRACT.initialization
            and contract.slow_drive_clock_id == MODEL_CONTRACT.slow_drive_clock_id
            and contract.slow_drive_clock_definition == MODEL_CONTRACT.slow_drive_clock_definition
            and contract.time_domain == "uncalibrated_continuous_model_time"
            and contract.generator_rate_units == "inverse_model_time"
            and contract.duration_units == "model_time"
            and contract.integrated_response_units == "mean_position_index_times_model_time"
            and contract.physical_time_calibration_status
            == "absent_requires_external_clock_and_readout_calibration",
            "wrong timing, reversal, and initialization contracts fail closed",
            {
                "clock": invalid["wrong_dt"],
                "reversal": invalid["wrong_reversal"],
                "initialization": invalid["wrong_initialization"],
                "nonuniform_clock": invalid["nonuniform_clock"],
            },
        ),
        _gate(
            "affine_source_omission_refused",
            nulls["affine_source_omission_changes_fixed_equation"] is True
            and nulls["affine_source_l1_norm"]["fraction"] == "1/25",
            "the depolarizing affine source is nonzero and may not be omitted",
            nulls["affine_source_l1_norm"],
        ),
        _gate(
            "benchmark_c_unital_stationary_null",
            benchmark_c["maximum_fixed_rhs_error"] < 1e-14
            and benchmark_c["maximum_centered_readout_absolute_value"] == 0.0
            and benchmark_c["response_curvature_exact_fraction"] == "0/1",
            "Benchmark C has true stationary I/3 and zero response under this specialization",
            benchmark_c,
        ),
        _gate(
            "uniform_affine_slow_drive_clock",
            contract.slow_drive_clock_id == "uniform_affine_normalized_clock_v1"
            and contract.slow_drive_clock_definition
            == (
                "u=t/T;lambda_plus(t)=gamma_plus(u);"
                "lambda_minus(t)=lambda_plus(T-t)=gamma_plus(1-u);0<=t<=T"
            )
            and dynamic["slow_drive_clock_id"] == contract.slow_drive_clock_id
            and dynamic["slow_drive_clock_definition"] == contract.slow_drive_clock_definition
            and all(
                certificate["model_time_speed_bound"] == "sup_t||lambda_dot(t)||<=2*pi*s/T"
                and certificate["model_time_acceleration_bound"]
                == "sup_t||lambda_double_dot(t)||<=(2*pi)^2*s/T^2"
                for certificate in dynamic["scale_certificates"]
            ),
            "the C(s)/T proof uses the frozen affine u=t/T clock and its exact reverse",
            {
                "clock_id": dynamic["slow_drive_clock_id"],
                "definition": dynamic["slow_drive_clock_definition"],
                "bound_role": dynamic["clock_bound_role"],
            },
        ),
        _gate(
            "rigorous_curvature_and_line_interval",
            primary_dynamic["curvature_interval"]["upper"]["float"] < 0.0
            and primary_dynamic["line_integral_interval"]["upper"]["float"] < 0.0,
            "directed exact-rational intervals certify negative curvature and CCW line integral",
            {
                "curvature": primary_dynamic["curvature_interval"],
                "line": primary_dynamic["line_integral_interval"],
            },
        ),
        _gate(
            "analytic_remainder_certificate",
            primary_dynamic["duration_rule"] == "T0=2^ceil(log2(4*C(s)/L_min(s)))"
            and primary_dynamic["minimum_duration_T0"] > 0
            and primary_dynamic["negative_sign_certified"] is True
            and dynamic["trajectory_used_for_acceptance"] is False,
            "the C(s)/T bound and reviewed power-of-two T0 rule certify sign before any trajectory",
            {
                "C": primary_dynamic["remainder_constant_C"],
                "T0": primary_dynamic["minimum_duration_T0"],
                "rule": primary_dynamic["duration_rule"],
            },
        ),
        _gate(
            "fixed_and_joint_ladders_certified",
            dynamic["all_signs_certified"] is True
            and dynamic["joint_area_relative_ratios_contract_by_at_least_one_half"] is True
            and all(
                item["two_times_right_le_left"] is True
                for item in dynamic["successive_joint_remainder_bounds"]
            ),
            (
                "fixed-scale T and joint s/T ladders are certified with every relative bound "
                "at most half its predecessor"
            ),
            {
                "fixed": dynamic["fixed_scale_duration_ladder"],
                "joint": dynamic["joint_area_relative_ladder"],
            },
        ),
        _gate(
            "smooth_positive_real_projective_state",
            projective["stationary_eigenvector_helper_used"] is False
            and projective["channel_equivalent_under_frozen_generator"] is True
            and projective["is_current_core_helper_branch_state_geometry"] is False
            and projective["minimum_exact_corner_probability"] > 0.0
            and projective["psi_norm_error"] < 1e-14
            and projective["all_sampled_psi_components_real"] is True,
            "the explicit positive-real normalized D0 state map is smooth on the frozen box",
            projective,
        ),
        _gate(
            "omega_zero_response_nonzero",
            projective["projective_curvature_bd_exact_fraction"] == "0/1"
            and projective["numerical_projective_curvature_bd"] == 0.0
            and response["response_curvature_bd"]["numerator"] != 0,
            "Omega_bd=0 exactly while the separately computed response F_bd is nonzero",
            {
                "omega": projective["projective_curvature_bd_exact_fraction"],
                "F_bd": response["response_curvature_bd"],
            },
        ),
    ]
    names = [gate.name for gate in gates]
    registered = [name for case_names in CASE_GATE_MAP.values() for name in case_names]
    if len(names) != len(set(names)):
        raise RuntimeError("duplicate live theorem gate name")
    if set(names) != set(registered):
        raise RuntimeError(
            f"live gate registry mismatch: orphan={sorted(set(names)-set(registered))}, "
            f"absent={sorted(set(registered)-set(names))}"
        )
    return gates


def derive_case_dispositions(gates: list[Gate]) -> dict[str, str]:
    """Derive every C1-C13 disposition solely from its registered live gates."""

    status = {gate.name: gate.passed for gate in gates}
    dispositions: dict[str, str] = {}
    for case_id, expected in EXPECTED_CASE_DISPOSITIONS.items():
        dispositions[case_id] = (
            expected
            if all(status[name] for name in CASE_GATE_MAP[case_id])
            else expected.removesuffix("_PASS") + "_FAIL"
        )
    return dispositions


def execute_program(
    contract: LindbladProofContract = MODEL_CONTRACT,
    *,
    gate_overrides: Mapping[str, bool] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute the internal analytic program with explicit fail-closed overrides for tests."""

    certificates = copy.deepcopy(_base_certificates())
    gates = build_gates(certificates, contract)
    if gate_overrides:
        known = {gate.name for gate in gates}
        unknown = set(gate_overrides) - known
        if unknown:
            raise ValueError(f"unknown gate override: {sorted(unknown)}")
        if any(type(value) is not bool for value in gate_overrides.values()):
            raise TypeError("gate overrides must be booleans")
        gates = [
            Gate(
                gate.name,
                gate.passed and gate_overrides.get(gate.name, True),
                gate.requirement,
                gate.observed,
            )
            for gate in gates
        ]
    cases = derive_case_dispositions(gates)
    failed = [gate.name for gate in gates if not gate.passed]
    all_gates_pass = not failed and cases == EXPECTED_CASE_DISPOSITIONS
    response = certificates["exact_response"]["response_curvature_bd"]
    primary_dynamic = certificates["dynamic"]["scale_certificates"][0]
    summary = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": "PASS_INTERNAL_ANALYTIC" if all_gates_pass else "FAIL_INTERNAL_ANALYTIC",
        "evidence_status": "NO_EMPIRICAL_EVIDENCE",
        "all_gates_pass": all_gates_pass,
        "failed_gates": failed,
        "case_dispositions": cases,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "contract": contract.jsonable(),
        "metrics": {
            "exact_response_curvature_fraction": response["fraction"],
            "exact_response_curvature_float": response["float"],
            "uniform_full_rank_floor": certificates["stationary"]["uniform_full_rank_floor"],
            "primary_scale": primary_dynamic["scale"],
            "primary_remainder_C": primary_dynamic["remainder_constant_C"],
            "primary_line_magnitude_lower": primary_dynamic["line_magnitude_lower"],
            "primary_duration_T0": primary_dynamic["minimum_duration_T0"],
            "projective_curvature_exact_fraction": certificates["projective_no_go"][
                "projective_curvature_bd_exact_fraction"
            ],
        },
        "gates": [gate.jsonable() for gate in gates],
    }
    records = [
        {"record_type": "certificate", "name": name, "value": value}
        for name, value in sorted(certificates.items())
    ] + [{"record_type": "gate", **gate.jsonable()} for gate in gates]
    return summary, records

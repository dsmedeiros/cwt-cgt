"""Gate orchestration for the named Benchmark D contractive response theorem."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import numpy as np

from .adapter import (
    authored_probability_inactivity,
    benchmark_d_three_step_diagnostics,
    constant_projective_reference_certificate,
    core_affine_equivalence,
    core_readout_certificate,
    phase10_benchmark_c_two_step_diagnostics,
)
from .contract import (
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    FORMAL_RESPONSE_CURVATURE,
    MODEL_CONTRACT,
)
from .exact_oracle import exact_margin_certificate, exact_response_oracle
from .fixed_branch import (
    ContractionCertificateError,
    analytic_response_curvature,
    contraction_certificate,
    fixed_branch_certificates,
    numerical_response_curvature,
)
from .response import (
    core_cycle_equivalence,
    fixed_loop_refinement,
    loop_domain_diagnostics,
    null_control_diagnostics,
    reverse_loop,
    shrinking_loop_refinement,
    square_loop,
)


@dataclass(frozen=True)
class Gate:
    """Deterministic analytic/numerical acceptance gate."""

    name: str
    requirement: str
    passed: bool

    def jsonable(self) -> dict[str, str]:
        return {
            "name": self.name,
            "requirement": self.requirement,
            "status": "pass" if self.passed else "fail",
        }


def derive_case_dispositions(gates: list[Gate]) -> dict[str, str]:
    """Derive every case from its registered gates, failing closed on any miss."""

    if set(CASE_GATE_MAP) != set(EXPECTED_CASE_DISPOSITIONS):
        raise AssertionError("case-to-gate registry is incomplete")
    if any(len(names) != len(set(names)) for names in CASE_GATE_MAP.values()):
        raise AssertionError("a case contains a duplicate gate registration")
    live_names = [gate.name for gate in gates]
    if len(live_names) != len(set(live_names)):
        raise AssertionError("live gate names must be unique")
    registered_names = {name for names in CASE_GATE_MAP.values() for name in names}
    if set(live_names) != registered_names:
        orphan_live = sorted(set(live_names) - registered_names)
        absent_live = sorted(registered_names - set(live_names))
        raise AssertionError(
            f"live gate registry mismatch: orphan_live={orphan_live}, absent_live={absent_live}"
        )
    gate_status = {gate.name: gate.passed for gate in gates}
    dispositions: dict[str, str] = {}
    for case_id, expected in EXPECTED_CASE_DISPOSITIONS.items():
        registered = CASE_GATE_MAP[case_id]
        if not registered:
            raise AssertionError(f"case {case_id} has no executable gate")
        missing = [name for name in registered if name not in gate_status]
        if missing:
            raise AssertionError(f"case {case_id} names unknown gates: {missing}")
        failed = [name for name in registered if not gate_status[name]]
        dispositions[case_id] = expected if not failed else f"FAIL_INTERNAL_ANALYTIC[{','.join(failed)}]"
    return dispositions


def _depolarizing_zero_refuses_certificate() -> bool:
    try:
        contraction_certificate(0.0)
    except ContractionCertificateError:
        return True
    return False


def _loop_convention_diagnostics() -> dict[str, object]:
    steps = 7
    path = square_loop(
        (float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion)),
        0.02,
        steps,
    )
    reverse = reverse_loop(path)
    return {
        "stored_points": len(path),
        "expected_stored_points": 4 * steps + 1,
        "updates": len(path) - 1,
        "expected_updates": 4 * steps,
        "closed_exactly": bool(np.array_equal(path[0], path[-1])),
        "reverse_exactly": bool(np.array_equal(reverse, path[::-1])),
        "duplicate_initial_sampled": False,
        "closing_endpoint_update_count": 1,
    }


@lru_cache(maxsize=1)
def _execute_program_cached() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute all authored theorem gates without external or empirical data."""

    exact_oracle = exact_response_oracle()
    margins = exact_margin_certificate()
    equivalence = core_affine_equivalence()
    readout = core_readout_certificate()
    projective_reference = constant_projective_reference_certificate()
    fixed = fixed_branch_certificates()
    analytic_curvature = analytic_response_curvature(
        float(MODEL_CONTRACT.center_bias),
        float(MODEL_CONTRACT.center_diffusion),
    )
    numerical_curvature = numerical_response_curvature()
    core_cycle = core_cycle_equivalence()
    fixed_loop = fixed_loop_refinement()
    shrinking = shrinking_loop_refinement()
    loop_domain = loop_domain_diagnostics()
    nulls = null_control_diagnostics()
    phase10 = phase10_benchmark_c_two_step_diagnostics()
    benchmark_d_three_step = benchmark_d_three_step_diagnostics()
    conventions = _loop_convention_diagnostics()
    contraction = contraction_certificate(float(MODEL_CONTRACT.depolarizing))
    authored_p_inactivity_error = authored_probability_inactivity()

    exact_curvature = float(exact_oracle.response_curvature_bd)
    fixed_rows = fixed_loop["rows"]
    shrinking_rows = shrinking["rows"]
    identity = nulls["identity_readout"]
    constant = nulls["constant_branch"]
    benchmark_c = nulls["benchmark_c"]

    gates = [
        Gate(
            "named_core_binding",
            "D0 analytic kernel and diagonal affine trace agree with core APIs",
            equivalence["max_kernel_error"] <= 1e-14
            and equivalence["max_affine_error"] <= 5e-14
            and equivalence["max_kraus_tp_error"] <= 5e-14
            and equivalence["max_projection_delta"] <= 5e-13
            and equivalence["max_fixed_point_api_error"] <= 2e-11
            and core_cycle["absolute_error"] <= 5e-10
            and authored_p_inactivity_error <= 1e-15,
        ),
        Gate(
            "named_core_readout_binding",
            "executed response path obtains core mean_position=diag(1,2,3,4,5)",
            readout["observable_name"] == "mean_position"
            and readout["core_function"] == "cwt.cgt.open_system.observable_operator"
            and readout["expected_diagonal"] == [1, 2, 3, 4, 5]
            and readout["maximum_absolute_error"] == 0.0
            and readout["hermiticity_error"] == 0.0,
        ),
        Gate(
            "exact_kraus_and_margin_certificate",
            "clip/support/rescale/square-root margins are strictly positive and TP is exact",
            all(
                margins[name]["float"] > 0.0
                for name in (
                    "clip_margin",
                    "minimum_active_kernel_entry",
                    "rescale_margin",
                    "sqrt_radicand_margin",
                )
            )
            and margins["core_rescale_branch_inactive"] is True
            and margins["maximum_exact_tp_error"]["fraction"] == "0/1"
            and all(item["fraction"] == "1/1" for item in margins["center_source_tp_totals"]),
        ),
        Gate(
            "global_contraction_certificate",
            "global trace/L1 factor is exactly 124/125",
            contraction["factor"] == 124.0 / 125.0
            and margins["global_trace_and_l1_contraction"]["fraction"] == "124/125",
        ),
        Gate(
            "true_full_rank_fixed_branch",
            "exact depolarizing floor gives full rank; sampled branch varies and residual is certified",
            fixed["max_fixed_residual_l1"] <= 1e-14
            and fixed["banach_error_upper_bound_l1"] <= 2e-12
            and fixed["max_trace_error"] <= 2e-14
            and fixed["global_depolarizing_eigenvalue_floor"] == 1.0 / 625.0
            and fixed["sampled_minimum_fixed_eigenvalue"] >= 0.14
            and fixed["sampled_fixed_branch_variation_l2"] >= 0.05
            and fixed["max_raw_fixed_step_delta_fro"] <= 1e-14,
        ),
        Gate(
            "exact_fraction_oracle",
            "Fraction-valued differentiation reproduces the independent formal F_bd fraction",
            exact_oracle.matches_formal_fraction
            and exact_oracle.response_curvature_bd == FORMAL_RESPONSE_CURVATURE,
        ),
        Gate(
            "nonzero_response_curvature",
            "analytic and independent numerical curls match the exact negative nonzero F_bd",
            exact_curvature < -1.0
            and abs(analytic_curvature - exact_curvature) <= 1e-8
            and abs(numerical_curvature - exact_curvature) <= 1e-4,
        ),
        Gate(
            "constant_projective_reference_zero",
            "separate channel-equivalent constant normalized state has exact Omega_bd=0",
            projective_reference["definition_sha256"]
            == "97fcd1ee64b25bf2c437a367ce6b9699df233cbe177a65bc51231ee68fd4ee02"
            and projective_reference["maximum_probability_variation"] == 0.0
            and projective_reference["maximum_phase_variation"] == 0.0
            and projective_reference["maximum_normalized_psi_variation"] == 0.0
            and projective_reference["psi_norm_error"] == 0.0
            and projective_reference["maximum_executed_p_to_declared_error"] == 0.0
            and projective_reference["maximum_executed_theta_to_declared_error"] == 0.0
            and projective_reference["maximum_executed_psi_to_declared_gauge_aligned_error"] == 0.0
            and projective_reference["maximum_executed_projector_to_declared_error"] == 0.0
            and projective_reference["omega_bd_exact_fraction"] == "0/1"
            and projective_reference["authored_stationary_probability_used_as_projective_branch"] is False
            and projective_reference["channel_equivalence_error"] == 0.0,
        ),
        Gate(
            "fixed_loop_one_over_n",
            "Q_anti approaches the finite-loop line integral with O(1/N) endpoint error",
            -1.05 <= fixed_loop["tail_log_slope"] <= -0.95
            and fixed_loop["tail_scaled_error_ratio"] <= 1.02
            and fixed_rows[-1]["absolute_error"] < fixed_rows[-2]["absolute_error"]
            and fixed_rows[-1]["q_anti"] < 0.0,
        ),
        Gate(
            "registered_loop_domain_containment",
            "every registered loop point is inside the certified closed D0 control box",
            loop_domain["all_registered_loops_contained"] is True
            and all(row["side"] <= 0.04 for row in loop_domain["rows"]),
        ),
        Gate(
            "shrinking_loop_area_limit",
            "development-selected in-box regression: growing N*s drives Q_anti/s^2 toward F_bd",
            all(
                shrinking_rows[index + 1]["updates_times_side"] > shrinking_rows[index]["updates_times_side"]
                for index in range(len(shrinking_rows) - 1)
            )
            and max(shrinking["successive_error_ratios"]) <= 0.60
            and shrinking["finest_relative_density_error"] <= 0.10
            and shrinking["numerical_tolerances_selected_during_harness_development"] is True,
        ),
        Gate(
            "fixed_solver_centering_budget",
            "conservative fixed-solver centering budget is negligible versus observed convergence error",
            shrinking["max_centering_budget_to_observed_density_error"] <= 1e-3,
        ),
        Gate(
            "loop_update_reversal_endpoint_contract",
            "CW is stored-sequence reverse; initial duplicate skipped; close updated once",
            conventions["stored_points"] == conventions["expected_stored_points"]
            and conventions["updates"] == conventions["expected_updates"]
            and conventions["closed_exactly"] is True
            and conventions["reverse_exactly"] is True
            and conventions["duplicate_initial_sampled"] is False
            and conventions["closing_endpoint_update_count"] == 1,
        ),
        Gate(
            "identity_readout_null",
            "identity readout has zero orientation-odd response",
            abs(identity["q_anti"]) <= 1e-10,
        ),
        Gate(
            "constant_branch_null",
            "constant fixed branch has zero orientation-odd response",
            abs(constant["q_anti"]) <= 1e-12,
        ),
        Gate(
            "depolarizing_zero_refusal",
            "depolarizing=0 cannot receive the strict 124/125 contraction certificate",
            _depolarizing_zero_refuses_certificate(),
        ),
        Gate(
            "benchmark_c_true_fixed_unital_null",
            "Benchmark C C0 has true fixed I/3 and zero centered primary response",
            benchmark_c["max_kernel_column_error"] <= 5e-15
            and benchmark_c["max_true_fixed_to_identity_over_three_fro"] <= 5e-14
            and abs(benchmark_c["centered_primary_cycle_sum"]) <= 1e-12,
        ),
        Gate(
            "phase10_benchmark_c_two_step_surrogate_rejected",
            "tracked Phase10 Benchmark-C branch_steps=2 surrogate is demonstrably not fixed",
            phase10["benchmark_id"] == "benchmark_c"
            and phase10["branch_id"] == "C0"
            and phase10["recorded_branch_steps"] == 2
            and phase10["historical_entry_explicit_branch_steps"] == 2
            and phase10["current_library_default_branch_steps"] == 3
            and phase10["recorded_dephasing_gamma"] == 0.2
            and phase10["surrogate_fixed_residual_fro"] >= 0.04
            and phase10["surrogate_to_true_fixed_fro"] >= 0.70,
        ),
    ]
    failed = [gate.name for gate in gates if not gate.passed]
    case_dispositions = derive_case_dispositions(gates)
    summary = {
        "schema_version": 1,
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": MODEL_CONTRACT.disposition if not failed else "FAIL_INTERNAL_ANALYTIC",
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "central_empirical_external_claim_status": "PROOF_INCOMPLETE",
        "numerics_are_not_the_analytic_proof": True,
        "no_study_pass": True,
        "all_gates_pass": not failed,
        "failed_gates": failed,
        "contract": MODEL_CONTRACT.jsonable(),
        "metrics": {
            "exact_response_curvature_fraction": (
                f"{exact_oracle.response_curvature_bd.numerator}/"
                f"{exact_oracle.response_curvature_bd.denominator}"
            ),
            "exact_response_curvature_float": exact_curvature,
            "analytic_response_curvature_float": analytic_curvature,
            "numerical_response_curvature_float": numerical_curvature,
            "fixed_loop_tail_log_slope": fixed_loop["tail_log_slope"],
            "fixed_loop_tail_scaled_error_ratio": fixed_loop["tail_scaled_error_ratio"],
            "shrinking_finest_relative_density_error": shrinking["finest_relative_density_error"],
            "sampled_fixed_branch_minimum_eigenvalue": fixed["sampled_minimum_fixed_eigenvalue"],
            "sampled_fixed_branch_variation_l2": fixed["sampled_fixed_branch_variation_l2"],
            "exact_global_fixed_eigenvalue_floor": fixed["global_depolarizing_eigenvalue_floor"],
            "shrinking_max_centering_budget_ratio": shrinking[
                "max_centering_budget_to_observed_density_error"
            ],
            "phase10_two_step_surrogate_fixed_residual_fro": phase10["surrogate_fixed_residual_fro"],
        },
        "case_dispositions": case_dispositions,
        "gates": [gate.jsonable() for gate in gates],
        "claim_ceiling": (
            "Internal synthetic authored five-state fixed-tick Benchmark D D0 channel/readout only; "
            "not the full scheduler, physical time, CGT alignment, empirical evidence, external "
            "validation, topology, or a universal response law."
        ),
    }
    records: list[dict[str, Any]] = [
        {"record_type": "exact_response_oracle", **exact_oracle.jsonable()},
        {"record_type": "exact_margins", **margins},
        {
            "record_type": "core_affine_equivalence",
            **equivalence,
            **core_cycle,
            "authored_probability_inactivity_error": authored_p_inactivity_error,
        },
        {"record_type": "core_readout_certificate", **readout},
        {"record_type": "constant_projective_reference", **projective_reference},
        {"record_type": "fixed_branch_certificates", **fixed},
        {"record_type": "fixed_loop_refinement", **fixed_loop},
        {"record_type": "shrinking_loop_refinement", **shrinking},
        {"record_type": "loop_domain_containment", **loop_domain},
        {"record_type": "null_controls", **nulls},
        {"record_type": "phase10_benchmark_c_two_step_limitation", **phase10},
        {"record_type": "benchmark_d_three_step_separate_diagnostic", **benchmark_d_three_step},
        {"record_type": "loop_conventions", **conventions},
    ]
    records.extend(
        {
            "record_type": "case_disposition",
            "case_id": case_id,
            "disposition": disposition,
        }
        for case_id, disposition in case_dispositions.items()
    )
    return summary, records


def execute_program() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Return a defensive copy of the deterministic in-process computation."""

    return copy.deepcopy(_execute_program_cached())

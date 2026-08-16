"""Executable analytic fixtures accompanying the contractive response theorem."""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from .contracts import AnalyticDisposition, Gate
from .counterexamples import (
    EXPECTED_CASE_DISPOSITIONS,
    case_dispositions_match,
    counterexample_matrix,
    propagator_decay_without_frozen_invertibility,
    realizability_identity_error,
)
from .forms import (
    closed_circle_path,
    conditional_alignment_bound,
    line_integral,
    log_slope,
    rotational_one_form,
)
from .models import (
    alpha_from_dt,
    continuous_harmonic_cycle,
    interaction_pair,
    realizability_pair,
)


@dataclass(frozen=True)
class ProgramConfig:
    """Deterministic internal fixture configuration, not an empirical protocol."""

    rho: float = 0.65
    center: tuple[float, float] = (0.3, -0.2)
    fixed_scale: float = 0.2
    fixed_steps: tuple[int, ...] = (64, 128, 256, 512, 1024, 2048)
    scaled_sides: tuple[float, ...] = (0.32, 0.16, 0.08, 0.04, 0.02)
    scaled_fixed_steps: int = 512
    coupled_ns_constant: float = 64.0
    continuous_tau: float = 0.5
    continuous_periods: tuple[float, ...] = (8.0, 16.0, 32.0, 64.0, 128.0)
    continuous_samples: int = 32768

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


DEFAULT_CONFIG = ProgramConfig()


def _relative_error(observed: float, expected: float) -> float:
    if not math.isfinite(observed) or not math.isfinite(expected) or abs(expected) <= 1e-15:
        raise ValueError("relative error requires finite values and a nonzero target")
    return float(abs(observed - expected) / abs(expected))


def _record_pair(
    record_type: str,
    steps: int,
    scale: float,
    initialization: str,
    observed: float,
    target: float,
    even: float,
    **extra: Any,
) -> dict[str, Any]:
    return {
        "record_type": record_type,
        "steps": int(steps),
        "scale": float(scale),
        "initialization": initialization,
        "q_anti": float(observed),
        "line_integral": float(target),
        "absolute_remainder": float(abs(observed - target)),
        "relative_remainder": _relative_error(observed, target),
        "orientation_even": float(even),
        **extra,
    }


def execute_program(
    config: ProgramConfig = DEFAULT_CONFIG,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute deterministic fixtures; numerical success is not the analytic proof."""

    beta = rotational_one_form(1.0)
    center = np.asarray(config.center, dtype=float)
    records: list[dict[str, Any]] = []

    fixed_errors: dict[str, list[float]] = {"equilibrium": [], "periodic": []}
    fixed_even: dict[str, list[float]] = {"equilibrium": [], "periodic": []}
    for initialization in ("equilibrium", "periodic"):
        for steps in config.fixed_steps:
            path = closed_circle_path(center, config.fixed_scale, steps)
            pair = realizability_pair(beta, path, config.rho, initialization=initialization)
            target = line_integral(beta, path)
            error = abs(pair.anti - target)
            fixed_errors[initialization].append(error)
            fixed_even[initialization].append(abs(pair.even))
            records.append(
                _record_pair(
                    "fixed_loop_refinement",
                    steps,
                    config.fixed_scale,
                    initialization,
                    pair.anti,
                    target,
                    pair.even,
                )
            )
    generic_fixed_slope = log_slope(list(config.fixed_steps[-4:]), fixed_errors["equilibrium"][-4:])
    periodic_fixed_slope = log_slope(list(config.fixed_steps[-4:]), fixed_errors["periodic"][-4:])

    generic_scaled_ratios: list[float] = []
    periodic_scaled_ratios: list[float] = []
    generic_area_relative_coupled: list[float] = []
    periodic_area_relative_coupled: list[float] = []
    for scale in config.scaled_sides:
        fixed_path = closed_circle_path(center, scale, config.scaled_fixed_steps)
        fixed_target = line_integral(beta, fixed_path)
        for initialization in ("equilibrium", "periodic"):
            pair = realizability_pair(beta, fixed_path, config.rho, initialization=initialization)
            error = abs(pair.anti - fixed_target)
            if initialization == "equilibrium":
                denominator = scale / config.scaled_fixed_steps + scale**2 / config.scaled_fixed_steps
                generic_scaled_ratios.append(error / denominator)
            else:
                denominator = scale**2 / config.scaled_fixed_steps + scale / config.scaled_fixed_steps**2
                periodic_scaled_ratios.append(error / denominator)
            records.append(
                _record_pair(
                    "scaled_bound_check",
                    config.scaled_fixed_steps,
                    scale,
                    initialization,
                    pair.anti,
                    fixed_target,
                    pair.even,
                    bound_denominator=float(denominator),
                    observed_bound_ratio=float(error / denominator),
                )
            )

        coupled_steps = int(round(config.coupled_ns_constant / scale))
        coupled_path = closed_circle_path(center, scale, coupled_steps)
        coupled_target = line_integral(beta, coupled_path)
        generic_pair = realizability_pair(beta, coupled_path, config.rho, initialization="equilibrium")
        periodic_pair = realizability_pair(beta, coupled_path, config.rho, initialization="periodic")
        generic_area_relative_coupled.append(abs(generic_pair.anti - coupled_target) / abs(coupled_target))
        periodic_area_relative_coupled.append(abs(periodic_pair.anti - coupled_target) / abs(coupled_target))

    periodic_area_relative_slope = log_slope(list(config.scaled_sides), periodic_area_relative_coupled)
    generic_tail_ratio = generic_area_relative_coupled[-1] / generic_area_relative_coupled[-2]

    interaction_path = closed_circle_path(center, config.fixed_scale, config.fixed_steps[-1])
    interaction = interaction_pair(
        rotational_one_form(2.0),
        rotational_one_form(0.5),
        interaction_path,
        config.rho,
        initialization="periodic",
    )
    interaction_target = 1.5 * line_integral(beta, interaction_path)
    interaction_error = _relative_error(interaction["interaction_D"], interaction_target)
    records.append(
        {
            "record_type": "nonzero_baseline_interaction",
            **interaction,
            "target_integral_dB_difference": interaction_target,
            "relative_error": interaction_error,
            "ordinary_did_factor": (
                interaction["ordinary_difference_in_differences"] / interaction["interaction_D"]
            ),
        }
    )

    continuous_errors: dict[str, list[float]] = {"equilibrium": [], "periodic": []}
    continuous_target = math.pi * config.fixed_scale**2
    for initialization in ("equilibrium", "periodic"):
        for period in config.continuous_periods:
            result = continuous_harmonic_cycle(
                beta,
                center,
                config.fixed_scale,
                config.continuous_tau,
                period,
                initialization=initialization,
                samples=config.continuous_samples,
            )
            error = abs(result["total_response"] - continuous_target)
            continuous_errors[initialization].append(error)
            records.append(
                {
                    "record_type": "continuous_stable_ode",
                    "initialization": initialization,
                    "period": period,
                    "tau": config.continuous_tau,
                    "tau_over_period": result["tau_over_period"],
                    "response": result["total_response"],
                    "line_integral": continuous_target,
                    "absolute_remainder": error,
                    "alpha_at_sample_dt": result["alpha_at_sample_dt"],
                }
            )
    continuous_generic_slope = log_slope(
        list(config.continuous_periods[-4:]), continuous_errors["equilibrium"][-4:]
    )
    continuous_periodic_slope = log_slope(
        list(config.continuous_periods[-4:]), continuous_errors["periodic"][-4:]
    )

    counterexamples = counterexample_matrix()
    continuous_assumption_counterexample = propagator_decay_without_frozen_invertibility()
    records.extend({"record_type": "frozen_case", **case} for case in counterexamples)
    by_case = {str(case["case_id"]): case for case in counterexamples}
    no_go_error = realizability_identity_error()

    alignment_example = {
        "zero_set_compatibility_required": True,
        "pointwise_collinearity_required": True,
        "closedness_condition": "d(kappa) wedge Omega = 0",
        "two_dimensional_test": "INELIGIBLE_TAUTOLOGY",
        "three_dimensional_test": "full-rank areas plus held-out oblique direction",
        "varying_kappa_obstruction_volume_coefficient": 1.0,
        "kappa_index": "experiment/coupling/readout",
        "surface_mass_convention": "two_dimensional_Hausdorff_area",
        "two_form_norm_convention": "comass_in_the_declared_parameter_norm",
        "center_kappa_lipschitz": 0.5,
        "omega_comass_sup": 0.4,
        "surface_diameter": 0.1,
        "conditional_bound_example": conditional_alignment_bound(
            0.2,
            0.03,
            0.004,
            kappa_lipschitz=0.5,
            omega_comass_sup=0.4,
            surface_diameter=0.1,
        ),
        "conditional_bound_expected": 0.014,
    }
    records.append({"record_type": "alignment_characterization", **alignment_example})

    alpha = alpha_from_dt(0.02, 0.4)
    rho_from_alpha = 1.0 - alpha
    alpha_mapping_error = abs(rho_from_alpha - math.exp(-0.02 / 0.4))

    gates = [
        Gate(
            "generic_fixed_loop_inverse_N",
            -1.2 <= generic_fixed_slope <= -0.8,
            generic_fixed_slope,
            "equilibrium-reset fixed-loop remainder log slope lies in [-1.2,-0.8]",
        ),
        Gate(
            "periodic_fixed_loop_improvement",
            -2.2 <= periodic_fixed_slope <= -1.8,
            periodic_fixed_slope,
            "unique-periodic fixed-loop remainder exhibits the fixture's O(N^-2) cancellation",
        ),
        Gate(
            "scaled_generic_bound",
            max(generic_scaled_ratios) <= 4.0,
            max(generic_scaled_ratios),
            "error/(s/N+s^2/N) <= 4 on the frozen ladder",
        ),
        Gate(
            "scaled_periodic_bound",
            max(periodic_scaled_ratios) <= 2.0,
            max(periodic_scaled_ratios),
            "error/(s^2/N+s/N^2) <= 2 on the frozen ladder",
        ),
        Gate(
            "area_relative_regime_separation",
            generic_tail_ratio >= 0.85 and periodic_area_relative_slope >= 1.8,
            {
                "generic_tail_ratio": generic_tail_ratio,
                "periodic_log_slope": periodic_area_relative_slope,
                "Ns": config.coupled_ns_constant,
            },
            "at fixed Ns the generic error stalls while the periodic relative error decays",
        ),
        Gate(
            "interaction_with_nonzero_B0_and_factor_two",
            interaction_error <= 0.002
            and abs(interaction["qanti_zero"]) > 0.01
            and interaction["ordinary_difference_in_differences"] == 2.0 * interaction["interaction_D"],
            {
                "relative_error": interaction_error,
                "qanti_zero": interaction["qanti_zero"],
                "did_factor": interaction["ordinary_difference_in_differences"]
                / interaction["interaction_D"],
            },
            "D approaches integral(B_on-B_0), B_0 is nonzero, and ordinary DID=2D",
        ),
        Gate(
            "exact_realizability_no_go",
            no_go_error <= 1e-14,
            no_go_error,
            "-H(I-M)^-1 M X reproduces an arbitrary declared beta to machine precision",
        ),
        Gate(
            "non_implication_counterexamples",
            abs(float(by_case["C1"]["omega_uv"])) > 0.1
            and abs(float(by_case["C1"]["response_curvature_uv"])) <= 1e-8
            and abs(float(by_case["C2"]["omega_uv"])) <= 1e-8
            and abs(float(by_case["C2"]["response_curvature_uv"])) > 0.5,
            {"C1": by_case["C1"], "C2": by_case["C2"]},
            "Omega!=0 does not imply response curvature, and response curvature does not imply Omega",
        ),
        Gate(
            "frozen_case_dispositions",
            case_dispositions_match(counterexamples),
            {case["case_id"]: case["disposition"] for case in counterexamples},
            f"complete C1-C8/P1 disposition mapping equals {EXPECTED_CASE_DISPOSITIONS}",
        ),
        Gate(
            "computed_counterexample_constructions",
            np.allclose(by_case["C3"]["kappa_values"], [-1.0, 0.0, 1.0], atol=1e-7)
            and float(by_case["C3"]["max_alignment_error"]) <= 1e-7
            and float(by_case["C4"]["projective_vs_analytic_connection_error"]) <= 1e-7
            and max(float(value) for value in by_case["C4"]["max_coefficient_identity_errors"]) <= 1e-7
            and abs(float(by_case["C5"]["pointwise_quotient"]) + 0.6) <= 1e-10
            and float(by_case["C5"]["quotient_identity_error"]) <= 1e-10
            and abs(float(by_case["C6"]["independent_constant_state_omega_uv"])) <= 1e-10
            and float(by_case["C6"]["coarse_odd_remainder"]) > float(by_case["C6"]["fine_odd_remainder"]),
            {case_id: by_case[case_id] for case_id in ("C3", "C4", "C5", "C6")},
            "C3-C6 are computed forms/dynamics, not declarative dispositions",
        ),
        Gate(
            "gauge_and_coordinate_covariance",
            max(
                float(by_case["C7"]["gauge_curvature_max_error"]),
                float(by_case["C7"]["coordinate_geometry_max_error"]),
                float(by_case["C7"]["coordinate_response_max_error"]),
            )
            <= 1e-7,
            by_case["C7"],
            "gauge and coordinate covariance errors <= 1e-7",
        ),
        Gate(
            "three_dimensional_aligned_oracle_control",
            int(by_case["P1"]["area_rank"]) == 3
            and float(by_case["P1"]["normalized_area_condition"]) <= 3.01
            and float(by_case["P1"]["max_tensor_error"]) <= 1e-6
            and float(by_case["P1"]["heldout_absolute_error"]) <= 1e-6,
            by_case["P1"],
            (
                "deliberately aligned oracle/positive implementation control has F_R=2*Omega "
                "on full-rank and held-out directions"
            ),
        ),
        Gate(
            "nonnormal_scope_boundary",
            float(by_case["C8"]["minimum_gap"]) == 1.0
            and float(by_case["C8"]["nonnormal_commutator_norm"]) > 0.1
            and by_case["C8"]["biorthogonal_curvature"] == [-2.0, 2.0],
            by_case["C8"],
            "fixed-gap non-normal case is explicitly out of the right-state theorem scope",
        ),
        Gate(
            "continuous_stable_ode_rates",
            -1.4 <= continuous_generic_slope <= -0.8 and -2.2 <= continuous_periodic_slope <= -1.7,
            {
                "equilibrium_slope": continuous_generic_slope,
                "periodic_slope": continuous_periodic_slope,
            },
            "stable-ODE fixture exhibits generic O(tau/T) and stronger periodic cancellation",
        ),
        Gate(
            "continuous_inverse_assumption_is_independent",
            continuous_assumption_counterexample["uniform_frozen_inverse_exists"] is False
            and continuous_assumption_counterexample["frozen_jacobian_at_pi_over_two"] == 0.0
            and float(continuous_assumption_counterexample["sampled_max_prefactor_ratio"])
            <= float(continuous_assumption_counterexample["decay_prefactor_bound"]) + 1e-12,
            continuous_assumption_counterexample,
            "driven propagator decay does not imply the separately required bounded frozen inverse",
        ),
        Gate(
            "continuous_discrete_alpha_mapping",
            alpha_mapping_error <= 1e-15,
            {"alpha": alpha, "rho_error": alpha_mapping_error},
            "alpha(dt)=1-exp(-dt/tau) exactly matches the held-input relaxation map",
        ),
        Gate(
            "alignment_characterization_and_bound",
            alignment_example["varying_kappa_obstruction_volume_coefficient"] == 1.0
            and abs(
                float(alignment_example["conditional_bound_example"])
                - float(alignment_example["conditional_bound_expected"])
            )
            <= 1e-15,
            alignment_example,
            (
                "zero-set/collinearity/closure conditions and the comass center-kappa "
                "approximation bound are explicit"
            ),
        ),
    ]

    gate_payload = [gate.as_dict() for gate in gates]
    failed = [gate.name for gate in gates if not gate.passed]
    disposition = (
        AnalyticDisposition.PASS_INTERNAL_ANALYTIC
        if not failed
        else AnalyticDisposition.FAIL_INTERNAL_ANALYTIC
    )
    summary = {
        "schema_version": 1,
        "experiment_id": "response_theorem_proof_program",
        "disposition": disposition.value,
        "evidence_status": "NO_EMPIRICAL_EVIDENCE",
        "claim_scope": "finite-dimensional uniformly contractive analytic class and authored fixtures",
        "central_empirical_external_claim_status": "PROOF_INCOMPLETE",
        "numerics_prove_theorem": False,
        "no_observational_or_experimental_data": True,
        "no_study_pass": True,
        "config": config.as_dict(),
        "metrics": {
            "generic_fixed_loop_slope": generic_fixed_slope,
            "periodic_fixed_loop_slope": periodic_fixed_slope,
            "max_generic_scaled_bound_ratio": max(generic_scaled_ratios),
            "max_periodic_scaled_bound_ratio": max(periodic_scaled_ratios),
            "generic_fixed_Ns_tail_ratio": generic_tail_ratio,
            "periodic_area_relative_slope_at_fixed_Ns": periodic_area_relative_slope,
            "interaction_relative_error": interaction_error,
            "no_go_identity_error": no_go_error,
            "continuous_generic_slope": continuous_generic_slope,
            "continuous_periodic_slope": continuous_periodic_slope,
            "continuous_decay_counterexample_prefactor": continuous_assumption_counterexample[
                "sampled_max_prefactor_ratio"
            ],
        },
        "gates": gate_payload,
        "failed_gates": failed,
        "case_dispositions": {case["case_id"]: case["disposition"] for case in counterexamples},
    }
    return summary, records

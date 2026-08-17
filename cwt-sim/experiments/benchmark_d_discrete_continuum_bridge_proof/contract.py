"""Frozen contract for the rational Benchmark-D bridge theorem."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class ControlBox:
    """Closed D0 box on which the exact identities are asserted."""

    bias_min: Fraction = Fraction(1, 100)
    bias_max: Fraction = Fraction(1, 20)
    diffusion_min: Fraction = Fraction(41, 200)
    diffusion_max: Fraction = Fraction(49, 200)


@dataclass(frozen=True)
class FixedTimePremises:
    """Exact, machine-checkable premises for the fixed-time bridge bound."""

    local_defect_static: Fraction = Fraction(76, 625)
    local_defect_speed_pi_coefficient: Fraction = Fraction(6, 5)
    bound_time_coefficient: Fraction = Fraction(214, 25)
    bound_circle_pi_coefficient: Fraction = Fraction(120)
    q_step_prefactor: Fraction = Fraction(1)
    q_step_power: int = 1
    positive_integer_clock_required: bool = True
    discrete_exact_equilibrium_initialization: bool = True
    continuous_exact_equilibrium_initialization: bool = True
    contraction_product_uses_delta_h: bool = True
    right_endpoint_update_then_sample: bool = True
    closing_endpoint_once: bool = True
    exact_reverse_of_common_path: bool = True


@dataclass(frozen=True)
class BridgeContract:
    """Every model, clock, reducer, proof, and claim-scope choice."""

    experiment_id: str = "benchmark_d_discrete_continuum_bridge_proof"
    benchmark_id: str = "benchmark_d"
    branch_id: str = "D0"
    node_count: int = 5
    control_names: tuple[str, str] = ("b", "d")
    box: ControlBox = ControlBox()
    center_bias: Fraction = Fraction(3, 100)
    center_diffusion: Fraction = Fraction(9, 40)

    theorem_family_scope: str = "abstract_exact_fraction_D0_diagonal_population_family"
    h_domain: str = "positive_rational_h_with_0<h<=1/5"
    h_upper: Fraction = Fraction(1, 5)
    core_regression_scope: str = "finite_float_core_regression_and_provenance_only_not_uniform_runtime_proof"
    core_runtime_h_min: Fraction = Fraction(1, 10**12)
    core_runtime_h_max: Fraction = Fraction(1, 5)
    edge_jump_scale: Fraction = Fraction(1, 5)
    depolarizing_rate: Fraction = Fraction(1, 25)
    depolarizing_rule: str = "q_h=delta*h"
    coherent_scale: Fraction = Fraction(0)
    site_potential_scale: Fraction = Fraction(0)
    actual_dephasing: Fraction = Fraction(3, 10)

    # The remaining OpenSystemConfig values are explicit but no branch/fixed
    # helper is permitted to participate in the theorem path.
    branch_steps_unused: int = 1
    fixed_point_max_iter_unused: int = 1
    fixed_point_tol_unused: Fraction = Fraction(1, 10**12)
    dephasing_values: tuple[Fraction, ...] = (Fraction(3, 10),)
    coherence_switch_floor: Fraction = Fraction(1, 5)
    scan_mesh: int = 9
    branch_helper_policy: str = "forbidden_in_theorem_path"
    fixed_point_helper_policy: str = "forbidden_in_theorem_path"
    projection_policy: str = "core_crosscheck_only_and_proven_inactive"

    transpose_convention: str = "column_population_uses_K_transpose"
    population_map_formula: str = "E_h=(1-delta*h)*(I+h*a*(K^T-I))*x+delta*h*u"
    affine_source_formula: str = "c_h=h*(delta/5)*one"
    effective_generator_formula: str = "A_h=a*(1-delta*h)*(K^T-I)-delta*I"
    exact_fixed_branch_formula: str = "xbar_h=-A_h^-1*c"
    stationary_positivity_bound: str = "xbar_h_component_floor_at_least_4/69_not_q_h/5"
    derivative_proof_mode: str = "exact_affine_C2_with_zero_second_control_derivatives"
    proof_mode: str = "symbolic_fraction_and_directed_interval_not_finite_ladder"

    observable_name: str = "mean_position"
    response_centering: str = "instantaneous_exact_xbar_h"
    response_scaling: str = "Q_h=h*S_h_where_S_h=sum_right_endpoint_centered_readout"
    response_units: str = "mean_position_index_times_model_time"
    update_convention: str = "right_endpoint_update_then_sample"
    reversal_convention: str = "gamma_minus(t)=gamma_plus(T-t)"
    endpoint_convention: str = "skip_duplicate_initial_and_process_closing_endpoint_once"
    slow_clock: str = "uniform_affine_u=t/T_on_common_circle"
    initialization: str = "exact_instantaneous_equilibrium_at_common_loop_start"
    scale_domain: str = "positive_rational_s_with_0<s<=1/100"
    scale_upper: Fraction = Fraction(1, 100)
    circle_scale: Fraction = Fraction(1, 100)
    qanti_definition: str = "Qanti_h=(Q_h_plus-Q_h_minus)/2"
    did_definition: str = "ordinary_scaled_orientation_difference=2*Qanti_h"

    fixed_time: FixedTimePremises = FixedTimePremises()
    pi_enclosure: tuple[Fraction, Fraction] = (Fraction(333, 106), Fraction(355, 113))
    primary_limit_order: str = "h_to_0_at_fixed_T_s_then_T_to_infinity_then_optional_s_to_0"
    joint_limit_scope: str = "only_if_h*T_to_0_with_bound;area_relative_also_s*T_to_infinity_and_h*T/s^2_to_0"
    limit_interchangeability: str = "not_claimed"

    legacy_discrete_context: str = "dt=9/50_q=1/125_is_off_primary_family"
    legacy_continuous_context: str = "hash_bound_structural_target_not_numerical_convergence_evidence"
    exponential_context: str = "optional_context_only_never_primary_or_acceptance"
    empirical_status: str = "NO_EMPIRICAL_EVIDENCE"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    claim_ceiling: str = (
        "exact rational bridge on the authored five-state D0 diagonal invariant population sector and "
        "mean-position readout in uncalibrated model-time only; no full-density, scheduler, physical, "
        "empirical, CGT-alignment, general-CWT, topology, or population claim"
    )

    def jsonable(self) -> dict[str, Any]:
        """Return a strict-JSON-compatible exact representation."""

        def convert(value: Any) -> Any:
            if isinstance(value, Fraction):
                return {
                    "fraction": f"{value.numerator}/{value.denominator}",
                    "float": float(value),
                }
            if isinstance(value, dict):
                return {key: convert(item) for key, item in value.items()}
            if isinstance(value, tuple):
                return [convert(item) for item in value]
            return value

        return convert(asdict(self))


MODEL_CONTRACT = BridgeContract()

FORMAL_CT_CENTER_CURVATURE = Fraction(
    -28888766872100000000000,
    235345963257301712101,
)
FORMAL_CENTER_FIRST_H_COEFFICIENT = Fraction(
    228322311704703213246688000000,
    44415389442843585257542657921,
)


REFUSAL_SPECS = {
    "R01": "legacy_dt_9/50_q_1/125_off_family",
    "R02": "fixed_or_exponential_q_forbidden_as_primary",
    "R03": "wrong_jump_or_dephasing_h_scaling",
    "R04": "missing_affine_source_or_K_transpose",
    "R05": "missing_or_doubled_h_response_scaling",
    "R06": "wrong_or_iterative_fixed_branch_centering",
    "R07": "endpoint_reversal_clock_or_path_mismatch",
    "R08": "incomplete_diagonal_affine_identity",
    "R09": "active_clip_rescale_or_projection_branch",
    "R10": "q_h_over_5_mislabeled_as_stationary_floor",
    "R11": "per_tick_gap_reused_across_h",
    "R12": "finite_ladder_or_Ns_only_claimed_as_proof",
    "R13": "unproved_joint_limit_or_limit_interchange",
    "R14": "omitted_context_or_source_provenance",
    "R15": "full_density_scheduler_physical_empirical_or_CGT_claim_inflation",
    "R16": "nonzero_coherent_or_site_scale_or_zero_delta",
    "R17": "branch_helper_Euler_PSD_or_projection_dependent_theorem",
    "R18": "finite_core_samples_or_tiny_h_float_claimed_as_uniform_runtime_proof",
    "R19": "scale_outside_exact_0<s<=1/100_domain",
    "R20": "nonrecursive_or_link_following_predecessor_context_closure",
}


EXPECTED_CASE_DISPOSITIONS = {
    "C1": "PRIMARY_RATIONAL_FAMILY_LOCKED",
    "C2": "CORE_CPTP_SAFETY_AND_DIAGONAL_IDENTITY_PASS",
    "C3": "GENERATOR_SOURCE_AND_C2_CONTROL_PASS",
    "C4": "EXACT_STATIONARY_BRANCH_AND_CONTRACTION_PASS",
    "C5": "EXACT_hB_GRADIENT_IDENTITY_PASS",
    "C6": "EXACT_hF_SIGN_LIMIT_AND_ERROR_BOUND_PASS",
    "C7": "Q_SCALING_CLOCK_REVERSAL_AND_FACTORS_PASS",
    "C8": "FIXED_TIME_BRIDGE_BOUND_PASS",
    "C9": "ITERATED_AND_CONDITIONAL_JOINT_LIMIT_SCOPE_PASS",
    "C10": "LEGACY_CONTEXT_OFF_FAMILY_AND_HASH_BOUND",
    "C11": "ADVERSARIAL_REFUSAL_MATRIX_COMPLETE",
    "C12": "CLAIM_CEILING_NO_EVIDENCE_UPGRADE",
}


CASE_GATE_MAP = {
    "C1": ("contract_exact_primary_family",),
    "C2": (
        "d0_clip_inactive",
        "kraus_cp_tp_uniform",
        "safety_rescale_inactive",
        "projection_inactive",
        "finite_core_diagonal_regression",
    ),
    "C3": ("exact_generator_source_identity", "uniform_c2_parameter_control"),
    "C4": ("exact_stationary_branch", "uniform_contraction_and_resolvent"),
    "C5": ("exact_hB_gradient_identity", "closed_loop_gradient_cancellation"),
    "C6": (
        "exact_hF_identity",
        "curvature_sign_interval",
        "center_limit_oracle",
        "curvature_error_bound",
    ),
    "C7": (
        "response_units_and_h_scaling",
        "loop_clock_reversal_endpoint_contract",
        "qanti_and_did_factors",
    ),
    "C8": ("fixed_time_bridge_bound", "scale_domain_uniform_containment"),
    "C9": ("iterated_and_joint_limit_scope",),
    "C10": ("legacy_context_off_family", "context_artifact_hash_closure"),
    "C11": ("refusal_matrix_complete",),
    "C12": ("claim_ceiling",),
}

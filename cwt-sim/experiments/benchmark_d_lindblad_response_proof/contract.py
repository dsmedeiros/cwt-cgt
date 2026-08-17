"""Frozen theorem contract for the Benchmark D continuous Lindblad specialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class ControlBox:
    """Closed control box on which every analytic certificate is asserted."""

    bias_min: Fraction = Fraction(1, 100)
    bias_max: Fraction = Fraction(1, 20)
    diffusion_min: Fraction = Fraction(41, 200)
    diffusion_max: Fraction = Fraction(49, 200)


@dataclass(frozen=True)
class LindbladProofContract:
    """All model, clock, path, readout, and claim-scope choices."""

    experiment_id: str = "benchmark_d_lindblad_response_proof"
    benchmark_id: str = "benchmark_d"
    branch_id: str = "D0"
    control_names: tuple[str, str] = ("b", "d")
    box: ControlBox = ControlBox()
    center_bias: Fraction = Fraction(3, 100)
    center_diffusion: Fraction = Fraction(9, 40)
    node_count: int = 5

    # Every field of cwt.cgt.lindblad.LindbladConfig is explicit here.
    dt: Fraction = Fraction(1, 50)
    integration_steps: int = 30
    coherent_scale: Fraction = Fraction(0)
    edge_jump_scale: Fraction = Fraction(1, 5)
    site_potential_scale: Fraction = Fraction(0)
    depolarizing_rate: Fraction = Fraction(1, 25)
    dephasing_values: tuple[Fraction, ...] = (Fraction(3, 10),)
    coherence_switch_floor: Fraction = Fraction(1, 5)
    scan_mesh: int = 9
    actual_dephasing: Fraction = Fraction(3, 10)

    observable_name: str = "mean_position"
    circle_scale: Fraction = Fraction(1, 100)
    positive_orientation: str = "counterclockwise_in_db_wedge_dd"
    reversal_convention: str = "gamma_cw(u)=gamma_ccw(1-u)"
    initialization: str = "instantaneous_equilibrium_at_u=0"
    slow_drive_clock_id: str = "uniform_affine_normalized_clock_v1"
    slow_drive_clock_definition: str = (
        "u=t/T;lambda_plus(t)=gamma_plus(u);" "lambda_minus(t)=lambda_plus(T-t)=gamma_plus(1-u);0<=t<=T"
    )
    response_definition: str = "Q=integral_0^T Tr[O(rho-rho_bar)]d(model_time)"
    time_domain: str = "uncalibrated_continuous_model_time"
    generator_rate_units: str = "inverse_model_time"
    duration_units: str = "model_time"
    readout_units: str = "dimensionless_mean_position_index"
    integrated_response_units: str = "mean_position_index_times_model_time"
    physical_time_calibration_status: str = "absent_requires_external_clock_and_readout_calibration"
    flow_backend: str = "analytic_interval_certificate_no_trajectory"
    endpoint_convention: str = "closed_circle_no_duplicated_time_endpoint"

    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    claim_ceiling: str = (
        "internal authored Benchmark D five-state Lindblad generator and mean-position readout only; "
        "not a derived CWT continuum limit, CGT alignment law, physical model, or empirical evidence"
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


MODEL_CONTRACT = LindbladProofContract()

FORMAL_RESPONSE_CURVATURE = Fraction(
    -28888766872100000000000,
    235345963257301712101,
)

EXPECTED_CASE_DISPOSITIONS = {
    "C1": "D0_CORE_BINDING_PASS",
    "C2": "AFFINE_LINDBLAD_IDENTITY_PASS",
    "C3": "UNIFORM_CONTRACTION_AND_INVERSE_PASS",
    "C4": "TRUE_STATIONARY_BRANCH_PASS",
    "C5": "EXACT_RESPONSE_CURVATURE_PASS",
    "C6": "ORIENTATION_AND_FACTOR_TWO_PASS",
    "C7": "IDENTITY_READOUT_NULL_PASS",
    "C8": "READOUT_COVARIANCE_PASS",
    "C9": "INVALID_MODEL_VARIANTS_REFUSED",
    "C10": "AFFINE_SOURCE_REQUIRED_PASS",
    "C11": "BENCHMARK_C_TRUE_STATIONARY_NULL_PASS",
    "C12": "RIGOROUS_DYNAMIC_SIGN_CERTIFICATE_PASS",
    "C13": "ZERO_OMEGA_NONZERO_RESPONSE_NO_GO_PASS",
}

CASE_GATE_MAP = {
    "C1": ("explicit_contract", "d0_core_kernel_and_readout"),
    "C2": (
        "affine_population_generator",
        "diagonal_invariant_subspace_core_equivalence",
    ),
    "C3": ("trace_norm_contraction", "frozen_inverse_bound"),
    "C4": ("exact_stationary_branch", "uniform_full_rank_floor"),
    "C5": ("exact_center_oracle", "nonzero_response_curvature"),
    "C6": ("circle_orientation_reversal", "qanti_and_did_factor_two"),
    "C7": ("identity_readout_null",),
    "C8": ("linear_readout_covariance",),
    "C9": (
        "zero_depolarization_refused",
        "coherent_or_gauge_variant_refused",
        "euler_projection_backend_refused",
        "clock_reversal_initialization_mutations_refused",
    ),
    "C10": ("affine_source_omission_refused",),
    "C11": ("benchmark_c_unital_stationary_null",),
    "C12": (
        "uniform_affine_slow_drive_clock",
        "rigorous_curvature_and_line_interval",
        "analytic_remainder_certificate",
        "fixed_and_joint_ladders_certified",
    ),
    "C13": ("smooth_positive_real_projective_state", "omega_zero_response_nonzero"),
}


def contract_issues(contract: LindbladProofContract) -> list[str]:
    """Fail closed unless the exact reviewed specialization is selected."""

    expected = MODEL_CONTRACT
    issues: list[str] = []
    for field_name in expected.__dataclass_fields__:
        if getattr(contract, field_name) != getattr(expected, field_name):
            issues.append(f"CONTRACT_MISMATCH:{field_name}")
    if contract.depolarizing_rate <= 0:
        issues.append("DEPOLARIZING_RATE_NOT_POSITIVE")
    if contract.coherent_scale != 0 or contract.site_potential_scale != 0:
        issues.append("NONZERO_HAMILTONIAN_OR_SITE_GAUGE_OUT_OF_SCOPE")
    if "euler" in contract.flow_backend.lower() or "project" in contract.flow_backend.lower():
        issues.append("EULER_OR_PROJECTION_BACKEND_FORBIDDEN")
    return sorted(set(issues))

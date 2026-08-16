"""Frozen model contract for the Benchmark D open-response specialization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction


@dataclass(frozen=True)
class ControlBox:
    """Closed interior control box on which the analytic certificates apply."""

    bias_min: Fraction = Fraction(1, 100)
    bias_max: Fraction = Fraction(1, 20)
    diffusion_min: Fraction = Fraction(41, 200)
    diffusion_max: Fraction = Fraction(49, 200)


@dataclass(frozen=True)
class ModelContract:
    """Exact authored channel/readout specialization; no scheduler semantics are inferred."""

    experiment_id: str = "benchmark_d_open_response_proof"
    benchmark_id: str = "benchmark_d"
    branch_id: str = "D0"
    control_names: tuple[str, str] = ("b", "d")
    center_bias: Fraction = Fraction(3, 100)
    center_diffusion: Fraction = Fraction(9, 40)
    box: ControlBox = ControlBox()
    node_count: int = 5
    dt: Fraction = Fraction(9, 50)
    edge_jump_scale: Fraction = Fraction(1, 5)
    depolarizing: Fraction = Fraction(1, 125)
    coherent_scale: Fraction = Fraction(0, 1)
    site_potential_scale: Fraction = Fraction(0, 1)
    dephasing: Fraction = Fraction(3, 10)
    observable_name: str = "mean_position"
    update_convention: str = "right_endpoint_update_then_sample"
    reversal_convention: str = "cw_is_exact_reverse_of_stored_ccw_sequence"
    endpoint_convention: str = "skip_duplicate_initial_and_process_closing_endpoint_once"
    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    disposition: str = "PASS_INTERNAL_ANALYTIC"

    @property
    def jump_probability_scale(self) -> Fraction:
        return self.dt * self.edge_jump_scale

    @property
    def contraction_factor(self) -> Fraction:
        return 1 - self.depolarizing

    @property
    def depolarizing_floor(self) -> Fraction:
        return self.depolarizing / self.node_count

    def jsonable(self) -> dict[str, object]:
        """Return an exact, explicit representation for generated artifacts."""

        raw = asdict(self)

        def convert(value: object) -> object:
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

        return convert(raw)  # type: ignore[return-value]


MODEL_CONTRACT = ModelContract()

# This value is an independent acceptance oracle copied from the formal derivation.
# The implementation must recompute it from Fraction-valued matrices before comparison.
FORMAL_RESPONSE_CURVATURE = Fraction(
    -1389405980846240823998759336989273383099794763750000000000,
    2559023550169319630994375590863181495045970285707766901,
)

EXPECTED_CASE_DISPOSITIONS = {
    "C1": "CORE_DIAGONAL_EQUIVALENCE_PASS",
    "C2": "EXACT_CONTRACTION_CERTIFIED",
    "C3": "NONZERO_RESPONSE_CURVATURE_PASS",
    "C4": "FIXED_LOOP_ASYMPTOTIC_PASS",
    "C5": "SHRINKING_LOOP_LIMIT_PASS",
    "C6": "IDENTITY_READOUT_ZERO_PASS",
    "C7": "CONSTANT_BRANCH_ZERO_PASS",
    "C8": "DEPOLARIZING_ZERO_REFUSES_CERTIFICATE",
    "C9": "BENCHMARK_C_UNITAL_ZERO_PASS",
    "C10": "PHASE10_BENCHMARK_C_TWO_STEP_SURROGATE_NOT_FIXED",
}

# Case outcomes are derived from their registered executable gates.  This map is
# deliberately data, rather than an if/elif report renderer, so every case can
# be mutation-tested for fail-closed behavior.
CASE_GATE_MAP = {
    "C1": ("named_core_binding", "named_core_readout_binding"),
    "C2": (
        "exact_kraus_and_margin_certificate",
        "global_contraction_certificate",
        "true_full_rank_fixed_branch",
    ),
    "C3": (
        "exact_fraction_oracle",
        "nonzero_response_curvature",
        "constant_projective_reference_zero",
    ),
    "C4": ("fixed_loop_one_over_n", "loop_update_reversal_endpoint_contract"),
    "C5": (
        "registered_loop_domain_containment",
        "shrinking_loop_area_limit",
        "fixed_solver_centering_budget",
        "loop_update_reversal_endpoint_contract",
    ),
    "C6": ("identity_readout_null",),
    "C7": ("constant_branch_null",),
    "C8": ("depolarizing_zero_refusal",),
    "C9": ("benchmark_c_true_fixed_unital_null",),
    "C10": ("phase10_benchmark_c_two_step_surrogate_rejected",),
}

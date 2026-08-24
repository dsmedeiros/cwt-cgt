"""Frozen pre-access adapter contract and immutable call plan."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from types import MappingProxyType

from .exact import canonical_sha256, strict_equal

Point = tuple[Fraction, Fraction, Fraction]

PREDICTOR_SOURCE_COMMIT_OID = "c140709179719eb6ed827097e1aa96c26acf93f6"
PREDICTOR_SOURCE_TREE_OID = "28caa6b381f52cc39d75585ace08c823134cbeff"
PREDICTOR_METADATA_COMMIT_OID = "1f4cd82e9e44faea22ab3b12464042a0678b3abd"
PREDICTOR_METADATA_LOCK_SHA256 = "9b9f2c112581f575f35cf599afd2f708bc9c241eed2512ef166ed62293757cd8"
PRODUCER_SOURCE_LOCK_SHA256 = "d513614df4f375a756b7cb593cd47ac729b4a702dcea5448be69cdfa9e3da3a9"
GEOMETRY_PLAN_SHA256 = "b44e7c5490aaf696e959f637ddf83a7993e11f599c92085a91ae121ec175b4e1"

CALIBRATION_CENTERS: tuple[Point, ...] = (
    (Fraction(3, 200), Fraction(21, 100), Fraction(2, 5)),
    (Fraction(9, 200), Fraction(21, 100), Fraction(3, 5)),
    (Fraction(3, 200), Fraction(6, 25), Fraction(3, 5)),
    (Fraction(9, 200), Fraction(6, 25), Fraction(2, 5)),
    (Fraction(1, 40), Fraction(43, 200), Fraction(7, 12)),
    (Fraction(1, 25), Fraction(47, 200), Fraction(5, 12)),
)
CONFIRMATION_CENTERS: tuple[Point, Point] = (
    (Fraction(1, 50), Fraction(23, 100), Fraction(11, 20)),
    (Fraction(1, 25), Fraction(11, 50), Fraction(9, 20)),
)
HELDOUT_CENTER: Point = (Fraction(7, 200), Fraction(23, 100), Fraction(7, 15))
HELDOUT_AREA_VECTOR = (1, -1, 3)
CHORD_RADIUS = Fraction(1, 20)
ZERO_RADIUS = Fraction(0)
COMPONENT_ORDER = ("F_d_t", "F_t_b", "F_b_d")
COORDINATE_SCALES: Point = (Fraction(1, 50), Fraction(1, 50), Fraction(1, 6))
NORMALIZED_CURVATURE_SCALES = (
    COORDINATE_SCALES[1] * COORDINATE_SCALES[2],
    COORDINATE_SCALES[2] * COORDINATE_SCALES[0],
    COORDINATE_SCALES[0] * COORDINATE_SCALES[1],
)
TARGET_EXPRESSION = (
    "DeltaF(c)=direct_response_curl(build_branch_bundle(c,r=1/20),orientation=+1)"
    "-direct_response_curl(build_branch_bundle(c,r=0),orientation=+1)"
)

PRODUCER_CALLABLES = MappingProxyType(
    {
        "build_branch_bundle": MappingProxyType(
            {
                "module": "experiments.loop_flux_counting_curvature_proof.generator",
                "qualname": "build_branch_bundle",
                "blob_oid": "387e504810ab1a87078dedff200e853b72a31891",
                "sha256_raw": "1c1af952976428da9bd21801effbe87a891c94231100629d38c736564b50beb1",
                "signature": "(*,center=None,radius=None)->BranchBundle",
                "source_span_sha256": "7f9cc1740df598a6f486bfa3d0a8b569059194ace8d2ff3d6dc6add0e634e780",
                "canonical_ast_sha256": "c6cb8a6e4c538faf870e6372b2b425f6db8b5e1dd85ed7d6bc93b3c83174bb5a",
                "transitive_call_graph_sha256": (
                    "57c854b4f80ef8ad4cda291315b3e33b504129cf56df4c336c4d337a89ab2471"
                ),
            }
        ),
        "direct_response_curl": MappingProxyType(
            {
                "module": "experiments.loop_flux_counting_curvature_proof.counting_lane",
                "qualname": "_direct_response_curl_record",
                "blob_oid": "592f69d765814b2a8545f4c0aa081f6cb1a9ea2f",
                "sha256_raw": "02b34cfc3a4e61799d1a850a6e294b549d062aac8f6dffb0395f249f4db64782",
                "signature": "(bundle,*,orientation=1)->dict[str,object]",
                "source_span_sha256": "0f2a61cde05f59e5ca4ea6daafb5b0ae0a5260f1b11e78402f60c464e7788807",
                "canonical_ast_sha256": "f77f9f9d3c18cc141d1039e9c43eb8388f719b668c20ed970994952d6a40814f",
                "transitive_call_graph_sha256": (
                    "71b7af52ada31c2be6f45709a08bfc26aabc509d1dabce9b885cbd534c104282"
                ),
            }
        ),
        "fcs_normal_connection_curl": MappingProxyType(
            {
                "module": "experiments.loop_flux_counting_curvature_proof.counting_lane",
                "qualname": "_fcs_normal_connection_jet_record",
                "blob_oid": "592f69d765814b2a8545f4c0aa081f6cb1a9ea2f",
                "sha256_raw": "02b34cfc3a4e61799d1a850a6e294b549d062aac8f6dffb0395f249f4db64782",
                "signature": "(bundle)->dict[str,object]",
                "source_span_sha256": "3b9080869b048c61e147d8904761843a1f33123f739f0b50e052df8df03e61bd",
                "canonical_ast_sha256": "db9959d52bcd45ae819124b81723c3def0271aabc8f15a8c694bf1588fd5516e",
                "transitive_call_graph_sha256": (
                    "68ab3ffa08069596c4ce6b3284266b0c31dcb329692aeed4bdc6e7cfe14e4cd3"
                ),
            }
        ),
    }
)


@dataclass(frozen=True)
class AdapterContract:
    experiment_id: str = "generator_tensor_response_protocol"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    relation_scope: str = "MODEL_SPECIFIC_RELATIONS_ONLY"
    predictor_source_commit_oid: str = PREDICTOR_SOURCE_COMMIT_OID
    predictor_source_tree_oid: str = PREDICTOR_SOURCE_TREE_OID
    predictor_metadata_commit_oid: str = PREDICTOR_METADATA_COMMIT_OID
    predictor_metadata_lock_sha256: str = PREDICTOR_METADATA_LOCK_SHA256
    producer_source_lock_sha256: str = PRODUCER_SOURCE_LOCK_SHA256
    target_expression: str = TARGET_EXPRESSION
    component_order: tuple[str, str, str] = COMPONENT_ORDER
    coordinate_scales: Point = COORDINATE_SCALES
    normalized_curvature_scales: tuple[Fraction, Fraction, Fraction] = NORMALIZED_CURVATURE_SCALES
    orientation: int = 1
    calibration_sample_call_count: int = 12
    calibration_center_count: int = 6
    calibration_equation_count: int = 18
    coefficient_count: int = 3
    confirmation_center_count: int = 2
    heldout_area_vector: tuple[int, int, int] = HELDOUT_AREA_VECTOR
    intercept_allowed: bool = False
    normalization_allowed: bool = False
    sign_flip_allowed: bool = False
    weights_allowed: bool = False
    regularization_allowed: bool = False
    tolerance_allowed: bool = False
    fallback_allowed: bool = False
    orientation_averaging_allowed: bool = False
    extra_curvature_factor_allowed: bool = False
    degenerate_fit_prediction_allowed: bool = False
    authoritative_response_entrypoint: str = (
        "outer_trusted_detached_launcher_to_fresh_isolated_whole_phase_child_only"
    )
    outer_trusted_orchestrator_is_sole_access_authority: bool = True
    child_argv_and_globals_are_defense_in_depth: bool = True
    arbitrary_same_process_memory_or_syscall_compromise_out_of_scope: bool = True
    detached_exact_lock_checkout_required: bool = True
    adjacent_python_cache_refused: bool = True
    external_empty_pycache_prefix_required: bool = True
    trusted_absolute_python_and_git_required: bool = True
    post_result_external_verification_required: bool = True
    inprocess_response_api_authoritative: bool = False
    local_ledger_grants_phase_authority: bool = False
    durable_outer_ledger_binding_required: bool = True
    durable_outer_ledger_outside_detached_worktree: bool = True
    durable_outer_ledger_keyed_by_authority_session_sequence: bool = True
    outer_provisions_and_verifies_durable_ledger: bool = True
    outer_refuses_launch_when_exact_ledger_key_exists: bool = True
    child_atomically_consumes_ledger_key_before_producer_import: bool = True
    durable_outer_ledger_process_controlled_not_cryptographic: bool = True
    durable_ledger_evidence_requires_later_external_commit: bool = True
    next_phase_requires_committed_external_outcome: bool = True
    external_outcome_delta_path_count: int = 2
    historical_unopened_claimed: bool = False
    reservation_status: str = "RESERVED_BY_PROCESS_ATTESTATION / NOT_CRYPTOGRAPHICALLY_PROVEN_UNOPENED"
    claim_ceiling: str = (
        "internal exact model-specific calibration/confirmation/heldout protocol only; "
        "no empirical, physical, universal, full-CWT, or historically-unopened claim"
    )


MODEL_CONTRACT = AdapterContract()

ORDERED_GATES = (
    "G0_exact_contract_and_immutable_anchors",
    "G1_count_blind_geometry_call_plan",
    "G2_locked_producer_source_and_callable_surface",
    "G3_strict_fraction_response_schema",
    "G4_exact_center_major_twelve_call_calibration",
    "G5_exact_rank_three_fit_and_eighteen_zero_residuals",
    "G6_prediction_commit_precedes_confirmation_access",
    "G7_atomic_two_center_confirmation",
    "G8_scalar_only_heldout_after_confirmation_pass",
    "G9_terminal_no_retry_incident_semantics",
    "G10_lane_partition_firewalls_and_response_seal",
    "G11_claim_ceiling_and_source_lock_refusal",
)


def calibration_call_plan() -> tuple[tuple[str, Point, Fraction], ...]:
    return tuple(
        (f"A{index}", center, radius)
        for index, center in enumerate(CALIBRATION_CENTERS, start=1)
        for radius in (CHORD_RADIUS, ZERO_RADIUS)
    )


def confirmation_call_plan() -> tuple[tuple[str, Point, Fraction], ...]:
    return tuple(
        (f"V{index}", center, radius)
        for index, center in enumerate(CONFIRMATION_CENTERS, start=1)
        for radius in (CHORD_RADIUS, ZERO_RADIUS)
    )


def heldout_call_plan() -> tuple[tuple[str, Point, Fraction], ...]:
    return tuple(("H", HELDOUT_CENTER, radius) for radius in (CHORD_RADIUS, ZERO_RADIUS))


def contract_record(contract: AdapterContract = MODEL_CONTRACT) -> dict[str, object]:
    if type(contract) is not AdapterContract:
        raise TypeError("adapter contract type refused")
    record = asdict(contract)
    record["calibration_centers"] = CALIBRATION_CENTERS
    record["confirmation_centers"] = CONFIRMATION_CENTERS
    record["heldout_center"] = HELDOUT_CENTER
    record["calibration_call_plan"] = calibration_call_plan()
    record["confirmation_call_plan"] = confirmation_call_plan()
    record["heldout_call_plan"] = heldout_call_plan()
    record["producer_callables"] = {key: dict(value) for key, value in PRODUCER_CALLABLES.items()}
    return record


def contract_issues(contract: AdapterContract = MODEL_CONTRACT) -> tuple[str, ...]:
    if type(contract) is not AdapterContract:
        return ("contract_type",)
    expected = AdapterContract()
    issues = list(
        name for name, wanted in asdict(expected).items() if not strict_equal(asdict(contract)[name], wanted)
    )
    if canonical_sha256(contract_record(contract)) != CONTRACT_SHA256:
        issues.append("reviewed_contract_sha256")
    if canonical_sha256(ORDERED_GATES) != GATE_REGISTRY_SHA256:
        issues.append("reviewed_gate_registry_sha256")
    if (
        canonical_sha256({key: dict(value) for key, value in PRODUCER_CALLABLES.items()})
        != PRODUCER_CALLABLES_SHA256
    ):
        issues.append("reviewed_producer_callable_registry_sha256")
    return tuple(issues)


CONTRACT_SHA256 = "830109f07b9729409310b7b39f50da41ea95a9d30d11ba77039297edc8215e17"
GATE_REGISTRY_SHA256 = "22e5d9e7e1d3f365aa18e320de9cc1b003f031fd21499d0339cf457606c27311"
PRODUCER_CALLABLES_SHA256 = "56c26dede0c04726f0c0cb5904da0d5bdf8295221553a7f312b1272fed772734"

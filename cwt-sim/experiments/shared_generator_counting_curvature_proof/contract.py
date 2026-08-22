"""Frozen model, claim, and immutable gate contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class SharedGeneratorContract:
    experiment_id: str = "shared_generator_counting_curvature_proof"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    relation_scope: str = "MODEL_SPECIFIC_RELATIONS_ONLY"
    claim_ceiling: str = (
        "internal exact Benchmark-D D0 shared-generator counting-curvature classifications only; "
        "refutes only SAME_CURVATURE and frozen zero-preserving homogeneous Omega-only maps for "
        "the declared state geometry; affine, nonlinear, and generator-dependent maps remain open; "
        "not universal or full CWT, calibrated physical response, or empirical evidence"
    )

    node_count: int = 5
    edge_rate: Fraction = Fraction(1, 5)
    depolarizing_rate: Fraction = Fraction(1, 25)
    dephasing_rate: Fraction = Fraction(3, 10)
    site_potential_scale: Fraction = Fraction(0)
    theta_value: Fraction = Fraction(0)
    b_bounds: tuple[Fraction, Fraction] = (Fraction(1, 100), Fraction(1, 20))
    d_bounds: tuple[Fraction, Fraction] = (Fraction(41, 200), Fraction(49, 200))
    h_bounds: tuple[Fraction, Fraction] = (Fraction(1, 20), Fraction(3, 20))
    t0_delta_bounds: tuple[Fraction, Fraction] = (Fraction(1, 50), Fraction(3, 50))
    t0_center: tuple[Fraction, Fraction, Fraction] = (
        Fraction(3, 100),
        Fraction(9, 40),
        Fraction(1, 25),
    )
    t1_center: tuple[Fraction, Fraction, Fraction] = (
        Fraction(3, 100),
        Fraction(9, 40),
        Fraction(1, 10),
    )

    current_edge: tuple[int, int] = (1, 2)
    positive_count_definition: str = "q_positive_counts_index_1_to_2_physical_nodes_2_to_3"
    tilted_gain_definition: str = "Wq_gain_mn=exp(q*d_mn)*W_gain_mn"
    geometric_cumulant_definition: str = "Q_geometric=-closed_integral_A(q)"
    response_connection_identity: str = "B_i=-partial_q_A_i_at_q0"
    response_curvature_identity: str = "F_R=-partial_q_d_parameter_A_at_q0"
    orientation_convention: str = "reverse_count_negates_B_and_F"
    qanti_definition: str = "Qanti=(Qplus-Qminus)/2"
    full_orientation_difference: str = "Qplus-Qminus=2*Qanti"

    time_domain: str = "uncalibrated_continuous_model_time"
    generator_rate_units: str = "inverse_model_time"
    response_one_form_units: str = "B_i=count_per_control_i"
    response_curvature_units: str = "F_ij=count_per_control_i_per_control_j"
    t0_control_units: tuple[tuple[str, str], ...] = (
        ("b", "dimensionless"),
        ("d", "dimensionless"),
        ("delta", "inverse_model_time"),
    )
    t1_control_units: tuple[tuple[str, str], ...] = (
        ("b", "dimensionless"),
        ("d", "dimensionless"),
        ("h", "inverse_model_time"),
    )
    t0_component_units: tuple[tuple[str, str], ...] = (
        ("B_b", "count"),
        ("B_d", "count"),
        ("B_delta", "count_times_model_time"),
        ("F_d_delta", "count_times_model_time"),
        ("F_delta_b", "count_times_model_time"),
        ("F_b_d", "count"),
    )
    t1_component_units: tuple[tuple[str, str], ...] = (
        ("B_b", "count"),
        ("B_d", "count"),
        ("B_h", "count_times_model_time"),
        ("F_d_h", "count_times_model_time"),
        ("F_h_b", "count_times_model_time"),
        ("F_b_d", "count"),
    )
    local_curvature_scope: str = "exact_local_parameter_two_form_at_frozen_centers"
    response_curvature_definition: str = "F_R=d_parameter_B_R_on_exact_smooth_stationary_branch"
    closure_scope: str = "local_exact_dF_R=d_squared_B_R=0_only"
    coordinate_covariance_scope: str = "declared_smooth_control_reparameterizations_only"
    zero_set_scope: str = "same_curvature_and_frozen_zero_preserving_homogeneous_Omega_only_maps_only"
    theorem_backend: str = "exact_Q_i_stationary_Drazin_SLD_and_FCS_algebra"
    core_calls_are_acceptance_authority: bool = False
    finite_differences_are_acceptance_authority: bool = False
    positive_map_claim_allowed: bool = False
    empirical_claim_allowed: bool = False

    def jsonable(self) -> dict[str, Any]:
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


MODEL_CONTRACT = SharedGeneratorContract()

FORMAL_T0_RESPONSE_ONE_FORM = (
    Fraction(99174704606406543600, 235345963257301712101),
    Fraction(-2982694889205050400, 235345963257301712101),
    Fraction(-57603369703026499200, 235345963257301712101),
)
FORMAL_T0_RESPONSE_CURVATURE = (
    Fraction(-2852470336327977600000, 3059497522344922257313),
    Fraction(-21393527522459832000000, 3059497522344922257313),
    Fraction(-3803293781770636800000, 3059497522344922257313),
)
_T1_RESPONSE_DENOMINATOR = (
    2080842432711018945368409152344330835212655288035660610473077874093258219017176210460353903988422507947
)
FORMAL_T1_RESPONSE_ONE_FORM = tuple(
    Fraction(numerator, _T1_RESPONSE_DENOMINATOR)
    for numerator in (
        860511178385397105120140632644211239362106486003259903187281039922055143094807421694626120624216272000,
        -28779859168440410938794644780181941942597451637480931751710652665424030619736269970361244365671539200,
        -6304174414970572439872780909036217489001279248495460583226180294290830841744929414113892862748583600,
    )
)
FORMAL_T1_RESPONSE_CURVATURE = tuple(
    Fraction(numerator, _T1_RESPONSE_DENOMINATOR)
    for numerator in (
        -21734262311867549723777883309442995354317959821535428552622866273619550624437857274115396679165936000,
        -128681673822693304363735294258719652453751191019537206532230173463017759420003028659871940975912712000,
        -2472772042392441058214583134090433299847311403430832322827817755449418184625387206344082136342990464000,
    )
)
FORMAL_T1_UNIFORM_FLOOR = Fraction(2997, 20_000_000)
FORMAL_T0_UNIFORM_FLOOR = Fraction(5991, 80_000_000)

REVIEWED_GATE_ITEMS = (
    ("G0", "exact_config_control_box_and_no_defaults"),
    ("G1", "same_generator_source_stationary_geometry_counting_response"),
    ("G2", "unique_uniformly_full_rank_contracting_stationary_branch"),
    ("G3", "exact_Drazin_and_branch_derivative_identities"),
    ("G4", "actual_branch_projective_and_SLD_geometry"),
    ("G5", "tilted_generator_orientation_TP_and_current_derivative"),
    ("G6", "exact_response_one_form_and_curvature"),
    ("G7", "same_curvature_and_zero_preserving_homogeneous_map_refusal_only"),
    ("G8", "authenticated_geometry_counting_oracle_firewalls"),
    ("G9", "prediction_lock_and_positive_inference_refusal"),
    ("G10", "covariance_closure_units_zero_sets_and_obstructions"),
    ("G11", "reverse_count_identity_h_zero_and_same_model_nulls"),
    ("G12", "exact_orientation_qanti_factor_two_and_local_curvature_scope"),
    ("G13", "immutable_registry_and_claim_semantics"),
)

REVIEWED_GATE_OWNER_ITEMS = (
    ("G0", "CONFIG"),
    ("G1", "SHARED_GENERATOR"),
    ("G2", "SHARED_GENERATOR"),
    ("G3", "SHARED_GENERATOR"),
    ("G4", "GEOMETRY"),
    ("G5", "COUNTING"),
    ("G6", "COUNTING"),
    ("G7", "CLASSIFIER"),
    ("G8", "FIREWALL"),
    ("G9", "PIPELINE"),
    ("G10", "CLASSIFIER"),
    ("G11", "NULLS"),
    ("G12", "LOOP_SCOPE"),
    ("G13", "REGISTRY_CLAIMS"),
)

REVIEWED_CASE_DISPOSITION_ITEMS = (
    ("T0", "SAME_GENERATOR_CLASSICAL_THREE_CONTROL_ZERO_SET_OBSTRUCTION"),
    ("T1", "SAME_GENERATOR_COHERENT_THREE_CONTROL_ZERO_SET_OBSTRUCTION"),
    ("T2", "FCS_EXTENDED_EIGENBUNDLE_RESPONSE_IDENTITY_DISTINCT_FROM_STATE_CGT"),
    (
        "POSITIVE_MAP",
        "SAME_CURVATURE_AND_FROZEN_ZERO_PRESERVING_HOMOGENEOUS_OMEGA_MAPS_REFUSED_OTHERS_OPEN",
    ),
    ("SCOPE", "PASS_INTERNAL_ANALYTIC_NO_EMPIRICAL_EVIDENCE_MODEL_SPECIFIC_ONLY"),
)

REVIEWED_CASE_GATE_ITEMS = (
    (
        "T0",
        ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11", "G12", "G13"),
    ),
    (
        "T1",
        ("G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "G10", "G11", "G12", "G13"),
    ),
    ("T2", ("G0", "G1", "G3", "G5", "G6", "G8", "G9", "G10", "G12", "G13")),
    ("POSITIVE_MAP", ("G7", "G9", "G10", "G13")),
    ("SCOPE", ("G13",)),
)

REVIEWED_GATE_ITEMS_SHA256 = "e967361c6cb390494408cbd8f5b77241d1f2b9d6bbb79c6bab02f94c98a205a7"
REVIEWED_GATE_OWNER_SHA256 = "ad03ea9f49b25138566be2f8963e9277fb601433d61b5de7e679b08e8b592998"
REVIEWED_CASE_DISPOSITIONS_SHA256 = "8bbd236c48461e4220e3c274aca870ba4fd3f58fe91ac5975604aa21082eccb8"
REVIEWED_CASE_GATE_SHA256 = "ed162c5fde53e416b49e41c32a0f1266d2fdf0649dc716d77970d82e31421900"
REVIEWED_CLAIMS_SHA256 = "8a6b11ad5105a511111811bd24bfec3eec632a4b8a95df735d46a40966bd8d47"


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_payload(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _claims_payload() -> dict[str, object]:
    return {
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": MODEL_CONTRACT.disposition,
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "relation_scope": MODEL_CONTRACT.relation_scope,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "cases": list(REVIEWED_CASE_DISPOSITION_ITEMS),
    }


def validate_reviewed_registry() -> None:
    checks = (
        (sha256_payload(REVIEWED_GATE_ITEMS), REVIEWED_GATE_ITEMS_SHA256),
        (sha256_payload(REVIEWED_GATE_OWNER_ITEMS), REVIEWED_GATE_OWNER_SHA256),
        (sha256_payload(REVIEWED_CASE_DISPOSITION_ITEMS), REVIEWED_CASE_DISPOSITIONS_SHA256),
        (sha256_payload(REVIEWED_CASE_GATE_ITEMS), REVIEWED_CASE_GATE_SHA256),
        (sha256_payload(_claims_payload()), REVIEWED_CLAIMS_SHA256),
    )
    if any(expected == "TO_FREEZE" or actual != expected for actual, expected in checks):
        raise RuntimeError("immutable reviewed registry fingerprint mismatch")
    gate_ids = tuple(item[0] for item in REVIEWED_GATE_ITEMS)
    if gate_ids != tuple(f"G{index}" for index in range(14)) or len(set(gate_ids)) != 14:
        raise RuntimeError("reviewed gates must be exactly ordered G0 through G13")
    if tuple(item[0] for item in REVIEWED_GATE_OWNER_ITEMS) != gate_ids:
        raise RuntimeError("gate owner registry must exactly cover the ordered gates")
    case_ids = tuple(item[0] for item in REVIEWED_CASE_DISPOSITION_ITEMS)
    if tuple(item[0] for item in REVIEWED_CASE_GATE_ITEMS) != case_ids:
        raise RuntimeError("case gate registry order differs from dispositions")
    if any(gate not in gate_ids for _, gates in REVIEWED_CASE_GATE_ITEMS for gate in gates):
        raise RuntimeError("case registry contains an unknown gate")


def canonical_registry_record() -> dict[str, object]:
    validate_reviewed_registry()
    return {
        "schema_version": 1,
        "ordered_gates": [{"gate_id": gate, "name": name} for gate, name in REVIEWED_GATE_ITEMS],
        "gate_owners": [{"gate_id": gate, "owner": owner} for gate, owner in REVIEWED_GATE_OWNER_ITEMS],
        "case_dispositions": [
            {"case_id": case, "disposition": disposition}
            for case, disposition in REVIEWED_CASE_DISPOSITION_ITEMS
        ],
        "case_gates": [
            {"case_id": case, "gate_ids": list(gates)} for case, gates in REVIEWED_CASE_GATE_ITEMS
        ],
        "fingerprints": {
            "ordered_gates": REVIEWED_GATE_ITEMS_SHA256,
            "gate_owners": REVIEWED_GATE_OWNER_SHA256,
            "case_dispositions": REVIEWED_CASE_DISPOSITIONS_SHA256,
            "case_gates": REVIEWED_CASE_GATE_SHA256,
            "claims": REVIEWED_CLAIMS_SHA256,
        },
    }


def contract_issues(contract: SharedGeneratorContract) -> list[str]:
    def exact_value_matches(actual: Any, expected: Any) -> bool:
        if type(actual) is not type(expected):
            return False
        if type(expected) is tuple:
            return len(actual) == len(expected) and all(
                exact_value_matches(left, right) for left, right in zip(actual, expected, strict=True)
            )
        if type(expected) is Fraction:
            return actual.numerator == expected.numerator and actual.denominator == expected.denominator
        return actual == expected

    issues = [
        f"CONTRACT_MISMATCH:{field}"
        for field in MODEL_CONTRACT.__dataclass_fields__
        if not exact_value_matches(getattr(contract, field), getattr(MODEL_CONTRACT, field))
    ]
    if (
        contract.core_calls_are_acceptance_authority is not False
        or contract.finite_differences_are_acceptance_authority is not False
    ):
        issues.append("NUMERICAL_OR_CORE_REGRESSION_PROMOTED_TO_AUTHORITY")
    if contract.positive_map_claim_allowed is not False or contract.empirical_claim_allowed is not False:
        issues.append("CLAIM_CEILING_EXCEEDED")
    return sorted(set(issues))

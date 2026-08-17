"""Frozen contract and immutable gate registry for the 3D proof program."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from fractions import Fraction
from typing import Any


@dataclass(frozen=True)
class ConstitutiveMap3DContract:
    """Every reviewed convention and claim boundary used by the program."""

    experiment_id: str = "constitutive_map_3d_proof"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    relation_scope: str = "MODEL_SPECIFIC_RELATIONS_ONLY"
    claim_ceiling: str = (
        "internal synthetic Benchmark-C kinetic-control derivation and experiment-local QP3 "
        "same-operator calibration only; not universal or full CWT, physical response, empirical "
        "evidence, or a general CGT-response alignment law"
    )
    two_form_vector_order: tuple[str, str, str] = ("F_v_alpha", "F_alpha_u", "F_u_v")
    response_curvature_convention: str = "F_ij=partial_i beta_j-partial_j beta_i"
    berry_curvature_convention: str = "Omega_ij=+2 Im<C_i|C_j>"

    bc3_benchmark_id: str = "benchmark_c"
    bc3_branch_id: str = "C0"
    bc3_u_bounds: tuple[Fraction, Fraction] = (Fraction(1, 20), Fraction(3, 20))
    bc3_v_bounds: tuple[Fraction, Fraction] = (Fraction(1, 20), Fraction(3, 20))
    bc3_alpha_bounds: tuple[Fraction, Fraction] = (Fraction(3, 10), Fraction(2, 5))
    bc3_gain: Fraction = Fraction(9, 20)
    bc3_contraction_max: Fraction = Fraction(7, 10)
    bc3_update_rule: str = "x_next=x+alpha*(theta-x)"
    bc3_initialization: str = "equilibrium_at_stored_initial_control"
    bc3_clock: str = "right_endpoint_update_then_sample"
    bc3_reverse: str = "exact_reverse_of_stored_forward_controls"
    bc3_heldout_center: tuple[Fraction, Fraction, Fraction] = (
        Fraction(3, 25),
        Fraction(2, 25),
        Fraction(1, 3),
    )
    bc3_tangent_1: tuple[int, int, int] = (2, -1, 0)
    bc3_tangent_2: tuple[int, int, int] = (2, 0, -1)
    bc3_area_vector: tuple[int, int, int] = (1, 2, 2)
    bc3_scales: tuple[Fraction, ...] = (
        Fraction(1, 400),
        Fraction(1, 800),
        Fraction(1, 1600),
        Fraction(1, 3200),
    )
    bc3_steps_per_edge: tuple[int, ...] = (1024, 4096, 16384, 65536)
    bc3_fixed_scale_steps_per_edge: tuple[int, ...] = (64, 128, 256, 512)
    bc3_formula: str = (
        "eta=J_x dot dtheta;m=(1-alpha)/alpha;beta=-m*eta;" "F=alpha^-2*dalpha wedge eta-m*deta"
    )
    bc3_disposition: str = "SAME_MODEL_KINETIC_CONTROL_GEOMETRY_KERNEL_SEPARATION"

    qp3_domain: str = "R3_without_origin_declared_contractible_tubes_around_frozen_points"
    qp3_hamiltonian: str = "H=3/5*I+2/5*P_plus"
    qp3_projector: str = "P_plus=(I+n_dot_sigma)/2;n=lambda/abs(lambda)"
    qp3_eigenvalues: tuple[Fraction, Fraction] = (Fraction(1), Fraction(3, 5))
    qp3_gap: Fraction = Fraction(2, 5)
    qp3_positive_observable: str = "O_i=+partial_i_H"
    qp3_conventional_observable: str = "O_i=-partial_i_H"
    qp3_centers: tuple[tuple[int, int, int], ...] = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    qp3_heldout: tuple[Fraction, Fraction, Fraction] = (
        Fraction(1, 3),
        Fraction(2, 3),
        Fraction(2, 3),
    )
    qp3_heldout_density: Fraction = Fraction(1, 2)
    qp3_chern_number: int = 1
    qp3_disposition: str = "SAME_OPERATOR_SAME_CONNECTION_FULL_RANK_CALIBRATION_ONLY"

    pointwise_fit_allowed: bool = False
    geometry_fed_response_allowed: bool = False
    heldout_response_fit_allowed: bool = False
    auxiliary_branch_allowed: bool = False
    gain_as_control_allowed: bool = False
    universal_claim_allowed: bool = False

    def jsonable(self) -> dict[str, Any]:
        """Return strict-JSON data while preserving every exact rational."""

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


MODEL_CONTRACT = ConstitutiveMap3DContract()

REVIEWED_CASE_DISPOSITION_ITEMS = (
    ("BC3", "SAME_MODEL_KINETIC_CONTROL_GEOMETRY_KERNEL_SEPARATION"),
    ("QP3", "SAME_OPERATOR_SAME_CONNECTION_FULL_RANK_CALIBRATION_ONLY"),
    ("REFUSALS", "INELIGIBLE_AND_CIRCULAR_CONTROLS_REFUSED"),
    ("SCOPE", "PASS_INTERNAL_ANALYTIC_NO_EMPIRICAL_EVIDENCE_MODEL_SPECIFIC_ONLY"),
)

REVIEWED_CASE_GATE_OWNERSHIP = (
    (
        "BC3",
        (
            "bc3_contract_and_domain",
            "bc3_local_c0_and_predecessor_binding",
            "bc3_dynamics_contraction_and_conventions",
            "bc3_exact_factorization_and_covariance",
            "bc3_directed_interval_nonzero_margins",
            "bc3_geometry_rank1_and_alpha_fiber_separation",
            "bc3_prediction_lock_and_heldout_split",
            "bc3_response_oracle_firewall",
            "bc3_generic_ladder_and_nulls",
        ),
    ),
    (
        "QP3",
        (
            "qp3_same_operator_projector_and_gap",
            "qp3_monopole_geometry",
            "qp3_kubo_sign_and_factor",
            "qp3_rank3_centers_and_heldout",
            "qp3_gauge_coordinate_closure_and_chern",
            "qp3_constant_projector_and_nonscalar_refusals",
        ),
    ),
    ("REFUSALS", ("ineligible_and_circular_control_matrix",)),
    ("SCOPE", ("claim_ceiling_and_evidence_scope",)),
)

REVIEWED_CASE_DISPOSITIONS_SHA256 = "dcfa502591eab92410654c6599de4ea08219d5e06b918884797b490fbc292f55"
REVIEWED_GATE_OWNERSHIP_SHA256 = "a54ee7ef9b3dbd6856025fa5d61ad517fb8ae7415650adc2beda5ad1612f99bd"
REVIEWED_ORDERED_GATE_NAMES_SHA256 = "3abf916a18741dc404282634902666a5bf9c2b5ddfcfbf90c25d850da391b828"
REVIEWED_CLAIMS_CASES_SHA256 = "911cc98661ed0221c39990832793a1d4d3cfe50447fe98148632d88af42dad7c"


def _canonical_json_bytes(payload: Any) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(payload)).hexdigest()


def _ordered_gate_names() -> tuple[str, ...]:
    return tuple(name for _, names in REVIEWED_CASE_GATE_OWNERSHIP for name in names)


def _claims_cases_payload() -> dict[str, object]:
    return {
        "experiment_id": "constitutive_map_3d_proof",
        "disposition": "PASS_INTERNAL_ANALYTIC",
        "evidence_status": "NO_EMPIRICAL_EVIDENCE",
        "relation_scope": "MODEL_SPECIFIC_RELATIONS_ONLY",
        "claim_ceiling": (
            "internal synthetic Benchmark-C kinetic-control derivation and experiment-local QP3 "
            "same-operator calibration only; not universal or full CWT, physical response, empirical "
            "evidence, or a general CGT-response alignment law"
        ),
        "cases": list(REVIEWED_CASE_DISPOSITION_ITEMS),
    }


def validate_reviewed_registry_constants() -> None:
    checks = {
        "case_dispositions": (
            _sha256(REVIEWED_CASE_DISPOSITION_ITEMS),
            REVIEWED_CASE_DISPOSITIONS_SHA256,
        ),
        "gate_ownership": (
            _sha256(REVIEWED_CASE_GATE_OWNERSHIP),
            REVIEWED_GATE_OWNERSHIP_SHA256,
        ),
        "ordered_gate_names": (
            _sha256(_ordered_gate_names()),
            REVIEWED_ORDERED_GATE_NAMES_SHA256,
        ),
        "claims_cases": (
            _sha256(_claims_cases_payload()),
            REVIEWED_CLAIMS_CASES_SHA256,
        ),
    }
    failed = [name for name, (actual, reviewed) in checks.items() if actual != reviewed]
    if failed:
        raise RuntimeError(f"reviewed registry fingerprint mismatch: {failed}")
    names = _ordered_gate_names()
    if len(names) != 17 or len(names) != len(set(names)):
        raise RuntimeError("reviewed gate names must be exactly 17 ordered unique values")
    if _claims_cases_payload() != {
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": MODEL_CONTRACT.disposition,
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "relation_scope": MODEL_CONTRACT.relation_scope,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "cases": list(REVIEWED_CASE_DISPOSITION_ITEMS),
    }:
        raise RuntimeError("live contract is not the independently reviewed claims/cases record")


def expected_case_dispositions() -> dict[str, str]:
    validate_reviewed_registry_constants()
    return dict(REVIEWED_CASE_DISPOSITION_ITEMS)


def case_gate_ownership() -> tuple[tuple[str, tuple[str, ...]], ...]:
    validate_reviewed_registry_constants()
    return REVIEWED_CASE_GATE_OWNERSHIP


def canonical_registry_record() -> dict[str, object]:
    validate_reviewed_registry_constants()
    dispositions = [
        {"case_id": case_id, "disposition": disposition}
        for case_id, disposition in REVIEWED_CASE_DISPOSITION_ITEMS
    ]
    ownership = [
        {"case_id": case_id, "gate_names": list(gate_names)}
        for case_id, gate_names in REVIEWED_CASE_GATE_OWNERSHIP
    ]
    return {
        "schema_version": 2,
        "case_dispositions": dispositions,
        "case_dispositions_sha256": REVIEWED_CASE_DISPOSITIONS_SHA256,
        "gate_ownership": ownership,
        "gate_ownership_sha256": REVIEWED_GATE_OWNERSHIP_SHA256,
        "ordered_gate_names": list(_ordered_gate_names()),
        "ordered_gate_names_sha256": REVIEWED_ORDERED_GATE_NAMES_SHA256,
        "claims_cases_sha256": REVIEWED_CLAIMS_CASES_SHA256,
    }


def contract_issues(contract: ConstitutiveMap3DContract) -> list[str]:
    """Reject any deviation from the reviewed specialization."""

    issues = [
        f"CONTRACT_MISMATCH:{field_name}"
        for field_name in MODEL_CONTRACT.__dataclass_fields__
        if getattr(contract, field_name) != getattr(MODEL_CONTRACT, field_name)
    ]
    flattened = [name for _, names in case_gate_ownership() for name in names]
    if len(flattened) != len(set(flattened)):
        issues.append("DUPLICATE_GATE_OWNERSHIP")
    if contract.bc3_area_vector != (1, 2, 2):
        issues.append("BC3_AREA_VECTOR_MISMATCH")
    if any(
        (
            contract.pointwise_fit_allowed,
            contract.geometry_fed_response_allowed,
            contract.heldout_response_fit_allowed,
            contract.auxiliary_branch_allowed,
            contract.gain_as_control_allowed,
            contract.universal_claim_allowed,
        )
    ):
        issues.append("FORBIDDEN_SCOPE_ENABLED")
    return sorted(set(issues))

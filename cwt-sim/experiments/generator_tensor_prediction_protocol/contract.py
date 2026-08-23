"""Frozen pre-response contract, exposure registry, and gate ownership."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from fractions import Fraction
from types import MappingProxyType

from .exact import canonical_exact_sha256

Point = tuple[Fraction, Fraction, Fraction]


@dataclass(frozen=True)
class ProtocolContract:
    experiment_id: str = "generator_tensor_prediction_protocol"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    relation_scope: str = "MODEL_SPECIFIC_RELATIONS_ONLY"
    response_accessed: bool = False
    response_unlock_available: bool = False
    node_count: int = 5
    controls: tuple[str, str, str] = ("b", "d", "t")
    coordinate_scales: Point = (
        Fraction(1, 50),
        Fraction(1, 50),
        Fraction(1, 6),
    )
    edge_rate: Fraction = Fraction(1, 5)
    depolarizing_rate: Fraction = Fraction(1, 25)
    dephasing_rate: Fraction = Fraction(3, 10)
    line_coherent_scale: Fraction = Fraction(1, 10)
    chord_radius: Fraction = Fraction(1, 20)
    two_form_order: tuple[str, str, str] = ("d_t", "t_b", "b_d")
    count_orientation_values: tuple[int, int, int] = (-1, 0, 1)
    claim_ceiling: str = (
        "response-free internal analytic eligibility and no-go certificates only; "
        "no response observation, fitted predictor, universal, full-CWT, physical, "
        "empirical, or successful-heldout claim"
    )


MODEL_CONTRACT = ProtocolContract()

A_CENTERS: tuple[Point, ...] = (
    (Fraction(3, 200), Fraction(21, 100), Fraction(2, 5)),
    (Fraction(9, 200), Fraction(21, 100), Fraction(3, 5)),
    (Fraction(3, 200), Fraction(6, 25), Fraction(3, 5)),
    (Fraction(9, 200), Fraction(6, 25), Fraction(2, 5)),
    (Fraction(1, 40), Fraction(43, 200), Fraction(7, 12)),
    (Fraction(1, 25), Fraction(47, 200), Fraction(5, 12)),
)
V_CENTERS: tuple[Point, Point] = (
    (Fraction(1, 50), Fraction(23, 100), Fraction(11, 20)),
    (Fraction(1, 25), Fraction(11, 50), Fraction(9, 20)),
)
HELDOUT_CENTER: Point = (
    Fraction(7, 200),
    Fraction(23, 100),
    Fraction(7, 15),
)
HELDOUT_TANGENTS = ((1, 1, 0), (-1, 2, 1))
HELDOUT_AREA_VECTOR = (1, -1, 3)

PUBLIC_PREDECESSOR_CENTER: Point = (
    Fraction(3, 100),
    Fraction(9, 40),
    Fraction(1, 2),
)
EXPOSED_DIAGNOSTIC_CENTERS: tuple[Point, ...] = (
    (Fraction(1, 100), Fraction(41, 200), Fraction(1, 3)),
    (Fraction(1, 20), Fraction(41, 200), Fraction(2, 3)),
    (Fraction(1, 100), Fraction(49, 200), Fraction(2, 3)),
    (Fraction(1, 20), Fraction(49, 200), Fraction(1, 3)),
)

RESERVATION_STATUS = "RESERVED_BY_PROCESS_ATTESTATION / NOT_CRYPTOGRAPHICALLY_PROVEN_UNOPENED"

REVIEWED_EXPOSURE_ENTRIES = (
    (
        "PUBLIC_PR309_CENTER",
        "excluded_public_predecessor_context",
        (Fraction(3, 100), Fraction(9, 40), Fraction(1, 2)),
        "EXPOSED_PUBLIC_PREDECESSOR_RESPONSE",
    ),
    *tuple(
        (f"D{index}", "excluded_retrospective_diagnostic", point, "EXPOSED_INELIGIBLE_DIAGNOSTIC")
        for index, point in enumerate(EXPOSED_DIAGNOSTIC_CENTERS, start=1)
    ),
    *tuple(
        (f"A{index}", "reserved_calibration", point, RESERVATION_STATUS)
        for index, point in enumerate(A_CENTERS, start=1)
    ),
    *tuple(
        (f"V{index}", "reserved_whole_center_confirmation", point, RESERVATION_STATUS)
        for index, point in enumerate(V_CENTERS, start=1)
    ),
    ("H", "reserved_heldout_oblique", HELDOUT_CENTER, RESERVATION_STATUS),
)
REVIEWED_EXPOSURE_REGISTRY_SHA256 = "ec13af5208b2ba2d3a8d7806d04df95877394abaf42e6676c7dbce2a049fd509"

EXPOSURE_REGISTRY = MappingProxyType(
    {
        name: MappingProxyType({"role": role, "point": point, "status": status})
        for name, role, point, status in REVIEWED_EXPOSURE_ENTRIES
    }
)

ORDERED_GATES = (
    "G0_exact_contract_and_exposure_registry",
    "G1_count_blind_generator_and_branch",
    "G2_krylov3_exact_closure_coefficients",
    "G3_krylov3_rank_three_nullity_zero",
    "G4_krylov3_no_nontrivial_closed_member",
    "G5_connection_scalar_and_gauge_construction",
    "G6_connection_structural_closure_covariance_units",
    "G7_connection_exact_frozen_point_design",
    "G8_reserved_confirmation_and_heldout_geometry_only",
    "G9_role_firewalls_and_response_sentinel",
    "G10_pre_response_protocol_state",
    "G11_claim_ceiling",
)

CASE_GATE_MAP = MappingProxyType(
    {
        "N0_KRYLOV3_NO_GO": ORDERED_GATES[0:5] + ORDERED_GATES[8:12],
        "P0_CONNECTION_GEOMETRY_ELIGIBILITY": (
            ORDERED_GATES[0],
            ORDERED_GATES[1],
            *ORDERED_GATES[5:12],
        ),
    }
)

EXPECTED_CASE_DISPOSITIONS = MappingProxyType(
    {
        "N0_KRYLOV3_NO_GO": "INELIGIBLE_NOT_CLOSED",
        "P0_CONNECTION_GEOMETRY_ELIGIBILITY": "ELIGIBLE_PRE_RESPONSE_ONLY",
    }
)


def _strict_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) is tuple:
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)  # type: ignore[arg-type]
        )
    if type(left) is list:
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)  # type: ignore[arg-type]
        )
    if type(left) is dict:
        return tuple(left) == tuple(right) and all(  # type: ignore[arg-type]
            _strict_equal(left[key], right[key]) for key in left  # type: ignore[index,union-attr]
        )
    if type(left) is MappingProxyType:
        return tuple(left) == tuple(right) and all(  # type: ignore[arg-type]
            _strict_equal(left[key], right[key]) for key in left  # type: ignore[index,union-attr]
        )
    return bool(left == right)


def contract_issues(contract: ProtocolContract = MODEL_CONTRACT) -> tuple[str, ...]:
    expected = ProtocolContract()
    issues = []
    if type(contract) is not ProtocolContract:
        return ("contract_type",)
    observed_record = asdict(contract)
    expected_record = asdict(expected)
    for name, wanted in expected_record.items():
        observed = observed_record[name]
        if not _strict_equal(observed, wanted):
            issues.append(name)
    return tuple(issues)


def exposure_registry_payload(registry: object = EXPOSURE_REGISTRY) -> tuple:
    if type(registry) is not MappingProxyType:
        raise TypeError("exposure registry must be the exact immutable mapping type")
    payload = []
    for name, entry in registry.items():
        if type(name) is not str or type(entry) is not MappingProxyType:
            raise TypeError("exposure registry entry type refused")
        if tuple(entry) != ("role", "point", "status"):
            raise ValueError("exposure registry entry schema refused")
        role, point, status = entry["role"], entry["point"], entry["status"]
        if (
            type(role) is not str
            or type(point) is not tuple
            or len(point) != 3
            or any(type(value) is not Fraction for value in point)
            or type(status) is not str
        ):
            raise TypeError("exposure registry entry value type refused")
        payload.append((name, role, point, status))
    return tuple(payload)


def exposure_registry_sha256(registry: object = EXPOSURE_REGISTRY) -> str:
    return canonical_exact_sha256(exposure_registry_payload(registry))


def exposure_registry_issues(registry: object = EXPOSURE_REGISTRY) -> tuple[str, ...]:
    issues: list[str] = []
    try:
        payload = exposure_registry_payload(registry)
    except (TypeError, ValueError) as exc:
        return (f"schema:{exc}",)
    if not _strict_equal(payload, REVIEWED_EXPOSURE_ENTRIES):
        issues.append("reviewed_entries")
    if len({entry[2] for entry in payload}) != len(payload):
        issues.append("duplicate_point")
    if canonical_exact_sha256(payload) != REVIEWED_EXPOSURE_REGISTRY_SHA256:
        issues.append("reviewed_digest")
    return tuple(issues)

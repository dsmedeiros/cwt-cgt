"""Frozen exact model, claim, case, and gate contract."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, fields, is_dataclass
from fractions import Fraction
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True)
class LoopFluxContract:
    experiment_id: str = "loop_flux_counting_curvature_proof"
    disposition: str = "PASS_INTERNAL_ANALYTIC"
    evidence_status: str = "NO_EMPIRICAL_EVIDENCE"
    relation_scope: str = "MODEL_SPECIFIC_RELATIONS_ONLY"
    classification: str = (
        "BOTH_CURVATURES_NONZERO / SCALAR_MAP_REFUTED_BY_SIGN_NONCOLLINEARITY / "
        "GENERAL_GENERATOR_DEPENDENT_MAP_OPEN"
    )
    claim_ceiling: str = (
        "exact internal five-state one-chord Lindblad stationary-branch, mean-Uhlmann, "
        "and counted-FCS local-curvature classification only; no full-CWT, universal, "
        "physical-pumping, calibrated-clock, empirical, or positive-general-map claim"
    )
    node_count: int = 5
    controls: tuple[str, str, str] = ("b", "d", "t")
    b_bounds: tuple[Fraction, Fraction] = (Fraction(1, 100), Fraction(1, 20))
    d_bounds: tuple[Fraction, Fraction] = (Fraction(41, 200), Fraction(49, 200))
    t_bounds: tuple[Fraction, Fraction] = (Fraction(1, 3), Fraction(2, 3))
    center: tuple[Fraction, Fraction, Fraction] = (
        Fraction(3, 100),
        Fraction(9, 40),
        Fraction(1, 2),
    )
    edge_rate: Fraction = Fraction(1, 5)
    depolarizing_rate: Fraction = Fraction(1, 25)
    dephasing_rate: Fraction = Fraction(3, 10)
    line_coherent_scale: Fraction = Fraction(1, 10)
    chord_radius: Fraction = Fraction(1, 20)
    site_potential_scale: Fraction = Fraction(0)
    count_edge: tuple[int, int] = (1, 2)
    positive_count_definition: str = "positive_q_counts_index_1_to_2_physical_nodes_2_to_3"
    loop_orientation: tuple[int, int, int, int] = (0, 1, 2, 0)
    two_form_vector_order: tuple[str, str, str] = ("F_d_t", "F_t_b", "F_b_d")
    metric_convention: str = "g_ij=Tr[X_i L_j]=1/2 Tr[rho {L_i,L_j}]"
    curvature_convention: str = "Omega_ij=(1/(4i))*Tr[rho[L_i,L_j]]"
    local_curvature_only: bool = True
    finite_time_pumping_claimed: bool = False
    positive_general_map_claimed: bool = False
    empirical_evidence_claimed: bool = False
    physical_clock_calibrated: bool = False
    core_calls_are_acceptance_authority: bool = False


MODEL_CONTRACT = LoopFluxContract()

ORDERED_GATES = (
    "G0_exact_config",
    "G1_generator_source_identity",
    "G2_flux_and_gauge_covariance",
    "G3_branch_floor_and_gap",
    "G4_drazin_derivatives_and_rank",
    "G5_sld_mean_uhlmann_curvature",
    "G6_counting_and_fcs_identity",
    "G7_scalar_noncollinearity_obstruction",
    "G8_covariance_units_and_local_curvature",
    "G9_reverse_count_and_null_controls",
    "G10_lane_firewalls_and_lock",
    "G11_general_map_refusal",
    "G12_provenance_registry_and_claim_ceiling",
)

CASE_GATE_MAP = MappingProxyType(
    {
        "C1_MODEL_AND_SOURCE": ("G0_exact_config", "G1_generator_source_identity"),
        "C2_FLUX_BRANCH_AND_RANK": (
            "G2_flux_and_gauge_covariance",
            "G3_branch_floor_and_gap",
            "G4_drazin_derivatives_and_rank",
        ),
        "C3_STATE_GEOMETRY": ("G5_sld_mean_uhlmann_curvature",),
        "C4_COUNTING_GEOMETRY": ("G6_counting_and_fcs_identity",),
        "C5_RELATION_CLASSIFICATION": (
            "G7_scalar_noncollinearity_obstruction",
            "G8_covariance_units_and_local_curvature",
        ),
        "C6_NULLS_AND_FIREWALLS": (
            "G9_reverse_count_and_null_controls",
            "G10_lane_firewalls_and_lock",
        ),
        "C7_SCOPE_AND_PUBLICATION": (
            "G11_general_map_refusal",
            "G12_provenance_registry_and_claim_ceiling",
        ),
    }
)

EXPECTED_CASE_DISPOSITIONS = MappingProxyType({name: "PASS" for name in CASE_GATE_MAP})

# Frozen only after an independent source-first review.  Live producers never
# derive their own acceptance oracle from these values.
REVIEWED_RECORD_DIGESTS = MappingProxyType(
    {
        "contract": "d5500b023825a84b75f1dedac2129f01e02542f131f3060d53f9ec5488e90db6",
        "generator": "0fd74a7b675995f3ad43aa7ce41cea4f288d4dd6e5037986f0b5fe478e5fd950",
        "flux": "82271d035f1e09a0f25b1213eb8fb51287877c3dc04b194fe9ab7df2bc8e588f",
        "floor": "22d24ad41391889cccb3d707f2db849356f3fee9a2a218f7371fc9bcf1030532",
        "branch": "4f7343cab06633f6c8020a4e05a0b93e8110face94b7e112e25885d5244f4175",
        "geometry": "741ec419a18290ab9e8528c9b2441fe8c569db01ccf4045ac3dcf9db499a5f9b",
        "counting": "6d28a0be1f6fa40040424d5d8ffd58f95e7c5172bc1b83464675c2e1839331be",
        "fcs": "9f551d3e538a3ba44534dbb45147a4363b1307653a8bb3fc6b6ebadf544ad154",
        "nulls": "b87b6cb568d59f4c8dad44bc40ffe4f7323ee8630bc4663b9d2ed983df02750d",
        "pipeline": "e6ed5016a3f51bdd6cef7f454a18f358c37069de02fdeec6beee2a3f31d7915f",
        "scope": "cfa000c77951834a46f2058bd16a71a53501d0e4b9a96e95f03870b17fe2fdab",
    }
)
REVIEWED_RECORD_AGGREGATE_SHA256 = "43016768dba2e8f31ae7fefedea9082ff1902ea4936225e7e89828d7cb800709"


def _jsonable(value: Any) -> Any:
    from .exact import Gaussian

    if type(value) is Gaussian:
        return {
            "real": _jsonable(value.real),
            "imag": _jsonable(value.imag),
        }
    if type(value) is Fraction:
        return {
            "fraction": f"{value.numerator}/{value.denominator}",
            "numerator": value.numerator,
            "denominator": value.denominator,
        }
    if type(value) is tuple:
        return [_jsonable(item) for item in value]
    if type(value) is list:
        return [_jsonable(item) for item in value]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError("noncanonical contract mapping key")
        return {key: _jsonable(item) for key, item in value.items()}
    if type(value) is MappingProxyType:
        return _jsonable(dict(value))
    if value is None or type(value) in {bool, int, str}:
        return value
    raise TypeError(f"noncanonical contract value: {type(value).__name__}")


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(_jsonable(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    ).encode("utf-8")


def sha256_record(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


REVIEWED_CONTRACT_SHA256 = "d5500b023825a84b75f1dedac2129f01e02542f131f3060d53f9ec5488e90db6"
REVIEWED_REGISTRY_SHA256 = "5aee5de36a6bea68433f4d208e56dce985ea6beb277a121e774926000b5f37a5"


def _strict_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if is_dataclass(left) and not isinstance(left, type):
        return all(
            _strict_equal(getattr(left, field.name), getattr(right, field.name)) for field in fields(left)
        )
    if isinstance(left, (tuple, list)):
        return len(left) == len(right) and all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    if isinstance(left, dict):
        return tuple(left) == tuple(right) and all(_strict_equal(left[key], right[key]) for key in left)
    return bool(left == right)


def contract_issues(contract: LoopFluxContract = MODEL_CONTRACT) -> list[str]:
    if not _strict_equal(contract, MODEL_CONTRACT):
        return ["contract differs in exact nested type or value"]
    try:
        if sha256_record(asdict(contract)) != REVIEWED_CONTRACT_SHA256:
            return ["contract differs from the exact reviewed typed record"]
    except (TypeError, ValueError, OverflowError) as exc:
        return [f"contract is not canonical: {exc}"]
    return []


def registry_issues() -> list[str]:
    current = {
        "ordered_gates": ORDERED_GATES,
        "case_gate_map": dict(CASE_GATE_MAP),
        "expected_case_dispositions": dict(EXPECTED_CASE_DISPOSITIONS),
        "claims": {
            "disposition": MODEL_CONTRACT.disposition,
            "evidence_status": MODEL_CONTRACT.evidence_status,
            "relation_scope": MODEL_CONTRACT.relation_scope,
            "classification": MODEL_CONTRACT.classification,
            "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        },
    }
    issues: list[str] = []
    if sha256_record(current) != REVIEWED_REGISTRY_SHA256:
        issues.append("registry differs from its independent reviewed digest")
    owned = [gate for gates in CASE_GATE_MAP.values() for gate in gates]
    if tuple(owned) != ORDERED_GATES:
        issues.append("gate ownership must exactly preserve the reviewed order")
    if len(owned) != len(set(owned)):
        issues.append("gate ownership contains a duplicate")
    return issues


def record_digest_issues(records: dict[str, object]) -> list[str]:
    expected_keys = tuple(REVIEWED_RECORD_DIGESTS)
    if tuple(records) != expected_keys:
        return ["record names/order differ from reviewed record registry"]
    try:
        observed = {name: sha256_record(records[name]) for name in expected_keys}
    except (TypeError, ValueError, OverflowError) as exc:
        return [f"reviewed records are noncanonical: {exc}"]
    issues = [name for name in expected_keys if observed[name] != REVIEWED_RECORD_DIGESTS[name]]
    aggregate = sha256_record(observed)
    if aggregate != REVIEWED_RECORD_AGGREGATE_SHA256:
        issues.append("aggregate")
    return [f"reviewed record digest mismatch: {name}" for name in issues]

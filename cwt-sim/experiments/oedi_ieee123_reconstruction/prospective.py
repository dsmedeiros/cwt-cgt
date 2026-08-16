"""Metadata-only preparation for the locked prospective passive analysis.

``prepare_prospective`` hashes profile bytes and parses DSS metadata, but it
never converts a nonlegacy CSV value to a number or computes an outcome
statistic.  Confirmation is implemented separately and remains digest-locked.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import math
import platform
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
import scipy

from experiments.oedi_ieee123_reconstruction.retrospective import (
    LEGACY_PROFILE_PATHS,
    PV49_PATH,
    TEMPERATURE_PATH,
    _line_edges,
    build_corrected_physical_graph,
    derive_source_bus,
    parse_transformer_metadata,
)
from experiments.oedi_ieee123_reconstruction.source import (
    EXPERIMENT_DIR,
    PINNED_COMMIT,
    SourceIntegrityError,
    canonical_json_sha256,
    count_nonempty_rows_bytes,
    git_blob_metadata,
    parse_load_definitions,
    parse_loadshape_definitions,
    sha256_file,
    verify_source,
)

PROTOCOL_PATH = EXPERIMENT_DIR / "PROSPECTIVE_PASSIVE_PROTOCOL_LOCK.md"
SPLIT_SALT = "CWT-OEDI-PASSIVE-V1"
LEGACY_BASE_BUSES = frozenset({"1", "19", "47", "49", "65"})
PHASE_BY_CONDUCTOR = {"1": "A", "2": "B", "3": "C"}
MAPPING_AMENDMENT = {
    "timing": "pre_outcome_access",
    "reason": (
        "Pinned OpenDSS comment semantics make the trailing yearly tokens for S48 and S49c "
        "inactive. No identifier-based inference is permitted."
    ),
    "affected_loads": ["S48", "S49c"],
    "classification": "no_explicit_active_yearly_mapping",
    "superseded_draft_hash": None,
    "outcome_values_seen_before_amendment": False,
}
EXPECTED_CALIBRATION_IDS = {
    "S7a",
    "S12b",
    "S33a",
    "S34c",
    "S4c",
    "S53a",
    "S59b",
    "S60a",
    "S62c",
    "S66c",
    "S75c",
    "S79a",
    "S94a",
    "S96b",
    "S107b",
    "S111a",
}
EXPECTED_CONFIRMATION_IDS = {
    "S2b",
    "S5c",
    "S6c",
    "S9a",
    "S10a",
    "S11a",
    "S16c",
    "S17c",
    "S20a",
    "S22b",
    "S24c",
    "S28a",
    "S29a",
    "S30c",
    "S31c",
    "S32c",
    "S37a",
    "S38b",
    "S39b",
    "S41c",
    "S42a",
    "S43b",
    "S45a",
    "S46a",
    "S50c",
    "S51a",
    "S52a",
    "S55a",
    "S56b",
    "S58b",
    "S63a",
    "S64b",
    "S68a",
    "S69a",
    "S70a",
    "S71a",
    "S73c",
    "S74c",
    "S77b",
    "S80b",
    "S82a",
    "S83c",
    "S84c",
    "S85c",
    "S86b",
    "S87b",
    "S88a",
    "S90b",
    "S92c",
    "S95b",
    "S98a",
    "S99b",
    "S100c",
    "S102c",
    "S103c",
    "S104c",
    "S106b",
    "S109a",
    "S112a",
    "S113a",
    "S114a",
}


def _phase_label(load: dict[str, Any]) -> str | None:
    if load["phases"] != 1 or load["conn"] != "wye":
        return None
    conductors = load["conductors"]
    if len(conductors) != 1:
        return None
    return PHASE_BY_CONDUCTOR.get(conductors[0])


def _signature_text(signature: tuple[int, int, int]) -> str:
    return f"A{signature[0]}_B{signature[1]}_C{signature[2]}"


def _bus_hash(base_bus: str) -> tuple[str, str]:
    hash_input = f"{SPLIT_SALT}|{PINNED_COMMIT}|BUS|{base_bus}"
    return hash_input, hashlib.sha256(hash_input.encode("utf-8")).hexdigest()


def allocate_cluster_split(
    eligible_loads: list[dict[str, Any]],
) -> dict[str, Any]:
    """Allocate calibration buses by signature-stratified largest remainder."""

    by_bus: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for load in eligible_loads:
        by_bus[load["base_bus"]].append(load)
    if not by_bus:
        raise SourceIntegrityError("No fresh eligible bus clusters are available")

    buses_by_signature: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    bus_records: dict[str, dict[str, Any]] = {}
    for base_bus, members in sorted(by_bus.items()):
        counts = Counter(member["phase"] for member in members)
        signature = (counts["A"], counts["B"], counts["C"])
        hash_input, digest = _bus_hash(base_bus)
        buses_by_signature[signature].append(base_bus)
        bus_records[base_bus] = {
            "base_bus": base_bus,
            "signature": _signature_text(signature),
            "signature_counts": {"A": signature[0], "B": signature[1], "C": signature[2]},
            "split_hash_input_utf8": hash_input,
            "split_hash_sha256": digest,
            "eligible_load_ids": sorted(member["load_id"] for member in members),
        }

    bus_count = len(by_bus)
    target = math.ceil(0.20 * bus_count)
    floors: dict[tuple[int, int, int], int] = {}
    remainders: list[tuple[float, str, tuple[int, int, int]]] = []
    for signature, buses in buses_by_signature.items():
        exact = target * len(buses) / bus_count
        floors[signature] = math.floor(exact)
        remainders.append((exact - floors[signature], _signature_text(signature), signature))
    unallocated = target - sum(floors.values())
    for _, _, signature in sorted(remainders, key=lambda item: (-item[0], item[1]))[:unallocated]:
        floors[signature] += 1

    calibration_buses: set[str] = set()
    allocation_records = []
    for signature in sorted(buses_by_signature, key=_signature_text):
        ordered = sorted(
            buses_by_signature[signature],
            key=lambda base_bus: (bus_records[base_bus]["split_hash_sha256"], base_bus),
        )
        count = floors[signature]
        selected = ordered[:count]
        calibration_buses.update(selected)
        allocation_records.append(
            {
                "signature": _signature_text(signature),
                "remaining_bus_count": len(ordered),
                "calibration_quota_exact": target * len(ordered) / bus_count,
                "calibration_bus_count": count,
                "calibration_buses": selected,
            }
        )

    for base_bus, record in bus_records.items():
        record["split"] = "calibration" if base_bus in calibration_buses else "confirmation"
    return {
        "salt": SPLIT_SALT,
        "pinned_commit_in_digest": PINNED_COMMIT,
        "unit": "physical_base_bus_cluster",
        "canonical_bus_rule": (
            "resolved active DSS Bus1 base with conductor suffix stripped, whitespace trimmed, "
            "case-folded, and no numeric coercion"
        ),
        "stratification": "eligible phase-count signature (nA,nB,nC)",
        "allocation": "K=ceil(0.20*N), deterministic largest remainder, then lowest hashes",
        "largest_remainder_tie_break": "lexicographic signature text A<n>_B<n>_C<n>",
        "remaining_bus_count": bus_count,
        "calibration_target_bus_count": target,
        "calibration_buses": sorted(calibration_buses),
        "confirmation_buses": sorted(set(by_bus) - calibration_buses),
        "signature_allocations": allocation_records,
        "buses": [bus_records[bus] for bus in sorted(bus_records)],
    }


def _loadshape_catalog(
    source_dir: Path, *, include_git_metadata: bool
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    definitions = parse_loadshape_definitions(source_dir / "qsts/IEEE123LoadShapes.dss")
    by_shape: dict[str, dict[str, Any]] = {}
    catalog: list[dict[str, Any]] = []
    for definition in definitions:
        if definition.shape_id in by_shape:
            raise SourceIntegrityError(f"Duplicate LoadShape identifier: {definition.shape_id}")
        path = source_dir / definition.profile_path
        exists = path.is_file()
        record = {
            "shape_id": definition.shape_id,
            "profile_path": definition.profile_path,
            "profile_exists": exists,
            "sha256": sha256_file(path) if exists else None,
            "byte_size": path.stat().st_size if exists else None,
            "nonempty_row_count": count_nonempty_rows_bytes(path) if exists else None,
            "declared_npts": definition.npts,
            "declared_interval_hours": definition.interval_hours,
            "numeric_values_accessed": False,
        }
        if include_git_metadata and exists:
            blob = git_blob_metadata(source_dir, definition.profile_path)
            record.update(blob)
            if record["sha256"] != blob["canonical_git_blob_sha256"]:
                raise SourceIntegrityError(
                    f"Working bytes for {definition.profile_path} do not match the canonical "
                    f"pinned Git blob: working SHA-256 {record['sha256']}, canonical "
                    f"{blob['canonical_git_blob_sha256']}"
                )
            if record["byte_size"] != blob["git_blob_byte_size"]:
                raise SourceIntegrityError(
                    f"Working byte size for {definition.profile_path} differs from the "
                    "canonical pinned Git blob"
                )
        else:
            record.update(
                {
                    "git_blob_oid": None,
                    "git_blob_byte_size": None,
                    "canonical_git_blob_sha256": None,
                }
            )
        catalog.append(record)
        by_shape[definition.shape_id] = record
    return catalog, by_shape


def _source_code_hashes() -> dict[str, str]:
    paths = (
        EXPERIMENT_DIR / "__init__.py",
        EXPERIMENT_DIR / "source.py",
        EXPERIMENT_DIR / "retrospective.py",
        EXPERIMENT_DIR / "prospective.py",
        EXPERIMENT_DIR / "prospective_confirm.py",
        EXPERIMENT_DIR / "run.py",
        EXPERIMENT_DIR / "RETROSPECTIVE_METHOD.md",
        PROTOCOL_PATH,
        EXPERIMENT_DIR / "UPSTREAM_MANIFEST.json",
    )
    return {path.name: sha256_file(path) for path in paths}


def runtime_versions() -> dict[str, str]:
    """Return the decision-affecting runtime versions frozen by prepare."""

    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "scipy": scipy.__version__,
        "networkx": nx.__version__,
        "typer": importlib.metadata.version("typer"),
    }


def membership_payload(loads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return the exact decision-affecting membership projection."""

    return [
        {
            "load_id": load["load_id"],
            "base_bus": load["base_bus"],
            "phase": load["phase"],
            "profile_path": load["profile_path"],
            "profile_sha256": load["profile_sha256"],
            "mapping_status": load["mapping_status"],
            "profile_metadata_valid": load["profile_metadata_valid"],
            "membership": load["membership"],
        }
        for load in loads
    ]


def compute_split_manifest_hash(prepared: dict[str, Any]) -> str:
    """Recompute the split/membership hash from mutable prepared fields."""

    return canonical_json_sha256(
        {
            "split": prepared["split"],
            "membership": membership_payload(prepared["loads"]),
            "amendment": prepared["mapping_amendment"],
        }
    )


def compute_source_inventory_hash(prepared: dict[str, Any]) -> str:
    """Recompute the all-91 canonical profile catalog hash."""

    return canonical_json_sha256(prepared["loadshape_catalog"])


def _distance_adequacy(
    graph: nx.Graph,
    confirmation: list[dict[str, Any]],
) -> dict[str, Any]:
    by_phase: dict[str, set[str]] = defaultdict(set)
    for load in confirmation:
        by_phase[load["phase"]].add(load["base_bus"])
    distances_by_phase: dict[str, list[int]] = {}
    for phase in ("A", "B", "C"):
        buses = sorted(by_phase[phase])
        distances = {
            nx.shortest_path_length(graph, left, right)
            for index, left in enumerate(buses)
            for right in buses[index + 1 :]
        }
        distances_by_phase[phase] = sorted(distances)
    return {
        "distinct_graph_distances_by_phase": distances_by_phase,
        "at_least_three_distances_each_phase": all(
            len(distances_by_phase[phase]) >= 3 for phase in ("A", "B", "C")
        ),
    }


def prepare_prospective(
    source_dir: Path,
    *,
    require_git: bool = True,
    enforce_pinned_counts: bool = True,
) -> dict[str, Any]:
    """Create the frozen split/access plan without opening any outcome values."""

    source_dir = source_dir.resolve()
    verification = verify_source(source_dir, require_git=require_git)
    load_definitions = parse_load_definitions(source_dir / "qsts/IEEE123LoadsQsts.dss")
    loadshape_catalog, shape_by_id = _loadshape_catalog(source_dir, include_git_metadata=require_git)

    loads: list[dict[str, Any]] = []
    mapped_count = 0
    mapped_wye_count = 0
    mapping_defects: list[dict[str, Any]] = []
    for definition in load_definitions:
        record = definition.to_dict()
        phase = _phase_label(record)
        shape = shape_by_id.get(definition.yearly) if definition.yearly else None
        if definition.yearly is None:
            mapping_status = "no_explicit_active_yearly_mapping"
        elif shape is None:
            mapping_status = "active_yearly_does_not_resolve_uniquely"
        else:
            mapping_status = "explicit_active_yearly_mapping"
        profile_valid = bool(
            shape
            and shape["profile_exists"]
            and shape["declared_npts"] == 35_040
            and shape["nonempty_row_count"] == 35_040
            and shape["declared_interval_hours"] == 0.25
        )
        mapped = mapping_status == "explicit_active_yearly_mapping"
        mapped_count += int(mapped)
        mapped_wye_count += int(mapped and phase is not None)
        record.update(
            {
                "phase": phase,
                "mapping_status": mapping_status,
                "profile_path": shape["profile_path"] if shape else None,
                "profile_sha256": shape["sha256"] if shape else None,
                "profile_byte_size": shape["byte_size"] if shape else None,
                "sample_count": shape["nonempty_row_count"] if shape else None,
                "interval_hours": shape["declared_interval_hours"] if shape else None,
                "profile_metadata_valid": profile_valid,
                "numeric_values_accessed": False,
            }
        )
        if not mapped:
            mapping_defects.append(
                {
                    "load_id": definition.load_id,
                    "base_bus": definition.base_bus,
                    "mapping_status": mapping_status,
                }
            )
        loads.append(record)

    fresh_eligible = [
        load
        for load in loads
        if load["base_bus"] not in LEGACY_BASE_BUSES
        and load["phase"] is not None
        and load["mapping_status"] == "explicit_active_yearly_mapping"
        and load["profile_metadata_valid"]
    ]
    split = allocate_cluster_split(fresh_eligible)
    calibration_buses = set(split["calibration_buses"])
    confirmation_buses = set(split["confirmation_buses"])
    fresh_eligible_ids = {load["load_id"] for load in fresh_eligible}
    for load in loads:
        if load["base_bus"] in LEGACY_BASE_BUSES:
            membership = "discovery_only_legacy_bus_cluster"
        elif load["load_id"] in fresh_eligible_ids:
            membership = "calibration" if load["base_bus"] in calibration_buses else "confirmation"
        elif load["mapping_status"] != "explicit_active_yearly_mapping":
            membership = "catalogued_unmapped_excluded"
        else:
            membership = "exploratory_ineligible_excluded"
        load["membership"] = membership

    calibration = [load for load in loads if load["membership"] == "calibration"]
    confirmation = [load for load in loads if load["membership"] == "confirmation"]
    graph = build_corrected_physical_graph(source_dir)
    stub_graph = build_corrected_physical_graph(source_dir, include_open_stubs=True)
    source_bus = derive_source_bus(source_dir)
    line_records = _line_edges(source_dir / "qsts/master.dss")
    transformer_records = parse_transformer_metadata(
        source_dir / "qsts/master.dss"
    ) + parse_transformer_metadata(source_dir / "qsts/IEEE123Regulators.dss")
    disconnected = sorted(
        load["load_id"] for load in calibration + confirmation if load["base_bus"] not in graph
    )
    phase_counts = Counter(load["phase"] for load in confirmation)
    pair_counts = {phase: math.comb(phase_counts[phase], 2) for phase in ("A", "B", "C")}
    confirmation_signature_counts = Counter(
        bus_record["signature"] for bus_record in split["buses"] if bus_record["split"] == "confirmation"
    )
    qap_permutation_space_size = math.prod(
        math.factorial(count) for count in confirmation_signature_counts.values()
    )
    calibration_phases = {load["phase"] for load in calibration}
    distance_adequacy = _distance_adequacy(graph, confirmation)
    admitted_buses = sorted({load["base_bus"] for load in calibration + confirmation})
    primary_admitted_distances = [
        nx.shortest_path_length(graph, left, right)
        for index, left in enumerate(admitted_buses)
        for right in admitted_buses[index + 1 :]
    ]
    stub_admitted_distances = [
        nx.shortest_path_length(stub_graph, left, right)
        for index, left in enumerate(admitted_buses)
        for right in admitted_buses[index + 1 :]
    ]
    nonlegacy_candidate_defects = [
        {
            "load_id": load["load_id"],
            "base_bus": load["base_bus"],
            "mapping_status": load["mapping_status"],
        }
        for load in loads
        if load["base_bus"] not in LEGACY_BASE_BUSES
        and load["phase"] is not None
        and load["mapping_status"] != "explicit_active_yearly_mapping"
    ]

    count_checks = {
        "load_definition_count_91": len(load_definitions) == 91,
        "loadshape_file_count_91": len(loadshape_catalog) == 91,
        "explicit_active_mapping_count_89": mapped_count == 89,
        "explicit_mapped_one_phase_wye_count_81": mapped_wye_count == 81,
        "fresh_mapped_wye_count_77": len(fresh_eligible) == 77,
    }
    if enforce_pinned_counts and not all(count_checks.values()):
        raise SourceIntegrityError(f"Pinned population counts did not match: {count_checks}")

    adequacy_checks = {
        "at_least_ten_confirmation_buses": len(confirmation_buses) >= 10,
        "at_least_ten_confirmation_profiles_each_phase": all(
            phase_counts[phase] >= 10 for phase in ("A", "B", "C")
        ),
        "at_least_fifty_confirmation_profiles": len(confirmation) >= 50,
        "calibration_carries_each_phase": calibration_phases == {"A", "B", "C"},
        "at_least_three_distances_each_phase": distance_adequacy["at_least_three_distances_each_phase"],
        "all_admitted_buses_connected": not disconnected and nx.is_connected(graph),
        "source_bus_oracle": source_bus == "150" and source_bus in graph,
        "no_nonlegacy_candidate_mapping_defect": not nonlegacy_candidate_defects,
        "primary_topology_oracle": (
            graph.number_of_nodes() == 130
            and graph.number_of_edges() == 129
            and nx.is_tree(graph)
            and sum(line_id not in {"sw7", "sw8"} for line_id, _, _ in line_records) == 124
            and len(transformer_records) == 8
            and len(line_records) - 2 + len(transformer_records) == 132
        ),
        "open_stub_topology_oracle": (
            stub_graph.number_of_nodes() == 132
            and stub_graph.number_of_edges() == 131
            and nx.is_tree(stub_graph)
            and len(line_records) + len(transformer_records) == 134
        ),
        "open_stub_admitted_distance_vector_exact": (primary_admitted_distances == stub_admitted_distances),
        "frozen_membership_matches_oracle": (
            {load["load_id"] for load in calibration} == EXPECTED_CALIBRATION_IDS
            and {load["load_id"] for load in confirmation} == EXPECTED_CONFIRMATION_IDS
        ),
        "pair_and_qap_space_oracle": (
            pair_counts == {"A": 300, "B": 120, "C": 190}
            and qap_permutation_space_size == 789568637724233695255040401494127477134458880000000000000
        ),
    }
    pre_outcome_status = "pass" if all(adequacy_checks.values()) else "indeterminate"

    source_inventory_hash = canonical_json_sha256(loadshape_catalog)
    prepared_for_hash = {
        "split": split,
        "loads": loads,
        "mapping_amendment": MAPPING_AMENDMENT,
    }
    split_manifest_hash = compute_split_manifest_hash(prepared_for_hash)
    code_hashes = _source_code_hashes()
    freeze_components = {
        "protocol_sha256": code_hashes[PROTOCOL_PATH.name],
        "source_code_hashes": code_hashes,
        "upstream_commit": PINNED_COMMIT,
        "source_inventory_sha256": source_inventory_hash,
        "split_manifest_sha256": split_manifest_hash,
        "runtime_versions": runtime_versions(),
    }
    freeze_digest = canonical_json_sha256(freeze_components)

    access_plan = {
        "prepare": {
            "numeric_profile_paths_allowed": [],
            "operation": (
                "hash bytes, compare canonical Git blobs, count nonempty rows without numeric "
                "conversion, and parse DSS metadata only"
            ),
        },
        "reconstruct": {
            "numeric_profile_paths_allowed": sorted(list(LEGACY_PROFILE_PATHS.values()) + [PV49_PATH]),
            "temperature_path": TEMPERATURE_PATH,
            "temperature_numeric_access": "forbidden_verified_hash_only",
        },
        "calibration": {
            "status": "not_executed",
            "numeric_access_condition": (
                "only after exact detached-lock SHA, frozen digest, and explicit reviewer unlock"
            ),
            "profile_paths": sorted(load["profile_path"] for load in calibration if load["profile_path"]),
        },
        "confirm": {
            "status": "locked_pending_root_and_adversarial_approval",
            "required_unlock_digest": freeze_digest,
            "strict_qc_rule": ("every admitted calibration and confirmation profile must pass; no attrition"),
            "profile_paths": sorted(load["profile_path"] for load in confirmation if load["profile_path"]),
        },
    }
    return {
        "schema_version": 1,
        "experiment_id": "oedi_ieee123_prospective_passive",
        "mode": "metadata_only_prepare",
        "dataset_classification": (
            "profiles packaged with an external public test-system dataset; measurement "
            "provenance unspecified"
        ),
        "dataset_doi": "10.25984/2228282",
        "dataset_landing_page": "https://data.openei.org/submissions/5773",
        "claim_scope_if_eventually_run": (
            "prespecified within-OEDI-package association under a conditional bus-bundle "
            "random-label null; common passive-locality diagnostic only"
        ),
        "field_observation_provenance_established": False,
        "not_independent_dataset_replication": True,
        "not_prospective_collection": True,
        "not_theory_specific_evidence": True,
        "confirmation_population_wording": (
            "previously unanalysed in the tracked repository/current workflow and "
            "prospectively specified for this analysis"
        ),
        "pre_outcome_status": pre_outcome_status,
        "confirmation_values_accessed": False,
        "nonlegacy_profile_values_or_statistics_accessed": False,
        "threshold_disclosure": (
            "T>=0.10 was selected after the five-profile historical exploration but is "
            "prospective for the locked confirmation membership"
        ),
        "full_year_residualization_disclosure": (
            "quarter-hour medians are estimated from the full confirmation year, not from "
            "a training period or out-of-sample normalization"
        ),
        "mapping_amendment": MAPPING_AMENDMENT,
        "population": {
            "load_count": len(loads),
            "loadshape_catalog_count": len(loadshape_catalog),
            "explicit_active_mapping_count": mapped_count,
            "mapped_one_phase_wye_count": mapped_wye_count,
            "fresh_mapped_wye_count": len(fresh_eligible),
            "mapping_defects": mapping_defects,
            "count_checks": count_checks,
        },
        "loads": loads,
        "loadshape_catalog": loadshape_catalog,
        "split": split,
        "adequacy": {
            "checks": adequacy_checks,
            "confirmation_bus_count": len(confirmation_buses),
            "confirmation_profile_count": len(confirmation),
            "confirmation_phase_counts": dict(sorted(phase_counts.items())),
            "confirmation_pair_counts": pair_counts,
            "confirmation_pair_count_total": sum(pair_counts.values()),
            "confirmation_signature_bus_counts": dict(sorted(confirmation_signature_counts.items())),
            "qap_permutation_space_size": qap_permutation_space_size,
            "calibration_phases": sorted(calibration_phases),
            **distance_adequacy,
            "disconnected_load_ids": disconnected,
        },
        "access_plan": access_plan,
        "lateral_root_bus": source_bus,
        "lateral_root_derivation": "active Circuit.ieee123 Bus1 in qsts/master.dss",
        "source_verification": verification,
        "source_inventory_sha256": source_inventory_hash,
        "split_manifest_sha256": split_manifest_hash,
        "freeze_components": freeze_components,
        "freeze_digest_sha256": freeze_digest,
    }

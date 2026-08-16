"""Digest-locked confirmation runner for the OEDI passive association protocol.

Importing this module does not open any profile.  ``execute_confirmation``
requires the exact frozen digest published by metadata-only ``prepare``.
"""

from __future__ import annotations

import hashlib
import itertools
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

import networkx as nx
import numpy as np
from scipy import stats

from experiments.oedi_ieee123_reconstruction.prospective import (
    PROTOCOL_PATH,
    _source_code_hashes,
    compute_source_inventory_hash,
    compute_split_manifest_hash,
    runtime_versions,
)
from experiments.oedi_ieee123_reconstruction.retrospective import (
    build_corrected_physical_graph,
    derive_source_bus,
)
from experiments.oedi_ieee123_reconstruction.source import (
    PINNED_COMMIT,
    SourceIntegrityError,
    canonical_json_sha256,
    load_numeric_profile,
    parse_buscoord_labels,
    sha256_file,
    verify_source,
)

QAP_SEED = int.from_bytes(hashlib.sha256(b"CWT-OEDI-PASSIVE-V1|QAP").digest()[:16], "big")
INITIAL_MONTE_CARLO_DRAWS = 99_999
MAX_MONTE_CARLO_DRAWS = 999_999
ALPHA = 0.05
MONTE_CARLO_CONFIDENCE = 0.99


def _strict_correlation(left: np.ndarray, right: np.ndarray) -> float:
    if left.shape != right.shape or left.ndim != 1 or left.size < 3:
        raise SourceIntegrityError("Correlation vectors must be equal one-dimensional arrays")
    if not np.all(np.isfinite(left)) or not np.all(np.isfinite(right)):
        raise SourceIntegrityError("Correlation vectors contain non-finite values")
    if float(np.var(left)) <= 0.0 or float(np.var(right)) <= 0.0:
        raise SourceIntegrityError("Correlation is undefined for a constant vector")
    value = float(np.corrcoef(left, right)[0, 1])
    if not math.isfinite(value):
        raise SourceIntegrityError("Correlation is undefined")
    return value


def quarter_hour_residual(values: np.ndarray) -> np.ndarray:
    """Subtract full-year quarter-hour medians (not trained normalization)."""

    if values.size != 365 * 96:
        raise SourceIntegrityError("Expected exactly 365 days of 96 quarter-hour samples")
    days = values.reshape(365, 96)
    residual = days - np.median(days, axis=0, keepdims=True)
    flattened = residual.reshape(-1)
    if float(np.var(flattened)) <= 0.0:
        raise SourceIntegrityError("Quarter-hour residual variance must be positive")
    return flattened


def _spearman(distance: np.ndarray, dissimilarity: np.ndarray) -> float:
    """Spearman statistic with average ranks for ties and strict undefined handling."""

    if distance.size < 3 or dissimilarity.size != distance.size:
        raise SourceIntegrityError("Spearman statistic requires at least three paired values")
    if not np.all(np.isfinite(distance)) or not np.all(np.isfinite(dissimilarity)):
        raise SourceIntegrityError("Spearman inputs must be finite")
    if np.unique(distance).size < 2 or np.unique(dissimilarity).size < 2:
        raise SourceIntegrityError("Spearman statistic is undefined for a constant input")
    value = stats.spearmanr(distance, dissimilarity, nan_policy="raise").statistic
    if not math.isfinite(float(value)):
        raise SourceIntegrityError("Spearman statistic is undefined")
    return float(value)


def _loads_by_bus_phase(loads: list[dict[str, Any]]) -> dict[str, dict[str, tuple[str, ...]]]:
    grouped: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
    for load in loads:
        grouped[load["base_bus"]][load["phase"]].append(load["load_id"])
    return {
        bus: {phase: tuple(sorted(ids)) for phase, ids in phases.items()} for bus, phases in grouped.items()
    }


def _signature(phases: dict[str, tuple[str, ...]]) -> tuple[int, int, int]:
    return tuple(len(phases.get(phase, ())) for phase in ("A", "B", "C"))


def _pair_locations(
    loads: list[dict[str, Any]], graph: nx.Graph
) -> list[tuple[str, str, str, str, str, float]]:
    by_phase: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for load in loads:
        by_phase[load["phase"]].append(load)
    pairs = []
    for phase in ("A", "B", "C"):
        members = sorted(by_phase[phase], key=lambda item: (item["base_bus"], item["load_id"]))
        for left, right in itertools.combinations(members, 2):
            if left["base_bus"] == right["base_bus"]:
                continue
            pairs.append(
                (
                    phase,
                    left["base_bus"],
                    right["base_bus"],
                    left["load_id"],
                    right["load_id"],
                    float(nx.shortest_path_length(graph, left["base_bus"], right["base_bus"])),
                )
            )
    return pairs


def _dissimilarities(
    vectors: dict[str, np.ndarray],
) -> dict[tuple[str, str], float]:
    values: dict[tuple[str, str], float] = {}
    for left, right in itertools.combinations(sorted(vectors), 2):
        values[(left, right)] = 1.0 - _strict_correlation(vectors[left], vectors[right])
    return values


def _lookup(matrix: dict[tuple[str, str], float], left: str, right: str) -> float:
    return matrix[tuple(sorted((left, right)))]


def _prepare_rank_kernel(
    location_pairs: list[tuple[str, str, str, str, str, float]],
    bundle_members: dict[str, dict[str, tuple[str, ...]]],
    dissimilarity: dict[tuple[str, str], float],
    distance_functions: dict[str, Callable[[str, str, float], float]],
) -> tuple[dict[str, float], Callable[[dict[str, str]], dict[str, float]]]:
    """Pre-rank invariant pair values so QAP draws require only gathers/dot products."""

    observed_keys = [tuple(sorted((record[3], record[4]))) for record in location_pairs]
    observed_values = np.asarray([dissimilarity[key] for key in observed_keys], dtype=float)
    value_ranks = stats.rankdata(observed_values, method="average")
    rank_by_pair = dict(zip(observed_keys, value_ranks, strict=True))
    value_center = float(np.mean(value_ranks))
    value_norm = float(np.linalg.norm(value_ranks - value_center))
    if value_norm <= 0.0:
        raise SourceIntegrityError("QAP dissimilarity ranks are constant")

    names = list(distance_functions)
    normalized_distance_ranks = []
    for name in names:
        function = distance_functions[name]
        values = np.asarray(
            [function(record[1], record[2], record[-1]) for record in location_pairs],
            dtype=float,
        )
        ranks = stats.rankdata(values, method="average")
        centered = ranks - np.mean(ranks)
        norm = float(np.linalg.norm(centered))
        if norm <= 0.0:
            raise SourceIntegrityError(f"QAP distance ranks are constant for {name}")
        normalized_distance_ranks.append(centered / norm)
    distance_kernel = np.vstack(normalized_distance_ranks)

    def evaluate(assignment: dict[str, str]) -> dict[str, float]:
        mapped_ranks = np.empty(len(location_pairs), dtype=float)
        for index, (phase, left_bus, right_bus, left_id, right_id, _) in enumerate(location_pairs):
            source_left = assignment[left_bus]
            source_right = assignment[right_bus]
            left_index = bundle_members[left_bus][phase].index(left_id)
            right_index = bundle_members[right_bus][phase].index(right_id)
            mapped_left = bundle_members[source_left][phase][left_index]
            mapped_right = bundle_members[source_right][phase][right_index]
            mapped_ranks[index] = rank_by_pair[tuple(sorted((mapped_left, mapped_right)))]
        normalized_values = (mapped_ranks - value_center) / value_norm
        statistics = distance_kernel @ normalized_values
        return {name: float(value) for name, value in zip(names, statistics, strict=True)}

    identity = {bus: bus for bus in bundle_members}
    return evaluate(identity), evaluate


def _signature_groups(bundle_members: dict[str, dict[str, tuple[str, ...]]]) -> list[list[str]]:
    groups: dict[tuple[int, int, int], list[str]] = defaultdict(list)
    for bus, phases in bundle_members.items():
        groups[_signature(phases)].append(bus)
    return [sorted(groups[key]) for key in sorted(groups)]


def permutation_space_size(groups: list[list[str]]) -> int:
    """Return the exact number of admissible bus-bundle allocations."""

    return math.prod(math.factorial(len(group)) for group in groups)


def _exact_assignments(groups: list[list[str]]) -> Iterable[dict[str, str]]:
    permutations = [itertools.permutations(group) for group in groups]
    for combination in itertools.product(*permutations):
        assignment = {}
        for targets, sources in zip(groups, combination, strict=True):
            assignment.update(zip(targets, sources, strict=True))
        yield assignment


def _random_assignment(groups: list[list[str]], rng: np.random.Generator) -> dict[str, str]:
    assignment = {}
    for targets in groups:
        sources = rng.permutation(np.asarray(targets, dtype=object)).tolist()
        assignment.update(zip(targets, sources, strict=True))
    return assignment


def _clopper_pearson(extreme: int, draws: int, confidence: float) -> tuple[float, float]:
    tail = (1.0 - confidence) / 2.0
    lower = 0.0 if extreme == 0 else float(stats.beta.ppf(tail, extreme, draws - extreme + 1))
    upper = 1.0 if extreme == draws else float(stats.beta.ppf(1.0 - tail, extreme + 1, draws - extreme))
    return lower, upper


def qap_test(
    loads: list[dict[str, Any]],
    graph: nx.Graph,
    vectors: dict[str, np.ndarray],
    *,
    max_exact: int = INITIAL_MONTE_CARLO_DRAWS,
    initial_draws: int = INITIAL_MONTE_CARLO_DRAWS,
    maximum_draws: int = MAX_MONTE_CARLO_DRAWS,
    bus_file_order: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Run the exact or PCG64 bus-bundle conditional random-label test."""

    members = _loads_by_bus_phase(loads)
    groups = _signature_groups(members)
    locations = _pair_locations(loads, graph)
    dissimilarity = _dissimilarities(vectors)
    if bus_file_order is None:
        bus_file_order = {bus: index for index, bus in enumerate(sorted(members))}
    distance_functions: dict[str, Callable[[str, str, float], float]] = {
        "primary_graph_distance": lambda _left, _right, graph_distance: graph_distance,
        "numeric_bus_id_distance": lambda left, right, _: abs(float(left) - float(right)),
        "buscoords_file_order_distance": lambda left, right, _: abs(
            bus_file_order[left] - bus_file_order[right]
        ),
    }
    observed_statistics, evaluate_assignment = _prepare_rank_kernel(
        locations, members, dissimilarity, distance_functions
    )
    observed = observed_statistics["primary_graph_distance"]
    control_names = ("numeric_bus_id_distance", "buscoords_file_order_distance")
    space = permutation_space_size(groups)

    if space <= max_exact:
        if space < math.ceil(1.0 / ALPHA):
            return {
                "status": "indeterminate",
                "reason": "exact permutation space cannot resolve p<=0.05",
                "method": "exact_unique_bus_bundle_enumeration",
                "permutation_space_size": space,
                "observed_T": observed,
            }
        extreme = 0
        control_extreme = {name: 0 for name in control_names}
        enumerated = 0
        for assignment in _exact_assignments(groups):
            statistics = evaluate_assignment(assignment)
            extreme += int(statistics["primary_graph_distance"] >= observed)
            for name in control_names:
                control_extreme[name] += int(statistics[name] >= observed_statistics[name])
            enumerated += 1
        return {
            "status": "complete",
            "method": "exact_unique_bus_bundle_enumeration",
            "observed_allocation_included_once": True,
            "extreme_comparator": "T_perm >= T_observed with no tolerance",
            "permutation_space_size": space,
            "enumerated": enumerated,
            "extreme_count": extreme,
            "observed_T": observed,
            "p_value": extreme / enumerated,
            "specificity_controls": {
                name: {
                    "observed_T": observed_statistics[name],
                    "extreme_count": control_extreme[name],
                    "p_value": control_extreme[name] / enumerated,
                    "same_permutations_as_primary": True,
                }
                for name in control_names
            },
        }

    rng = np.random.Generator(np.random.PCG64(QAP_SEED))
    extreme = 0
    control_extreme = {name: 0 for name in control_names}
    draws = 0
    target = initial_draws
    interval = (0.0, 1.0)
    while True:
        while draws < target:
            assignment = _random_assignment(groups, rng)
            statistics = evaluate_assignment(assignment)
            extreme += int(statistics["primary_graph_distance"] >= observed)
            for name in control_names:
                control_extreme[name] += int(statistics[name] >= observed_statistics[name])
            draws += 1
        interval = _clopper_pearson(extreme, draws, MONTE_CARLO_CONFIDENCE)
        crosses = interval[0] <= ALPHA <= interval[1]
        if not crosses or target >= maximum_draws:
            break
        target = maximum_draws
    return {
        "status": "indeterminate" if interval[0] <= ALPHA <= interval[1] else "complete",
        "reason": (
            "99% Monte Carlo interval still crosses 0.05 at maximum draws"
            if interval[0] <= ALPHA <= interval[1]
            else None
        ),
        "method": "PCG64_bus_bundle_monte_carlo",
        "seed_decimal": QAP_SEED,
        "same_rng_stream_extended": draws > initial_draws,
        "extreme_comparator": "T_perm >= T_observed with no tolerance",
        "permutation_space_size": space,
        "draws": draws,
        "extreme_count": extreme,
        "observed_T": observed,
        "p_value": (1 + extreme) / (draws + 1),
        "clopper_pearson_99": list(interval),
        "specificity_controls": {
            name: {
                "observed_T": observed_statistics[name],
                "extreme_count": control_extreme[name],
                "p_value_plus_one": (1 + control_extreme[name]) / (draws + 1),
                "same_permutations_as_primary": True,
            }
            for name in control_names
        },
    }


def _descriptive_statistic(
    loads: list[dict[str, Any]], graph: nx.Graph, vectors: dict[str, np.ndarray]
) -> float:
    locations = _pair_locations(loads, graph)
    dissimilarity = _dissimilarities(vectors)
    distances = np.asarray([record[-1] for record in locations], dtype=float)
    values = np.asarray([_lookup(dissimilarity, record[3], record[4]) for record in locations], dtype=float)
    return _spearman(distances, values)


def _robustness(
    loads: list[dict[str, Any]],
    graph: nx.Graph,
    raw: dict[str, np.ndarray],
    *,
    lateral_root_bus: str,
) -> dict[str, Any]:
    residual = {load_id: quarter_hour_residual(values) for load_id, values in raw.items()}
    raw_t = _descriptive_statistic(loads, graph, raw)
    diff_t = _descriptive_statistic(
        loads,
        graph,
        {load_id: np.diff(values) for load_id, values in raw.items()},
    )
    blocks = ((0, 91), (91, 182), (182, 273), (273, 365))
    block_t = []
    for start_day, stop_day in blocks:
        start = start_day * 96
        stop = stop_day * 96
        block_t.append(
            {
                "days_zero_based_half_open": [start_day, stop_day],
                "day_count": stop_day - start_day,
                "T": _descriptive_statistic(
                    loads,
                    graph,
                    {load_id: values[start:stop] for load_id, values in residual.items()},
                ),
            }
        )

    leave_one = []
    for omitted in sorted(raw):
        subset = [load for load in loads if load["load_id"] != omitted]
        subset_vectors = {key: value for key, value in residual.items() if key != omitted}
        leave_one.append(
            {"omitted_load_id": omitted, "T": _descriptive_statistic(subset, graph, subset_vectors)}
        )

    by_phase = {}
    for phase in ("A", "B", "C"):
        subset = [load for load in loads if load["phase"] == phase]
        ids = {load["load_id"] for load in subset}
        by_phase[phase] = {
            "profile_count": len(subset),
            "T_descriptive_no_secondary_p_value": _descriptive_statistic(
                subset, graph, {key: value for key, value in residual.items() if key in ids}
            ),
        }

    shifted = {}
    shift_days_by_load = {}
    for load_id, values in raw.items():
        shift_days = (
            int.from_bytes(
                hashlib.sha256(f"CWT-OEDI-PASSIVE-V1|SHIFT|{load_id}".encode("utf-8")).digest()[:8],
                "big",
            )
            % 365
        )
        shift_days_by_load[load_id] = shift_days
        shifted[load_id] = quarter_hour_residual(np.roll(values, shift_days * 96))
    shifted_t = _descriptive_statistic(loads, graph, shifted)

    # A lateral deletion is a source-rooted BFS edge leaving a branching node.
    # Evaluate only deletions retaining the predeclared profile/phase minima.
    root = lateral_root_bus
    if root not in graph:
        raise SourceIntegrityError(f"Frozen lateral root bus {root} is absent from the graph")
    bfs = nx.bfs_tree(graph, root)
    lateral_results = []
    for parent, child in bfs.edges:
        if graph.degree(parent) < 3:
            continue
        modified = graph.copy()
        modified.remove_edge(parent, child)
        retained_buses = nx.node_connected_component(modified, root)
        retained = [load for load in loads if load["base_bus"] in retained_buses]
        counts = Counter(load["phase"] for load in retained)
        if len(retained) < 50 or any(counts[phase] < 10 for phase in ("A", "B", "C")):
            continue
        ids = {load["load_id"] for load in retained}
        lateral_results.append(
            {
                "deleted_edge": [parent, child],
                "retained_profile_count": len(retained),
                "T": _descriptive_statistic(
                    retained,
                    modified,
                    {key: value for key, value in residual.items() if key in ids},
                ),
            }
        )

    return {
        "raw_profile_dissimilarity_T": raw_t,
        "first_difference_dissimilarity_T": diff_t,
        "full_year_residual_T": _descriptive_statistic(loads, graph, residual),
        "blocks": block_t,
        "positive_block_count": sum(record["T"] > 0.0 for record in block_t),
        "leave_one_load": leave_one,
        "leave_one_no_sign_reversal": all(record["T"] >= 0.0 for record in leave_one),
        "lateral_definition": (
            "each source-rooted BFS edge leaving an undirected-degree>=3 node; retain the "
            "source component and evaluate only if >=50 profiles and >=10 per phase remain"
        ),
        "lateral_root_bus": root,
        "lateral_deletions": lateral_results,
        "lateral_no_sign_reversal": bool(lateral_results)
        and all(record["T"] >= 0.0 for record in lateral_results),
        "whole_day_circular_shift_warning_T": shifted_t,
        "whole_day_shift_days": shift_days_by_load,
        "whole_day_shift_rule": (
            "UTF-8 SHA256('CWT-OEDI-PASSIVE-V1|SHIFT|<load_id>'), first 8 bytes "
            "big-endian modulo 365; zero means no roll and remains reported"
        ),
        "whole_day_zero_shift_loads": sorted(
            load_id for load_id, days in shift_days_by_load.items() if days == 0
        ),
        "phase_descriptive_results": by_phase,
        "secondary_inference": "none_run; any future secondary p-values require Holm adjustment",
        "weighted_distance": (
            "not run: the pinned files do not supply one coherent comparable length scale for "
            "line, switch, and transformer/regulator series elements"
        ),
    }


def _load_admitted_profiles(
    source_dir: Path,
    admitted: list[dict[str, Any]],
) -> tuple[dict[str, np.ndarray], list[dict[str, str]], list[str], list[dict[str, Any]]]:
    """Numerically QC every admitted profile and retain every access attempt."""

    profiles: dict[str, np.ndarray] = {}
    invalid: list[dict[str, str]] = []
    access_log: list[str] = []
    access_ledger: list[dict[str, Any]] = []
    for load in admitted:
        path = source_dir / load["profile_path"]
        attempt: dict[str, Any] = {
            "record_type": "admitted_profile_access_attempt",
            "load_id": load["load_id"],
            "membership": load["membership"],
            "profile_path": load["profile_path"],
            "status": "attempted",
            "numeric_parse_attempted": False,
        }
        access_ledger.append(attempt)
        try:
            observed_sha256 = sha256_file(path)
        except OSError as exc:
            reason = f"Could not hash admitted profile {load['profile_path']}: {exc}"
            attempt.update({"status": "failed_hash_access", "reason": reason})
            invalid.append({"load_id": load["load_id"], "reason": reason})
            continue
        if observed_sha256 != load["profile_sha256"]:
            reason = f"Profile hash changed after prepare: {load['profile_path']}"
            attempt.update(
                {
                    "status": "failed_hash",
                    "observed_sha256": observed_sha256,
                    "reason": reason,
                }
            )
            invalid.append({"load_id": load["load_id"], "reason": reason})
            continue
        try:
            attempt["numeric_parse_attempted"] = True
            values = load_numeric_profile(path)
            quarter_hour_residual(values)
        except SourceIntegrityError as exc:
            reason = str(exc)
            attempt.update({"status": "failed_numeric_qc", "reason": reason})
            invalid.append({"load_id": load["load_id"], "reason": reason})
            continue
        profiles[load["load_id"]] = values
        access_log.append(load["profile_path"])
        attempt.update({"status": "success", "observed_sha256": observed_sha256})
    return profiles, invalid, access_log, access_ledger


def _post_access_statistics(
    source_dir: Path,
    valid_loads: list[dict[str, Any]],
    raw: dict[str, np.ndarray],
    *,
    expected_lateral_root_bus: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Compute the frozen statistics after all admitted profiles pass QC."""

    graph = build_corrected_physical_graph(source_dir)
    derived_root = derive_source_bus(source_dir)
    if derived_root != expected_lateral_root_bus or derived_root != "150":
        raise SourceIntegrityError("Active Circuit source bus does not match the frozen lateral root bus 150")
    residual = {load_id: quarter_hour_residual(values) for load_id, values in raw.items()}
    raw_labels = parse_buscoord_labels(source_dir / "qsts/Buscoords.dss")
    physical_order: list[str] = []
    seen: set[str] = set()
    for label in raw_labels:
        if label in graph and label not in seen:
            physical_order.append(label)
            seen.add(label)
    if len(physical_order) != 130 or set(physical_order) != set(graph.nodes):
        raise SourceIntegrityError("Physical-only Buscoords ordinal mapping is not exactly 130 unique buses")
    bus_file_order = {bus: index for index, bus in enumerate(physical_order)}
    qap = qap_test(valid_loads, graph, residual, bus_file_order=bus_file_order)
    robustness = _robustness(
        valid_loads,
        graph,
        raw,
        lateral_root_bus=derived_root,
    )
    return qap, robustness


def execute_confirmation(
    source_dir: Path,
    prepared: dict[str, Any],
    *,
    unlock_digest: str,
    approved_prepared_payload_sha256: str,
    require_git: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Execute confirmation only after the exact frozen digest is supplied."""

    expected_digest = prepared["freeze_digest_sha256"]
    if unlock_digest != expected_digest:
        raise SourceIntegrityError("Confirmation remains locked: exact frozen digest was not supplied")
    if canonical_json_sha256(prepared) != approved_prepared_payload_sha256:
        raise SourceIntegrityError(
            "Prepared payload differs from the independently approved canonical payload hash"
        )
    source_inventory_hash = compute_source_inventory_hash(prepared)
    split_manifest_hash = compute_split_manifest_hash(prepared)
    if source_inventory_hash != prepared["source_inventory_sha256"]:
        raise SourceIntegrityError("Prepared all-91 source inventory hash is inconsistent")
    if split_manifest_hash != prepared["split_manifest_sha256"]:
        raise SourceIntegrityError("Prepared split/membership hash is inconsistent")
    current_source_hashes = _source_code_hashes()
    current_freeze_components = {
        "protocol_sha256": current_source_hashes[PROTOCOL_PATH.name],
        "source_code_hashes": current_source_hashes,
        "upstream_commit": PINNED_COMMIT,
        "source_inventory_sha256": source_inventory_hash,
        "split_manifest_sha256": split_manifest_hash,
        "runtime_versions": runtime_versions(),
    }
    if current_freeze_components != prepared["freeze_components"]:
        raise SourceIntegrityError("Frozen protocol/code/source/split/runtime components changed")
    if canonical_json_sha256(prepared["freeze_components"]) != expected_digest:
        raise SourceIntegrityError("Frozen component digest is internally inconsistent")
    if prepared["pre_outcome_status"] != "pass":
        raise SourceIntegrityError("Pre-outcome adequacy did not pass; confirmation is indeterminate")
    verify_source(source_dir, require_git=require_git)

    admitted = [load for load in prepared["loads"] if load["membership"] in {"calibration", "confirmation"}]
    invalid_admitted_metadata = [
        {
            "load_id": load["load_id"],
            "membership": load["membership"],
            "reason": "admitted mapping/profile metadata is invalid",
        }
        for load in admitted
        if load["mapping_status"] != "explicit_active_yearly_mapping"
        or not load["profile_metadata_valid"]
        or not load["profile_path"]
        or not load["profile_sha256"]
    ]
    if invalid_admitted_metadata:
        access_ledger = [
            {
                "record_type": "admitted_profile_access_attempt",
                **record,
                "status": "rejected_before_numeric_access",
                "numeric_parse_attempted": False,
            }
            for record in invalid_admitted_metadata
        ]
        return (
            {
                "status": "indeterminate",
                "reason": "invalid admitted calibration/confirmation metadata",
                "invalid_profiles": invalid_admitted_metadata,
                "numeric_access_log": [],
                "access_ledger": access_ledger,
            },
            access_ledger,
        )

    confirmation_loads = [load for load in prepared["loads"] if load["membership"] == "confirmation"]
    profiles, invalid, access_log, access_ledger = _load_admitted_profiles(source_dir, admitted)
    invalid_admitted_fraction = len(invalid) / len(admitted)
    raw = {
        load["load_id"]: profiles[load["load_id"]]
        for load in confirmation_loads
        if load["load_id"] in profiles
    }
    valid_loads = [load for load in confirmation_loads if load["load_id"] in raw]
    phase_counts = Counter(load["phase"] for load in valid_loads)
    if invalid or len(valid_loads) < 50 or any(phase_counts[phase] < 10 for phase in ("A", "B", "C")):
        summary = {
            "status": "indeterminate",
            "reason": "one or more admitted calibration/confirmation profiles failed strict QC",
            "invalid_profiles": invalid,
            "invalid_admitted_fraction": invalid_admitted_fraction,
            "numeric_access_log": access_log,
            "access_ledger": access_ledger,
        }
        return summary, access_ledger

    try:
        qap, robustness = _post_access_statistics(
            source_dir,
            valid_loads,
            raw,
            expected_lateral_root_bus=prepared["lateral_root_bus"],
        )
    except (SourceIntegrityError, OSError, ValueError) as exc:
        return (
            {
                "status": "indeterminate",
                "reason": f"post-access statistic undefined: {exc}",
                "numeric_access_log": access_log,
                "access_ledger": access_ledger,
            },
            access_ledger,
        )
    integrity = qap["status"] == "complete"
    robustness_pass = (
        robustness["raw_profile_dissimilarity_T"] > 0.0
        and robustness["first_difference_dissimilarity_T"] > 0.0
        and robustness["positive_block_count"] >= 3
        and robustness["leave_one_no_sign_reversal"]
        and robustness["lateral_no_sign_reversal"]
    )
    specificity_artifact = any(
        control["observed_T"] >= 0.10 and control.get("p_value", control.get("p_value_plus_one", 1.0)) <= 0.05
        for control in qap.get("specificity_controls", {}).values()
    )
    if not integrity:
        status = "indeterminate"
    elif specificity_artifact:
        status = "indeterminate"
    elif qap["observed_T"] < 0.10 or qap["p_value"] > 0.05:
        status = "fail"
    elif not robustness_pass:
        status = "fail"
    else:
        status = "pass"
    summary = {
        "schema_version": 1,
        "experiment_id": "oedi_ieee123_prospective_passive",
        "mode": "digest_unlocked_confirmation",
        "status": status,
        "claim_scope": (
            "prespecified within-OEDI-package association under a conditional bus-bundle "
            "random-label null; common passive-locality diagnostic only"
        ),
        "not_cgt_or_causal_evidence": True,
        "frozen_digest_sha256": expected_digest,
        "qap": qap,
        "specificity_control_triggered_indeterminate": specificity_artifact,
        "robustness": robustness,
        "valid_profile_count": len(valid_loads),
        "invalid_profiles": invalid,
        "invalid_admitted_fraction": invalid_admitted_fraction,
        "numeric_access_log": access_log,
        "access_ledger": access_ledger,
        "pair_count_is_not_sample_size": True,
        "feeder_count": 1,
        "population_confidence_interval": None,
    }
    return summary, access_ledger

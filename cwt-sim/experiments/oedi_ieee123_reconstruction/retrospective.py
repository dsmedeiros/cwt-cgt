"""Exact retrospective reconstruction plus corrected topology diagnostics."""

from __future__ import annotations

import itertools
import json
import math
import re
from pathlib import Path
from typing import Any

import networkx as nx
import numpy as np
from scipy import stats

from experiments.oedi_ieee123_reconstruction.source import (
    SourceIntegrityError,
    canonical_bus,
    load_numeric_profile,
    parse_buscoord_labels,
    parse_dss_objects,
    parse_load_definitions,
    parse_sensor_buses,
    verify_source,
)

LEGACY_LOAD_IDS = ("S1a", "S19a", "S47", "S49a", "S65a")
LEGACY_PROFILE_PATHS = {
    "S1a": "profiles/load_profiles/loadshape_S1a.csv",
    "S19a": "profiles/load_profiles/loadshape_S19a.csv",
    "S47": "profiles/load_profiles/loadshape_S47.csv",
    "S49a": "profiles/load_profiles/loadshape_S49a.csv",
    "S65a": "profiles/load_profiles/loadshape_S65a.csv",
}
PV49_PATH = "profiles/pv_profiles/pvshape_49.csv"
TEMPERATURE_PATH = "profiles/pv_profiles/temperature.csv"

ARCHIVED_REFERENCE: dict[str, Any] = {
    "oedi_graph_nodes": 214,
    "oedi_graph_edges": 126,
    "oedi_sensor_nodes": 85,
    "oedi_sensor_coverage_mean_hops": 0.4153846153846154,
    "oedi_sensor_coverage_median_hops": 0.0,
    "oedi_sensor_coverage_max_hops": 2.0,
    "sensor_degree_mean": 1.6705882352941177,
    "nonsensor_degree_mean": 0.8527131782945736,
    "sensor_betweenness_mean": 0.0055947226086820595,
    "nonsensor_betweenness_mean": 0.005207442794350815,
    "load_profile_pair_count": 10,
    "distance_corr_spearman": -0.309090909090909,
    "distance_corr_pearson": -0.35341357646028815,
    "pv_load_midday_sign_boundary_alpha": 1.1572718540076374,
}

ACTIVE_REFERENCE = {
    "node_count": 130,
    "sensor_degree_mean": 1.6705882352941177,
    "nonsensor_degree_mean": 2.4444444444444446,
    "sensor_betweenness_mean": 0.015300102599179207,
    "nonsensor_betweenness_mean": 0.040824181739879416,
}

CORRECTED_SENSOR_REFERENCE = {
    "sensor_node_count": 85,
    "nonsensor_node_count": 45,
    "unreachable_node_count": 0,
    "sensor_coverage_mean_hops": 0.4230769230769231,
    "sensor_coverage_median_hops": 0.0,
    "sensor_coverage_max_hops": 3.0,
    "sensor_degree_mean": 1.6823529411764706,
    "nonsensor_degree_mean": 2.5555555555555554,
    "sensor_betweenness_mean": 0.047335271317829455,
    "nonsensor_betweenness_mean": 0.16731804478897502,
}


def _line_edges(master_path: Path) -> list[tuple[str, str, str]]:
    edges: list[tuple[str, str, str]] = []
    for item in parse_dss_objects(master_path, "line"):
        try:
            bus1 = canonical_bus(item.properties["bus1"])
            bus2 = canonical_bus(item.properties["bus2"])
        except KeyError as exc:
            raise SourceIntegrityError(f"Line {item.object_id} is missing a bus endpoint") from exc
        edges.append((item.object_id.casefold(), bus1, bus2))
    return edges


def derive_source_bus(source_dir: Path) -> str:
    """Derive the canonical feeder source bus from the active Circuit statement."""

    circuits = parse_dss_objects(source_dir / "qsts/master.dss", "circuit")
    if len(circuits) != 1 or "bus1" not in circuits[0].properties:
        raise SourceIntegrityError("Expected exactly one active Circuit object with Bus1")
    source_bus = canonical_bus(circuits[0].properties["bus1"])
    if source_bus != "150":
        raise SourceIntegrityError(f"Pinned source-bus oracle expected 150, observed {source_bus}")
    return source_bus


def parse_transformer_metadata(path: Path) -> list[dict[str, Any]]:
    """Resolve transformer ``like=`` inheritance and continuation endpoints."""

    metadata: list[dict[str, Any]] = []
    resolved_by_id: dict[str, dict[str, str]] = {}
    for item in parse_dss_objects(path, "transformer"):
        own = dict(item.properties)
        like_id = own.get("like", "").casefold()
        if like_id:
            if like_id not in resolved_by_id:
                raise SourceIntegrityError(
                    f"Transformer {item.object_id} refers to unresolved like={like_id}"
                )
            props = {**resolved_by_id[like_id], **own}
        else:
            props = own
        resolved_by_id[item.object_id.casefold()] = props
        endpoints: list[str] = []
        buses = props.get("buses")
        if buses is not None:
            endpoints = re.findall(r"[^\s,\[\]]+", buses)
        else:
            endpoints = re.findall(r"(?i)(?<![\w.])bus\s*=\s*([^\s]+)", item.active_text)
        if len(endpoints) != 2:
            raise SourceIntegrityError(
                f"Transformer {item.object_id} has {len(endpoints)} parsed endpoints; expected 2"
            )
        metadata.append(
            {
                "element_id": item.object_id.casefold(),
                "phases": int(props["phases"]),
                "bus1": canonical_bus(endpoints[0]),
                "bus2": canonical_bus(endpoints[1]),
                "like": like_id or None,
            }
        )
    return metadata


def _transformer_edges(path: Path) -> list[tuple[str, str, str]]:
    return [
        (record["element_id"], record["bus1"], record["bus2"]) for record in parse_transformer_metadata(path)
    ]


def build_historical_graph(source_dir: Path) -> nx.Graph:
    """Reproduce the flawed Buscoords-plus-Line graph used historically."""

    graph = nx.Graph()
    graph.add_nodes_from(parse_buscoord_labels(source_dir / "qsts/Buscoords.dss"))
    graph.add_edges_from((bus1, bus2) for _, bus1, bus2 in _line_edges(source_dir / "qsts/master.dss"))
    return graph


def build_corrected_physical_graph(source_dir: Path, *, include_open_stubs: bool = False) -> nx.Graph:
    """Build the primary graph or its explicit ``*_OPEN``-stub robustness variant.

    The primary exclusion is a dataset-specific modeling convention declared
    by the pinned source comments; it is not a claim that OpenDSS disables
    these executable Line objects automatically.
    """

    graph = nx.Graph()
    labels = parse_buscoord_labels(source_dir / "qsts/Buscoords.dss")
    physical_nodes = [
        label
        for label in labels
        if not label.startswith("s") and (include_open_stubs or not label.endswith("_open"))
    ]
    graph.add_nodes_from(physical_nodes)
    for line_id, bus1, bus2 in _line_edges(source_dir / "qsts/master.dss"):
        if not include_open_stubs and (
            line_id in {"sw7", "sw8"} or bus1.endswith("_open") or bus2.endswith("_open")
        ):
            continue
        graph.add_edge(bus1, bus2, kind="line", element_id=line_id)
    transformer_sources = (
        source_dir / "qsts/master.dss",
        source_dir / "qsts/IEEE123Regulators.dss",
    )
    for path in transformer_sources:
        for element_id, bus1, bus2 in _transformer_edges(path):
            graph.add_edge(bus1, bus2, kind="transformer", element_id=element_id)
    return graph


def _group_means(graph: nx.Graph, sensors: set[str]) -> dict[str, float]:
    centrality = nx.betweenness_centrality(graph)
    sensor_nodes = sorted(sensors & set(graph.nodes))
    nonsensor_nodes = sorted(set(graph.nodes) - sensors)
    return {
        "sensor_degree_mean": float(np.mean([graph.degree(node) for node in sensor_nodes])),
        "nonsensor_degree_mean": float(np.mean([graph.degree(node) for node in nonsensor_nodes])),
        "sensor_betweenness_mean": float(np.mean([centrality[node] for node in sensor_nodes])),
        "nonsensor_betweenness_mean": float(np.mean([centrality[node] for node in nonsensor_nodes])),
    }


def historical_graph_metrics(graph: nx.Graph, sensors: set[str]) -> dict[str, Any]:
    """Compute the archived graph vector and expose its unreachable nodes."""

    sensor_nodes = sensors & set(graph.nodes)
    distances = nx.multi_source_dijkstra_path_length(graph, sensor_nodes, weight=None)
    values = np.asarray(list(distances.values()), dtype=float)
    isolates = sorted(nx.isolates(graph))
    return {
        "oedi_graph_nodes": graph.number_of_nodes(),
        "oedi_graph_edges": graph.number_of_edges(),
        "oedi_sensor_nodes": len(sensor_nodes),
        "oedi_sensor_coverage_mean_hops": float(np.mean(values)),
        "oedi_sensor_coverage_median_hops": float(np.median(values)),
        "oedi_sensor_coverage_max_hops": float(np.max(values)),
        **_group_means(graph, sensors),
        "sensor_reachable_node_count": len(distances),
        "isolate_count": len(isolates),
        "isolates": isolates,
    }


def active_subgraph_metrics(graph: nx.Graph, sensors: set[str]) -> dict[str, Any]:
    """Recompute centrality after removing the historical isolates."""

    active_nodes = [node for node, degree in graph.degree() if degree > 0]
    active = graph.subgraph(active_nodes).copy()
    return {
        "node_count": active.number_of_nodes(),
        "edge_count": active.number_of_edges(),
        "component_count": nx.number_connected_components(active),
        **_group_means(active, sensors),
    }


def corrected_graph_metrics(graph: nx.Graph) -> dict[str, Any]:
    """Summarize the corrected physical graph without conflating it with legacy metrics."""

    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "isolate_count": nx.number_of_isolates(graph),
        "component_count": nx.number_connected_components(graph),
        "connected": nx.is_connected(graph),
        "normally_open_switches_excluded": ["Sw7", "Sw8"],
        "open_stub_exclusion_ledger": {
            "Sw7": "151-300_OPEN",
            "Sw8": "54-94_OPEN",
        },
        "open_stub_semantics": (
            "dataset-specific *_OPEN pseudo-terminal convention; the DSS Line objects are "
            "executable and are not claimed to be disabled by OpenDSS"
        ),
        "transformer_connections_added": [
            "150-150r",
            "61s-610",
            "9-9r",
            "25-25r",
            "160-160r",
        ],
    }


def corrected_sensor_metrics(graph: nx.Graph, sensors: set[str]) -> dict[str, Any]:
    """Compute sensor diagnostics on the energized 130-bus primary graph only."""

    sensor_nodes = sensors & set(graph.nodes)
    distances = nx.multi_source_dijkstra_path_length(graph, sensor_nodes, weight=None)
    values = np.asarray(list(distances.values()), dtype=float)
    return {
        "sensor_node_count": len(sensor_nodes),
        "nonsensor_node_count": graph.number_of_nodes() - len(sensor_nodes),
        "unreachable_node_count": graph.number_of_nodes() - len(distances),
        "sensor_coverage_mean_hops": float(np.mean(values)),
        "sensor_coverage_median_hops": float(np.median(values)),
        "sensor_coverage_max_hops": float(np.max(values)),
        **_group_means(graph, sensors),
    }


def _profile_pair_records(
    historical_graph: nx.Graph,
    load_buses: dict[str, str],
    profiles: dict[str, np.ndarray],
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for left, right in itertools.combinations(LEGACY_LOAD_IDS, 2):
        distance = nx.shortest_path_length(
            historical_graph,
            load_buses[left],
            load_buses[right],
        )
        correlation = float(np.corrcoef(profiles[left], profiles[right])[0, 1])
        records.append(
            {
                "a": left.removeprefix("S"),
                "b": right.removeprefix("S"),
                "distance": int(distance),
                "corr": correlation,
            }
        )
    return records


def _profile_metrics(pairwise: list[dict[str, Any]]) -> dict[str, Any]:
    distances = np.asarray([record["distance"] for record in pairwise], dtype=float)
    correlations = np.asarray([record["corr"] for record in pairwise], dtype=float)
    spearman = stats.spearmanr(distances, correlations).statistic
    pearson = stats.pearsonr(distances, correlations).statistic
    return {
        "load_profile_pair_count": len(pairwise),
        "distance_corr_spearman": float(spearman),
        "distance_corr_pearson": float(pearson),
        "pairwise": pairwise,
    }


def _alpha_diagnostic(load49: np.ndarray, pv49: np.ndarray) -> float:
    mask = pv49 >= 0.2
    if not np.any(mask):
        raise SourceIntegrityError("PV>=0.2 mask is empty")
    return float(np.mean(load49[mask]) / np.mean(pv49[mask]))


def _is_close(observed: Any, expected: Any, tolerance: float = 1e-12) -> bool:
    if isinstance(expected, int):
        return observed == expected
    return math.isclose(float(observed), float(expected), rel_tol=tolerance, abs_tol=tolerance)


def execute_retrospective(
    source_dir: Path,
    *,
    require_git: bool = True,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run the locked retrospective reconstruction.

    Numeric access is deliberately restricted to the five historical load
    profiles and PV49.  Temperature is hash-verified but never numerically
    opened, and no nonlegacy load profile is opened.
    """

    source_dir = source_dir.resolve()
    verification = verify_source(source_dir, require_git=require_git)
    historical_graph = build_historical_graph(source_dir)
    corrected_graph = build_corrected_physical_graph(source_dir)
    sensors = parse_sensor_buses(source_dir / "sensors.json")
    loads = parse_load_definitions(source_dir / "qsts/IEEE123LoadsQsts.dss")
    load_by_id = {load.load_id.casefold(): load for load in loads}
    if len(loads) != 91 or len(load_by_id) != 91:
        raise SourceIntegrityError(f"Expected 91 unique Load elements, observed {len(load_by_id)}")

    selected_metadata = []
    profiles: dict[str, np.ndarray] = {}
    numeric_access_log: list[str] = []
    for load_id in LEGACY_LOAD_IDS:
        definition = load_by_id[load_id.casefold()]
        selected_metadata.append(definition.to_dict())
        profile_path = LEGACY_PROFILE_PATHS[load_id]
        profiles[load_id] = load_numeric_profile(source_dir / profile_path)
        numeric_access_log.append(profile_path)
    pv49 = load_numeric_profile(source_dir / PV49_PATH)
    numeric_access_log.append(PV49_PATH)
    alpha_mask_count = int(np.count_nonzero(pv49 >= 0.2))

    pairwise = _profile_pair_records(
        historical_graph,
        {load_id: load_by_id[load_id.casefold()].base_bus for load_id in LEGACY_LOAD_IDS},
        profiles,
    )
    archived = {
        **historical_graph_metrics(historical_graph, sensors),
        **_profile_metrics(pairwise),
        "pv_load_midday_sign_boundary_alpha": _alpha_diagnostic(profiles["S49a"], pv49),
    }
    active = active_subgraph_metrics(historical_graph, sensors)
    corrected = corrected_graph_metrics(corrected_graph)
    corrected["sensor_diagnostics_energized_graph"] = corrected_sensor_metrics(corrected_graph, sensors)
    stub_graph = build_corrected_physical_graph(source_dir, include_open_stubs=True)
    line_records = _line_edges(source_dir / "qsts/master.dss")
    transformer_records = parse_transformer_metadata(
        source_dir / "qsts/master.dss"
    ) + parse_transformer_metadata(source_dir / "qsts/IEEE123Regulators.dss")
    corrected.update(
        {
            "primary_line_object_count": sum(line_id not in {"sw7", "sw8"} for line_id, _, _ in line_records),
            "all_line_object_count_including_stubs": len(line_records),
            "transformer_object_count": len(transformer_records),
            "primary_raw_series_element_count": len(line_records) - 2 + len(transformer_records),
            "stub_included_raw_series_element_count": len(line_records) + len(transformer_records),
        }
    )
    load_buses_all = sorted({load.base_bus for load in loads})
    primary_distance_vector = [
        nx.shortest_path_length(corrected_graph, left, right)
        for index, left in enumerate(load_buses_all)
        for right in load_buses_all[index + 1 :]
    ]
    stub_distance_vector = [
        nx.shortest_path_length(stub_graph, left, right)
        for index, left in enumerate(load_buses_all)
        for right in load_buses_all[index + 1 :]
    ]
    corrected["include_open_stubs_robustness"] = {
        "node_count": stub_graph.number_of_nodes(),
        "edge_count": stub_graph.number_of_edges(),
        "component_count": nx.number_connected_components(stub_graph),
        "eligible_load_distance_vector_exactly_identical": (primary_distance_vector == stub_distance_vector),
    }

    archived_checks = {
        key: _is_close(archived[key], expected) for key, expected in ARCHIVED_REFERENCE.items()
    }
    active_checks = {key: _is_close(active[key], expected) for key, expected in ACTIVE_REFERENCE.items()}
    corrected_sensor_checks = {
        key: _is_close(corrected["sensor_diagnostics_energized_graph"][key], expected)
        for key, expected in CORRECTED_SENSOR_REFERENCE.items()
    }
    gates = [
        {
            "name": "pinned_source_integrity",
            "status": "pass",
            "requirement": "Git revision and all tracked selected-file SHA-256 digests match",
        },
        {
            "name": "corrected_sensor_diagnostics_reproduced",
            "status": "pass" if all(corrected_sensor_checks.values()) else "fail",
            "requirement": (
                "130-bus energized-graph coverage, degree, and NetworkX normalized "
                "betweenness match the metadata oracle"
            ),
        },
        {
            "name": "archived_vector_reproduced",
            "status": "pass" if all(archived_checks.values()) else "fail",
            "requirement": "every archived scalar matches within 1e-12",
        },
        {
            "name": "historical_parser_defect_exposed",
            "status": (
                "pass"
                if archived["isolate_count"] == 84 and archived["sensor_reachable_node_count"] == 130
                else "fail"
            ),
            "requirement": "84 isolates and 130 sensor-reachable nodes are reported",
        },
        {
            "name": "active_subgraph_reversal_reproduced",
            "status": "pass" if all(active_checks.values()) else "fail",
            "requirement": "active-only degree and betweenness reverse the historical interpretation",
        },
        {
            "name": "corrected_physical_graph_connected",
            "status": (
                "pass"
                if corrected["connected"]
                and corrected["isolate_count"] == 0
                and corrected["node_count"] == 130
                and corrected["edge_count"] == 129
                and corrected["primary_line_object_count"] == 124
                and corrected["transformer_object_count"] == 8
                and corrected["primary_raw_series_element_count"] == 132
                and corrected["include_open_stubs_robustness"]["node_count"] == 132
                and corrected["include_open_stubs_robustness"]["edge_count"] == 131
                and corrected["stub_included_raw_series_element_count"] == 134
                and corrected["include_open_stubs_robustness"][
                    "eligible_load_distance_vector_exactly_identical"
                ]
                else "fail"
            ),
            "requirement": (
                "primary 130/129 graph is a connected tree; adding the two executable open "
                "stubs gives 132/131 without changing any load-bus distance"
            ),
        },
        {
            "name": "numeric_access_boundary",
            "status": (
                "pass"
                if set(numeric_access_log) == set(LEGACY_PROFILE_PATHS.values()) | {PV49_PATH}
                else "fail"
            ),
            "requirement": "only five legacy loads and PV49 are numerically opened",
        },
        {
            "name": "alpha_mask_count_disclosed",
            "status": "pass" if alpha_mask_count == 15_098 else "fail",
            "requirement": "the PV>=0.2 mask contains exactly 15,098 quarter-hours",
        },
    ]
    status = "pass" if all(gate["status"] == "pass" for gate in gates) else "fail"
    summary = {
        "schema_version": 1,
        "experiment_id": "oedi_ieee123_reconstruction",
        "mode": "retrospective_post_hoc_reconstruction",
        "status": status,
        "evidence_tier": "reproducible_external_sample_system_reconstruction",
        "theory_support": "none",
        "dataset_classification": (
            "profiles packaged with an external public test-system dataset; measurement "
            "provenance unspecified"
        ),
        "historical_parser_metrics": archived,
        "active_only_diagnostic": active,
        "corrected_physical_graph": corrected,
        "archived_scalar_checks": archived_checks,
        "active_scalar_checks": active_checks,
        "corrected_sensor_scalar_checks": corrected_sensor_checks,
        "load_inventory_count": len(loads),
        "historical_selection_count": len(LEGACY_LOAD_IDS),
        "selected_load_metadata": selected_metadata,
        "dependent_pair_count": len(pairwise),
        "independent_profile_count": len(LEGACY_LOAD_IDS),
        "alpha_interpretation": {
            "dimensionless_shape_ratio": True,
            "tautological_mean_zeroing_rule": True,
            "pv_greater_equal_0_2_mask_count": alpha_mask_count,
            "load_rating_kw_ignored": 35.0,
            "pv_rating_kva_pmpp_ignored": 50.0,
            "temperature_verified_but_unused": True,
            "physical_net_power_balance": False,
        },
        "numeric_profile_access_log": numeric_access_log,
        "verified_but_not_numerically_opened": [TEMPERATURE_PATH],
        "nonlegacy_profile_values_opened": False,
        "source_verification": verification,
        "gates": gates,
    }
    records = [
        {
            "record_type": "historical_pair",
            **record,
            "dependent_five_profile_slice": True,
        }
        for record in pairwise
    ]
    return summary, records


def load_archived_reference(path: Path) -> dict[str, Any]:
    """Load the tracked historical JSON for an optional direct audit."""

    return json.loads(path.read_text(encoding="utf-8"))

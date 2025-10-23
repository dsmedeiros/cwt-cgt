from __future__ import annotations

import json

import networkx as nx
import numpy as np
import pytest

from experiments.adiabatic_boundary import run as adiabatic_run
from experiments.gateB_ridge_finder import run


def _mean_degree(substrate) -> float:
    graph = nx.Graph(substrate.G.to_undirected())
    degrees = np.array([deg for _, deg in graph.degree()], dtype=float)
    return float(degrees.mean()) if degrees.size else float("nan")


def _edge_payload(substrate) -> dict[tuple[int, int], tuple[float, float]]:
    graph = substrate.G
    payload: dict[tuple[int, int], tuple[float, float]] = {}
    for source, target, data in graph.edges(data=True):
        weight = float(data.get("weight", 1.0))
        delay = float(data.get("delay", 1.0))
        payload[(int(source), int(target))] = (weight, delay)
    return payload


def _assert_equivalent_substrates(actual, expected) -> None:
    assert actual.N == expected.N
    assert actual.node_index == expected.node_index

    actual_edges = _edge_payload(actual)
    expected_edges = _edge_payload(expected)
    assert actual_edges.keys() == expected_edges.keys()
    for edge in actual_edges:
        weight, delay = actual_edges[edge]
        exp_weight, exp_delay = expected_edges[edge]
        assert weight == pytest.approx(exp_weight)
        assert delay == pytest.approx(exp_delay)


def test_substrate_factories_match_baseline_parameters():
    names = [
        "watts_strogatz_p0",
        "watts_strogatz_p001",
        "watts_strogatz_p010",
        "periodic_lattice",
        "erdos_renyi",
        "barabasi_albert",
    ]
    built = run.build_substrates(names, seed=17)
    assert [entry.name for entry in built] == names

    for index, entry in enumerate(built):
        assert entry.factory_seed == 17 + 97 * index
        name = entry.name
        substrate = entry.substrate
        assert substrate.N == run.BASELINE_NODE_COUNT
        metrics = run.summarize_topology(substrate)
        assert set(metrics) == {"clustering", "path_length", "degree_variance", "assortativity"}

        mean_degree = _mean_degree(substrate)
        assert mean_degree == pytest.approx(run.TARGET_MEAN_DEGREE, rel=0.25, abs=0.5), name


def test_gateB_main_writes_topology_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    output_dir = tmp_path / "artifacts"

    run.main(
        [
            "--graphs",
            "watts_strogatz_p0",
            "--grid-size",
            "3",
            "--rho-range",
            "0.1",
            "0.3",
            "--tau-range",
            "0.5",
            "0.7",
            "--bootstrap",
            "4",
            "--seed",
            "11",
            "--transient-steps",
            "1",
            "--sample-steps",
            "1",
            "--top-k",
            "1",
            "--output-dir",
            str(output_dir),
        ]
    )

    graph_dir = output_dir / "watts_strogatz_p0"
    topology_path = graph_dir / "topology.json"
    assert topology_path.exists()

    topology_data = json.loads(topology_path.read_text(encoding="utf-8"))
    for key in ("clustering", "path_length", "degree_variance", "assortativity"):
        assert key in topology_data

    summary_path = output_dir / "summary.json"
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    assert "watts_strogatz_p0" in summary
    summary_entry = summary["watts_strogatz_p0"]
    descriptor = summary_entry.get("graph")
    assert descriptor["identifier"] == "watts_strogatz_p0"
    assert summary_entry.get("seed") == 11
    kwargs = descriptor.get("kwargs") or {}
    assert kwargs.get("seed") == 11
    for field in (
        "topology_clustering",
        "topology_path_length",
        "topology_degree_variance",
        "topology_assortativity",
    ):
        assert field in summary_entry
        value = summary_entry[field]
        assert value is None or isinstance(value, (int, float))

    graph_summary_path = graph_dir / "summary.json"
    graph_summary = json.loads(graph_summary_path.read_text(encoding="utf-8"))
    assert graph_summary["graph"]["identifier"] == "watts_strogatz_p0"
    assert graph_summary["seed"] == 11

    top_tiles_path = graph_dir / "top_omega_tiles.json"
    assert top_tiles_path.exists()
    top_tiles = json.loads(top_tiles_path.read_text(encoding="utf-8"))
    graph_block = top_tiles.get("graph")
    assert isinstance(graph_block, dict)
    assert graph_block.get("identifier") == "watts_strogatz_p0"
    kwargs = graph_block.get("kwargs") or {}
    assert kwargs.get("seed") == 11
    assert graph_block.get("seed") == 11


def test_phase1_artifact_loader_rebuilds_barabasi(tmp_path, monkeypatch):
    monkeypatch.setenv("MPLBACKEND", "Agg")
    output_dir = tmp_path / "artifacts"

    run.main(
        [
            "--graphs",
            "barabasi_albert",
            "--grid-size",
            "3",
            "--rho-range",
            "0.1",
            "0.3",
            "--tau-range",
            "0.5",
            "0.7",
            "--bootstrap",
            "4",
            "--seed",
            "13",
            "--transient-steps",
            "1",
            "--sample-steps",
            "1",
            "--top-k",
            "1",
            "--output-dir",
            str(output_dir),
        ]
    )

    graph_dir = output_dir / "barabasi_albert"
    rebuilt = adiabatic_run._load_substrate_artifact(graph_dir)
    expected = run.build_substrates(["barabasi_albert"], seed=13)[0].substrate

    _assert_equivalent_substrates(rebuilt, expected)

import json

import networkx as nx
import numpy as np
import pytest

from experiments.gateB_ridge_finder import run


def _mean_degree(substrate) -> float:
    graph = nx.Graph(substrate.G.to_undirected())
    degrees = np.array([deg for _, deg in graph.degree()], dtype=float)
    return float(degrees.mean()) if degrees.size else float("nan")


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
    assert [name for name, _ in built] == names

    for name, substrate in built:
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
    for field in (
        "topology_clustering",
        "topology_path_length",
        "topology_degree_variance",
        "topology_assortativity",
    ):
        assert field in summary_entry
        value = summary_entry[field]
        assert value is None or isinstance(value, (int, float))

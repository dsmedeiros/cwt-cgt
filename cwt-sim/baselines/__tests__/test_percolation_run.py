"""Tests for the percolation baseline driver."""

from __future__ import annotations

import sys
from pathlib import Path

import networkx as nx
import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from baselines.percolation import run as percolation_run  # noqa: E402


def test_simulate_percolation_statistics() -> None:
    """A small chain graph yields bounded GCC statistics."""

    graph = nx.path_graph(4)
    substrate = percolation_run._prepare_substrate(graph)  # type: ignore[attr-defined]
    rng = np.random.default_rng(0)
    summary = percolation_run.simulate_percolation(
        substrate,
        p=0.8,
        zeta=0.0,
        realizations=10,
        threshold=0.5,
        rng=rng,
    )

    assert 0.0 <= summary.S_mean <= 1.0
    assert summary.samples == 10
    assert summary.S_var >= 0.0


def test_simulate_percolation_deterministic() -> None:
    """Percolation realizations are reproducible under a fixed seed."""

    graph = nx.path_graph(5)
    substrate = percolation_run._prepare_substrate(graph)  # type: ignore[attr-defined]
    rng = np.random.default_rng(11)
    first = percolation_run.simulate_percolation(
        substrate,
        p=0.7,
        zeta=0.1,
        realizations=8,
        threshold=0.4,
        rng=rng,
    )
    rng_repeat = np.random.default_rng(11)
    second = percolation_run.simulate_percolation(
        substrate,
        p=0.7,
        zeta=0.1,
        realizations=8,
        threshold=0.4,
        rng=rng_repeat,
    )

    assert first == second


def test_cli_produces_artifacts(tmp_path: Path) -> None:
    """Running the CLI with a tiny grid writes metrics and artifacts."""

    argv = [
        "--output-dir",
        str(tmp_path),
        "--axes",
        "p",
        "zeta",
        "--grid-size",
        "2",
        "2",
        "--range",
        "p",
        "0.4",
        "0.6",
        "--range",
        "zeta",
        "0.0",
        "0.2",
        "--realizations",
        "4",
        "--giant-threshold",
        "0.5",
        "--graph-kind",
        "lattice_2d",
        "--lattice-size",
        "2",
        "2",
        "--steps",
        "2",
        "--top-k",
        "2",
        "--seed",
        "7",
    ]

    percolation_run.main(argv)

    runs_root = tmp_path / "baselines" / "percolation"
    runs = sorted(runs_root.glob("*")) if runs_root.exists() else []
    assert runs, "expected an experiment directory to be created"
    run_dir = runs[-1]

    metrics = run_dir / "metrics.csv"
    assert metrics.exists()
    content = metrics.read_text(encoding="utf-8")
    assert "omega_abs" in content
    assert "S_mean" in content

    heatmap = run_dir / "omega_abs_heatmap.png"
    assert heatmap.exists()

    top_tiles = run_dir / "top_omega_tiles.json"
    payload = top_tiles.read_text(encoding="utf-8")
    assert "top_tiles" in payload

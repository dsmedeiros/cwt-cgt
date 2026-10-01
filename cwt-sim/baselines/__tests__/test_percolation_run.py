"""Tests for the percolation baseline driver."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import networkx as nx
import numpy as np
import pandas as pd

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


def test_threshold_references_distinguish_bond_and_site_bond_models() -> None:
    reference = percolation_run._threshold_reference("lattice_2d", 0.0, 3.5)
    assert reference == (0.5, "exact_infinite_square_lattice_bond")
    damaged, kind = percolation_run._threshold_reference("lattice_2d", 0.2, 3.5)
    assert np.isnan(damaged)
    assert kind == "unavailable_site_bond"
    assert percolation_run._threshold_reference("random_regular", 0.0, 4.0) == (
        1.0 / 3.0,
        "approximate_degree_mean_field",
    )


def test_scalar_proxies_recover_exact_derivatives() -> None:
    p = np.array([0.1, 0.4, 0.9])
    zeta = np.array([0.0, 0.2, 0.5])
    field = p[:, None] * zeta[None, :]
    derivative = percolation_run._finite_difference_axis(field, p, 0)
    np.testing.assert_allclose(derivative, np.broadcast_to(zeta, field.shape))
    mixed = percolation_run._curvature_from_grid(field, p, zeta)
    np.testing.assert_allclose(mixed[:-1, :-1], 1.0)
    assert np.isnan(mixed[-1, :]).all()
    assert np.isnan(mixed[:, -1]).all()


def test_run_schema_and_largest_component_observables() -> None:
    result = percolation_run.run(nx.path_graph(4), p=0.0, realizations=3, threshold=0.5)
    assert set(result) == {"steps", "observables", "metadata"}
    assert result["steps"] == 3
    assert result["observables"]["S_mean"] == 0.25
    assert result["observables"]["giant_fraction"] == 0.0
    connected = percolation_run.run(nx.path_graph(4), p=1.0, realizations=3)
    assert connected["observables"]["S_mean"] == 1.0
    assert connected["observables"]["giant_fraction"] == 1.0


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
        "4",
        "--seed",
        "7",
        "--enable-loops",
        "--loop-top-k",
        "4",
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
    assert "omega_abs_proxy" in content
    assert "S_mean" in content
    frame = pd.read_csv(metrics)
    assert (frame.loc[frame.zeta == 0, "threshold_estimate"] == 0.5).all()
    assert frame.loc[frame.zeta > 0, "threshold_estimate"].isna().all()
    assert set(frame.omega_method) == {"probability_derivative_proxy"}
    metadata = json.loads((run_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["axis_mapping"] == "labels_only"
    reports = list((run_dir / "loops").glob("*.json"))
    assert len(reports) == 4
    for report_path in reports:
        report = json.loads(report_path.read_text(encoding="utf-8"))
        json.dumps(report, allow_nan=False)
        if report["coordinates"]["zeta"] > 0:
            assert report["threshold_estimate"] is None
            assert report["threshold_distance"] is None
            assert report["near_threshold"] is False

    heatmap = run_dir / "omega_abs_heatmap.png"
    assert heatmap.exists()

    proxy_heatmap = run_dir / "omega_heatmap_proxy.png"
    assert proxy_heatmap.exists()

    top_tiles = run_dir / "top_omega_tiles.json"
    payload = json.loads(top_tiles.read_text(encoding="utf-8"))
    assert payload["top_tiles"], "expected top tiles data"
    assert any("omega_abs_proxy" in tile for tile in payload["top_tiles"])

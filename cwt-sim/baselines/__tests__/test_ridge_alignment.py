"""Integration tests validating baseline ridge alignment on tiny grids."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from baselines.ising import run as ising_run  # noqa: E402
from baselines.kuramoto import run as kuramoto_run  # noqa: E402
from baselines.percolation import run as percolation_run  # noqa: E402


@pytest.fixture()
def output_root(tmp_path: Path) -> Path:
    target = tmp_path / "artifacts"
    target.mkdir()
    return target


def _latest_run_dir(root: Path, model: str) -> Path:
    runs_root = root / "baselines" / model
    runs = sorted(runs_root.glob("*"))
    assert runs, f"expected a run directory to be created for {model}"
    return runs[-1]


def test_ising_ridge_tracks_zero_field(output_root: Path) -> None:
    """Ising ridge should peak near zero field with sign flips recorded."""

    argv = [
        "--output-dir",
        str(output_root),
        "--axes",
        "T",
        "h",
        "--grid-size",
        "5",
        "5",
        "--range",
        "T",
        "2.0",
        "2.4",
        "--range",
        "h",
        "-0.05",
        "0.05",
        "--lattice-size",
        "12",
        "12",
        "--steps",
        "40",
        "--warmup-sweeps",
        "20",
        "--top-k",
        "5",
        "--seed",
        "2024",
        "--enable-loops",
        "--loop-top-k",
        "1",
        "--loop-delta-scale",
        "0.8",
    ]
    ising_run.main(argv)

    run_dir = _latest_run_dir(output_root, "ising")
    metrics_path = run_dir / "metrics.csv"
    metrics = pd.read_csv(metrics_path)

    peak = metrics.loc[metrics["omega_abs"].idxmax()]
    assert 2.0 <= peak["T"] <= 2.3
    assert abs(float(peak["h"])) <= 0.03

    loops_dir = run_dir / "loops"
    loop_files = sorted(loops_dir.glob("*.json"))
    assert loop_files, "expected loop diagnostics to be emitted"
    payload = json.loads(loop_files[0].read_text(encoding="utf-8"))
    assert payload.get("loop", {}).get("sign_flip_detected") is True


def test_kuramoto_ridge_near_synchronisation_threshold(output_root: Path) -> None:
    """Kuramoto ridge should cluster where coupling balances disorder."""

    argv = [
        "--output-dir",
        str(output_root),
        "--graph-kind",
        "ring3",
        "--graph-param",
        "n=16",
        "--grid-size",
        "5",
        "5",
        "--coupling-range",
        "0.5",
        "1.5",
        "--disorder-range",
        "0.0",
        "0.5",
        "--steps",
        "60",
        "--warmup-steps",
        "30",
        "--top-k",
        "5",
        "--seed",
        "2024",
    ]
    kuramoto_run.main(argv)

    run_dir = _latest_run_dir(output_root, "kuramoto")
    metrics = pd.read_csv(run_dir / "metrics.csv")

    peak = metrics.loc[metrics["omega_abs"].idxmax()]
    threshold_delta = abs(float(peak["kappa"]) - 2.0 * float(peak["sigma"]))
    assert threshold_delta <= 0.5
    assert float(peak["kappa"]) >= 0.75

    top_tiles = json.loads((run_dir / "top_omega_tiles.json").read_text(encoding="utf-8"))
    first_tile = top_tiles.get("top_tiles", [{}])[0]
    assert pytest.approx(first_tile.get("omega_abs", 0.0), rel=1e-3) == float(peak["omega_abs"])


def test_percolation_ridge_matches_bond_threshold(output_root: Path) -> None:
    """Percolation ridge should peak near the critical occupation probability."""

    argv = [
        "--output-dir",
        str(output_root),
        "--axes",
        "p",
        "zeta",
        "--grid-size",
        "5",
        "5",
        "--range",
        "p",
        "0.3",
        "0.7",
        "--range",
        "zeta",
        "-0.1",
        "0.1",
        "--realizations",
        "5",
        "--steps",
        "20",
        "--seed",
        "2024",
        "--graph-kind",
        "lattice_2d",
        "--graph-param",
        "rows=16",
        "--graph-param",
        "cols=16",
        "--top-k",
        "5",
    ]
    percolation_run.main(argv)

    run_dir = _latest_run_dir(output_root, "percolation")
    metrics = pd.read_csv(run_dir / "metrics.csv")

    peak = metrics.loc[metrics["omega_abs"].idxmax()]
    assert abs(float(peak["p"]) - 0.5) <= 0.05

    top_tiles = json.loads((run_dir / "top_omega_tiles.json").read_text(encoding="utf-8"))
    first_tile = top_tiles.get("top_tiles", [{}])[0]
    coordinates = first_tile.get("coordinates", {})
    assert pytest.approx(float(coordinates.get("rho", 0.0)), abs=1e-6) == 0.5

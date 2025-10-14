"""Tests for the SIS baseline driver."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import baselines  # noqa: F401  # pylint: disable=unused-import
import numpy as np

sis_run = importlib.import_module("_cwt_sim_baselines.sis.run")


def test_simulate_sis_bounds() -> None:
    """Simulated prevalence remains bounded between zero and one."""

    adjacency = np.zeros((3, 3), dtype=float)
    rng = np.random.default_rng(0)
    result = sis_run.simulate_sis(
        adjacency,
        infection_rate=0.2,
        recovery_rate=0.1,
        steps=5,
        initial_prevalence=0.5,
        rng=rng,
    )

    assert result.prevalence.shape == (5,)
    assert np.all(result.prevalence >= 0.0)
    assert np.all(result.prevalence <= 1.0)


def test_cli_produces_sis_artifacts(tmp_path: Path) -> None:
    """Running the CLI with a tiny grid writes metrics and artifacts."""

    argv = [
        "--output-dir",
        str(tmp_path),
        "--axes",
        "infection_rate",
        "recovery_rate",
        "--grid-size",
        "2",
        "2",
        "--range",
        "infection_rate",
        "0.1",
        "0.2",
        "--range",
        "recovery_rate",
        "0.05",
        "0.1",
        "--steps",
        "6",
        "--warmup",
        "1",
        "--initial-prevalence",
        "0.2",
        "--graph-kind",
        "random_regular",
        "--graph-param",
        "n=6",
        "--graph-param",
        "degree=2",
        "--seed",
        "4",
        "--top-k",
        "1",
        "--enable-loops",
        "--loop-top-k",
        "1",
    ]

    sis_run.main(argv)

    runs_root = tmp_path / "baselines" / "sis"
    runs = sorted(runs_root.glob("*")) if runs_root.exists() else []
    assert runs, "expected an experiment directory to be created"
    run_dir = runs[-1]

    metrics = run_dir / "metrics.csv"
    assert metrics.exists()
    content = metrics.read_text(encoding="utf-8")
    assert "omega_abs" in content
    assert "R0_proxy" in content
    assert "prevalence_mean" in content

    heatmap = run_dir / "omega_abs_heatmap.png"
    assert heatmap.exists()

    top_tiles = run_dir / "top_omega_tiles.json"
    payload = json.loads(top_tiles.read_text(encoding="utf-8"))
    tiles = payload.get("top_tiles", [])
    assert tiles, "expected at least one top tile"

    loops_dir = run_dir / "loops"
    assert loops_dir.exists()
    loop_files = sorted(loops_dir.glob("*.json"))
    assert loop_files, "expected hotspot reports when loops are enabled"
    report = json.loads(loop_files[0].read_text(encoding="utf-8"))
    assert "prevalence_trace" in report
    assert isinstance(report.get("near_critical"), bool)

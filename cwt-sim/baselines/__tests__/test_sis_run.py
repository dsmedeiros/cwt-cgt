# ruff: noqa: E402,I001

"""Tests for the SIS baseline driver."""

from __future__ import annotations

import csv
import importlib
import json
import math
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import baselines  # noqa: E402,F401  # pylint: disable=unused-import
import pytest  # noqa: E402
import numpy as np  # noqa: E402

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
    assert "omega_abs_proxy" in content
    assert "R0_proxy" in content
    assert "prevalence_mean" in content

    heatmap = run_dir / "omega_abs_heatmap.png"
    assert heatmap.exists()

    proxy_heatmap = run_dir / "omega_heatmap_proxy.png"
    assert proxy_heatmap.exists()

    top_tiles = run_dir / "top_omega_tiles.json"
    payload = json.loads(top_tiles.read_text(encoding="utf-8"))
    tiles = payload.get("top_tiles", [])
    assert tiles, "expected at least one top tile"
    assert any("omega_abs_proxy" in tile for tile in tiles)

    loops_dir = run_dir / "loops"
    assert loops_dir.exists()
    loop_files = sorted(loops_dir.glob("*.json"))
    assert loop_files, "expected hotspot reports when loops are enabled"
    report = json.loads(loop_files[0].read_text(encoding="utf-8"))
    assert "prevalence_trace" in report
    assert isinstance(report.get("near_critical"), bool)


def test_cli_respects_axis_aliases(tmp_path: Path) -> None:
    """Reordering the axes preserves infection and recovery semantics."""

    argv = [
        "--output-dir",
        str(tmp_path),
        "--axes",
        "recovery_rate",
        "infection_rate",
        "--grid-size",
        "2",
        "2",
        "--range",
        "infection_rate",
        "0.7",
        "0.8",
        "--range",
        "recovery_rate",
        "0.1",
        "0.2",
        "--steps",
        "18",
        "--warmup",
        "2",
        "--initial-prevalence",
        "0.2",
        "--graph-kind",
        "random_regular",
        "--graph-param",
        "n=6",
        "--graph-param",
        "degree=3",
        "--seed",
        "11",
    ]

    sis_run.main(argv)

    runs_root = tmp_path / "baselines" / "sis"
    runs = sorted(runs_root.glob("*")) if runs_root.exists() else []
    assert runs, "expected an experiment directory to be created"
    run_dir = runs[-1]

    metrics = run_dir / "metrics.csv"
    assert metrics.exists()

    with metrics.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    assert rows, "expected metrics to contain entries"
    for row in rows:
        infection_rate = float(row["infection_rate"])
        recovery_rate = float(row["recovery_rate"])
        assert infection_rate == pytest.approx(0.7) or infection_rate == pytest.approx(0.8)
        assert recovery_rate == pytest.approx(0.1) or recovery_rate == pytest.approx(0.2)
        spectral_radius = float(row["spectral_radius"])
        expected_r0 = spectral_radius * infection_rate / recovery_rate
        assert float(row["R0_proxy"]) == pytest.approx(expected_r0)
        if math.isfinite(recovery_rate) and recovery_rate > 0:
            assert float(row["R0_proxy"]) > 1.0

"""Tests for the Kuramoto baseline simulation driver."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from baselines.kuramoto import run as kuramoto_run  # noqa: E402


def test_simulate_kuramoto_basic_statistics() -> None:
    """A tiny two-node system produces a sensible order parameter."""

    adjacency = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=float)
    result = kuramoto_run.simulate_kuramoto(
        adjacency,
        coupling=0.8,
        sigma=0.2,
        dt=0.05,
        warmup_steps=2,
        sample_steps=5,
        integration="rk2",
        intrinsic_mean=0.0,
        seed=42,
    )
    assert 0.0 <= result.r_mean <= 1.0
    assert result.r_std >= 0.0 or np.isnan(result.r_std)
    assert result.freq_spread >= 0.0 or np.isnan(result.freq_spread)


def test_curvature_estimators_shape() -> None:
    """Curvature estimators return grids matching the input dimensions."""

    axis = np.linspace(0.0, 1.0, 3)
    order = np.exp(1j * np.outer(axis, axis))
    curvature = kuramoto_run.compute_cwt_curvature(order, axis, axis)
    proxy = kuramoto_run._finite_difference_curvature(order.real, axis, axis)
    assert curvature.shape == (3, 3)
    assert proxy.shape == (3, 3)


def test_cli_produces_artifacts(tmp_path: Path) -> None:
    """Running the CLI with a small grid writes metrics and artifacts."""

    argv = [
        "--output-dir",
        str(tmp_path),
        "--graph-kind",
        "ring3",
        "--grid-size",
        "2",
        "2",
        "--coupling-range",
        "0.5",
        "0.7",
        "--disorder-range",
        "0.0",
        "0.2",
        "--dt",
        "0.05",
        "--warmup-steps",
        "1",
        "--steps",
        "2",
        "--top-k",
        "2",
        "--seed",
        "123",
    ]
    kuramoto_run.main(argv)

    runs_root = tmp_path / "baselines" / "kuramoto"
    runs = sorted(runs_root.glob("*")) if runs_root.exists() else []
    assert runs, "expected an experiment directory to be created"
    run_dir = runs[-1]

    metrics = run_dir / "metrics.csv"
    assert metrics.exists()
    content = metrics.read_text(encoding="utf-8")
    assert "omega_abs" in content

    heatmap = run_dir / "omega_abs_heatmap.png"
    assert heatmap.exists()

    top_tiles = run_dir / "top_omega_tiles.json"
    payload = json.loads(top_tiles.read_text(encoding="utf-8"))
    assert payload["top_tiles"], "expected top tiles to be recorded"

"""Tests for the Kuramoto baseline simulation driver."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Mapping, Sequence

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


def test_compute_cwt_curvature_uses_cache(monkeypatch) -> None:
    """Curvature queries using the same inputs reuse the cached experiment result."""

    calls: list[tuple[np.ndarray, Sequence[float], Sequence[float]]] = []

    def fake_experiment(
        order: np.ndarray,
        axis0: Sequence[float],
        axis1: Sequence[float],
        *,
        module_path: str,
        timeout: float,
    ) -> np.ndarray:  # type: ignore[override]
        calls.append((np.asarray(order), tuple(axis0), tuple(axis1)))
        return np.ones_like(np.asarray(order, dtype=float).real)

    monkeypatch.setenv("CWT_CURVATURE_EXPERIMENT", "stub.module")
    monkeypatch.setattr(kuramoto_run, "_invoke_curvature_experiment", fake_experiment)

    axis = np.linspace(0.0, 1.0, 4)
    order = np.exp(1j * np.outer(axis, axis))

    first = kuramoto_run.compute_cwt_curvature(order, axis, axis)
    second = kuramoto_run.compute_cwt_curvature(order + 0.0j, list(axis), list(axis))

    assert np.allclose(first, np.ones_like(first))
    assert np.allclose(second, first)
    assert len(calls) == 1


def test_run_cwt_loop_enriches_with_experiment(monkeypatch) -> None:
    """Wilson loop reports include experiment telemetry when available."""

    base_report = {
        "center": {"kappa": 0.5, "sigma": 0.2},
        "loop": {"span_kappa": 0.1, "span_sigma": 0.08},
    }

    def fake_local(*args, **kwargs):  # type: ignore[override]
        return dict(base_report)

    captured: dict[str, object] = {}

    def fake_experiment(
        report: Mapping[str, object],
        *,
        module_path: str,
        descriptor: Mapping[str, object],
        center_axes: tuple[str, str],
        extent_scale: float,
        sample_steps: int,
        warmup_steps: int,
        seed: int | None,
        timeout: float,
    ) -> dict[str, object]:
        captured.update(
            {
                "module_path": module_path,
                "descriptor": descriptor,
                "center_axes": center_axes,
                "extent_scale": extent_scale,
                "sample_steps": sample_steps,
                "warmup_steps": warmup_steps,
                "seed": seed,
                "timeout": timeout,
            }
        )
        return {"module": module_path, "phi_abs": 1.23}

    monkeypatch.setattr(kuramoto_run, "_run_cwt_loop_local", fake_local)
    monkeypatch.setattr(kuramoto_run, "_run_cwt_loop_experiment", fake_experiment)
    monkeypatch.setenv("CWT_LOOP_EXPERIMENT", "stub.loop")

    adjacency = np.zeros((0, 0), dtype=float)
    record = {
        "kappa_index": 0,
        "sigma_index": 1,
        "kappa": 0.5,
        "sigma": 0.2,
        "omega": 0.0,
        "omega_abs": 0.0,
        "graph_kind": "ring3",
    }

    result = kuramoto_run.run_cwt_loop(
        adjacency,
        record,
        [0.5, 0.6],
        [0.1, 0.2],
        dt=0.05,
        warmup_steps=5,
        sample_steps=10,
        integration="rk2",
        intrinsic_mean=0.0,
        base_seed=42,
        delta_scale=0.1,
    )

    assert "experiment" in result
    assert result["experiment"]["module"] == "stub.loop"
    assert captured["module_path"] == "stub.loop"
    descriptor = captured["descriptor"]
    assert isinstance(descriptor, Mapping)
    top_tiles = descriptor.get("top_tiles")
    assert isinstance(top_tiles, list)
    assert top_tiles and top_tiles[0]["indices"] == [0, 1]
    assert captured["seed"] == 42
    assert captured["center_axes"] == ("kappa", "sigma")
    assert captured["sample_steps"] == 10
    assert captured["warmup_steps"] == 5
    assert "warnings" not in result

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

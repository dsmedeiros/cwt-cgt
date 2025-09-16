"""Stage-0 analytic validation experiments for CGT geometry estimators."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from cwt.geometry.adapt_mesh import curvature_anytime
from cwt.geometry.curvature import curvature_tile
from cwt.geometry.fs_distance import fs_distance
from cwt.geometry.metric import metric_tile
from cwt.geometry.psi import build_psi


# ---------------------------------------------------------------------------
# Dataclasses describing the structured results returned by the analytic runs.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DimerSweepResult:
    """Results for the two-node dimer sweep."""

    delta: np.ndarray
    fs_distance: np.ndarray
    fs_expected: np.ndarray
    curvature_omegas: np.ndarray
    overlap_magnitudes: np.ndarray

    def max_abs_error(self) -> float:
        return float(np.max(np.abs(self.fs_distance - self.fs_expected)))

    def is_monotone(self) -> bool:
        diffs = np.diff(self.fs_distance)
        return bool(np.all(diffs >= -1e-12))

    def is_bounded(self) -> bool:
        return bool(np.all(self.fs_distance <= (np.pi / 2.0) + 1e-12))


@dataclass(frozen=True)
class Line3Result:
    """Summary of the line3 sweep covering metric and curvature estimators."""

    sweep: np.ndarray
    metric_values: np.ndarray
    metric_delta: float
    curvature_mean: float
    curvature_ci: tuple[float, float]
    curvature_samples: int
    ci_tol: float
    min_overlap: float

    def ci_width(self) -> float:
        lower, upper = self.curvature_ci
        return float(upper - lower)

    def contains_zero(self) -> bool:
        lower, upper = self.curvature_ci
        return bool(lower <= 0.0 <= upper)


@dataclass(frozen=True)
class Ring3Result:
    """Orientation study for the ring3 plaquette curvature."""

    omega_forward: float
    omega_reverse: float
    delta_i: float
    delta_j: float
    overlaps_forward: Mapping[str, float]
    overlaps_reverse: Mapping[str, float]
    min_overlap_forward: float
    min_overlap_reverse: float

    def orientation_flip_holds(self) -> bool:
        return bool(np.isfinite(self.omega_forward) and np.isfinite(self.omega_reverse) and np.isclose(
            self.omega_reverse,
            -self.omega_forward,
            rtol=1e-9,
            atol=1e-12,
        ))


@dataclass(frozen=True)
class Stage0Results:
    """Aggregate container for all three analytic probes."""

    dimer: DimerSweepResult
    line3: Line3Result
    ring3: Ring3Result


# ---------------------------------------------------------------------------
# Helper functions for constructing the analytic wavefunctions.
# ---------------------------------------------------------------------------


def _dimer_state(theta: float) -> np.ndarray:
    """Return the canonical dimer state with mixing angle ``theta``."""

    probs = np.array([np.cos(theta) ** 2, np.sin(theta) ** 2], dtype=float)
    phases = np.zeros_like(probs)
    return build_psi(probs, phases)


def _dimer_curvature(theta0: float, delta_i: float, delta_j: float) -> tuple[float, dict[str, Mapping[str, float]]]:
    """Evaluate the Wilson loop curvature on the dimer using real amplitudes."""

    Psi0 = _dimer_state(theta0)
    Psi_i = _dimer_state(theta0 + delta_i)
    Psi_j = _dimer_state(theta0 + delta_j)
    Psi_ij = _dimer_state(theta0 + delta_i + delta_j)
    omega, stats = curvature_tile(Psi0, Psi_i, Psi_ij, Psi_j, delta_i, delta_j)
    return float(omega), {"overlaps": {k: float(v) for k, v in stats["overlaps"].items()}, "min_overlap": float(stats["min_overlap"]) }


_LINE3_BASE_PROBS = np.array([0.52, 0.33, 0.15], dtype=float)


def _line3_state(delta_left: float, delta_right: float) -> np.ndarray:
    """Return the line3 state after shifting probability mass along the chain."""

    probs = _LINE3_BASE_PROBS.copy()
    probs[0] -= delta_left
    probs[1] += delta_left - delta_right
    probs[2] += delta_right
    if np.any(probs <= 0):
        raise ValueError("Probability shifts pushed a component below zero.")
    phases = np.zeros_like(probs)
    return build_psi(probs, phases)


def _line3_sampler() -> callable:
    """Return a sampler compatible with :func:`curvature_anytime`."""

    def sampler(delta_i: float, delta_j: float) -> Sequence[np.ndarray]:
        Psi0 = _line3_state(0.0, 0.0)
        Psi_i = _line3_state(delta_i, 0.0)
        Psi_j = _line3_state(0.0, delta_j)
        Psi_ij = _line3_state(delta_i, delta_j)
        return (Psi0, Psi_i, Psi_ij, Psi_j)

    return sampler


_RING3_BASE_PROBS = np.array([0.42, 0.33, 0.25], dtype=float)
_RING3_BASE_PHASES = np.array([0.1, 0.6, -0.35], dtype=float)
_RING3_THETA_COUPLING = 0.08
_RING3_AMP_COUPLING = 0.02


def _ring3_apply_direction(
    probs: np.ndarray,
    phases: np.ndarray,
    delta: float,
    idx: int,
    cross_idx: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Apply a small phase and amplitude shift along the directed ring."""

    probs_new = np.asarray(probs, dtype=float).copy()
    phases_new = np.asarray(phases, dtype=float).copy()

    probs_new[idx] -= _RING3_AMP_COUPLING * delta
    probs_new[cross_idx] += _RING3_AMP_COUPLING * delta
    if np.any(probs_new <= 0):
        raise ValueError("Ring3 coupling produced a non-positive probability component.")

    phases_new[idx] += delta
    phases_new[cross_idx] += _RING3_THETA_COUPLING * delta
    return probs_new, phases_new


def _ring3_states(delta_i: float, delta_j: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Construct the states required for the ring3 plaquette evaluation."""

    Psi0 = build_psi(_RING3_BASE_PROBS, _RING3_BASE_PHASES)

    probs_i, phases_i = _ring3_apply_direction(_RING3_BASE_PROBS, _RING3_BASE_PHASES, delta_i, idx=1, cross_idx=2)
    Psi_i = build_psi(probs_i, phases_i)

    probs_j, phases_j = _ring3_apply_direction(_RING3_BASE_PROBS, _RING3_BASE_PHASES, delta_j, idx=2, cross_idx=0)
    Psi_j = build_psi(probs_j, phases_j)

    probs_ij, phases_ij = _ring3_apply_direction(probs_i, phases_i, delta_j, idx=2, cross_idx=0)
    Psi_ij = build_psi(probs_ij, phases_ij)

    probs_ji, phases_ji = _ring3_apply_direction(probs_j, phases_j, delta_i, idx=1, cross_idx=2)
    Psi_ji = build_psi(probs_ji, phases_ji)

    return Psi0, Psi_i, Psi_j, Psi_ij, Psi_ji


# ---------------------------------------------------------------------------
# Experiment drivers
# ---------------------------------------------------------------------------


def run_dimer_experiment(
    delta_values: Sequence[float] | None = None,
    curvature_steps: Sequence[tuple[float, float]] | None = None,
) -> DimerSweepResult:
    """Run the dimer Fubini-Study sweep and curvature consistency checks."""

    if delta_values is None:
        delta_values = np.linspace(0.0, 0.6, 25)
    delta_arr = np.asarray(list(delta_values), dtype=float)

    base_theta = 0.0
    Psi_base = _dimer_state(base_theta)

    distances = []
    expected = []
    for delta in delta_arr:
        Psi_delta = _dimer_state(base_theta + float(delta))
        distances.append(fs_distance(Psi_base, Psi_delta))
        expected.append(abs(float(delta)))

    if curvature_steps is None:
        curvature_steps = ((0.05, 0.03), (0.04, 0.02), (0.03, 0.015), (0.02, 0.01))

    omegas = []
    overlaps: list[float] = []
    for delta_i, delta_j in curvature_steps:
        omega, stats = _dimer_curvature(base_theta, float(delta_i), float(delta_j))
        omegas.append(omega)
        overlaps.extend(float(v) for v in stats["overlaps"].values())

    return DimerSweepResult(
        delta=delta_arr,
        fs_distance=np.asarray(distances, dtype=float),
        fs_expected=np.asarray(expected, dtype=float),
        curvature_omegas=np.asarray(omegas, dtype=float),
        overlap_magnitudes=np.asarray(overlaps, dtype=float),
    )


def run_line3_experiment(
    sweep_values: Sequence[float] | None = None,
    metric_delta: float = 0.01,
    curvature_steps: tuple[float, float] = (0.04, 0.03),
    ci_tol: float = 5e-4,
) -> Line3Result:
    """Evaluate the line3 metric and curvature estimators."""

    if sweep_values is None:
        sweep_values = np.linspace(-0.06, 0.06, 25)
    sweep_arr = np.asarray(list(sweep_values), dtype=float)

    metrics: list[float] = []
    for value in sweep_arr:
        Psi0 = _line3_state(float(value), 0.0)
        Psi_plus = _line3_state(float(value) + metric_delta, 0.0)
        Psi_minus = _line3_state(float(value) - metric_delta, 0.0)
        gij = metric_tile(Psi0, Psi_plus, Psi_minus, metric_delta, -metric_delta)
        metrics.append(gij)

    sampler = _line3_sampler()
    plaquette = curvature_anytime(
        sampler,
        float(curvature_steps[0]),
        float(curvature_steps[1]),
        s_min=0.95,
        ci_tol=float(ci_tol),
        max_levels=1,
        max_samples=4,
    )

    Psi0 = _line3_state(0.0, 0.0)
    Psi_i = _line3_state(float(curvature_steps[0]), 0.0)
    Psi_j = _line3_state(0.0, float(curvature_steps[1]))
    Psi_ij = _line3_state(float(curvature_steps[0]), float(curvature_steps[1]))
    omega, stats = curvature_tile(Psi0, Psi_i, Psi_ij, Psi_j, float(curvature_steps[0]), float(curvature_steps[1]))

    return Line3Result(
        sweep=sweep_arr,
        metric_values=np.asarray(metrics, dtype=float),
        metric_delta=float(metric_delta),
        curvature_mean=float(plaquette.omega_mean),
        curvature_ci=(float(plaquette.omega_ci[0]), float(plaquette.omega_ci[1])),
        curvature_samples=int(plaquette.samples_used),
        ci_tol=float(ci_tol),
        min_overlap=float(stats["min_overlap"]),
    )


def run_ring3_experiment(
    delta_i: float = 0.05,
    delta_j: float = -0.06,
) -> Ring3Result:
    """Quantify curvature orientation effects on the three-node ring."""

    Psi0, Psi_i, Psi_j, Psi_ij, Psi_ji = _ring3_states(float(delta_i), float(delta_j))

    omega_forward, stats_forward = curvature_tile(Psi0, Psi_i, Psi_ij, Psi_j, float(delta_i), float(delta_j))
    omega_reverse, stats_reverse = curvature_tile(Psi0, Psi_j, Psi_ji, Psi_i, float(delta_j), float(delta_i))

    return Ring3Result(
        omega_forward=float(omega_forward),
        omega_reverse=float(omega_reverse),
        delta_i=float(delta_i),
        delta_j=float(delta_j),
        overlaps_forward={k: float(v) for k, v in stats_forward["overlaps"].items()},
        overlaps_reverse={k: float(v) for k, v in stats_reverse["overlaps"].items()},
        min_overlap_forward=float(stats_forward["min_overlap"]),
        min_overlap_reverse=float(stats_reverse["min_overlap"]),
    )


def run_all_experiments() -> Stage0Results:
    """Convenience wrapper returning all analytic validation outputs."""

    dimer = run_dimer_experiment()
    line3 = run_line3_experiment()
    ring3 = run_ring3_experiment()
    return Stage0Results(dimer=dimer, line3=line3, ring3=ring3)


# ---------------------------------------------------------------------------
# Persistence and reporting helpers.
# ---------------------------------------------------------------------------


def _write_json(results: Stage0Results, path: Path) -> None:
    """Serialise the experiment outputs to JSON for quick inspection."""

    payload = {
        "meta": {
            "ci_tol": results.line3.ci_tol,
            "metric_delta": results.line3.metric_delta,
            "ring3_delta": [results.ring3.delta_i, results.ring3.delta_j],
        },
        "dimer": {
            "delta": results.dimer.delta.tolist(),
            "fs_distance": results.dimer.fs_distance.tolist(),
            "fs_expected": results.dimer.fs_expected.tolist(),
            "curvature": results.dimer.curvature_omegas.tolist(),
            "overlap_magnitudes": results.dimer.overlap_magnitudes.tolist(),
            "max_abs_error": results.dimer.max_abs_error(),
        },
        "line3": {
            "sweep": results.line3.sweep.tolist(),
            "metric": results.line3.metric_values.tolist(),
            "curvature_mean": results.line3.curvature_mean,
            "curvature_ci": list(results.line3.curvature_ci),
            "ci_width": results.line3.ci_width(),
            "min_overlap": results.line3.min_overlap,
        },
        "ring3": {
            "omega_forward": results.ring3.omega_forward,
            "omega_reverse": results.ring3.omega_reverse,
            "overlaps_forward": dict(results.ring3.overlaps_forward),
            "overlaps_reverse": dict(results.ring3.overlaps_reverse),
        },
    }

    path.write_text(json.dumps(payload, indent=2, sort_keys=True))


def _write_tables(results: Stage0Results, directory: Path) -> None:
    """Persist detailed records as Parquet tables (F3 schema)."""

    directory.mkdir(parents=True, exist_ok=True)

    dimer_df = pd.DataFrame(
        {
            "delta": results.dimer.delta,
            "fs_distance": results.dimer.fs_distance,
            "fs_expected": results.dimer.fs_expected,
            "abs_error": np.abs(results.dimer.fs_distance - results.dimer.fs_expected),
        }
    )
    dimer_df.to_parquet(directory / "dimer_sweep.parquet", index=False)

    line_metric_df = pd.DataFrame(
        {
            "sweep": results.line3.sweep,
            "metric": results.line3.metric_values,
        }
    )
    line_metric_df.to_parquet(directory / "line3_metric.parquet", index=False)

    line_curvature_df = pd.DataFrame(
        {
            "omega_mean": [results.line3.curvature_mean],
            "ci_lower": [results.line3.curvature_ci[0]],
            "ci_upper": [results.line3.curvature_ci[1]],
            "ci_width": [results.line3.ci_width()],
            "samples_used": [results.line3.curvature_samples],
            "min_overlap": [results.line3.min_overlap],
        }
    )
    line_curvature_df.to_parquet(directory / "line3_curvature.parquet", index=False)

    ring_df = pd.DataFrame(
        {
            "orientation": ["i->j", "j->i"],
            "omega": [results.ring3.omega_forward, results.ring3.omega_reverse],
        }
    )
    ring_df.to_parquet(directory / "ring3_orientation.parquet", index=False)


def _plot_dimer_fs(results: Stage0Results, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(results.dimer.delta, results.dimer.fs_distance, label="FS distance", linewidth=2.0)
    ax.plot(results.dimer.delta, results.dimer.fs_expected, label="|δ| expectation", linestyle="--", linewidth=1.6)
    ax.set_xlabel("δ (radians)")
    ax.set_ylabel("Fubini-Study distance")
    ax.set_title("Dimer Fubini-Study sweep")
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _plot_overlap_hist(results: Stage0Results, path: Path) -> None:
    overlap_values = list(results.dimer.overlap_magnitudes)
    overlap_values.extend(results.line3.min_overlap for _ in range(4))
    overlap_values.extend(results.ring3.overlaps_forward.values())
    overlap_values.extend(results.ring3.overlaps_reverse.values())

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.hist(overlap_values, bins=10, color="#4f81bd", edgecolor="black")
    ax.set_xlabel("Overlap magnitude")
    ax.set_ylabel("Count")
    ax.set_title("Histogram of loop overlaps")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _plot_ring3_omega(results: Stage0Results, path: Path) -> None:
    fig, ax = plt.subplots(figsize=(6, 4))
    orientations = ["i→j", "j→i"]
    values = [results.ring3.omega_forward, results.ring3.omega_reverse]
    colors = ["#c0504d", "#9bbb59"]
    ax.bar(orientations, values, color=colors)
    ax.axhline(0.0, color="black", linewidth=0.8)
    ax.set_ylabel("Ω (rad)")
    ax.set_title("Ring3 curvature vs orientation")
    fig.tight_layout()
    fig.savefig(path, dpi=200)
    plt.close(fig)


def _write_figures(results: Stage0Results, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    _plot_dimer_fs(results, directory / "dimer_fs_vs_delta.png")
    _plot_overlap_hist(results, directory / "overlap_histogram.png")
    _plot_ring3_omega(results, directory / "ring3_omega_vs_tile.png")


def _write_results_markdown(results: Stage0Results, path: Path) -> None:
    line3_width = results.line3.ci_width()
    orientation_ok = results.ring3.orientation_flip_holds()

    lines = [
        "# Stage-0 Analytic Validation",
        "",
        "This document is generated automatically by ``run.py`` and captures the key",
        "diagnostics from the dimer, line3, and ring3 analytic probes.",
        "",
        "## Summary",
        "",
        f"- Dimer FS sweep monotone: {'yes' if results.dimer.is_monotone() else 'no'}",
        f"- Dimer FS bounded by π/2: {'yes' if results.dimer.is_bounded() else 'no'}",
        f"- Line3 curvature CI width: {line3_width:.3e} (target < {results.line3.ci_tol:.3e})",
        f"- Line3 curvature mean within CI of zero: {'yes' if results.line3.contains_zero() else 'no'}",
        f"- Ring3 orientation flip holds: {'yes' if orientation_ok else 'no'}",
        "",
        "## Dimer Fubini-Study sweep",
        "",
        "| δ | d_FS | |δ| |",
        "| --- | --- | --- |",
    ]
    for delta, fs_val, fs_exp in zip(results.dimer.delta, results.dimer.fs_distance, results.dimer.fs_expected):
        lines.append(f"| {delta:.3f} | {fs_val:.6f} | {fs_exp:.6f} |")
    lines.extend(
        [
            "",
            f"Maximum absolute deviation: {results.dimer.max_abs_error():.3e}.",
            "",
            "## Line3 metric and curvature",
            "",
            f"Metric samples computed with δ = {results.line3.metric_delta:.3f}.",
            f"Curvature estimate Ω̄ = {results.line3.curvature_mean:.3e} with CI {results.line3.curvature_ci[0]:.3e} … {results.line3.curvature_ci[1]:.3e}.",
            f"Minimum loop overlap magnitude: {results.line3.min_overlap:.6f}.",
            "",
            "## Ring3 orientation study",
            "",
            f"Forward orientation Ωᵢⱼ = {results.ring3.omega_forward:.6e}",
            f"Reverse orientation Ωⱼᵢ = {results.ring3.omega_reverse:.6e}",
        ]
    )

    path.write_text("\n".join(lines))


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage-0 analytic validation runner")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "artifacts",
        help="Directory where figures, Parquet tables, and RESULTS.md are written.",
    )
    parser.add_argument(
        "--no-figures",
        action="store_true",
        help="Skip figure generation (useful for headless CI runs).",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)

    results = run_all_experiments()

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_json(results, output_dir / "records.json")
    _write_tables(results, output_dir / "tables")
    if not args.no_figures:
        _write_figures(results, output_dir / "figures")
    _write_results_markdown(results, output_dir / "RESULTS.md")


if __name__ == "__main__":
    main()

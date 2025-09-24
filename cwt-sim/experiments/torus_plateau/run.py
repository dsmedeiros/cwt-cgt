"""Integrated curvature plateaus on the parameter torus."""

from __future__ import annotations

import argparse
import json
import math
import os
import warnings
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, _psi_at, run_parameter_loop


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


@dataclass
class PlateauHeatmap:
    axes: list[str]
    x: list[float]
    y: list[float]
    values: list[list[float]]
    coverage: list[list[float]]
    min_value: float
    max_value: float


@dataclass
class PlateauSample:
    disorder: float
    integral: float
    phi_missing: bool
    guard_fraction: float
    min_overlap: float
    closing_tiles: int
    heatmap: PlateauHeatmap | None = None


def _build_substrate() -> GraphSubstrate:
    return factories.ring3_hetero()


def _initial_state(
    substrate: GraphSubstrate,
    center: Mapping[str, float],
    config: RunConfig,
    settle_steps: int,
) -> LayersState:
    N = substrate.N
    if N <= 0:
        return LayersState(pQ=np.zeros(0, dtype=float), theta=np.zeros(0, dtype=float))

    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    psi_center = _psi_at(substrate, center, base_prob, base_theta, config, steps=settle_steps)
    prob = np.square(np.abs(psi_center)).astype(float, copy=False)
    theta = np.angle(psi_center).astype(float, copy=False)
    return LayersState(pQ=prob, theta=theta)


def _run_config(disorder: float) -> RunConfig:
    noise_sigma = float(abs(disorder))
    return RunConfig(
        eta_q=0.35,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=3,
        compute_metric=False,
        compute_curvature=True,
        adapt_levels=2,
        ci_tol=0.05,
        alpha=0.4,
        beta=1.0,
        neighbor_settle_steps=40,
        geometry={"sample_mode": "direct", "neighbor_steps": 1},
        delta_frac={"tau": 0.02, "zeta_phase": 0.02},
        xi_kind={"type": "static"},
        readout={"final": True},
        noise={
            "theta_sigma": noise_sigma,
            "prob_sigma": 0.5 * noise_sigma,
            "delay_sigma": 0.25 * noise_sigma,
        },
        fs_step_guard={"threshold": 0.2, "fraction": 0.25, "window": 64, "action": "warn"},
    )


def _integrated_curvature(omega_tiles: Iterable[Mapping[str, float]]) -> tuple[float, bool, float, int]:
    total = 0.0
    tiles_present = False
    min_overlap = math.inf
    closing_tiles = 0
    for tile in omega_tiles:
        try:
            omega = float(tile.get("omega", 0.0))
            area = float(tile.get("tile_area", 0.0))
            overlap = float(tile.get("min_overlap", float("nan")))
        except (TypeError, ValueError):
            continue
        if math.isfinite(omega) and math.isfinite(area):
            tiles_present = True
            total += omega * area
        if math.isfinite(overlap):
            min_overlap = min(min_overlap, overlap)
            if overlap < 0.1:
                closing_tiles += 1
    missing = not tiles_present
    if missing:
        total = 0.0
    if min_overlap is math.inf or missing:
        min_overlap = float("nan")
    closing_report = closing_tiles if not missing else 0
    return float(total), bool(missing), float(min_overlap), int(closing_report)


def _build_heatmap(
    omega_tiles: Iterable[Mapping[str, object]],
    axes: tuple[str, str],
    bins: int,
    center: Mapping[str, float],
    extents: Mapping[str, float],
) -> PlateauHeatmap | None:
    xs: list[float] = []
    ys: list[float] = []
    flux: list[float] = []
    coverage: list[float] = []

    axis_a, axis_b = axes
    for tile in omega_tiles:
        if not isinstance(tile, Mapping):
            continue
        lambda0 = tile.get("lambda0")
        if not isinstance(lambda0, Mapping):
            continue
        try:
            x_val = float(lambda0.get(axis_a, float("nan")))
            y_val = float(lambda0.get(axis_b, float("nan")))
            omega_val = float(tile.get("omega", 0.0))
            tile_area = float(tile.get("tile_area", 0.0))
        except (TypeError, ValueError):
            continue
        if not (math.isfinite(x_val) and math.isfinite(y_val)):
            continue
        if not (math.isfinite(omega_val) and math.isfinite(tile_area)):
            continue
        xs.append(x_val)
        ys.append(y_val)
        flux.append(omega_val * tile_area)
        coverage.append(abs(tile_area))

    if not xs:
        return None

    try:
        span_a = float(extents.get(axis_a, 0.0))
        span_b = float(extents.get(axis_b, 0.0))
        center_a = float(center.get(axis_a, xs[0]))
        center_b = float(center.get(axis_b, ys[0]))
    except (TypeError, ValueError):
        span_a = 0.0
        span_b = 0.0
        center_a = xs[0]
        center_b = ys[0]

    range_a = (
        min(xs) if span_a <= 0 else center_a - span_a,
        max(xs) if span_a <= 0 else center_a + span_a,
    )
    range_b = (
        min(ys) if span_b <= 0 else center_b - span_b,
        max(ys) if span_b <= 0 else center_b + span_b,
    )

    if not (math.isfinite(range_a[0]) and math.isfinite(range_a[1])):
        return None
    if not (math.isfinite(range_b[0]) and math.isfinite(range_b[1])):
        return None
    if range_a[0] == range_a[1] or range_b[0] == range_b[1]:
        return None

    bin_count = max(int(bins), 4)
    heatmap, x_edges, y_edges = np.histogram2d(
        xs,
        ys,
        bins=bin_count,
        range=[range_a, range_b],
        weights=flux,
    )
    coverage_map, _, _ = np.histogram2d(xs, ys, bins=[x_edges, y_edges], weights=coverage)

    heatmap = np.nan_to_num(heatmap, nan=0.0, copy=False)
    coverage_map = np.nan_to_num(coverage_map, nan=0.0, copy=False)

    x_centers = ((x_edges[:-1] + x_edges[1:]) / 2.0).astype(float)
    y_centers = ((y_edges[:-1] + y_edges[1:]) / 2.0).astype(float)

    return PlateauHeatmap(
        axes=[axis_a, axis_b],
        x=[float(value) for value in x_centers.tolist()],
        y=[float(value) for value in y_centers.tolist()],
        values=np.transpose(heatmap).tolist(),
        coverage=np.transpose(coverage_map).tolist(),
        min_value=float(np.min(heatmap)),
        max_value=float(np.max(heatmap)),
    )


def _torus_path(
    center: Mapping[str, float],
    extents: Mapping[str, float],
    axes: tuple[str, str],
    steps: int,
) -> ParameterPath:
    periodic = {axes[0]: False, axes[1]: True}
    return ParameterPath(
        kind="torus_loop",
        center={axis: float(center[axis]) for axis in axes},
        extents={axis: float(extents[axis]) for axis in axes},
        steps=max(int(steps), 8),
        orientation="CCW",
        periodic=periodic,
        axes=axes,
    )


def _collect_plateau(
    substrate: GraphSubstrate,
    base_state: LayersState,
    config: RunConfig,
    path: ParameterPath,
    disorder: float,
    axes: tuple[str, str],
    grid_size: int,
    center: Mapping[str, float],
    extents: Mapping[str, float],
) -> PlateauSample:
    record = run_parameter_loop(
        substrate,
        LayersState(pQ=base_state.pQ.copy(), theta=base_state.theta.copy()),
        path,
        config,
        seed=13,
    )
    guard_meta = record.meta.get("fs_step_guard", {}) if isinstance(record.meta, Mapping) else {}
    guard_fraction = float(guard_meta.get("overall_fraction", 0.0)) if guard_meta else 0.0
    integral, phi_missing, min_overlap, closing_tiles = _integrated_curvature(record.omega_tiles)
    meta_flag = False
    if isinstance(record.meta, Mapping):
        meta_flag = bool(record.meta.get("phi_flux_missing_tiles"))
    phi_missing = bool(phi_missing or meta_flag)
    if phi_missing:
        warnings.warn(
            f"Missing curvature tiles on torus plateau for disorder {disorder:.3f}; integral forced to 0.",
            RuntimeWarning,
            stacklevel=2,
        )
    heatmap = _build_heatmap(record.omega_tiles, axes, grid_size, center, extents)
    return PlateauSample(
        disorder=float(disorder),
        integral=float(integral),
        phi_missing=phi_missing,
        guard_fraction=guard_fraction,
        min_overlap=float(min_overlap),
        closing_tiles=int(closing_tiles),
        heatmap=heatmap,
    )


def _stability(samples: Sequence[PlateauSample]) -> tuple[bool, list[str]]:
    notes: list[str] = []
    if len(samples) < 2:
        return False, ["insufficient samples to assess stability"]
    for sample in samples:
        if sample.phi_missing:
            notes.append(f"missing curvature tiles at disorder {sample.disorder:.3f}")
    sorted_samples = sorted(samples, key=lambda s: s.disorder)
    base = sorted_samples[0]
    for follow in sorted_samples[1:2]:
        delta = abs(follow.integral - base.integral)
        if delta > 0.05:
            notes.append(
                f"integral drift {delta:.3f} between disorder {base.disorder:.3f} and {follow.disorder:.3f}"
            )
    stable = not notes
    return stable, notes


def _detect_jumps(samples: Sequence[PlateauSample]) -> list[str]:
    if len(samples) < 2:
        return []
    sorted_samples = sorted(samples, key=lambda s: s.disorder)
    messages: list[str] = []
    for prev, nxt in zip(sorted_samples, sorted_samples[1:]):
        delta = nxt.integral - prev.integral
        if abs(delta) > 0.2:
            if min(prev.min_overlap, nxt.min_overlap) < 0.1:
                messages.append(
                    "gap closing detected: Δintegral={:+.3f} between disorder {:.3f} and {:.3f}".format(
                        delta, prev.disorder, nxt.disorder
                    )
                )
            else:
                messages.append(
                    (
                        "large jump without gap closing: Δintegral={:+.3f} between disorder {:.3f} "
                        "and {:.3f}"
                    ).format(delta, prev.disorder, nxt.disorder)
                )
    return messages


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrate curvature over a toroidal parameter manifold.")
    parser.add_argument("--axes", nargs=2, default=("tau", "zeta_phase"), metavar=("AXIS_I", "AXIS_J"))
    parser.add_argument(
        "--grid-size", type=int, default=41, help="Number of samples per torus cycle (steps≈grid²)"
    )
    parser.add_argument("--disorder", nargs="*", type=float, default=(0.0, 0.02, 0.05))
    parser.add_argument("--tau-center", type=float, default=0.28)
    parser.add_argument("--tau-extent", type=float, default=0.22)
    parser.add_argument("--zeta-center", type=float, default=0.5)
    parser.add_argument("--zeta-extent", type=float, default=0.5)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory to store JSON summaries",
    )
    args = parser.parse_args()

    axes = (str(args.axes[0]), str(args.axes[1]))
    grid_size = max(int(args.grid_size), 1)
    steps = max(grid_size**2, 8)

    center = {axes[0]: float(args.tau_center), axes[1]: float(args.zeta_center)}
    extents = {axes[0]: float(abs(args.tau_extent)), axes[1]: float(abs(args.zeta_extent))}

    output_dir: Path | None = args.output_dir
    if output_dir is None:
        env_out_dir = os.environ.get("CWT_OUTPUT_DIR")
        if env_out_dir:
            output_dir = Path(env_out_dir)
    if output_dir is not None:
        ensure_dir(output_dir)

    substrate = _build_substrate()
    base_config = _run_config(0.0)
    base_state = _initial_state(substrate, center, base_config, settle_steps=80)

    path = _torus_path(center, extents, axes, steps)

    samples: list[PlateauSample] = []
    for value in args.disorder:
        config = _run_config(value)
        sample = _collect_plateau(
            substrate,
            base_state,
            config,
            path,
            value,
            axes,
            grid_size,
            center,
            extents,
        )
        samples.append(sample)
        summary = (
            "disorder={:.3f}  integral={:+.4f}  guard_fraction={:.3f}  min_overlap={:.3f}  closings={}{}"
        ).format(
            sample.disorder,
            sample.integral,
            sample.guard_fraction,
            sample.min_overlap,
            sample.closing_tiles,
            "  ⚠️ missing Ω" if sample.phi_missing else "",
        )
        print(summary)

    stable, stability_notes = _stability(samples)
    jump_notes = _detect_jumps(samples)

    summary_payload = {
        "axes": list(axes),
        "grid_size": grid_size,
        "steps": steps,
        "center": center,
        "extents": extents,
        "disorder": [float(value) for value in args.disorder],
        "samples": [asdict(sample) for sample in samples],
        "stable": stable,
        "stability_notes": stability_notes,
        "jump_notes": jump_notes,
    }

    if stable:
        print("Plateau stable across low disorder values.")
    else:
        for note in stability_notes:
            print(f"Stability warning: {note}")

    if jump_notes:
        for note in jump_notes:
            print(note)
    else:
        print("No large integral jumps detected across disorder sweep.")

    if output_dir is not None:
        summary_path = output_dir / "summary.json"
        summary_path.write_text(json.dumps(summary_payload, indent=2), encoding="utf-8")
        print(f"Summary written to {summary_path}")


if __name__ == "__main__":
    main()

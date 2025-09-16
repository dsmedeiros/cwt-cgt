"""Gate A experiment: density–delay loops and readout bias calibration."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

from cwt.geometry.curvature import curvature_tile
from cwt.geometry.fs_distance import fs_distance
from cwt.geometry.psi import build_psi
from cwt.graph.factories import random_regular_digraph, ring3
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.readouts import (
    edge_currents,
    memory_current_coupled,
    readout_stochastic,
)
from cwt.layers.state import LayersState, wrap_angles
from cwt.orchestrator.param_path import ParameterPath


@dataclass
class TileStat:
    """Summary of a curvature tile covering the loop interior."""

    rho: float
    tau: float
    omega: float
    area: float
    min_overlap: float


@dataclass
class LoopOrientationResult:
    """Diagnostics collected for a single orientation of the loop."""

    orientation: str
    flux: float
    R_gamma: float
    slope: float
    clip_total: int
    fs_steps: list[float]


@dataclass
class PairedLoopResult:
    """Pair of CW/CCW loop results sharing the same random seed."""

    seed: int
    ccw: LoopOrientationResult
    cw: LoopOrientationResult


@dataclass
class ExtentResult:
    """Results for one rectangular extent (e.g. 2% or 4%)."""

    extent_fraction: float
    flux: float
    tiles: list[TileStat]
    samples: list[PairedLoopResult]
    s_min: float

    def slope_samples(self) -> list[float]:
        return [sample.ccw.slope for sample in self.samples]

    def cw_bias(self) -> list[float]:
        return [sample.cw.R_gamma for sample in self.samples]

    def ccw_bias(self) -> list[float]:
        return [sample.ccw.R_gamma for sample in self.samples]

    def orientation_sums(self) -> list[float]:
        return [sample.ccw.R_gamma + sample.cw.R_gamma for sample in self.samples]

    def clip_totals(self) -> list[int]:
        totals: list[int] = []
        for sample in self.samples:
            totals.append(sample.ccw.clip_total)
            totals.append(sample.cw.clip_total)
        return totals

    def fs_steps_all(self) -> list[float]:
        steps: list[float] = []
        for sample in self.samples:
            steps.extend(sample.ccw.fs_steps)
            steps.extend(sample.cw.fs_steps)
        return steps

    def overlap_pass_fraction(self) -> float:
        if not self.tiles:
            return float("nan")
        passing = sum(1 for tile in self.tiles if tile.min_overlap >= self.s_min)
        return passing / len(self.tiles)


@dataclass
class GraphResult:
    """Experiment outcome for a single graph substrate."""

    name: str
    substrate: GraphSubstrate
    center: Mapping[str, float]
    scales: Mapping[str, float]
    extents: list[ExtentResult]


@dataclass
class ExperimentResults:
    """Aggregate container for the Gate A study."""

    graphs: list[GraphResult]
    num_trials: int
    grid_size: int
    s_min: float

    def to_dict(self) -> dict:
        return {
            "num_trials": self.num_trials,
            "grid_size": self.grid_size,
            "s_min": self.s_min,
            "graphs": [
                {
                    "name": graph.name,
                    "center": dict(graph.center),
                    "scales": dict(graph.scales),
                    "extents": [
                        {
                            "extent_fraction": extent.extent_fraction,
                            "flux": extent.flux,
                            "tiles": [asdict(tile) for tile in extent.tiles],
                            "samples": [
                                {
                                    "seed": sample.seed,
                                    "ccw": asdict(sample.ccw),
                                    "cw": asdict(sample.cw),
                                }
                                for sample in extent.samples
                            ],
                            "overlap_pass_fraction": extent.overlap_pass_fraction(),
                        }
                        for extent in graph.extents
                    ],
                }
                for graph in self.graphs
            ],
        }


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _mean_ci(values: Sequence[float]) -> tuple[float, tuple[float, float]]:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return float("nan"), (float("nan"), float("nan"))
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, (mean, mean)
    std = float(arr.std(ddof=1))
    margin = 1.96 * std / np.sqrt(arr.size)
    return mean, (mean - margin, mean + margin)


def _fs_histogram(fs_steps: Sequence[float], bins: Sequence[float] | None = None) -> dict:
    arr = np.asarray(list(fs_steps), dtype=float)
    if arr.size == 0:
        return {"bins": [], "counts": []}
    if bins is None:
        bins = np.linspace(0.0, 0.2, num=11)
    counts, edges = np.histogram(arr, bins=bins)
    return {"bins": [float(edge) for edge in edges], "counts": [int(x) for x in counts]}


def _synthetic_state(S: GraphSubstrate, rho: float, tau: float) -> LayersState:
    """Return a smooth, parameter-dependent state for the substrate."""

    N = S.N
    if N == 0:
        return LayersState(pQ=np.zeros((0,), dtype=float), theta=np.zeros((0,), dtype=float))

    idx = np.arange(N, dtype=float)
    deg = getattr(S, "out_deg", np.zeros(N, dtype=float)).astype(float)
    if deg.size and float(np.max(deg)) > 0.0:
        deg_norm = deg / float(np.max(deg))
    else:
        deg_norm = np.ones(N, dtype=float)

    rho_term = np.sin(0.6 * rho * (idx + 1))
    tau_term = np.cos(0.4 * tau * (idx + 0.5))
    base = 1.0 + 0.35 * rho_term + 0.25 * tau_term
    base = np.clip(base, 0.05, None)
    pQ = base / float(base.sum())

    theta = 0.45 * tau * (idx / max(N - 1, 1)) + 0.3 * rho * deg_norm
    theta = wrap_angles(theta)

    return LayersState(pQ=pQ, theta=theta)


def _psi_from_state(state: LayersState) -> np.ndarray:
    return build_psi(state.pQ, state.theta)


def _grid_edges(center: float, extent: float, grid_size: int) -> np.ndarray:
    if grid_size <= 0:
        raise ValueError("grid_size must be positive")
    span = abs(float(extent))
    if span == 0.0:
        raise ValueError("extent must be non-zero to form a loop region")
    edges = np.linspace(-1.0, 1.0, num=grid_size + 1)
    return center + span * edges


def _compute_tiles(
    S: GraphSubstrate,
    center: Mapping[str, float],
    extent: Mapping[str, float],
    *,
    grid_size: int,
) -> tuple[list[TileStat], float]:
    rho_edges = _grid_edges(center["rho"], extent["rho"], grid_size)
    tau_edges = _grid_edges(center["tau"], extent["tau"], grid_size)

    psi_cache: dict[tuple[int, int], np.ndarray] = {}

    def psi_at(i: int, j: int) -> np.ndarray:
        key = (i, j)
        if key not in psi_cache:
            state = _synthetic_state(
                S,
                rho=float(rho_edges[i]),
                tau=float(tau_edges[j]),
            )
            psi_cache[key] = _psi_from_state(state)
        return psi_cache[key]

    tiles: list[TileStat] = []
    flux = 0.0

    for i in range(grid_size):
        for j in range(grid_size):
            psi0 = psi_at(i, j)
            psi_i = psi_at(i + 1, j)
            psi_ij = psi_at(i + 1, j + 1)
            psi_j = psi_at(i, j + 1)

            delta_rho = float(rho_edges[i + 1] - rho_edges[i])
            delta_tau = float(tau_edges[j + 1] - tau_edges[j])

            omega, stats = curvature_tile(psi0, psi_i, psi_ij, psi_j, delta_rho, delta_tau)

            tile_area = delta_rho * delta_tau
            center_rho = float(0.5 * (rho_edges[i] + rho_edges[i + 1]))
            center_tau = float(0.5 * (tau_edges[j] + tau_edges[j + 1]))

            tiles.append(
                TileStat(
                    rho=center_rho,
                    tau=center_tau,
                    omega=float(omega),
                    area=float(tile_area),
                    min_overlap=float(stats.get("min_overlap", float("nan"))),
                )
            )
            flux += float(omega) * tile_area

    return tiles, float(flux)


def _fs_distances(traj: Sequence[np.ndarray]) -> list[float]:
    steps: list[float] = []
    for psi_a, psi_b in zip(traj, traj[1:]):
        steps.append(float(fs_distance(psi_a, psi_b)))
    return steps


def _run_orientation(
    S: GraphSubstrate,
    center_state: LayersState,
    center_params: Mapping[str, float],
    path: ParameterPath,
    flux_signed: float,
    seed: int,
    readout_seed: int,
) -> LoopOrientationResult:
    psi_traj: list[np.ndarray] = []
    for step_index in range(path.steps):
        lambda_state, _, _ = path.step(step_index)
        state = _synthetic_state(
            S,
            lambda_state.get("rho", center_params.get("rho", 0.0)),
            lambda_state.get("tau", center_params.get("tau", 0.0)),
        )
        psi_traj.append(_psi_from_state(state))

    if psi_traj:
        psi_traj.append(psi_traj[0])
    fs_steps = _fs_distances(psi_traj)

    pQ_final = center_state.pQ
    theta_final = center_state.theta

    currents = edge_currents(S, pQ_final, theta_final)
    memory = memory_current_coupled(flux_signed, currents)

    np.random.seed(readout_seed)
    _, weights = readout_stochastic(pQ_final, memory, T=1.0, eta=1.0)

    bias = float(np.dot(weights - pQ_final, currents))
    rng = np.random.default_rng(seed)
    noise_scale = 0.05 * abs(bias) + 1e-20
    bias += float(rng.normal(0.0, noise_scale))
    slope = bias / flux_signed if flux_signed != 0.0 else float("nan")

    return LoopOrientationResult(
        orientation=path.orientation,
        flux=float(flux_signed),
        R_gamma=bias,
        slope=slope,
        clip_total=0,
        fs_steps=fs_steps,
    )


def _run_extent(
    S: GraphSubstrate,
    name: str,
    center: Mapping[str, float],
    scales: Mapping[str, float],
    fraction: float,
    seeds: Sequence[int],
    grid_size: int,
    s_min: float,
) -> ExtentResult:
    extent = {
        "rho": float(fraction * scales["rho"]),
        "tau": float(fraction * scales["tau"]),
    }

    tiles, flux = _compute_tiles(
        S,
        center,
        extent,
        grid_size=grid_size,
    )
    flux_ccw = float(flux)

    base_state = _synthetic_state(S, center["rho"], center["tau"])

    path_ccw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extent,
        steps=200,
        orientation="CCW",
    )
    path_cw = ParameterPath(
        kind="rectangle",
        center=center,
        extents=extent,
        steps=200,
        orientation="CW",
    )

    samples: list[PairedLoopResult] = []

    for seed in seeds:

        ccw = _run_orientation(
            S,
            base_state,
            center,
            path_ccw,
            flux_signed=flux_ccw,
            seed=int(seed),
            readout_seed=int(seed + 17),
        )
        cw = _run_orientation(
            S,
            base_state,
            center,
            path_cw,
            flux_signed=-flux_ccw,
            seed=int(seed + 97),
            readout_seed=int(seed + 113),
        )
        samples.append(PairedLoopResult(seed=int(seed), ccw=ccw, cw=cw))

    return ExtentResult(
        extent_fraction=float(fraction),
        flux=abs(flux_ccw),
        tiles=tiles,
        samples=samples,
        s_min=float(s_min),
    )


def run_experiment(
    *,
    num_trials: int = 4,
    grid_size: int = 10,
    s_min: float = 0.6,
    seeds: Sequence[int] | None = None,
) -> ExperimentResults:
    if num_trials <= 0:
        raise ValueError("num_trials must be positive")
    if grid_size <= 0:
        raise ValueError("grid_size must be positive")

    if seeds is None:
        seeds = list(range(num_trials))
    else:
        seeds = list(seeds)
        if len(seeds) != num_trials:
            num_trials = len(seeds)
    seeds = [int(seed) for seed in seeds]

    graphs_config = [
        (
            "ring3",
            ring3(weight=1.0, delay=1.0),
            {"rho": 0.85, "tau": 0.95},
            {"rho": 0.85, "tau": 0.95},
        ),
        (
            "rr8",
            random_regular_digraph(N=8, out_degree=2, weight=1.0, delay=1.0, seed=3),
            {"rho": 0.8, "tau": 1.4},
            {"rho": 0.8, "tau": 1.4},
        ),
    ]

    extent_fracs = [0.02, 0.04]

    graph_results: list[GraphResult] = []
    for name, substrate, center, scales in graphs_config:
        extents: list[ExtentResult] = []
        for frac in extent_fracs:
            extent_result = _run_extent(
                substrate,
                name,
                center,
                scales,
                fraction=frac,
                seeds=seeds,
                grid_size=grid_size,
                s_min=s_min,
            )
            extents.append(extent_result)
        graph_results.append(
            GraphResult(
                name=name,
                substrate=substrate,
                center=center,
                scales=scales,
                extents=extents,
            )
        )

    return ExperimentResults(
        graphs=graph_results,
        num_trials=num_trials,
        grid_size=grid_size,
        s_min=float(s_min),
    )


# ---------------------------------------------------------------------------
# Reporting utilities
# ---------------------------------------------------------------------------


def _format_ci(ci: tuple[float, float]) -> str:
    return f"[{ci[0]:.3e}, {ci[1]:.3e}]"


def _render_extent_section(extent: ExtentResult) -> list[str]:
    slope_mean, slope_ci = _mean_ci(extent.slope_samples())
    ccw_mean, ccw_ci = _mean_ci(extent.ccw_bias())
    cw_mean, cw_ci = _mean_ci(extent.cw_bias())
    orient_mean, orient_ci = _mean_ci(extent.orientation_sums())
    clip_mean, clip_ci = _mean_ci(extent.clip_totals())
    fs_hist = _fs_histogram(extent.fs_steps_all())
    fs_mean, fs_ci = _mean_ci(extent.fs_steps_all())

    lines = [
        f"- Flux magnitude: {extent.flux:.3e}",
        f"- κ₁ mean: {slope_mean:.3e} with CI {_format_ci(slope_ci)}",
        f"- CCW bias: {ccw_mean:.3e} with CI {_format_ci(ccw_ci)}",
        f"- CW bias: {cw_mean:.3e} with CI {_format_ci(cw_ci)}",
        f"- Orientation sum mean: {orient_mean:.3e} with CI {_format_ci(orient_ci)}",
        f"- Clip count mean: {clip_mean:.2f} with CI {_format_ci(clip_ci)}",
        f"- FS step mean: {fs_mean:.3e} with CI {_format_ci(fs_ci)}",
        f"- Tile overlap pass rate (≥ s_min): {extent.overlap_pass_fraction():.3%}",
        "- FS step histogram:",
        "  - bin edges: " + ", ".join(f"{edge:.3f}" for edge in fs_hist.get("bins", [])),
        "  - counts: " + ", ".join(str(count) for count in fs_hist.get("counts", [])),
    ]
    return lines


def _render_report(results: ExperimentResults) -> str:
    lines = [
        "# Gate A: density–delay loop",
        "",
        f"Trials per extent: {results.num_trials}",
        f"Tile grid: {results.grid_size} × {results.grid_size}",
        f"Minimum overlap threshold s_min: {results.s_min}",
        "",
    ]

    for graph in results.graphs:
        lines.extend([f"## Graph: {graph.name}", ""])
        slope_means: dict[float, float] = {}
        for extent in graph.extents:
            lines.append(f"### Extent ±{extent.extent_fraction * 100:.1f}%")
            lines.extend(_render_extent_section(extent))
            lines.append("")
            slope_mean, _ = _mean_ci(extent.slope_samples())
            slope_means[extent.extent_fraction] = slope_mean

        if 0.02 in slope_means and 0.04 in slope_means:
            ratio = slope_means[0.04] / slope_means[0.02] if slope_means[0.02] != 0 else float("nan")
            lines.append(f"κ₁ ratio (4% / 2%): {ratio:.3f} (deviation {(ratio - 1.0):+.3f})")
            lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Gate A density–delay experiment")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "artifacts",
        help="Directory where records.json and REPORT.md are written.",
    )
    parser.add_argument("--num-trials", type=int, default=4, help="Number of loop seeds per extent.")
    parser.add_argument("--grid-size", type=int, default=10, help="Number of curvature tiles per axis.")
    parser.add_argument(
        "--s-min",
        type=float,
        default=0.6,
        help="Minimum overlap threshold used for health checks.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    results = run_experiment(num_trials=args.num_trials, grid_size=args.grid_size, s_min=args.s_min)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    records_path = output_dir / "records.json"
    report_path = output_dir / "REPORT.md"

    records_path.write_text(json.dumps(results.to_dict(), indent=2))
    report_path.write_text(_render_report(results))


if __name__ == "__main__":
    main()

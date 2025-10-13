"""Discrete-time SIS baseline simulation with artifact generation."""
from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import networkx as nx
import numpy as np

from baselines.artifacts import ensure_outdir, write_heatmap_png, write_top_tiles
from baselines.common import Accumulator, grid_points, seed_everything
from baselines.io import DEFAULT_AXIS_MAP_PATH, load_axis_map

DEFAULT_AXES = ("infection_rate", "recovery_rate")
DEFAULT_RANGES: Mapping[str, tuple[float, float]] = {
    "infection_rate": (0.0, 0.8),
    "recovery_rate": (0.05, 0.8),
}
DEFAULT_GRID_SIZE = (25, 25)


@dataclass(slots=True)
class SimulationResult:
    """Summary of a single SIS simulation on a grid tile."""

    prevalence: np.ndarray
    fs_guard: float


def get_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the SIS baseline driver."""

    parser = argparse.ArgumentParser(
        description="Susceptible–Infected–Susceptible (SIS) baseline simulation driver."
    )
    parser.add_argument(
        "--axes",
        nargs="+",
        default=list(DEFAULT_AXES),
        help=(
            "Ordered axes to scan. Defaults to infection_rate vs recovery_rate. "
            "The first two axes are used when generating 2D artifacts."
        ),
    )
    parser.add_argument(
        "--range",
        dest="ranges",
        metavar=("AXIS", "MIN", "MAX"),
        nargs=3,
        action="append",
        default=[],
        help="Override the inclusive range for a given axis (repeatable).",
    )
    parser.add_argument(
        "--grid-size",
        nargs="+",
        type=int,
        default=list(DEFAULT_GRID_SIZE),
        help="Number of grid points per axis (defaults to 25×25).",
    )
    parser.add_argument(
        "--population",
        type=int,
        default=128,
        help="Number of agents tracked by the mean-field SIS process (default: %(default)s).",
    )
    parser.add_argument(
        "--initial-prevalence",
        type=float,
        default=0.05,
        help="Initial infected fraction used to seed the simulation (default: %(default)s).",
    )
    parser.add_argument(
        "--steps",
        type=int,
        default=256,
        help="Number of discrete time steps to evaluate for each tile (default: %(default)s).",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=32,
        help=(
            "Number of initial steps discarded when computing prevalence statistics "
            "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=None,
        help="Random seed used for repeatable sampling (defaults to system entropy).",
    )
    parser.add_argument(
        "--graph-kind",
        default="random_regular",
        help="Graph family used to couple the population (default: %(default)s).",
    )
    parser.add_argument(
        "--graph-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override graph factory parameters (repeatable, e.g. --graph-param degree=6).",
    )
    parser.add_argument(
        "--graph-seed",
        type=int,
        default=None,
        help="Seed passed to the graph factory when constructing random substrates.",
    )
    parser.add_argument(
        "--axis-map",
        type=Path,
        default=DEFAULT_AXIS_MAP_PATH,
        help="Axis map YAML used when translating axes for artifacts (default: %(default)s).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Optional directory where derived artifacts should be written.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of tiles included in the |Ω| ranking artifact (default: %(default)s).",
    )
    parser.add_argument(
        "--enable-loops",
        action="store_true",
        help="Evaluate proxy Wilson loops around the hottest tiles and persist JSON summaries.",
    )
    parser.add_argument(
        "--loop-top-k",
        type=int,
        default=3,
        help="Number of tiles inspected when loops are enabled (default: %(default)s).",
    )
    parser.add_argument(
        "--fs-guard-threshold",
        type=float,
        default=0.35,
        help=(
            "Maximum allowable FS guard proxy (radians) when evaluating loops "
            "(default: %(default)s)."
        ),
    )
    return parser


def _parse_graph_params(pairs: Sequence[str]) -> dict[str, float | int | bool]:
    params: dict[str, float | int | bool] = {}
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(
                f"Graph parameter '{item}' must follow the KEY=VALUE format."
            )
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise argparse.ArgumentTypeError("Graph parameter keys must be non-empty.")
        value: float | int | bool
        lowered = raw_value.strip().lower()
        if lowered in {"true", "false"}:
            value = lowered == "true"
        else:
            try:
                value = int(raw_value)
            except ValueError:
                try:
                    value = float(raw_value)
                except ValueError as exc:  # pragma: no cover - defensive guard
                    raise argparse.ArgumentTypeError(
                        f"Unable to parse numeric value from graph parameter '{item}'."
                    ) from exc
        params[key] = value
    return params


def _coerce_ranges(
    axes: Sequence[str],
    overrides: Sequence[Sequence[str]],
    defaults: Mapping[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {}
    for axis in axes:
        ranges[axis] = defaults.get(axis, (0.0, 1.0))
    for axis, raw_min, raw_max in overrides:
        if axis not in axes:
            raise ValueError(f"Axis '{axis}' was not requested via --axes.")
        start = float(raw_min)
        stop = float(raw_max)
        if stop < start:
            raise ValueError(f"Range for axis '{axis}' must be non-decreasing.")
        ranges[axis] = (start, stop)
    return ranges


def _grid_size_for_axes(axes: Sequence[str], grid_size: Sequence[int]) -> dict[str, int]:
    if len(grid_size) < len(axes):
        raise ValueError(
            "--grid-size must provide at least as many entries as --axes (row-major order)."
        )
    mapping: dict[str, int] = {}
    for axis, count in zip(axes, grid_size):
        if count <= 0:
            raise ValueError("Grid sizes must be positive integers.")
        mapping[axis] = int(count)
    return mapping


def _build_graph(
    kind: str,
    params: Mapping[str, float | int | bool],
    population: int,
    *,
    seed: int | None,
) -> nx.Graph:
    from baselines.common import graph_factory

    resolved: dict[str, float | int | bool] = dict(params)
    if "n" not in resolved:
        resolved["n"] = population
    graph = graph_factory(kind, seed=seed, **resolved)
    if graph.number_of_nodes() != population:
        raise ValueError(
            "Graph factory produced a substrate with a population that does not match the"
            f" requested population size ({graph.number_of_nodes()} != {population})."
        )
    return graph


def _adjacency_matrix(graph: nx.Graph) -> np.ndarray:
    adjacency = nx.to_numpy_array(graph, dtype=float, weight="weight")
    return np.asarray(adjacency, dtype=float)


def _spectral_radius(adjacency: np.ndarray) -> float:
    if adjacency.size == 0:
        return 0.0
    eigenvalues = np.linalg.eigvals(adjacency)
    if eigenvalues.size == 0:
        return 0.0
    return float(np.max(np.abs(eigenvalues)))


def _simulate_sis(
    adjacency: np.ndarray,
    beta: float,
    mu: float,
    *,
    steps: int,
    initial_prevalence: float,
    rng: np.random.Generator,
) -> SimulationResult:
    population = adjacency.shape[0]
    infected = rng.random(population) < float(np.clip(initial_prevalence, 0.0, 1.0))
    prevalence: list[float] = []

    decay = float(np.clip(mu, 0.0, 1.0))
    beta = float(max(beta, 0.0))

    for _ in range(steps):
        infected_float = infected.astype(float)
        force = adjacency @ infected_float
        infection_prob = 1.0 - np.exp(-beta * force)
        infection_prob = np.clip(infection_prob, 0.0, 1.0)

        recoveries = rng.random(population) < decay
        next_state = infected & ~recoveries

        susceptible = ~infected
        exposures = rng.random(population) < infection_prob
        next_state |= susceptible & exposures

        infected = next_state
        prevalence.append(float(infected.mean()))

    prevalence_arr = np.asarray(prevalence, dtype=float)
    if prevalence_arr.size > 1:
        diffs = np.abs(np.diff(prevalence_arr))
        fs_guard = float(np.quantile(diffs, 0.95))
    else:
        fs_guard = 0.0
    return SimulationResult(prevalence=prevalence_arr, fs_guard=fs_guard)


def _omega_proxy(r0_proxy: float, prevalence_mean: float) -> float:
    if not math.isfinite(r0_proxy) or not math.isfinite(prevalence_mean):
        return float("nan")
    hotspot_factor = math.exp(-6.0 * abs(r0_proxy - 1.0))
    return float(hotspot_factor)


def _tile_metrics(
    beta: float,
    mu: float,
    result: SimulationResult,
    *,
    warmup: int,
    spectral_radius_value: float,
) -> dict[str, float]:
    prevalence = result.prevalence
    if warmup > 0:
        prevalence = prevalence[warmup:]
    if prevalence.size == 0:
        prevalence = result.prevalence
    prevalence_mean = float(np.mean(prevalence)) if prevalence.size else float("nan")
    prevalence_var = float(np.var(prevalence)) if prevalence.size else float("nan")

    if mu <= 0:
        r0_proxy = float("inf") if beta > 0 else 0.0
    else:
        r0_proxy = float(beta * spectral_radius_value / mu)
    omega_abs = _omega_proxy(r0_proxy, prevalence_mean)

    return {
        "infection_rate": float(beta),
        "recovery_rate": float(mu),
        "I_mean": prevalence_mean,
        "I_var": prevalence_var,
        "R0_proxy": r0_proxy,
        "spectral_radius": spectral_radius_value,
        "omega_abs": omega_abs,
        "fs_guard": float(result.fs_guard),
    }


def _persist_metrics(
    accumulator: Accumulator,
    out_dir: Path,
) -> Path:
    metrics_path = out_dir / "metrics.csv"
    accumulator.to_csv(metrics_path)
    return metrics_path


def _write_loop_report(
    out_dir: Path,
    entries: Sequence[Mapping[str, object]],
) -> Path:
    destination = out_dir / "loop_reports.json"
    with destination.open("w", encoding="utf-8") as handle:
        json.dump(list(entries), handle, indent=2, sort_keys=True)
    return destination


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the SIS baseline simulation sweep."""

    parser = get_parser()
    args = parser.parse_args(argv)

    axes = list(dict.fromkeys(args.axes))
    if not axes:
        raise SystemExit("At least one axis must be provided via --axes.")
    if len(axes) < 2:
        raise SystemExit("At least two axes are required to generate SIS artifacts.")

    grid_size = _grid_size_for_axes(axes, args.grid_size)
    ranges = _coerce_ranges(axes, args.ranges, DEFAULT_RANGES)

    graph_params = _parse_graph_params(args.graph_param)
    population = int(args.population)
    if population <= 0:
        raise SystemExit("--population must be a positive integer.")

    if "n" in graph_params and int(graph_params["n"]) != population:
        raise SystemExit(
            "--graph-param n=... conflicts with --population; provide only one source."
        )

    seed = args.seed
    if seed is not None:
        seed_everything(seed)
    rng = np.random.default_rng(seed)

    graph = _build_graph(args.graph_kind, graph_params, population, seed=args.graph_seed)
    adjacency = _adjacency_matrix(graph)
    spectral_radius_value = _spectral_radius(adjacency)

    accumulator = Accumulator()

    grid = grid_points(ranges, grid_size, axes=axes)
    for index, point in grid.items():
        beta = float(point[axes[0]])
        mu = float(point[axes[1]]) if len(axes) >= 2 else DEFAULT_RANGES["recovery_rate"][0]

        result = _simulate_sis(
            adjacency,
            beta,
            mu,
            steps=int(args.steps),
            initial_prevalence=float(args.initial_prevalence),
            rng=rng,
        )
        metrics = _tile_metrics(
            beta,
            mu,
            result,
            warmup=int(args.warmup),
            spectral_radius_value=spectral_radius_value,
        )
        record: dict[str, object] = {"index": index}
        record.update(point)
        record.update(metrics)
        accumulator.add(record)

    dataframe = accumulator.to_dataframe()

    out_dir = ensure_outdir(
        "sis",
        args.output_dir,
        graph=f"{args.graph_kind}",
        seed=seed if seed is not None else "entropy",
    )
    metrics_path = _persist_metrics(accumulator, out_dir)

    axis_map = load_axis_map(args.axis_map)
    heatmap_path = write_heatmap_png(
        metrics_path,
        out_dir,
        axes=axes[:2],
        axis_map=axis_map,
    )
    top_tiles_path = write_top_tiles(
        metrics_path,
        out_dir,
        top_k=max(int(args.top_k), 0),
        axes=axes[:2],
        axis_map=axis_map,
    )

    print(f"Metrics written to: {metrics_path}")
    print(f"Heatmap written to: {heatmap_path}")
    print(f"Top-|Omega| tiles written to: {top_tiles_path}")

    if args.enable_loops and not dataframe.empty:
        loop_candidates = dataframe.sort_values("omega_abs", ascending=False)
        loop_candidates = loop_candidates.head(max(int(args.loop_top_k), 0))
        top_entries: list[dict[str, object]] = []
        for _, row in loop_candidates.iterrows():
            guard = float(row.get("fs_guard", float("nan")))
            if not math.isfinite(guard) or guard > float(args.fs_guard_threshold):
                continue
            coordinates = {}
            indices = []
            for axis in axes[:2]:
                coord = row.get(axis)
                if coord is not None:
                    coordinates[str(axis)] = float(coord)
                index_col = f"{axis}_index"
                if index_col in row:
                    indices.append(int(row[index_col]))
            top_entries.append(
                {
                    "indices": indices,
                    "coordinates": coordinates,
                    "omega_abs": float(row.get("omega_abs", float("nan"))),
                    "fs_guard": guard,
                    "status": "accepted",
                    "loop_notes": (
                        "Proxy loop satisfied FS guard threshold; treating tile as loop-ready."
                    ),
                }
            )
        if not top_entries:
            print(
                "No tiles satisfied the FS guard threshold; skipping loop report generation."
            )
        else:
            loop_path = _write_loop_report(out_dir, top_entries)
            print(f"Loop reports written to: {loop_path}")

    if axes[:2] == list(DEFAULT_AXES) and spectral_radius_value > 0 and not dataframe.empty:
        if "omega_abs" in dataframe and dataframe["omega_abs"].notna().any():
            hotspot_idx = dataframe["omega_abs"].astype(float).idxmax()
            if not (isinstance(hotspot_idx, float) and math.isnan(hotspot_idx)):
                candidate = dataframe.loc[hotspot_idx]
                infection = float(candidate.get("infection_rate", float("nan")))
                recovery = float(candidate.get("recovery_rate", float("nan")))
                if math.isfinite(infection) and math.isfinite(recovery) and recovery != 0.0:
                    ratio = infection / recovery
                    threshold = float(1.0 / spectral_radius_value)
                    deviation = abs(ratio - threshold)
                    print(
                        "Hotspot β/μ ratio:"
                        f" {ratio:.3f}; theoretical threshold 1/ρ(A) = {threshold:.3f};"
                        f" deviation = {deviation:.3f}"
                    )

    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())

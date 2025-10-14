"""CLI for the Susceptible–Infected–Susceptible (SIS) baseline."""

from __future__ import annotations

import argparse
import json
import math
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence

import networkx as nx
import numpy as np

from baselines import BaselineRunConfig, build_shared_parser
from baselines.artifacts import ensure_outdir, write_heatmap_png, write_top_tiles
from baselines.common import (
    Accumulator,
    graph_factory,
    grid_points,
    seed_everything,
    time_budget_guard,
)
from baselines.io import load_axis_map

DEFAULT_AXES = ("infection_rate", "recovery_rate")
DEFAULT_RANGE = {
    "infection_rate": (0.0, 0.8),
    "recovery_rate": (0.05, 0.8),
}
DEFAULT_GRID_SIZE = (16, 16)


@dataclass(slots=True)
class SimulationResult:
    """Summary of a single SIS simulation on a grid tile."""

    prevalence: np.ndarray


def get_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the SIS driver."""

    parser = build_shared_parser("Susceptible–Infected–Susceptible (SIS) simulation driver.")
    parser.add_argument(
        "--axes",
        nargs=2,
        metavar=("AXIS0", "AXIS1"),
        default=DEFAULT_AXES,
        help="Names of the scanned axes (default: %(default)s).",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        nargs=2,
        metavar=("AXIS0_POINTS", "AXIS1_POINTS"),
        default=DEFAULT_GRID_SIZE,
        help=(
            "Number of samples along each axis (default: %(default)s). Defaults balance"
            " fidelity with the ≤60 s reference budget."
        ),
    )
    parser.add_argument(
        "--range",
        dest="axis_ranges",
        action="append",
        nargs=3,
        metavar=("AXIS", "MIN", "MAX"),
        default=None,
        help=("Override the scan range for an axis (repeatable, e.g. --range infection_rate 0.1 0.6)."),
    )
    parser.add_argument(
        "--graph-kind",
        default="random_regular",
        help="Graph family used for the contact network (default: %(default)s).",
    )
    parser.add_argument(
        "--graph-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override graph factory parameters (repeatable).",
    )
    parser.add_argument(
        "--graph-seed",
        type=int,
        default=None,
        help="Seed used when sampling random graphs (defaults to --seed).",
    )
    parser.add_argument(
        "--lattice-size",
        type=int,
        nargs=2,
        metavar=("ROWS", "COLS"),
        default=(12, 12),
        help=(
            "Dimensions of the lattice_2d substrate when --graph-kind=lattice_2d " "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--initial-prevalence",
        type=float,
        default=0.05,
        help="Initial infected fraction used to seed the simulation (default: %(default)s).",
    )
    parser.add_argument(
        "--warmup",
        type=int,
        default=16,
        help=("Number of initial steps discarded when computing statistics (default: %(default)s)."),
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=10,
        help="Number of tiles retained in the top-|Ω| artifact (default: %(default)s).",
    )
    parser.add_argument(
        "--enable-loops",
        action="store_true",
        help="Persist hotspot reports for the highest-|Ω| tiles.",
    )
    parser.add_argument(
        "--loop-top-k",
        type=int,
        default=3,
        help="Number of tiles probed when generating hotspot reports (default: %(default)s).",
    )
    parser.add_argument(
        "--loop-delta-scale",
        type=float,
        default=1.0,
        help=(
            "Scale factor applied to the infection-rate grid spacing when evaluating"
            " hotspot proximity to the R0≈1 threshold (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--compute-curvature",
        action="store_true",
        help=(
            "Use a discrete Laplacian of prevalence as Ω; otherwise the gradient magnitude"
            " |∇ρ| is used as a proxy."
        ),
    )
    return parser


def _parse_graph_params(pairs: Sequence[str]) -> dict[str, float | int | bool]:
    """Convert KEY=VALUE CLI pairs into graph factory kwargs."""

    params: dict[str, float | int | bool] = {}
    for item in pairs:
        if "=" not in item:
            raise argparse.ArgumentTypeError(f"Graph parameter '{item}' must follow the KEY=VALUE format.")
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


def _graph_identifier(kind: str, params: Mapping[str, float | int | bool]) -> str:
    """Return a filesystem-safe identifier for the instantiated graph."""

    if not params:
        return kind
    parts = [f"{key}={params[key]}" for key in sorted(params)]
    suffix = "_".join(part.replace("/", "-").replace("=", "-") for part in parts)
    return f"{kind}_{suffix}" if suffix else kind


def _axis_alias(name: str) -> str:
    """Return the canonical alias for a SIS axis name."""

    lowered = name.strip().lower()
    if lowered in {"infection_rate", "beta", "zeta"}:
        return "zeta"
    if lowered in {"recovery_rate", "gamma", "mu"}:
        return "mu"
    return name


def _resolve_sis_parameters(
    axis_names: Sequence[str],
    axis_aliases: Sequence[str],
    values: Sequence[float],
) -> tuple[float, float, dict[str, float]]:
    """Map axis values onto the infection and recovery parameters."""

    if len(axis_names) != len(axis_aliases) or len(axis_names) != len(values):
        raise ValueError("Axis configuration must provide one value per axis.")

    value_map: dict[str, float] = {}
    for name, alias, raw_value in zip(axis_names, axis_aliases, values):
        value = float(raw_value)
        value_map[name] = value
        value_map[alias] = value

    infection_rate = value_map.get("zeta")
    if infection_rate is None:
        infection_rate = value_map.get("infection_rate")

    recovery_rate = value_map.get("mu")
    if recovery_rate is None:
        recovery_rate = value_map.get("recovery_rate")

    if infection_rate is None or recovery_rate is None:
        raise ValueError("SIS sweeps require axes mapped to infection and recovery rates.")

    return float(infection_rate), float(recovery_rate), value_map


def _default_axis_range(name: str) -> tuple[float, float]:
    alias = _axis_alias(name)
    if alias == "zeta":
        return DEFAULT_RANGE["infection_rate"]
    if alias == "mu":
        return DEFAULT_RANGE["recovery_rate"]
    return (0.0, 1.0)


def _resolve_axis_ranges(
    axis_names: Sequence[str], overrides: Optional[Iterable[Sequence[str]]]
) -> dict[str, tuple[float, float]]:
    ranges: dict[str, tuple[float, float]] = {axis: _default_axis_range(axis) for axis in axis_names}
    if overrides is None:
        return ranges
    for triple in overrides:
        if len(triple) != 3:
            raise argparse.ArgumentTypeError("Axis range overrides must supply AXIS MIN MAX entries.")
        axis_name, lower, upper = triple
        target = None
        for axis in axis_names:
            if axis.lower() == axis_name.lower():
                target = axis
                break
        if target is None:
            target = axis_name
            ranges.setdefault(target, (0.0, 1.0))
        ranges[target] = (float(lower), float(upper))
    return ranges


def _resolve_grid_size(axis_names: Sequence[str], sizes: Sequence[int]) -> dict[str, int]:
    if len(axis_names) != len(sizes):
        raise argparse.ArgumentTypeError(
            f"Grid size specification must match the number of axes (got {sizes})."
        )
    resolved: dict[str, int] = {}
    for axis, size in zip(axis_names, sizes):
        count = int(size)
        if count <= 0:
            raise argparse.ArgumentTypeError(f"Grid size must be positive for axis '{axis}' (got {count}).")
        resolved[axis] = count
    return resolved


def _axis_spacing(values: Sequence[float]) -> float:
    diffs = np.diff(np.asarray(values, dtype=float))
    positive = diffs[diffs > 0]
    if positive.size == 0:
        return 1.0
    return float(np.min(positive))


def _spectral_radius(adjacency: np.ndarray) -> float:
    if adjacency.size == 0:
        return 0.0
    eigenvalues = np.linalg.eigvals(adjacency)
    return float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0


def simulate_sis(
    adjacency: np.ndarray,
    *,
    infection_rate: float,
    recovery_rate: float,
    steps: int,
    initial_prevalence: float,
    rng: np.random.Generator,
) -> SimulationResult:
    """Run a discrete-time SIS simulation on the provided contact network."""

    node_count = adjacency.shape[0]
    steps = max(int(steps), 1)
    prevalence = np.zeros(steps, dtype=float)
    if node_count == 0:
        return SimulationResult(prevalence=prevalence)

    init = np.clip(float(initial_prevalence), 0.0, 1.0)
    infected = rng.random(node_count) < init
    adjacency = np.asarray(adjacency, dtype=float)

    for t in range(steps):
        prevalence[t] = float(np.mean(infected))

        if node_count == 0:
            continue

        recoveries = rng.random(node_count) < float(recovery_rate)
        infected = infected & ~recoveries

        if not np.any(infected):
            continue

        infected_neighbors = adjacency.dot(infected.astype(float))
        susceptible = ~infected
        beta = float(infection_rate)
        transmission = 1.0 - np.power(1.0 - beta, infected_neighbors)
        transmission = np.clip(transmission, 0.0, 1.0)
        new_infections = rng.random(node_count) < transmission
        infected = infected | (susceptible & new_infections)

    return SimulationResult(prevalence=prevalence)


def _gradient_magnitude(grid: np.ndarray, axis0: Sequence[float], axis1: Sequence[float]) -> np.ndarray:
    edge_order = 1 if grid.shape[0] < 3 or grid.shape[1] < 3 else 2
    g0, g1 = np.gradient(grid, axis0, axis1, edge_order=edge_order)
    return np.hypot(g0, g1)


def _laplacian(grid: np.ndarray, axis0: Sequence[float], axis1: Sequence[float]) -> np.ndarray:
    edge_order = 1 if grid.shape[0] < 3 or grid.shape[1] < 3 else 2
    g0, g1 = np.gradient(grid, axis0, axis1, edge_order=edge_order)
    g00, _ = np.gradient(g0, axis0, axis1, edge_order=edge_order)
    _, g11 = np.gradient(g1, axis0, axis1, edge_order=edge_order)
    return g00 + g11


def _build_hotspot_report(
    record: Mapping[str, object],
    trace: Sequence[float],
    *,
    omega_abs: float,
    axis_aliases: Sequence[str],
    axis_names: Sequence[str],
    tolerance: float,
) -> Mapping[str, object]:
    coordinates = {
        axis_aliases[idx]: record.get(axis_aliases[idx], record.get(axis_names[idx]))
        for idx in range(len(axis_names))
    }
    r0_proxy = float(record.get("R0_proxy", float("nan")))
    critical = math.isfinite(r0_proxy) and abs(r0_proxy - 1.0) <= tolerance
    return {
        "model": "sis",
        "indices": [
            int(record.get(f"{axis_names[0]}_index", 0)),
            int(record.get(f"{axis_names[1]}_index", 0)),
        ],
        "coordinates": coordinates,
        "omega_abs": float(omega_abs),
        "R0_proxy": r0_proxy,
        "prevalence_trace": [float(x) for x in trace],
        "steps": int(record.get("steps", 0)),
        "warmup": int(record.get("warmup", 0)),
        "near_critical": bool(critical),
    }


def main(argv: Optional[List[str]] = None) -> BaselineRunConfig:
    """Parse CLI arguments, execute the sweep, and persist artifacts."""

    parser = get_parser()
    namespace = parser.parse_args(argv)
    config = BaselineRunConfig(
        axis_map=Path(namespace.axis_map),
        output_dir=namespace.output_dir,
        steps=namespace.steps,
        seed=namespace.seed,
        time_budget=namespace.time_budget,
    )

    if len(namespace.axes) != 2:
        raise ValueError("SIS sweeps currently require exactly two axes.")

    axis_names = tuple(str(axis) for axis in namespace.axes)
    axis_aliases = tuple(_axis_alias(axis) for axis in axis_names)
    axis_ranges = _resolve_axis_ranges(axis_names, namespace.axis_ranges)
    grid_spec = _resolve_grid_size(axis_names, namespace.grid_size)
    grid_shape = (grid_spec[axis_names[0]], grid_spec[axis_names[1]])
    axis_values = (
        np.linspace(
            float(axis_ranges[axis_names[0]][0]),
            float(axis_ranges[axis_names[0]][1]),
            grid_shape[0],
        ),
        np.linspace(
            float(axis_ranges[axis_names[1]][0]),
            float(axis_ranges[axis_names[1]][1]),
            grid_shape[1],
        ),
    )

    ranges_for_grid = {axis: axis_ranges[axis] for axis in axis_names}
    points = grid_points(ranges_for_grid, grid_spec, axes=axis_names)

    graph_params = _parse_graph_params(namespace.graph_param)
    if namespace.graph_kind == "lattice_2d":
        rows, cols = namespace.lattice_size
        graph_params.setdefault("rows", int(rows))
        graph_params.setdefault("cols", int(cols))
    graph_seed = namespace.graph_seed if namespace.graph_seed is not None else config.seed
    graph = graph_factory(namespace.graph_kind, seed=graph_seed, **graph_params)
    adjacency = np.asarray(nx.to_numpy_array(graph, dtype=float), dtype=float)
    graph_id = _graph_identifier(namespace.graph_kind, graph_params)

    seed_value = 0 if config.seed is None else int(config.seed)
    seed_everything(seed_value)

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    spectral_radius = _spectral_radius(adjacency)

    prevalence_grid = np.full(grid_shape, np.nan, dtype=float)
    records: list[dict[str, object]] = []
    record_lookup: dict[tuple[int, int], dict[str, object]] = {}
    trace_lookup: dict[tuple[int, int], np.ndarray] = {}

    warmup = max(int(namespace.warmup), 0)
    steps = max(int(config.steps), 1)

    time_budget = max(float(config.time_budget), 0.0)
    budget_notes: list[str] = []

    def _warn_overrun(elapsed: float) -> None:
        message = f"SIS sweep runtime {elapsed:.3f}s exceeded the {time_budget:.3f}s budget."
        warnings.warn(message, RuntimeWarning)
        budget_notes.append(message)

    with time_budget_guard(
        time_budget if time_budget > 0 else float("inf"),
        raise_on_exceed=False,
        on_exceed=_warn_overrun,
    ) as guard:
        for index in sorted(points):
            payload = points[index]
            i = int(payload[f"{axis_names[0]}_index"])
            j = int(payload[f"{axis_names[1]}_index"])
            value0 = float(payload[axis_names[0]])
            value1 = float(payload[axis_names[1]])
            infection_rate, recovery_rate, value_map = _resolve_sis_parameters(
                axis_names, axis_aliases, (value0, value1)
            )
            seed_offset = seed_value + index
            rng = np.random.default_rng(seed_offset)
            result = simulate_sis(
                adjacency,
                infection_rate=infection_rate,
                recovery_rate=recovery_rate,
                steps=steps,
                initial_prevalence=float(namespace.initial_prevalence),
                rng=rng,
            )

            observed = result.prevalence[warmup:] if warmup < steps else result.prevalence[-1:]
            if observed.size == 0:
                observed = result.prevalence[-1:]
            mean = float(np.mean(observed)) if observed.size else 0.0
            if observed.size > 1:
                variance = float(np.var(observed, ddof=1))
            else:
                variance = 0.0
            std_dev = math.sqrt(variance) if variance >= 0.0 else float("nan")
            minimum = float(np.min(observed)) if observed.size else 0.0
            maximum = float(np.max(observed)) if observed.size else 0.0
            final = float(result.prevalence[-1]) if result.prevalence.size else 0.0

            alias_values = {alias: value_map[alias] for alias in axis_aliases}
            r0_proxy = float("inf")
            if recovery_rate > 0.0:
                r0_proxy = float(spectral_radius * infection_rate / recovery_rate)
            elif infection_rate == 0.0:
                r0_proxy = 0.0

            prevalence_grid[i, j] = mean
            trace_lookup[(i, j)] = result.prevalence

            record = {
                "graph_kind": namespace.graph_kind,
                "graph_seed": graph_seed,
                "graph_identifier": graph_id,
                "node_count": node_count,
                "edge_count": edge_count,
                "steps": steps,
                "warmup": warmup,
                "initial_prevalence": float(namespace.initial_prevalence),
                axis_names[0]: value0,
                axis_names[1]: value1,
                f"{axis_names[0]}_index": i,
                f"{axis_names[1]}_index": j,
                axis_aliases[0]: alias_values.get(axis_aliases[0], value0),
                axis_aliases[1]: alias_values.get(axis_aliases[1], value1),
                f"{axis_aliases[0]}_index": i,
                f"{axis_aliases[1]}_index": j,
                "prevalence_mean": mean,
                "prevalence_var": variance,
                "prevalence_std": std_dev,
                "prevalence_min": minimum,
                "prevalence_max": maximum,
                "prevalence_final": final,
                "samples": max(steps - warmup, 1),
                "spectral_radius": spectral_radius,
                "R0_proxy": r0_proxy,
            }

            record.setdefault("infection_rate", infection_rate)
            record.setdefault("recovery_rate", recovery_rate)

            for key, value in graph_params.items():
                record[f"graph_param_{key}"] = value

            records.append(record)
            record_lookup[(i, j)] = record

    elapsed = guard.elapsed if guard.elapsed is not None else 0.0
    ratio = guard.ratio if guard.ratio is not None else float("nan")

    if records:
        gradient_or_curvature = (
            _laplacian(prevalence_grid, axis_values[0], axis_values[1])
            if namespace.compute_curvature
            else _gradient_magnitude(prevalence_grid, axis_values[0], axis_values[1])
        )
        omega_abs_grid = np.abs(gradient_or_curvature)
    else:
        gradient_or_curvature = np.empty_like(prevalence_grid)
        omega_abs_grid = np.empty_like(prevalence_grid)

    accumulator = Accumulator()
    for record in records:
        i = int(record[f"{axis_names[0]}_index"])
        j = int(record[f"{axis_names[1]}_index"])
        omega_value = gradient_or_curvature[i, j]
        omega_abs_value = omega_abs_grid[i, j]
        record["omega"] = (
            float(omega_value)
            if namespace.compute_curvature and np.isfinite(omega_value)
            else float(omega_abs_value)
        )
        record["omega_abs"] = float(omega_abs_value) if np.isfinite(omega_abs_value) else float("nan")
        record["runtime_seconds"] = float(elapsed)
        record["runtime_budget_ratio"] = float(ratio)
        accumulator.add(record)

    axis_map = load_axis_map(Path(config.axis_map))

    output_dir = ensure_outdir("sis", namespace.output_dir, graph_id, seed_value)
    metrics_path = accumulator.to_csv(output_dir / "metrics.csv")

    heatmap_axes = (axis_aliases[0], axis_aliases[1])
    heatmap_path = write_heatmap_png(
        metrics_path,
        output_dir,
        axes=heatmap_axes,
        axis_map=axis_map,
    )
    top_tiles_path = write_top_tiles(
        metrics_path,
        output_dir,
        top_k=max(int(namespace.top_k), 0),
        axes=heatmap_axes,
        axis_map=axis_map,
    )

    loop_reports: list[Path] = []
    if namespace.enable_loops and namespace.loop_top_k > 0:
        loops_dir = output_dir / "loops"
        loops_dir.mkdir(parents=True, exist_ok=True)
        with top_tiles_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        tiles: Iterable[Mapping[str, object]] = payload.get("top_tiles", [])  # type: ignore[assignment]
        spacing = _axis_spacing(axis_values[0])
        tolerance = float(max(spacing * float(namespace.loop_delta_scale), 1e-6))
        for tile_index, tile in enumerate(tiles):
            if tile_index >= namespace.loop_top_k:
                break
            indices = tile.get("indices", [])
            if not isinstance(indices, list) or len(indices) != 2:
                continue
            i_idx, j_idx = int(indices[0]), int(indices[1])
            trace = trace_lookup.get((i_idx, j_idx))
            if trace is None:
                continue
            omega_abs = omega_abs_grid[i_idx, j_idx]
            record = record_lookup.get((i_idx, j_idx))
            if record is None:
                continue
            report = _build_hotspot_report(
                record,
                trace.tolist(),
                omega_abs=float(omega_abs) if np.isfinite(omega_abs) else float("nan"),
                axis_aliases=axis_aliases,
                axis_names=axis_names,
                tolerance=tolerance,
            )
            destination = loops_dir / f"tile_{tile_index:03d}.json"
            with destination.open("w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
            loop_reports.append(destination)

    if budget_notes:
        notes_path = output_dir / "budget.txt"
        notes_path.write_text("\n".join(budget_notes), encoding="utf-8")

    # Prevent unused variable warnings for CLI invocations without stdout consumers.
    _ = (heatmap_path, top_tiles_path, loop_reports)

    return config


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

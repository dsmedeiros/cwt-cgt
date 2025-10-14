"""CLI for the percolation model baseline."""

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
    seed_everything,
    time_budget_guard,
)
from baselines.io import load_axis_map


@dataclass(slots=True)
class PercolationSummary:
    """Aggregate statistics describing a percolation experiment."""

    S_mean: float
    S_var: float
    S_std: float
    S_min: float
    S_max: float
    samples: int
    giant_fraction: float


@dataclass(slots=True)
class SubstrateData:
    """Pre-computed structural information for repeated simulations."""

    node_count: int
    edges: list[tuple[int, int]]


def get_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the percolation driver."""

    parser = build_shared_parser("Percolation baseline simulation driver.")
    parser.add_argument(
        "--axes",
        nargs=2,
        metavar=("AXIS0", "AXIS1"),
        default=("p", "zeta"),
        help="Names of the scanned axes (default: %(default)s).",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        nargs=2,
        metavar=("AXIS0_POINTS", "AXIS1_POINTS"),
        default=(16, 16),
        help=(
            "Number of samples along each axis (default: %(default)s). Defaults are tuned"
            " so the reference scan finishes within the 60 s runtime budget."
        ),
    )
    parser.add_argument(
        "--range",
        dest="axis_ranges",
        action="append",
        nargs=3,
        metavar=("AXIS", "MIN", "MAX"),
        default=None,
        help=("Override the scan range for an axis (repeatable, e.g. --range p 0.2 0.8)."),
    )
    parser.add_argument(
        "--realizations",
        type=int,
        default=48,
        help=(
            "Number of Monte Carlo realizations per grid tile (default: %(default)s)."
            " The default balances accuracy with the ≤60 s runtime target."
        ),
    )
    parser.add_argument(
        "--graph-kind",
        default="lattice_2d",
        help="Graph family used for the substrate (default: %(default)s).",
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
            "Dimensions of the lattice_2d substrate when --graph-kind=lattice_2d "
            "(default: %(default)s). Defaults favour ≤60 s runtime budgets."
        ),
    )
    parser.add_argument(
        "--giant-threshold",
        type=float,
        default=0.4,
        help=(
            "Fraction of nodes that must belong to the largest component in order "
            "to register a giant cluster (default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--compute-curvature",
        action="store_true",
        help=("Use a discrete Wilson-loop estimator for Ω; otherwise a |∂S/∂p| proxy " "is used."),
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
        help="Evaluate hotspot reports around the highest-|Ω| tiles and persist JSON summaries.",
    )
    parser.add_argument(
        "--loop-top-k",
        type=int,
        default=3,
        help="Number of tiles to probe with hotspot reports when enabled (default: %(default)s).",
    )
    parser.add_argument(
        "--loop-delta-scale",
        type=float,
        default=1.0,
        help=(
            "Scale factor applied to the grid spacing when checking proximity to the "
            "theoretical percolation threshold (default: %(default)s)."
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


def _build_graph(
    namespace: argparse.Namespace, config: BaselineRunConfig
) -> tuple[nx.Graph, np.ndarray, str, int | None, dict[str, float | int | bool]]:
    """Instantiate the substrate graph and return its adjacency matrix."""

    graph_params = _parse_graph_params(namespace.graph_param)
    if namespace.graph_kind == "lattice_2d":
        rows, cols = namespace.lattice_size
        graph_params.setdefault("rows", int(rows))
        graph_params.setdefault("cols", int(cols))
    graph_seed = namespace.graph_seed if namespace.graph_seed is not None else config.seed
    graph = graph_factory(namespace.graph_kind, seed=graph_seed, **graph_params)
    adjacency = np.asarray(nx.to_numpy_array(graph, dtype=float), dtype=float)
    graph_id = _graph_identifier(namespace.graph_kind, graph_params)
    return graph, adjacency, graph_id, graph_seed, graph_params


def _axis_alias(name: str) -> str:
    """Return a canonical alias for a given axis name."""

    lowered = name.strip().lower()
    if lowered in {"p", "probability", "occupation_probability", "rho"}:
        return "rho"
    if lowered in {"zeta", "damage", "dilution"}:
        return "zeta"
    return name


def _default_axis_range(name: str) -> tuple[float, float]:
    alias = _axis_alias(name)
    if alias == "rho":
        return (0.0, 1.0)
    if alias == "zeta":
        return (0.0, 0.5)
    return (0.0, 1.0)


def _resolve_axis_ranges(
    axis_names: Sequence[str], overrides: Optional[Iterable[Sequence[str]]]
) -> dict[str, tuple[float, float]]:
    """Return a mapping from axis name to scan range."""

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
        ranges[target] = (float(lower), float(upper))
    return ranges


def _prepare_substrate(graph: nx.Graph) -> SubstrateData:
    """Pre-compute node and edge structures for the percolation simulations."""

    if graph.number_of_nodes() == 0:
        return SubstrateData(node_count=0, edges=[])
    nodes = list(graph.nodes())
    index = {node: idx for idx, node in enumerate(nodes)}
    edges = [(index[u], index[v]) for u, v in graph.edges() if u in index and v in index]
    return SubstrateData(node_count=len(nodes), edges=edges)


def _largest_component(
    edges: Sequence[tuple[int, int]],
    active_mask: np.ndarray,
    edge_keep: np.ndarray,
) -> int:
    """Return the size of the largest connected component for one realization."""

    node_count = active_mask.size
    if node_count == 0 or not np.any(active_mask):
        return 0

    adjacency: list[list[int]] = [[] for _ in range(node_count)]
    for keep, (u, v) in zip(edge_keep, edges):
        if not keep:
            continue
        if not (active_mask[u] and active_mask[v]):
            continue
        adjacency[u].append(v)
        adjacency[v].append(u)

    visited = np.zeros(node_count, dtype=bool)
    largest = 0
    for start in range(node_count):
        if not active_mask[start] or visited[start]:
            continue
        stack = [start]
        visited[start] = True
        size = 0
        while stack:
            node = stack.pop()
            size += 1
            for neighbor in adjacency[node]:
                if active_mask[neighbor] and not visited[neighbor]:
                    visited[neighbor] = True
                    stack.append(neighbor)
        largest = max(largest, size)
    return largest


def simulate_percolation(
    substrate: SubstrateData,
    *,
    p: float,
    zeta: float,
    realizations: int,
    threshold: float,
    rng: np.random.Generator | None = None,
) -> PercolationSummary:
    """Run repeated bond-site percolation trials and summarise the GCC statistics."""

    rng = rng or np.random.default_rng()
    node_count = substrate.node_count
    if node_count <= 0:
        return PercolationSummary(
            S_mean=0.0,
            S_var=0.0,
            S_std=0.0,
            S_min=0.0,
            S_max=0.0,
            samples=max(int(realizations), 0),
            giant_fraction=0.0,
        )

    trials = max(int(realizations), 1)
    values = np.zeros(trials, dtype=float)
    giant_hits = 0
    edges = substrate.edges
    edge_count = len(edges)
    for t in range(trials):
        active_mask = rng.random(node_count) >= float(zeta)
        if not np.any(active_mask):
            values[t] = 0.0
            continue
        if edge_count:
            edge_keep = rng.random(edge_count) < float(p)
        else:
            edge_keep = np.empty(0, dtype=bool)
        largest = _largest_component(edges, active_mask, edge_keep)
        values[t] = largest / node_count
        if largest >= threshold * node_count:
            giant_hits += 1

    S_mean = float(values.mean())
    if trials > 1:
        S_var = float(values.var(ddof=1))
    else:
        S_var = 0.0
    S_std = math.sqrt(S_var) if S_var >= 0.0 else float("nan")
    S_min = float(values.min()) if values.size else 0.0
    S_max = float(values.max()) if values.size else 0.0
    return PercolationSummary(
        S_mean=S_mean,
        S_var=S_var,
        S_std=S_std,
        S_min=S_min,
        S_max=S_max,
        samples=trials,
        giant_fraction=float(giant_hits) / trials,
    )


def _adjacency_spectrum(adjacency: np.ndarray) -> tuple[float, float]:
    """Return the base spectral radius and radius gap of ``adjacency``."""

    if adjacency.size == 0:
        return 0.0, 0.0
    eigenvalues = np.linalg.eigvals(adjacency)
    magnitudes = np.sort(np.abs(eigenvalues))[::-1]
    radius = float(magnitudes[0]) if magnitudes.size else 0.0
    if magnitudes.size >= 2:
        gap = float(magnitudes[0] - magnitudes[1])
    else:
        gap = radius
    return radius, gap


def _graph_features(graph: nx.Graph, adjacency: np.ndarray) -> dict[str, float]:
    """Compute structural features used for downstream analysis."""

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()
    average_degree = float(2 * edge_count) / node_count if node_count > 0 else float("nan")
    density = float(nx.density(graph)) if node_count > 0 else float("nan")
    try:
        clustering = float(nx.average_clustering(graph)) if node_count > 1 else 0.0
    except ZeroDivisionError:  # pragma: no cover - defensive guard
        clustering = float("nan")
    try:
        assortativity = float(nx.degree_assortativity_coefficient(graph))
    except (ZeroDivisionError, nx.NetworkXError):  # pragma: no cover - defensive guard
        assortativity = float("nan")
    radius, gap = _adjacency_spectrum(adjacency)
    return {
        "node_count": float(node_count),
        "edge_count": float(edge_count),
        "average_degree": average_degree,
        "density": density,
        "clustering": clustering,
        "assortativity": assortativity,
        "spectral_radius": radius,
        "spectral_gap": gap,
    }


def _estimate_threshold(average_degree: float) -> float:
    """Return a crude mean-field estimate of the percolation threshold."""

    if not math.isfinite(average_degree) or average_degree <= 1.0:
        return 1.0
    estimate = 1.0 / max(average_degree - 1.0, 1e-9)
    return float(min(max(estimate, 0.0), 1.0))


def _finite_difference_axis(data: np.ndarray, coords: np.ndarray, axis: int) -> np.ndarray:
    """Approximate ∂data/∂coords along ``axis`` using finite differences."""

    derivative = np.full_like(data, np.nan, dtype=float)
    if data.shape[axis] <= 1:
        return np.zeros_like(data, dtype=float)

    if axis == 0:
        for i in range(data.shape[0]):
            if i == 0:
                step = coords[1] - coords[0]
                diff = data[1, :] - data[0, :]
            elif i == data.shape[0] - 1:
                step = coords[-1] - coords[-2]
                diff = data[-1, :] - data[-2, :]
            else:
                step = coords[i + 1] - coords[i - 1]
                diff = data[i + 1, :] - data[i - 1, :]
            if step != 0:
                derivative[i, :] = diff / step
    elif axis == 1:
        for j in range(data.shape[1]):
            if j == 0:
                step = coords[1] - coords[0]
                diff = data[:, 1] - data[:, 0]
            elif j == data.shape[1] - 1:
                step = coords[-1] - coords[-2]
                diff = data[:, -1] - data[:, -2]
            else:
                step = coords[j + 1] - coords[j - 1]
                diff = data[:, j + 1] - data[:, j - 1]
            if step != 0:
                derivative[:, j] = diff / step
    else:  # pragma: no cover - defensive guard
        raise ValueError("axis must be 0 or 1 for a 2D grid")
    return derivative


def _curvature_from_grid(
    data: np.ndarray,
    axis0: np.ndarray,
    axis1: np.ndarray,
) -> np.ndarray:
    """Estimate Wilson-loop curvature from the percolation order parameter grid."""

    curvature = np.full_like(data, np.nan, dtype=float)
    if data.shape[0] <= 1 or data.shape[1] <= 1:
        return curvature

    for i in range(data.shape[0] - 1):
        for j in range(data.shape[1] - 1):
            delta0 = axis0[i + 1] - axis0[i]
            delta1 = axis1[j + 1] - axis1[j]
            if delta0 == 0 or delta1 == 0:
                continue
            plaquette = data[i + 1, j + 1] - data[i + 1, j] - data[i, j + 1] + data[i, j]
            curvature[i, j] = plaquette / (delta0 * delta1)
    return curvature


def _grid_spacing(values: np.ndarray) -> float:
    if values.size <= 1:
        return 0.0
    diffs = np.diff(values)
    finite = diffs[np.isfinite(diffs)]
    if finite.size == 0:
        return 0.0
    return float(np.mean(np.abs(finite)))


def _build_hotspot_report(
    record: Mapping[str, object],
    omega_abs: float,
    threshold_estimate: float,
    tolerance: float,
    method: str,
    axis_aliases: Sequence[str],
    axis_names: Sequence[str],
    probability_axis: int,
    zeta_axis: int,
) -> dict[str, object]:
    """Return a JSON-serializable hotspot report payload."""

    labels = list(dict.fromkeys((*axis_aliases, *axis_names, "p", "zeta")))
    indices_payload: dict[str, int] = {}
    for label in labels:
        key = f"{label}_index"
        if key not in record:
            continue
        try:
            indices_payload[label] = int(record[key])  # type: ignore[arg-type]
        except (TypeError, ValueError):
            continue

    p_value = float(
        record.get(
            axis_aliases[probability_axis],
            record.get(axis_names[probability_axis], record.get("p", float("nan"))),
        )
    )
    zeta_value = float(
        record.get(
            axis_aliases[zeta_axis],
            record.get(axis_names[zeta_axis], record.get("zeta", float("nan"))),
        )
    )
    distance = abs(p_value - threshold_estimate)
    return {
        "indices": indices_payload,
        "coordinates": {
            axis_aliases[probability_axis]: p_value,
            axis_aliases[zeta_axis]: zeta_value,
            "p": p_value,
            "zeta": zeta_value,
        },
        "S_mean": float(record.get("S_mean", float("nan"))),
        "S_var": float(record.get("S_var", float("nan"))),
        "giant_fraction": float(record.get("giant_fraction", float("nan"))),
        "omega_abs": float(omega_abs),
        "method": method,
        "threshold_estimate": float(threshold_estimate),
        "threshold_distance": float(distance),
        "near_threshold": bool(distance <= tolerance),
        "tolerance": float(tolerance),
    }


def main(argv: Optional[List[str]] = None) -> BaselineRunConfig:
    """Parse CLI arguments, execute the grid scan, and persist artifacts."""

    parser = get_parser()
    namespace = parser.parse_args(argv)
    config = BaselineRunConfig(
        axis_map=Path(namespace.axis_map),
        output_dir=namespace.output_dir,
        steps=namespace.steps,
        seed=namespace.seed,
        time_budget=namespace.time_budget,
    )

    base_seed_value = int(config.seed if config.seed is not None else 0)
    seed_everything(base_seed_value)
    base_seed = np.random.SeedSequence(base_seed_value)

    graph, adjacency, graph_id, graph_seed, graph_params = _build_graph(namespace, config)
    substrate = _prepare_substrate(graph)
    features = _graph_features(graph, adjacency)
    threshold_estimate = _estimate_threshold(features.get("average_degree", float("nan")))

    axis_names = tuple(namespace.axes)
    if len(axis_names) != 2:
        raise ValueError("Percolation baseline currently supports exactly two scan axes")
    axis_aliases = (_axis_alias(axis_names[0]), _axis_alias(axis_names[1]))
    probability_axis = None
    for idx, alias in enumerate(axis_aliases):
        if alias == "rho":
            probability_axis = idx
            break
    if probability_axis is None:
        raise ValueError("At least one axis must correspond to the occupation probability")
    if "zeta" not in axis_aliases:
        raise ValueError("One axis must correspond to the damage parameter zeta")
    zeta_axis = axis_aliases.index("zeta")

    axis_ranges = _resolve_axis_ranges(axis_names, namespace.axis_ranges)
    grid_shape = (
        max(int(namespace.grid_size[0]), 1),
        max(int(namespace.grid_size[1]), 1),
    )

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

    S_mean_grid = np.full(grid_shape, np.nan, dtype=float)
    S_var_grid = np.full(grid_shape, np.nan, dtype=float)

    records: list[dict[str, object]] = []
    record_lookup: dict[tuple[int, int], dict[str, object]] = {}

    rng_children = base_seed.spawn(grid_shape[0] * grid_shape[1])
    giant_threshold = float(namespace.giant_threshold)

    time_budget = max(float(config.time_budget), 0.0)
    budget_notes: list[str] = []

    def _warn_overrun(elapsed: float) -> None:
        message = (
            f"Percolation sweep runtime {elapsed:.3f}s exceeded the {time_budget:.3f}s budget."
        )
        warnings.warn(message, RuntimeWarning)
        budget_notes.append(message)

    index = 0
    with time_budget_guard(
        time_budget if time_budget > 0 else float("inf"),
        raise_on_exceed=False,
        on_exceed=_warn_overrun,
    ) as guard:
        for i, value0 in enumerate(axis_values[0]):
            for j, value1 in enumerate(axis_values[1]):
                child_seed = rng_children[index]
                index += 1
                rng = np.random.default_rng(child_seed)
                values = (float(value0), float(value1))
                p_value = values[probability_axis]
                zeta_value = values[zeta_axis]
                summary = simulate_percolation(
                    substrate,
                    p=p_value,
                    zeta=zeta_value,
                    realizations=namespace.realizations,
                    threshold=giant_threshold,
                    rng=rng,
                )

                S_mean_grid[i, j] = summary.S_mean
                S_var_grid[i, j] = summary.S_var

                record = {
                    "graph_kind": namespace.graph_kind,
                    "graph_seed": graph_seed,
                    "graph_identifier": graph_id,
                    "realizations": int(summary.samples),
                    "giant_threshold": giant_threshold,
                    axis_names[0]: float(values[0]),
                    axis_names[1]: float(values[1]),
                    f"{axis_names[0]}_index": i,
                    f"{axis_names[1]}_index": j,
                    axis_aliases[0]: float(values[0]),
                    axis_aliases[1]: float(values[1]),
                    f"{axis_aliases[0]}_index": i,
                    f"{axis_aliases[1]}_index": j,
                    "S_mean": summary.S_mean,
                    "S_var": summary.S_var,
                    "S_std": summary.S_std,
                    "S_min": summary.S_min,
                    "S_max": summary.S_max,
                    "giant_fraction": summary.giant_fraction,
                }
                record.update(features)
                record["threshold_estimate"] = threshold_estimate
                for key, value in graph_params.items():
                    record[f"graph_param_{key}"] = value
                records.append(record)
                record_lookup[(i, j)] = record

    elapsed = guard.elapsed if guard.elapsed is not None else 0.0

    probability_values = axis_values[probability_axis]
    omega_grid = (
        _curvature_from_grid(S_mean_grid, axis_values[0], axis_values[1])
        if namespace.compute_curvature
        else _finite_difference_axis(S_mean_grid, probability_values, probability_axis)
    )
    omega_abs_grid = np.abs(omega_grid)

    other_axis = zeta_axis
    dS_other = _finite_difference_axis(
        S_mean_grid,
        axis_values[other_axis],
        other_axis,
    )

    accumulator = Accumulator()
    for record in records:
        i = int(record[f"{axis_names[0]}_index"])
        j = int(record[f"{axis_names[1]}_index"])
        omega_value = omega_grid[i, j]
        omega_abs_value = omega_abs_grid[i, j]
        record["omega"] = float(omega_value) if np.isfinite(omega_value) else float("nan")
        record["omega_abs"] = float(omega_abs_value) if np.isfinite(omega_abs_value) else float("nan")
        derivative_label = f"dS_d{axis_aliases[other_axis]}"
        record[derivative_label] = float(dS_other[i, j]) if np.isfinite(dS_other[i, j]) else float("nan")
        accumulator.add(record)

    axis_map = load_axis_map(Path(config.axis_map))

    seed_label = base_seed_value
    output_dir = ensure_outdir("percolation", namespace.output_dir, graph_id, seed_label)
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
        spacing = _grid_spacing(probability_values)
        tolerance = float(max(spacing * float(namespace.loop_delta_scale), 1e-6))
        method = "curvature" if namespace.compute_curvature else "finite_difference"
        for tile_index, tile in enumerate(tiles):
            if tile_index >= namespace.loop_top_k:
                break
            indices = tile.get("indices", [])
            if not isinstance(indices, list) or len(indices) != 2:
                continue
            i_idx, j_idx = int(indices[0]), int(indices[1])
            record = record_lookup.get((i_idx, j_idx))
            if record is None:
                continue
            omega_abs = omega_abs_grid[i_idx, j_idx]
            report = _build_hotspot_report(
                record,
                float(omega_abs) if np.isfinite(omega_abs) else float("nan"),
                threshold_estimate,
                tolerance,
                method,
                axis_aliases,
                axis_names,
                probability_axis,
                zeta_axis,
            )
            destination = loops_dir / f"loop_{axis_aliases[0]}{i_idx}_{axis_aliases[1]}{j_idx}.json"
            with destination.open("w", encoding="utf-8") as handle:
                json.dump(report, handle, indent=2, ensure_ascii=False)
            loop_reports.append(destination)

    if argv is None:
        print(
            f"Percolation baseline completed {grid_shape[0] * grid_shape[1]} grid points "
            f"on {namespace.graph_kind} in {elapsed:.3f}s; metrics written to {metrics_path}."
        )
        print(f"|Ω| heatmap stored at {heatmap_path} and top-tile summary at {top_tiles_path}.")
        if budget_notes:
            print(budget_notes[-1])
        if namespace.enable_loops and loop_reports:
            print(f"Hotspot reports written to {loop_reports[0].parent} " f"({len(loop_reports)} tiles).")
        print(
            "Mean-field threshold estimate p_c ≈ "
            f"{threshold_estimate:.3f}; inspect hotspot reports for alignment."
        )

    return config


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

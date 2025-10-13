"""CLI for the Ising model baseline."""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Mapping, Optional, Sequence

import networkx as nx
import numpy as np

from baselines import BaselineRunConfig, build_shared_parser
from baselines.artifacts import ensure_outdir, write_heatmap_png, write_top_tiles
from baselines.common import Accumulator, graph_factory, seed_everything
from baselines.io import load_axis_map


@dataclass(slots=True)
class SimulationResult:
    """Aggregate statistics captured from an Ising model simulation."""

    magnetization_mean: float
    magnetization_abs_mean: float
    magnetization_std: float
    susceptibility: float
    energy_mean: float
    energy_density: float
    energy_std: float
    heat_capacity: float
    samples: int


def get_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the Ising driver."""

    parser = build_shared_parser("Ising model baseline simulation driver.")
    parser.add_argument(
        "--axes",
        nargs=2,
        metavar=("AXIS0", "AXIS1"),
        default=("T", "h"),
        help="Names of the scanned axes (default: %(default)s).",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        nargs=2,
        metavar=("AXIS0_POINTS", "AXIS1_POINTS"),
        default=(25, 25),
        help="Number of samples along each axis (default: %(default)s).",
    )
    parser.add_argument(
        "--range",
        dest="axis_ranges",
        action="append",
        nargs=3,
        metavar=("AXIS", "MIN", "MAX"),
        default=None,
        help=(
            "Override the scan range for an axis (repeatable, e.g. --range T 1.0 4.0)."
        ),
    )
    parser.add_argument(
        "--graph-kind",
        default="lattice_2d",
        help="Graph family used for spin interactions (default: %(default)s).",
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
        default=(16, 16),
        help=(
            "Dimensions of the lattice_2d substrate when --graph-kind=lattice_2d "
            "(default: %(default)s)."
        ),
    )
    parser.add_argument(
        "--coupling",
        type=float,
        default=1.0,
        help="Interaction strength J (default: %(default)s).",
    )
    parser.add_argument(
        "--warmup-sweeps",
        type=int,
        default=200,
        help="Number of Metropolis sweeps discarded as warm-up (default: %(default)s).",
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
        help="Evaluate Wilson loops around the highest-|Ω| tiles and persist JSON reports.",
    )
    parser.add_argument(
        "--loop-top-k",
        type=int,
        default=3,
        help="Number of tiles to probe with explicit loops when enabled (default: %(default)s).",
    )
    parser.add_argument(
        "--loop-delta-scale",
        type=float,
        default=1.0,
        help=(
            "Scale factor applied to the grid spacing when constructing loop plaquettes "
            "(default: %(default)s)."
        ),
    )
    return parser


def _parse_graph_params(pairs: Sequence[str]) -> dict[str, float | int | bool]:
    """Convert KEY=VALUE CLI pairs into graph factory kwargs."""

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
    if lowered in {"t", "temp", "temperature", "tau"}:
        return "temperature"
    if lowered in {"h", "field", "eta"}:
        return "field"
    return name


def _default_axis_range(name: str) -> tuple[float, float]:
    alias = _axis_alias(name)
    if alias == "temperature":
        return (1.0, 4.0)
    if alias == "field":
        return (-0.5, 0.5)
    return (0.0, 1.0)


def _resolve_axis_ranges(
    axis_names: Sequence[str], overrides: Optional[Iterable[Sequence[str]]]
) -> dict[str, tuple[float, float]]:
    """Return a mapping from axis name to scan range."""

    ranges: dict[str, tuple[float, float]] = {
        axis: _default_axis_range(axis) for axis in axis_names
    }
    if overrides is None:
        return ranges
    for triple in overrides:
        if len(triple) != 3:
            raise argparse.ArgumentTypeError(
                "Axis range overrides must supply AXIS MIN MAX entries."
            )
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


def _axis_spacing(values: Sequence[float], index: int) -> float:
    """Return the characteristic spacing near ``values[index]``."""

    size = len(values)
    if size <= 1:
        return 0.0
    if index <= 0:
        return float(values[1] - values[0])
    if index >= size - 1:
        return float(values[-1] - values[-2])
    return float(0.5 * (values[index + 1] - values[index - 1]))


def _finite_difference_axis(
    data: np.ndarray, coordinates: Sequence[float], axis: int
) -> np.ndarray:
    """Compute a finite-difference derivative along a specified axis."""

    if axis not in (0, 1):
        raise ValueError("axis must be 0 or 1 for two-dimensional data")
    coords = np.asarray(coordinates, dtype=float)
    swapped = np.moveaxis(data, axis, 0)
    rows = swapped.shape[0]
    derivative = np.full_like(swapped, np.nan, dtype=float)
    if rows == 1:
        return np.moveaxis(derivative, 0, axis)
    for i in range(rows):
        for index in np.ndindex(*swapped.shape[1:]):
            value = swapped[(i,) + index]
            if not np.isfinite(value):
                continue
            if i == 0:
                forward = swapped[(i + 1,) + index]
                if np.isfinite(forward):
                    step = coords[i + 1] - coords[i]
                    if step != 0:
                        derivative[(i,) + index] = (forward - value) / step
            elif i == rows - 1:
                backward = swapped[(i - 1,) + index]
                if np.isfinite(backward):
                    step = coords[i] - coords[i - 1]
                    if step != 0:
                        derivative[(i,) + index] = (value - backward) / step
            else:
                forward = swapped[(i + 1,) + index]
                backward = swapped[(i - 1,) + index]
                if np.isfinite(forward) and np.isfinite(backward):
                    step = coords[i + 1] - coords[i - 1]
                    if step != 0:
                        derivative[(i,) + index] = (forward - backward) / step
    return np.moveaxis(derivative, 0, axis)


def _ising_energy(
    spins: np.ndarray,
    adjacency: np.ndarray,
    *,
    coupling: float,
    field: float,
) -> float:
    """Return the Ising Hamiltonian for ``spins`` on ``adjacency``."""

    interaction = -0.5 * coupling * float(spins @ (adjacency @ spins))
    field_term = -field * float(np.sum(spins))
    return interaction + field_term


def simulate_ising(
    adjacency: np.ndarray,
    *,
    temperature: float,
    field: float,
    coupling: float,
    warmup_sweeps: int,
    sample_sweeps: int,
    seed: int | None = None,
) -> SimulationResult:
    """Simulate an Ising model using Metropolis (Glauber) dynamics."""

    if adjacency.ndim != 2 or adjacency.shape[0] != adjacency.shape[1]:
        raise ValueError("adjacency must be a square matrix")
    n = adjacency.shape[0]
    if n == 0:
        return SimulationResult(
            magnetization_mean=float("nan"),
            magnetization_abs_mean=float("nan"),
            magnetization_std=float("nan"),
            susceptibility=float("nan"),
            energy_mean=float("nan"),
            energy_density=float("nan"),
            energy_std=float("nan"),
            heat_capacity=float("nan"),
            samples=0,
        )

    rng = np.random.default_rng(seed)
    spins = rng.choice([-1, 1], size=n)
    neighbors = [np.flatnonzero(adjacency[i]) for i in range(n)]
    weights = [
        adjacency[i, idx] if idx.size else np.array([], dtype=float)
        for i, idx in enumerate(neighbors)
    ]

    warmup = max(int(warmup_sweeps), 0)
    samples = max(int(sample_sweeps), 0)

    def sweep() -> None:
        order = np.arange(n)
        rng.shuffle(order)
        for idx in order:
            neigh_idx = neighbors[idx]
            neigh_weights = weights[idx]
            neighbor_sum = 0.0
            if neigh_idx.size:
                neighbor_sum = float(np.dot(neigh_weights, spins[neigh_idx]))
            local_field = coupling * neighbor_sum + field
            delta_e = 2.0 * spins[idx] * local_field
            if delta_e <= 0.0:
                spins[idx] = -spins[idx]
            elif temperature > 0.0:
                exponent = -delta_e / temperature
                probability = math.exp(exponent) if exponent > -700.0 else 0.0
                if rng.random() < probability:
                    spins[idx] = -spins[idx]

    for _ in range(warmup):
        sweep()

    magnetizations: list[float] = []
    energies: list[float] = []
    for _ in range(samples):
        sweep()
        magnetization = float(np.mean(spins))
        energy = _ising_energy(spins, adjacency, coupling=coupling, field=field)
        magnetizations.append(magnetization)
        energies.append(energy)

    if magnetizations:
        m_arr = np.asarray(magnetizations, dtype=float)
        e_arr = np.asarray(energies, dtype=float)
        m_mean = float(np.mean(m_arr))
        m_abs_mean = float(np.mean(np.abs(m_arr)))
        m_std = float(np.std(m_arr))
        m_var = float(np.var(m_arr))
        e_mean = float(np.mean(e_arr))
        e_std = float(np.std(e_arr))
        e_var = float(np.var(e_arr))
        susceptibility = (
            float((m_var * n) / temperature)
            if temperature > 0.0
            else float("nan")
        )
        heat_capacity = (
            float(e_var / (temperature * temperature * n))
            if temperature > 0.0
            else float("nan")
        )
        energy_density = float(e_mean / n)
    else:
        m_mean = float("nan")
        m_abs_mean = float("nan")
        m_std = float("nan")
        susceptibility = float("nan")
        e_mean = float("nan")
        energy_density = float("nan")
        e_std = float("nan")
        heat_capacity = float("nan")

    return SimulationResult(
        magnetization_mean=m_mean,
        magnetization_abs_mean=m_abs_mean,
        magnetization_std=m_std,
        susceptibility=susceptibility,
        energy_mean=e_mean,
        energy_density=energy_density,
        energy_std=e_std,
        heat_capacity=heat_capacity,
        samples=len(magnetizations),
    )


def _adjacency_spectrum(adjacency: np.ndarray) -> tuple[float, float]:
    """Return the spectral radius and first gap of ``adjacency``."""

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


def _sign_flip(values: Sequence[float]) -> bool:
    """Return ``True`` if the sequence contains opposing magnetization signs."""

    signs = {
        math.copysign(1.0, value)
        for value in values
        if value != 0.0 and math.isfinite(value)
    }
    return len(signs) > 1


def run_cwt_loop(
    adjacency: np.ndarray,
    record: Mapping[str, object],
    axis_values: tuple[Sequence[float], Sequence[float]],
    axis_names: Sequence[str],
    *,
    temp_axis: int,
    field_axis: int,
    coupling: float,
    warmup_sweeps: int,
    sample_sweeps: int,
    base_seed: int | None,
    delta_scale: float,
) -> Mapping[str, object]:
    """Evaluate a Wilson loop around ``record`` and return a JSON payload."""

    if len(axis_names) != 2:
        raise ValueError("Loops are only supported for two-dimensional grids")

    axis_aliases = (_axis_alias(axis_names[0]), _axis_alias(axis_names[1]))
    indices = [
        int(record.get(f"{axis_names[0]}_index", 0)),
        int(record.get(f"{axis_names[1]}_index", 0)),
    ]

    centers = [float(axis_values[0][indices[0]]), float(axis_values[1][indices[1]])]
    spans = [
        max(_axis_spacing(axis_values[0], indices[0]) * delta_scale, 0.0),
        max(_axis_spacing(axis_values[1], indices[1]) * delta_scale, 0.0),
    ]
    mins = [float(axis_values[0][0]), float(axis_values[1][0])]
    maxs = [float(axis_values[0][-1]), float(axis_values[1][-1])]

    offsets = {
        "bottom_left": (-0.5, -0.5),
        "bottom_right": (0.5, -0.5),
        "top_right": (0.5, 0.5),
        "top_left": (-0.5, 0.5),
    }

    corners: dict[str, dict[str, float]] = {}
    magnetizations: list[float] = []

    for idx, (label, (off0, off1)) in enumerate(offsets.items()):
        target = [
            float(np.clip(centers[0] + off0 * spans[0], mins[0], maxs[0])),
            float(np.clip(centers[1] + off1 * spans[1], mins[1], maxs[1])),
        ]
        seed_offset = None if base_seed is None else base_seed + indices[0] * 193 + indices[1] * 997 + idx
        temperature = target[temp_axis]
        field = target[field_axis]
        result = simulate_ising(
            adjacency,
            temperature=float(temperature),
            field=float(field),
            coupling=coupling,
            warmup_sweeps=warmup_sweeps,
            sample_sweeps=sample_sweeps,
            seed=seed_offset,
        )
        payload = {
            axis_names[0]: target[0],
            axis_names[1]: target[1],
            axis_aliases[0]: target[0],
            axis_aliases[1]: target[1],
            "temperature": float(temperature),
            "field": float(field),
            "M_mean": result.magnetization_mean,
            "M_abs_mean": result.magnetization_abs_mean,
        }
        corners[label] = payload
        magnetizations.append(result.magnetization_mean)

    extent0 = abs(corners["top_right"][axis_aliases[0]] - corners["top_left"][axis_aliases[0]])
    extent1 = abs(corners["top_right"][axis_aliases[1]] - corners["bottom_right"][axis_aliases[1]])
    area = max(extent0, 1e-12) * max(extent1, 1e-12)

    bl = corners["bottom_left"]["M_mean"]
    br = corners["bottom_right"]["M_mean"]
    tr = corners["top_right"]["M_mean"]
    tl = corners["top_left"]["M_mean"]
    omega = ((tr - tl) - (br - bl)) / area if area > 0 and math.isfinite(area) else float("nan")

    loop_report = {
        "indices": indices,
        "center": {
            axis_aliases[0]: centers[0],
            axis_aliases[1]: centers[1],
            "M_mean": float(record.get("M_mean", float("nan"))),
            "omega": float(record.get("omega", float("nan"))),
        },
        "loop": {
            axis_aliases[0]: {"span": spans[0], "extent": extent0},
            axis_aliases[1]: {"span": spans[1], "extent": extent1},
            "area": area,
            "omega": omega,
            "omega_abs": abs(omega) if math.isfinite(omega) else float("nan"),
            "fs_guard_triggered": bool(area <= 1e-12),
            "sign_flip_detected": _sign_flip(magnetizations),
        },
        "corners": [
            {
                "label": label,
                axis_aliases[0]: payload[axis_aliases[0]],
                axis_aliases[1]: payload[axis_aliases[1]],
                "temperature": payload["temperature"],
                "field": payload["field"],
                "M_mean": payload["M_mean"],
                "M_abs_mean": payload["M_abs_mean"],
            }
            for label, payload in corners.items()
        ],
    }
    return loop_report


def main(argv: Optional[List[str]] = None) -> BaselineRunConfig:
    """Parse CLI arguments, execute the grid scan, and persist artifacts."""

    parser = get_parser()
    namespace = parser.parse_args(argv)
    config = BaselineRunConfig(
        axis_map=Path(namespace.axis_map),
        output_dir=namespace.output_dir,
        steps=namespace.steps,
        seed=namespace.seed,
    )

    if config.seed is not None:
        seed_everything(config.seed)

    graph, adjacency, graph_id, graph_seed, graph_params = _build_graph(namespace, config)
    base_radius, base_gap = _adjacency_spectrum(adjacency)

    axis_names = tuple(namespace.axes)
    if len(axis_names) != 2:
        raise ValueError("Ising baseline currently supports exactly two scan axes")
    axis_aliases = (_axis_alias(axis_names[0]), _axis_alias(axis_names[1]))
    if "temperature" not in axis_aliases:
        raise ValueError("At least one axis must correspond to temperature")
    if "field" not in axis_aliases:
        raise ValueError("At least one axis must correspond to field")
    temp_axis = axis_aliases.index("temperature")
    field_axis = axis_aliases.index("field")

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

    magnetization_grid = np.full(grid_shape, np.nan, dtype=float)
    records: list[dict[str, object]] = []
    record_lookup: dict[tuple[int, int], dict[str, object]] = {}

    node_count = graph.number_of_nodes()
    edge_count = graph.number_of_edges()

    start = time.perf_counter()
    index = 0
    for i, value0 in enumerate(axis_values[0]):
        for j, value1 in enumerate(axis_values[1]):
            values = [float(value0), float(value1)]
            temperature = values[temp_axis]
            field = values[field_axis]
            seed_offset = None if config.seed is None else config.seed + index
            result = simulate_ising(
                adjacency,
                temperature=float(temperature),
                field=float(field),
                coupling=float(namespace.coupling),
                warmup_sweeps=namespace.warmup_sweeps,
                sample_sweeps=config.steps,
                seed=seed_offset,
            )
            magnetization_grid[i, j] = result.magnetization_mean

            record = {
                "graph_kind": namespace.graph_kind,
                "graph_seed": graph_seed,
                "graph_identifier": graph_id,
                "node_count": node_count,
                "edge_count": edge_count,
                "coupling": float(namespace.coupling),
                "temperature": float(temperature),
                "field": float(field),
                axis_names[0]: float(values[0]),
                axis_names[1]: float(values[1]),
                f"{axis_names[0]}_index": i,
                f"{axis_names[1]}_index": j,
                f"{axis_aliases[0]}_index": i,
                f"{axis_aliases[1]}_index": j,
                "M_mean": result.magnetization_mean,
                "M_abs_mean": result.magnetization_abs_mean,
                "M_std": result.magnetization_std,
                "chi_est": result.susceptibility,
                "energy_mean": result.energy_mean,
                "energy_density": result.energy_density,
                "energy_std": result.energy_std,
                "C_est": result.heat_capacity,
                "spectral_radius": float(namespace.coupling) * base_radius,
                "spectral_gap": float(namespace.coupling) * base_gap,
                "samples": result.samples,
            }
            records.append(record)
            record_lookup[(i, j)] = record
            index += 1
    elapsed = time.perf_counter() - start

    omega_grid = _finite_difference_axis(
        magnetization_grid, axis_values[temp_axis], temp_axis
    )
    omega_abs_grid = np.abs(omega_grid)

    accumulator = Accumulator()
    for record in records:
        i = int(record[f"{axis_names[0]}_index"])
        j = int(record[f"{axis_names[1]}_index"])
        omega_value = omega_grid[i, j]
        omega_abs_value = omega_abs_grid[i, j]
        record["omega"] = float(omega_value) if np.isfinite(omega_value) else float("nan")
        record["omega_abs"] = (
            float(omega_abs_value) if np.isfinite(omega_abs_value) else float("nan")
        )
        accumulator.add(record)

    axis_map = load_axis_map(Path(config.axis_map))

    seed_label = config.seed if config.seed is not None else "na"
    output_dir = ensure_outdir("ising", namespace.output_dir, graph_id, seed_label)
    metrics_path = accumulator.to_csv(output_dir / "metrics.csv")

    heatmap_axes = (_axis_alias(axis_names[0]), _axis_alias(axis_names[1]))
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
            loop_report = run_cwt_loop(
                adjacency,
                record,
                axis_values,
                axis_names,
                temp_axis=temp_axis,
                field_axis=field_axis,
                coupling=float(namespace.coupling),
                warmup_sweeps=namespace.warmup_sweeps,
                sample_sweeps=config.steps,
                base_seed=config.seed,
                delta_scale=float(max(namespace.loop_delta_scale, 1e-6)),
            )
            destination = loops_dir / f"loop_{axis_names[0]}{i_idx}_{axis_names[1]}{j_idx}.json"
            with destination.open("w", encoding="utf-8") as handle:
                json.dump(loop_report, handle, indent=2, ensure_ascii=False)
            loop_reports.append(destination)

    if argv is None:
        print(
            f"Ising baseline completed {grid_shape[0] * grid_shape[1]} grid points "
            f"on {namespace.graph_kind} in {elapsed:.3f}s; metrics written to {metrics_path}."
        )
        print(f"|Ω| heatmap stored at {heatmap_path} and top-tile summary at {top_tiles_path}.")
        if namespace.enable_loops and loop_reports:
            print(
                f"Loop diagnostics written to {loop_reports[0].parent} "
                f"({len(loop_reports)} tiles)."
            )

    return config


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

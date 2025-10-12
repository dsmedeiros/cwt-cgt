"""CLI for the Kuramoto oscillator baseline."""
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
from baselines.common import Accumulator, graph_factory, grid_points, seed_everything
from baselines.io import load_axis_map


@dataclass(slots=True)
class SimulationResult:
    """Summary statistics captured from a single Kuramoto simulation."""

    r_mean: float
    r_std: float
    freq_spread: float
    order_parameter: complex


def get_parser() -> argparse.ArgumentParser:
    """Construct the argument parser for the Kuramoto driver."""

    parser = build_shared_parser("Kuramoto oscillator baseline simulation driver.")
    parser.add_argument(
        "--graph-kind",
        default="ring3",
        help="Graph family used to couple oscillators (default: %(default)s).",
    )
    parser.add_argument(
        "--graph-param",
        action="append",
        default=[],
        metavar="KEY=VALUE",
        help="Override graph factory parameters (repeatable, e.g. --graph-param n=32).",
    )
    parser.add_argument(
        "--graph-seed",
        type=int,
        default=None,
        help="Seed used when sampling random graphs (defaults to --seed).",
    )
    parser.add_argument(
        "--grid-size",
        type=int,
        nargs=2,
        metavar=("KAPPA_POINTS", "SIGMA_POINTS"),
        default=(25, 25),
        help="Number of grid points along the coupling κ and disorder σ axes (default: %(default)s).",
    )
    parser.add_argument(
        "--coupling-range",
        type=float,
        nargs=2,
        metavar=("KAPPA_MIN", "KAPPA_MAX"),
        default=(0.0, 4.0),
        help="Inclusive coupling range κₘᵢₙ κₘₐₓ to scan (default: %(default)s).",
    )
    parser.add_argument(
        "--disorder-range",
        type=float,
        nargs=2,
        metavar=("SIGMA_MIN", "SIGMA_MAX"),
        default=(0.0, 2.0),
        help="Intrinsic frequency standard deviation σ range to explore (default: %(default)s).",
    )
    parser.add_argument(
        "--dt",
        type=float,
        default=0.05,
        help="Integration time step Δt for the phase updates (default: %(default)s).",
    )
    parser.add_argument(
        "--warmup-steps",
        type=int,
        default=200,
        help="Number of integration steps discarded as warm-up (default: %(default)s).",
    )
    parser.add_argument(
        "--integration",
        choices=("euler", "rk2"),
        default="rk2",
        help="Integration scheme for the Kuramoto dynamics (default: %(default)s).",
    )
    parser.add_argument(
        "--intrinsic-mean",
        type=float,
        default=0.0,
        help="Mean of the Gaussian intrinsic frequency distribution ω₀ (default: %(default)s).",
    )
    parser.add_argument(
        "--compute-curvature",
        action="store_true",
        help="Use a Wilson-loop curvature estimator; otherwise a finite-difference proxy is used.",
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
        help="Evaluate explicit Wilson loops for the highest-|Ω| tiles and store JSON reports.",
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
            "Scale factor applied to the grid spacing when constructing loop "
            "plaquettes (default: %(default)s)."
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


def _build_adjacency(kind: str, params: Mapping[str, float | int | bool], seed: int | None) -> np.ndarray:
    """Instantiate the coupling graph and return its weighted adjacency matrix."""

    graph = graph_factory(kind, seed=seed, **params)
    adjacency = np.asarray(nx.to_numpy_array(graph, dtype=float, weight="weight"), dtype=float)
    return adjacency


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


def _kuramoto_derivative(
    theta: np.ndarray,
    natural_freq: np.ndarray,
    coupling: float,
    adjacency: np.ndarray,
    inv_degree: np.ndarray,
) -> np.ndarray:
    """Return dθ/dt for the Kuramoto model with the supplied parameters."""

    phase_diff = theta[np.newaxis, :] - theta[:, np.newaxis]
    interaction = np.sum(adjacency * np.sin(phase_diff), axis=1)
    return natural_freq + coupling * interaction * inv_degree


def _integration_step(
    theta: np.ndarray,
    natural_freq: np.ndarray,
    coupling: float,
    adjacency: np.ndarray,
    inv_degree: np.ndarray,
    dt: float,
    method: str,
) -> tuple[np.ndarray, np.ndarray]:
    """Advance ``theta`` by one integration step and return the derivative."""

    if method == "euler":
        derivative = _kuramoto_derivative(theta, natural_freq, coupling, adjacency, inv_degree)
        theta_next = theta + dt * derivative
        return theta_next, derivative

    k1 = _kuramoto_derivative(theta, natural_freq, coupling, adjacency, inv_degree)
    midpoint = theta + 0.5 * dt * k1
    k2 = _kuramoto_derivative(midpoint, natural_freq, coupling, adjacency, inv_degree)
    theta_next = theta + dt * k2
    return theta_next, k2


def simulate_kuramoto(
    adjacency: np.ndarray,
    *,
    coupling: float,
    sigma: float,
    dt: float,
    warmup_steps: int,
    sample_steps: int,
    integration: str,
    intrinsic_mean: float,
    seed: int | None,
) -> SimulationResult:
    """Run the Kuramoto model on ``adjacency`` and return summary statistics."""

    node_count = adjacency.shape[0]
    if node_count == 0:
        return SimulationResult(
            r_mean=float("nan"),
            r_std=float("nan"),
            freq_spread=float("nan"),
            order_parameter=0.0j,
        )

    rng = np.random.default_rng(seed)
    theta = rng.uniform(0.0, 2.0 * math.pi, size=node_count)
    natural_freq = rng.normal(loc=float(intrinsic_mean), scale=float(max(sigma, 0.0)), size=node_count)

    degrees = adjacency.sum(axis=1)
    inv_degree = np.divide(1.0, degrees, out=np.zeros_like(degrees), where=degrees > 0.0)

    for _ in range(max(int(warmup_steps), 0)):
        theta, _ = _integration_step(
            theta,
            natural_freq,
            coupling,
            adjacency,
            inv_degree,
            dt,
            integration,
        )
        theta = np.mod(theta, 2.0 * math.pi)

    order_samples: list[complex] = []
    freq_spread_samples: list[float] = []
    for _ in range(max(int(sample_steps), 0)):
        theta, derivative = _integration_step(
            theta,
            natural_freq,
            coupling,
            adjacency,
            inv_degree,
            dt,
            integration,
        )
        theta = np.mod(theta, 2.0 * math.pi)
        phasor = np.exp(1j * theta)
        order_samples.append(np.mean(phasor))
        freq_spread_samples.append(float(np.std(derivative)))

    if order_samples:
        magnitudes = np.abs(order_samples)
        r_mean = float(np.mean(magnitudes))
        r_std = float(np.std(magnitudes))
        freq_spread = float(np.mean(freq_spread_samples)) if freq_spread_samples else float("nan")
        order_parameter = complex(np.mean(order_samples))
    else:
        r_mean = float("nan")
        r_std = float("nan")
        freq_spread = float("nan")
        order_parameter = 0.0j

    return SimulationResult(
        r_mean=r_mean,
        r_std=r_std,
        freq_spread=freq_spread,
        order_parameter=order_parameter,
    )


def _finite_difference_curvature(
    values: np.ndarray,
    axis0: Sequence[float],
    axis1: Sequence[float],
) -> np.ndarray:
    """Estimate |∇r| as a curvature proxy using finite differences."""

    grid = np.asarray(values, dtype=float)
    result = np.full_like(grid, np.nan, dtype=float)
    rows, cols = grid.shape
    for i in range(rows):
        for j in range(cols):
            center = grid[i, j]
            if not np.isfinite(center):
                continue

            # Axis 0 derivative
            if 0 < i < rows - 1:
                delta = axis0[i + 1] - axis0[i - 1]
                forward = grid[i + 1, j]
                backward = grid[i - 1, j]
                if np.isfinite(forward) and np.isfinite(backward) and delta != 0.0:
                    grad0 = (forward - backward) / delta
                elif np.isfinite(forward) and axis0[i + 1] != axis0[i]:
                    grad0 = (forward - center) / (axis0[i + 1] - axis0[i])
                elif np.isfinite(backward) and axis0[i] != axis0[i - 1]:
                    grad0 = (center - backward) / (axis0[i] - axis0[i - 1])
                else:
                    grad0 = 0.0
            elif i < rows - 1 and axis0[i + 1] != axis0[i] and np.isfinite(grid[i + 1, j]):
                grad0 = (grid[i + 1, j] - center) / (axis0[i + 1] - axis0[i])
            elif i > 0 and axis0[i] != axis0[i - 1] and np.isfinite(grid[i - 1, j]):
                grad0 = (center - grid[i - 1, j]) / (axis0[i] - axis0[i - 1])
            else:
                grad0 = 0.0

            # Axis 1 derivative
            if 0 < j < cols - 1:
                delta = axis1[j + 1] - axis1[j - 1]
                forward = grid[i, j + 1]
                backward = grid[i, j - 1]
                if np.isfinite(forward) and np.isfinite(backward) and delta != 0.0:
                    grad1 = (forward - backward) / delta
                elif np.isfinite(forward) and axis1[j + 1] != axis1[j]:
                    grad1 = (forward - center) / (axis1[j + 1] - axis1[j])
                elif np.isfinite(backward) and axis1[j] != axis1[j - 1]:
                    grad1 = (center - backward) / (axis1[j] - axis1[j - 1])
                else:
                    grad1 = 0.0
            elif j < cols - 1 and axis1[j + 1] != axis1[j] and np.isfinite(grid[i, j + 1]):
                grad1 = (grid[i, j + 1] - center) / (axis1[j + 1] - axis1[j])
            elif j > 0 and axis1[j] != axis1[j - 1] and np.isfinite(grid[i, j - 1]):
                grad1 = (center - grid[i, j - 1]) / (axis1[j] - axis1[j - 1])
            else:
                grad1 = 0.0

            result[i, j] = float(math.hypot(grad0, grad1))
    return result


def compute_cwt_curvature(
    order_field: np.ndarray,
    axis0: Sequence[float],
    axis1: Sequence[float],
) -> np.ndarray:
    """Estimate curvature using a Wilson-loop construction on the order parameter."""

    order = np.asarray(order_field, dtype=np.complex128)
    rows, cols = order.shape
    curvature = np.full((rows, cols), np.nan, dtype=float)
    if rows < 2 or cols < 2:
        return curvature

    phases = np.exp(1j * np.angle(order, deg=False))
    cell_values = np.full((rows - 1, cols - 1), np.nan, dtype=float)
    for i in range(rows - 1):
        delta0 = axis0[i + 1] - axis0[i]
        if delta0 == 0.0:
            continue
        for j in range(cols - 1):
            delta1 = axis1[j + 1] - axis1[j]
            if delta1 == 0.0:
                continue
            psi_bl = phases[i, j]
            psi_br = phases[i + 1, j]
            psi_tr = phases[i + 1, j + 1]
            psi_tl = phases[i, j + 1]
            loop = (
                np.conjugate(psi_bl) * psi_br
                * np.conjugate(psi_br) * psi_tr
                * np.conjugate(psi_tr) * psi_tl
                * np.conjugate(psi_tl) * psi_bl
            )
            area = delta0 * delta1
            if area == 0.0:
                continue
            cell_values[i, j] = float(np.angle(loop) / area)

    counts = np.zeros((rows, cols), dtype=int)
    sums = np.zeros((rows, cols), dtype=float)
    for i in range(rows - 1):
        for j in range(cols - 1):
            value = cell_values[i, j]
            if not np.isfinite(value):
                continue
            for di, dj in ((0, 0), (1, 0), (1, 1), (0, 1)):
                ii = i + di
                jj = j + dj
                sums[ii, jj] += value
                counts[ii, jj] += 1
    mask = counts > 0
    curvature[mask] = sums[mask] / counts[mask]
    return curvature


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


def _normalize_complex(value: complex) -> complex:
    """Project ``value`` onto the unit circle."""

    magnitude = abs(value)
    if magnitude <= 1e-12:
        return 1.0 + 0.0j
    return value / magnitude


def run_cwt_loop(
    adjacency: np.ndarray,
    record: Mapping[str, object],
    kappa_values: Sequence[float],
    sigma_values: Sequence[float],
    *,
    dt: float,
    warmup_steps: int,
    sample_steps: int,
    integration: str,
    intrinsic_mean: float,
    base_seed: int | None,
    delta_scale: float,
) -> Mapping[str, object]:
    """Evaluate a Wilson loop around ``record`` and return a JSON payload."""

    i = int(record["kappa_index"])
    j = int(record["sigma_index"])
    center_kappa = float(kappa_values[i])
    center_sigma = float(sigma_values[j])
    span_kappa = max(_axis_spacing(kappa_values, i) * delta_scale, 0.0)
    span_sigma = max(_axis_spacing(sigma_values, j) * delta_scale, 0.0)

    half_kappa = 0.5 * span_kappa
    half_sigma = 0.5 * span_sigma

    corners: dict[str, dict[str, float | complex]] = {}
    offsets = {
        "bottom_left": (-half_kappa, -half_sigma),
        "bottom_right": (half_kappa, -half_sigma),
        "top_right": (half_kappa, half_sigma),
        "top_left": (-half_kappa, half_sigma),
    }
    sigma_min, sigma_max = float(sigma_values[0]), float(sigma_values[-1])
    kappa_min, kappa_max = float(kappa_values[0]), float(kappa_values[-1])

    for idx, (label, (dk, ds)) in enumerate(offsets.items()):
        target_kappa = float(np.clip(center_kappa + dk, kappa_min, kappa_max))
        target_sigma = float(np.clip(center_sigma + ds, sigma_min, sigma_max))
        seed_offset = None if base_seed is None else base_seed + i * 193 + j * 997 + idx
        result = simulate_kuramoto(
            adjacency,
            coupling=target_kappa,
            sigma=target_sigma,
            dt=dt,
            warmup_steps=warmup_steps,
            sample_steps=sample_steps,
            integration=integration,
            intrinsic_mean=intrinsic_mean,
            seed=seed_offset,
        )
        corners[label] = {
            "kappa": target_kappa,
            "sigma": target_sigma,
            "r_mean": result.r_mean,
            "order_parameter": result.order_parameter,
        }

    psi_bl = _normalize_complex(corners["bottom_left"]["order_parameter"])
    psi_br = _normalize_complex(corners["bottom_right"]["order_parameter"])
    psi_tr = _normalize_complex(corners["top_right"]["order_parameter"])
    psi_tl = _normalize_complex(corners["top_left"]["order_parameter"])

    plaquette = (
        psi_bl.conjugate() * psi_br
        * psi_br.conjugate() * psi_tr
        * psi_tr.conjugate() * psi_tl
        * psi_tl.conjugate() * psi_bl
    )

    extent_kappa = abs(corners["top_right"]["kappa"] - corners["top_left"]["kappa"])
    extent_sigma = abs(corners["top_right"]["sigma"] - corners["bottom_right"]["sigma"])
    area = max(extent_kappa, 1e-12) * max(extent_sigma, 1e-12)
    omega = float(np.angle(plaquette) / area)

    loop_report = {
        "indices": [i, j],
        "center": {
            "kappa": center_kappa,
            "sigma": center_sigma,
            "r_mean": float(record.get("r_mean", float("nan"))),
            "omega": float(record.get("omega", float("nan"))),
        },
        "loop": {
            "delta_kappa": extent_kappa,
            "delta_sigma": extent_sigma,
            "span_kappa": span_kappa,
            "span_sigma": span_sigma,
            "area": area,
            "omega": omega,
            "omega_abs": abs(omega),
        },
        "corners": [
            {
                "label": label,
                "kappa": float(payload["kappa"]),
                "sigma": float(payload["sigma"]),
                "r_mean": float(payload["r_mean"]),
                "order_parameter": {
                    "real": float(complex(payload["order_parameter"]).real),
                    "imag": float(complex(payload["order_parameter"]).imag),
                    "magnitude": float(abs(payload["order_parameter"]))
                },
            }
            for label, payload in corners.items()
        ],
    }
    return loop_report


def _collect_records(
    adjacency: np.ndarray,
    namespace: argparse.Namespace,
    config: BaselineRunConfig,
    axis_mapping: Mapping[str, object],
    *,
    kappa_values: np.ndarray,
    sigma_values: np.ndarray,
    base_radius: float,
    base_gap: float,
) -> tuple[list[dict[str, object]], np.ndarray, np.ndarray]:
    """Simulate the grid and return records together with order/r grids."""

    shape = (kappa_values.size, sigma_values.size)
    order_grid = np.full(shape, np.nan + 0j, dtype=np.complex128)
    r_mean_grid = np.full(shape, np.nan, dtype=float)

    ranges = {"kappa": namespace.coupling_range, "sigma": namespace.disorder_range}
    grid_size = {"kappa": shape[0], "sigma": shape[1]}
    grid_spec = grid_points(ranges, grid_size, axes=("kappa", "sigma"))

    records: list[dict[str, object]] = []
    for index, entry in grid_spec.items():
        kappa_idx = int(entry["kappa_index"])
        sigma_idx = int(entry["sigma_index"])
        coupling = float(kappa_values[kappa_idx])
        sigma = float(sigma_values[sigma_idx])
        seed = None if config.seed is None else config.seed + index
        result = simulate_kuramoto(
            adjacency,
            coupling=coupling,
            sigma=sigma,
            dt=namespace.dt,
            warmup_steps=namespace.warmup_steps,
            sample_steps=config.steps,
            integration=namespace.integration,
            intrinsic_mean=namespace.intrinsic_mean,
            seed=seed,
        )

        order_grid[kappa_idx, sigma_idx] = result.order_parameter
        r_mean_grid[kappa_idx, sigma_idx] = result.r_mean

        canonical_kappa = coupling
        try:
            model_section = axis_mapping.get("models", {}) if isinstance(axis_mapping, Mapping) else {}
            kuramoto_entry = model_section.get("kuramoto", {}) if isinstance(model_section, Mapping) else {}
            axes_entry = kuramoto_entry.get("axes", {}) if isinstance(kuramoto_entry, Mapping) else {}
            alias = axes_entry.get("kappa") if isinstance(axes_entry, Mapping) else None
            if isinstance(alias, str) and alias != "coupling":
                canonical_kappa = coupling
        except AttributeError:  # pragma: no cover - defensive guard
            canonical_kappa = coupling

        record: dict[str, object] = {
            "graph_kind": namespace.graph_kind,
            "graph_seed": namespace.graph_seed if namespace.graph_seed is not None else config.seed,
            "kappa_index": kappa_idx,
            "sigma_index": sigma_idx,
            "kappa": float(canonical_kappa),
            "sigma": sigma,
            "coupling": coupling,
            "disorder": sigma,
            "r_mean": result.r_mean,
            "r_std": result.r_std,
            "freq_spread": result.freq_spread,
            "spectral_radius": coupling * base_radius,
            "spectral_gap": coupling * base_gap,
            "order_parameter_real": float(result.order_parameter.real),
            "order_parameter_imag": float(result.order_parameter.imag),
            "order_parameter_mag": float(abs(result.order_parameter)),
        }
        records.append(record)

    return records, order_grid, r_mean_grid


def main(argv: Optional[List[str]] = None) -> BaselineRunConfig:
    """Parse CLI arguments, execute the grid scan, and persist artifacts."""

    parser = get_parser()
    namespace = parser.parse_args(argv)
    config = BaselineRunConfig(
        axis_map=namespace.axis_map,
        output_dir=namespace.output_dir,
        steps=namespace.steps,
        seed=namespace.seed,
    )

    if config.seed is not None:
        seed_everything(config.seed)

    graph_params = _parse_graph_params(namespace.graph_param)
    graph_seed = namespace.graph_seed if namespace.graph_seed is not None else config.seed
    adjacency = _build_adjacency(namespace.graph_kind, graph_params, graph_seed)
    base_radius, base_gap = _adjacency_spectrum(adjacency)

    axis_map = load_axis_map(Path(config.axis_map))
    kappa_values = np.linspace(
        float(namespace.coupling_range[0]),
        float(namespace.coupling_range[1]),
        int(namespace.grid_size[0]),
    )
    sigma_values = np.linspace(
        float(namespace.disorder_range[0]),
        float(namespace.disorder_range[1]),
        int(namespace.grid_size[1]),
    )

    start = time.perf_counter()
    records, order_grid, r_mean_grid = _collect_records(
        adjacency,
        namespace,
        config,
        axis_map,
        kappa_values=kappa_values,
        sigma_values=sigma_values,
        base_radius=base_radius,
        base_gap=base_gap,
    )
    elapsed = time.perf_counter() - start

    if namespace.compute_curvature:
        curvature_grid = compute_cwt_curvature(order_grid, kappa_values, sigma_values)
    else:
        curvature_grid = _finite_difference_curvature(r_mean_grid, kappa_values, sigma_values)
    curvature_abs = np.abs(curvature_grid)

    accumulator = Accumulator()
    record_lookup: dict[tuple[int, int], dict[str, object]] = {}
    for record in records:
        i = int(record["kappa_index"])
        j = int(record["sigma_index"])
        omega = float(curvature_grid[i, j]) if np.isfinite(curvature_grid[i, j]) else float("nan")
        omega_abs = float(curvature_abs[i, j]) if np.isfinite(curvature_abs[i, j]) else float("nan")
        record["omega"] = omega
        record["omega_abs"] = omega_abs
        accumulator.add(record)
        record_lookup[(i, j)] = record

    graph_id = _graph_identifier(namespace.graph_kind, graph_params)
    seed_label = config.seed if config.seed is not None else "na"
    output_dir = ensure_outdir("kuramoto", namespace.output_dir, graph_id, seed_label)
    metrics_path = output_dir / "metrics.csv"
    accumulator.to_csv(metrics_path)

    heatmap_path = write_heatmap_png(
        metrics_path,
        output_dir,
        axes=("kappa", "sigma"),
        axis_map=axis_map,
    )
    top_tiles_path = write_top_tiles(
        metrics_path,
        output_dir,
        top_k=max(int(namespace.top_k), 0),
        axes=("kappa", "sigma"),
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
            i, j = int(indices[0]), int(indices[1])
            record = record_lookup.get((i, j))
            if record is None:
                continue
            loop_report = run_cwt_loop(
                adjacency,
                record,
                kappa_values,
                sigma_values,
                dt=namespace.dt,
                warmup_steps=namespace.warmup_steps,
                sample_steps=config.steps,
                integration=namespace.integration,
                intrinsic_mean=namespace.intrinsic_mean,
                base_seed=config.seed,
                delta_scale=float(max(namespace.loop_delta_scale, 1e-6)),
            )
            destination = loops_dir / f"loop_kappa{i}_sigma{j}.json"
            with destination.open("w", encoding="utf-8") as handle:
                json.dump(loop_report, handle, indent=2, ensure_ascii=False)
            loop_reports.append(destination)

    if argv is None:
        print(
            f"Kuramoto baseline completed {len(records)} grid points on {namespace.graph_kind} "
            f"in {elapsed:.3f}s; metrics written to {metrics_path}."
        )
        print(f"|Ω| heatmap stored at {heatmap_path} and top-tile summary at {top_tiles_path}.")
        if namespace.enable_loops and loop_reports:
            print(f"Loop diagnostics written to {loop_reports[0].parent} ({len(loop_reports)} tiles).")

    return config


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

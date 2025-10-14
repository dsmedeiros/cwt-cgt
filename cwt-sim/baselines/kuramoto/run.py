"""CLI for the Kuramoto oscillator baseline."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
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
    combine_proxy_magnitudes,
    graph_factory,
    grid_points,
    seed_everything,
    time_budget_guard,
)
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
        default=(16, 16),
        help=(
            "Number of grid points along the coupling κ and disorder σ axes (default: %(default)s)."
            " Defaults are tuned so the reference scan finishes within the 60 s budget."
        ),
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
        default=128,
        help=(
            "Number of integration steps discarded as warm-up (default: %(default)s)."
            " Defaults align with the ≤60 s runtime goal."
        ),
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


_CURVATURE_CACHE: dict[str, np.ndarray] = {}


def _curvature_cache_key(order_field: np.ndarray, axis0: Sequence[float], axis1: Sequence[float]) -> str:
    axis0_arr = np.asarray(axis0, dtype=float).ravel()
    axis1_arr = np.asarray(axis1, dtype=float).ravel()
    order_arr = np.asarray(order_field, dtype=np.complex128)
    fingerprint = hashlib.sha1()
    fingerprint.update(axis0_arr.tobytes())
    fingerprint.update(axis1_arr.tobytes())
    fingerprint.update(order_arr.view(np.float64).tobytes())
    return fingerprint.hexdigest()


def _compute_cwt_curvature_local(
    order_field: np.ndarray, axis0: Sequence[float], axis1: Sequence[float]
) -> np.ndarray:
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
                np.conjugate(psi_bl)
                * psi_br
                * np.conjugate(psi_br)
                * psi_tr
                * np.conjugate(psi_tr)
                * psi_tl
                * np.conjugate(psi_tl)
                * psi_bl
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


def _invoke_curvature_experiment(
    order_field: np.ndarray,
    axis0: Sequence[float],
    axis1: Sequence[float],
    *,
    module_path: str,
    timeout: float = 300.0,
) -> np.ndarray:
    """Execute an external curvature experiment returning the curvature grid.

    The default implementation currently raises ``NotImplementedError`` as the
    concrete experiment contract is repository specific.  Callers may monkeypatch
    this helper in tests to emulate an experiment response.
    """

    raise NotImplementedError("external curvature experiment invocation is not wired up for this repository")


def compute_cwt_curvature(
    order_field: np.ndarray,
    axis0: Sequence[float],
    axis1: Sequence[float],
    *,
    experiment_module: str | None = None,
    timeout: float = 300.0,
) -> np.ndarray:
    """Estimate curvature using a Wilson-loop construction.

    Results are memoised to avoid repeated work when the same order parameter and
    axes are provided multiple times.  When ``experiment_module`` is supplied (or
    the ``CWT_CURVATURE_EXPERIMENT`` environment variable is set) the helper will
    attempt to delegate to an external experiment via
    :func:`_invoke_curvature_experiment`.  If delegation fails the local Wilson
    loop estimator is used as a fallback to preserve the previous behaviour.
    """

    key = _curvature_cache_key(order_field, axis0, axis1)
    cached = _CURVATURE_CACHE.get(key)
    if cached is not None:
        return cached.copy()

    module_override = experiment_module or os.environ.get("CWT_CURVATURE_EXPERIMENT")
    if module_override:
        try:
            curvature = _invoke_curvature_experiment(
                order_field, axis0, axis1, module_path=str(module_override), timeout=timeout
            )
        except Exception:  # pragma: no cover - defensive fallback
            curvature = _compute_cwt_curvature_local(order_field, axis0, axis1)
    else:
        curvature = _compute_cwt_curvature_local(order_field, axis0, axis1)

    _CURVATURE_CACHE[key] = curvature.copy()
    return curvature.copy()


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


def _coerce_float(value: object) -> float | None:
    try:
        numeric = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return numeric if math.isfinite(numeric) else None


def _run_cwt_loop_local(
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
    """Evaluate a Wilson loop locally around ``record`` without external tooling."""

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
        psi_bl.conjugate()
        * psi_br
        * psi_br.conjugate()
        * psi_tr
        * psi_tr.conjugate()
        * psi_tl
        * psi_tl.conjugate()
        * psi_bl
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
                    "magnitude": float(abs(payload["order_parameter"])),
                },
            }
            for label, payload in corners.items()
        ],
    }
    return loop_report


_DEFAULT_LOOP_MODULE = "experiments.loop_at_hotspot.run"
_LOOP_TIMEOUT = 300.0


def _run_cwt_loop_experiment(
    base_report: Mapping[str, object],
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
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_root = Path(tmp_dir)
        hotspot_path = tmp_root / "hotspots.json"
        summary_path = tmp_root / "summary.json"
        hotspot_path.write_text(json.dumps(descriptor, indent=2, ensure_ascii=False), encoding="utf-8")

        extent_value = max(float(extent_scale), 1e-4)
        axis_i, axis_j = center_axes
        command = [
            sys.executable,
            "-m",
            module_path,
            "--hotspots",
            str(hotspot_path),
            "--axes",
            axis_i,
            axis_j,
            "--extents",
            f"{extent_value:.12g}",
            "--limit",
            "1",
            "--save-summary",
            str(summary_path),
            "--base-steps",
            str(max(int(sample_steps), 1)),
            "--neighbor-settle-steps",
            str(max(int(warmup_steps), 1)),
        ]

        graph_kind = None
        center_meta = base_report.get("center")
        if isinstance(center_meta, Mapping):
            graph_kind = center_meta.get("graph")
        if not graph_kind:
            graph_kind = base_report.get("graph_kind")
        if not graph_kind:
            graph_kind = descriptor.get("graph")
        if not graph_kind:
            top_tiles = descriptor.get("top_tiles")
            if isinstance(top_tiles, Sequence):
                for entry in top_tiles:
                    if isinstance(entry, Mapping):
                        graph_kind = entry.get("graph_kind")
                        if graph_kind:
                            break
        if graph_kind:
            command.extend(["--graph", str(graph_kind)])

        fs_guard = None
        loop_meta = base_report.get("loop")
        if isinstance(loop_meta, Mapping):
            fs_guard = loop_meta.get("fs_guard")
        if fs_guard is None:
            fs_guard = os.environ.get("CWT_LOOP_FS_GUARD")
        guard_value = _coerce_float(fs_guard)
        if guard_value is not None:
            command.extend(["--fs-guard", f"{guard_value:.12g}"])

        if seed is not None:
            command.extend(["--seed", str(int(seed))])

        env = os.environ.copy()
        env["PYTHONHASHSEED"] = "0"
        if seed is not None:
            env["CWT_SEED"] = str(int(seed))

        experiment_warnings: list[str] = []

        def _warn_overrun(elapsed: float) -> None:
            message = f"Loop experiment runtime {elapsed:.3f}s exceeded the {timeout:.3f}s budget."
            warnings.warn(message, RuntimeWarning)
            experiment_warnings.append(message)

        with time_budget_guard(timeout, raise_on_exceed=False, on_exceed=_warn_overrun) as guard:
            subprocess.run(command, check=True, env=env, timeout=timeout)

        duration = guard.elapsed if guard.elapsed is not None else 0.0

        if not summary_path.exists():
            raise RuntimeError("loop experiment completed without producing a summary")

        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        hotspots = payload.get("hotspots")
        if not isinstance(hotspots, list) or not hotspots:
            raise RuntimeError("loop experiment summary did not contain hotspots")
        hotspot = hotspots[0]
        if not isinstance(hotspot, Mapping):
            raise RuntimeError("loop experiment hotspot entry is not a mapping")

        extents = hotspot.get("extents")
        if not isinstance(extents, list) or not extents:
            raise RuntimeError("loop experiment hotspot missing extent summaries")
        extent_entry = extents[0]
        if not isinstance(extent_entry, Mapping):
            raise RuntimeError("loop experiment extent summary is not a mapping")

        extent_spec = extent_entry.get("extents")
        axis_map: Mapping[str, object] = {}
        if isinstance(extent_spec, Mapping):
            candidate = extent_spec.get("map")
            if isinstance(candidate, Mapping):
                axis_map = candidate

        def _orientation_stats(name: str) -> dict[str, object]:
            payload_inner = extent_entry.get(name)
            if not isinstance(payload_inner, Mapping):
                return {"orientation": name, "available": False}
            phi = _coerce_float(payload_inner.get("phi"))
            memory = payload_inner.get("memory")
            readout = None
            if isinstance(memory, list) and memory:
                readout = _coerce_float(memory[-1])
            return {
                "orientation": name,
                "available": True,
                "phi": phi,
                "phi_abs": abs(phi) if isinstance(phi, float) and math.isfinite(phi) else None,
                "phi_missing": bool(payload_inner.get("phi_missing")),
                "fs_p95": _coerce_float(payload_inner.get("fs_p95")),
                "fs_guard_exceeded": bool(payload_inner.get("fs_guard_exceeded")),
                "readout": readout,
            }

        orientations = [_orientation_stats("ccw"), _orientation_stats("cw")]
        phi_candidates = [item.get("phi") for item in orientations if isinstance(item.get("phi"), float)]
        phi_abs = max((abs(value) for value in phi_candidates if math.isfinite(value)), default=float("nan"))
        guard_flag = any(bool(item.get("fs_guard_exceeded")) for item in orientations)

        payload_report = {
            "module": module_path,
            "orientations": orientations,
            "extent": {axis: _coerce_float(axis_map.get(axis)) for axis in center_axes},
            "phi_abs": phi_abs,
            "fs_guard_exceeded": guard_flag,
            "summary_path": str(summary_path),
            "duration": float(duration),
            "time_budget_seconds": float(timeout),
        }
        if experiment_warnings:
            payload_report["warnings"] = list(experiment_warnings)

        return payload_report


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
    """Evaluate a Wilson loop around ``record``.

    The local Wilson-loop estimate is always returned.  When an external
    experiment module is available the report is enriched with its telemetry,
    while gracefully degrading if the probe fails or times out.
    """

    base_report = _run_cwt_loop_local(
        adjacency,
        record,
        kappa_values,
        sigma_values,
        dt=dt,
        warmup_steps=warmup_steps,
        sample_steps=sample_steps,
        integration=integration,
        intrinsic_mean=intrinsic_mean,
        base_seed=base_seed,
        delta_scale=delta_scale,
    )

    module_override = None
    if isinstance(record.get("loop_experiment"), str):
        module_override = str(record["loop_experiment"])
    module_path = module_override or os.environ.get("CWT_LOOP_EXPERIMENT") or _DEFAULT_LOOP_MODULE

    center = base_report.get("center") if isinstance(base_report.get("center"), Mapping) else {}
    center_kappa = _coerce_float(center.get("kappa")) if center else None
    if center_kappa is None:
        center_kappa = _coerce_float(record.get("kappa"))
    center_sigma = _coerce_float(center.get("sigma")) if center else None
    if center_sigma is None:
        center_sigma = _coerce_float(record.get("sigma"))

    descriptor = {
        "axes": ["kappa", "sigma"],
        "top_tiles": [
            {
                "indices": [int(record.get("kappa_index", 0)), int(record.get("sigma_index", 0))],
                "coordinates": {"kappa": center_kappa or 0.0, "sigma": center_sigma or 0.0},
                "omega": _coerce_float(record.get("omega")),
                "omega_abs": _coerce_float(record.get("omega_abs")),
                "graph_kind": record.get("graph_kind"),
            }
        ],
    }

    warnings: list[str] = []
    try:
        experiment_report = _run_cwt_loop_experiment(
            base_report,
            module_path=module_path,
            descriptor=descriptor,
            center_axes=("kappa", "sigma"),
            extent_scale=max(
                (
                    float(base_report.get("loop", {}).get("span_kappa", 0.0))
                    if isinstance(base_report.get("loop"), Mapping)
                    else 0.0
                ),
                (
                    float(base_report.get("loop", {}).get("span_sigma", 0.0))
                    if isinstance(base_report.get("loop"), Mapping)
                    else 0.0
                ),
                float(delta_scale),
            ),
            sample_steps=sample_steps,
            warmup_steps=warmup_steps,
            seed=base_seed,
            timeout=_LOOP_TIMEOUT,
        )
        base_report = dict(base_report)
        base_report["experiment"] = experiment_report
        if isinstance(experiment_report, Mapping) and experiment_report.get("warnings"):
            experiment_warnings = experiment_report.get("warnings")
            if isinstance(experiment_warnings, Sequence):
                warnings.extend(str(item) for item in experiment_warnings)
    except subprocess.TimeoutExpired:
        warnings.append("loop_experiment_timeout")
    except FileNotFoundError as exc:
        warnings.append(f"loop_experiment_missing:{exc}")
    except Exception as exc:  # pragma: no cover - defensive catch-all
        warnings.append(f"loop_experiment_error:{exc}")

    if warnings:
        base_report = dict(base_report)
        base_report.setdefault("warnings", warnings)

    return base_report


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
        time_budget=namespace.time_budget,
        map_to_cwt=namespace.map_to_cwt,
    )

    base_seed = int(config.seed if config.seed is not None else 0)
    seed_everything(base_seed)

    graph_params = _parse_graph_params(namespace.graph_param)
    graph_seed = namespace.graph_seed if namespace.graph_seed is not None else base_seed
    adjacency = _build_adjacency(namespace.graph_kind, graph_params, graph_seed)
    base_radius, base_gap = _adjacency_spectrum(adjacency)

    axis_map = load_axis_map(Path(config.axis_map)) if config.map_to_cwt else {}
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

    time_budget = max(float(config.time_budget), 0.0)
    budget_notes: list[str] = []

    def _warn_overrun(elapsed: float) -> None:
        message = f"Kuramoto sweep runtime {elapsed:.3f}s exceeded the {time_budget:.3f}s budget."
        warnings.warn(message, RuntimeWarning)
        budget_notes.append(message)

    with time_budget_guard(
        time_budget if time_budget > 0 else float("inf"),
        raise_on_exceed=False,
        on_exceed=_warn_overrun,
    ) as guard:
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
    elapsed = guard.elapsed if guard.elapsed is not None else 0.0

    if namespace.compute_curvature:
        curvature_grid = compute_cwt_curvature(order_grid, kappa_values, sigma_values)
    else:
        curvature_grid = _finite_difference_curvature(r_mean_grid, kappa_values, sigma_values)
    curvature_abs = np.abs(curvature_grid)

    order_magnitude_grid = np.abs(order_grid)
    proxy_components = [
        _finite_difference_curvature(r_mean_grid, kappa_values, sigma_values),
        _finite_difference_curvature(order_magnitude_grid, kappa_values, sigma_values),
    ]
    omega_proxy_grid = combine_proxy_magnitudes(proxy_components)

    accumulator = Accumulator()
    record_lookup: dict[tuple[int, int], dict[str, object]] = {}
    for record in records:
        i = int(record["kappa_index"])
        j = int(record["sigma_index"])
        omega = float(curvature_grid[i, j]) if np.isfinite(curvature_grid[i, j]) else float("nan")
        omega_abs = float(curvature_abs[i, j]) if np.isfinite(curvature_abs[i, j]) else float("nan")
        proxy_value = float(omega_proxy_grid[i, j]) if np.isfinite(omega_proxy_grid[i, j]) else float("nan")
        record["omega"] = omega
        record["omega_abs"] = omega_abs
        record["omega_abs_proxy"] = proxy_value
        accumulator.add(record)
        record_lookup[(i, j)] = record

    graph_id = _graph_identifier(namespace.graph_kind, graph_params)
    seed_label = base_seed
    output_dir = ensure_outdir("kuramoto", namespace.output_dir, graph_id, seed_label)
    metrics_path = output_dir / "metrics.csv"
    accumulator.to_csv(metrics_path)

    heatmap_path = write_heatmap_png(
        metrics_path,
        output_dir,
        axes=("kappa", "sigma"),
        axis_map=axis_map,
        value_column="omega_abs",
    )
    write_heatmap_png(
        metrics_path,
        output_dir,
        axes=("kappa", "sigma"),
        axis_map=axis_map,
        filename="omega_heatmap_proxy.png",
        value_column="omega_abs_proxy",
        colorbar_label=r"|Ω| proxy",
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
                base_seed=base_seed,
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
        if budget_notes:
            print(budget_notes[-1])
        if namespace.enable_loops and loop_reports:
            print(f"Loop diagnostics written to {loop_reports[0].parent} ({len(loop_reports)} tiles).")

    return config


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

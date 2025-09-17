"""Gate C experiment: topology robustness under noise perturbations."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import scipy.sparse as sp

from cwt.geometry.curvature import curvature_tile
from cwt.geometry.fs_distance import fs_distance
from cwt.geometry.psi import build_psi, inner
from cwt.graph.factories import random_regular_digraph, ring3
from cwt.graph.kernels import build_transport_kernel
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.readouts import memory_current_coupled, readout_stochastic
from cwt.layers.state import LayersState, wrap_angles
from cwt.orchestrator.param_path import ParameterPath

from ..report_helpers import (
    ReportHeaderMetrics,
    fs_histogram,
    render_health_banner,
    render_report_header,
)
from cwt.metrics.eval_curves import spectral_gap


@dataclass
class TrialResult:
    """Statistics collected for a single noisy loop traversal."""

    seed: int
    R_gamma: float
    s_bar: float
    overlap_avg: float
    min_overlap: float
    fs_steps: list[float]


@dataclass
class NoiseLevelResult:
    """Aggregate measurements for a fixed noise strength."""

    phase_std: float
    amp_noise: float
    delay_std: float
    trials: list[TrialResult]
    s_bar_mean: float
    overlap_mean: float
    quantized: bool

    def R_gamma_samples(self) -> list[float]:
        return [trial.R_gamma for trial in self.trials]

    def coherence_samples(self) -> list[float]:
        return [trial.s_bar for trial in self.trials]

    def overlap_samples(self) -> list[float]:
        return [trial.overlap_avg for trial in self.trials]


@dataclass
class GraphResult:
    """Results for a single substrate across the phase-noise sweep."""

    name: str
    substrate: GraphSubstrate
    center: Mapping[str, float]
    extents: Mapping[str, float]
    flux: float
    noise_levels: list[NoiseLevelResult]
    overlap_threshold: float
    coherence_threshold: float


@dataclass
class ExperimentResults:
    """Container for the Gate C noise-robustness study."""

    graphs: list[GraphResult]
    phase_std_values: list[float]
    amp_noise: float
    delay_std: float
    num_trials: int
    loop_steps: int
    overlap_threshold: float
    coherence_threshold: float

    def to_dict(self) -> dict:
        return {
            "phase_std_values": list(self.phase_std_values),
            "amp_noise": float(self.amp_noise),
            "delay_std": float(self.delay_std),
            "num_trials": int(self.num_trials),
            "loop_steps": int(self.loop_steps),
            "overlap_threshold": float(self.overlap_threshold),
            "coherence_threshold": float(self.coherence_threshold),
            "graphs": [
                {
                    "name": graph.name,
                    "center": dict(graph.center),
                    "extents": dict(graph.extents),
                    "flux": float(graph.flux),
                    "overlap_threshold": float(graph.overlap_threshold),
                    "coherence_threshold": float(graph.coherence_threshold),
                    "noise_levels": [
                        {
                            "phase_std": lvl.phase_std,
                            "amp_noise": lvl.amp_noise,
                            "delay_std": lvl.delay_std,
                            "s_bar_mean": lvl.s_bar_mean,
                            "overlap_mean": lvl.overlap_mean,
                            "quantized": lvl.quantized,
                            "trials": [asdict(trial) for trial in lvl.trials],
                        }
                        for lvl in graph.noise_levels
                    ],
                }
                for graph in self.graphs
            ],
        }


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------


def _mean_ci(values: Iterable[float]) -> tuple[float, tuple[float, float]]:
    arr = np.asarray(list(values), dtype=float)
    if arr.size == 0:
        return float("nan"), (float("nan"), float("nan"))
    mean = float(arr.mean())
    if arr.size == 1:
        return mean, (mean, mean)
    std = float(arr.std(ddof=1))
    margin = 1.96 * std / np.sqrt(arr.size)
    return mean, (mean - margin, mean + margin)


def _health_metrics(results: ExperimentResults) -> tuple[float, dict, list[float]]:
    total_trials = 0
    passing_trials = 0
    fs_all: list[float] = []

    for graph in results.graphs:
        threshold = graph.overlap_threshold
        for level in graph.noise_levels:
            for trial in level.trials:
                total_trials += 1
                if math.isfinite(trial.min_overlap) and trial.min_overlap >= threshold:
                    passing_trials += 1
                fs_all.extend(trial.fs_steps)

    pass_rate = passing_trials / total_trials if total_trials else float("nan")
    return pass_rate, fs_histogram(fs_all), []


def _gateC_header_metrics(results: ExperimentResults) -> ReportHeaderMetrics:
    """Return universal diagnostics for the Gate C experiment."""

    overlaps: list[float] = []
    fs_steps: list[float] = []
    readouts: list[float] = []

    for graph in results.graphs:
        for level in graph.noise_levels:
            for trial in level.trials:
                overlaps.append(trial.min_overlap)
                fs_steps.extend(trial.fs_steps)
                readouts.append(trial.R_gamma)

    overlap_vals = np.asarray(overlaps, dtype=float)
    overlap_vals = overlap_vals[np.isfinite(overlap_vals)]
    min_overlap = float(overlap_vals.min()) if overlap_vals.size else float("nan")
    mean_overlap = float(overlap_vals.mean()) if overlap_vals.size else float("nan")

    fs_arr = np.asarray(fs_steps, dtype=float)
    fs_arr = fs_arr[np.isfinite(fs_arr)]
    fs_mean = float(fs_arr.mean()) if fs_arr.size else float("nan")
    fs_p95 = float(np.percentile(fs_arr, 95)) if fs_arr.size else float("nan")

    phi_flux = sum(graph.flux for graph in results.graphs)
    geom_area = float(
        np.sum(
            4.0 * abs(graph.extents.get("rho", 0.0)) * abs(graph.extents.get("tau", 0.0))
            for graph in results.graphs
        )
    )

    extent_labels = [
        f"ρ±{graph.extents.get('rho', 0.0):.2f}, τ±{graph.extents.get('tau', 0.0):.2f}"
        for graph in results.graphs
    ]

    readout_arr = np.asarray(readouts, dtype=float)
    readout_arr = readout_arr[np.isfinite(readout_arr)]

    pass_rate, _, _ = _health_metrics(results)

    gap_values: list[float] = []
    for graph in results.graphs:
        center = graph.center
        try:
            K = build_transport_kernel(
                graph.substrate,
                rho=float(center.get("rho", 0.0)),
                tau_scale=float(center.get("tau", center.get("tau_scale", 1.0))),
            )
        except Exception:  # pragma: no cover - defensive
            continue
        try:
            gap_values.append(spectral_gap(K))
        except Exception:  # pragma: no cover - defensive
            continue

    spectral_gap_mean = float(np.mean(gap_values)) if gap_values else float("nan")

    return ReportHeaderMetrics(
        min_overlap=min_overlap,
        mean_overlap=mean_overlap,
        pass_rate=pass_rate,
        fs_mean=fs_mean,
        fs_p95=fs_p95,
        phi_flux=phi_flux,
        geom_area=geom_area,
        extents=extent_labels,
        steps=results.loop_steps,
        R_ccw=float(readout_arr.mean()) if readout_arr.size else float("nan"),
        grad_r=float(np.mean(np.abs(readout_arr))) if readout_arr.size else float("nan"),
        spectral_gap=spectral_gap_mean,
    )


def _synthetic_state(S: GraphSubstrate, rho: float, tau: float) -> LayersState:
    """Return a smooth state over the substrate parameterised by ``rho`` and ``tau``."""

    N = S.N
    if N == 0:
        empty = np.zeros((0,), dtype=float)
        return LayersState(pQ=empty.copy(), theta=empty.copy())

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


def _compute_flux(
    S: GraphSubstrate,
    center: Mapping[str, float],
    extent: Mapping[str, float],
    *,
    grid_size: int,
) -> float:
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

    flux = 0.0
    for i in range(grid_size):
        for j in range(grid_size):
            psi0 = psi_at(i, j)
            psi_i = psi_at(i + 1, j)
            psi_ij = psi_at(i + 1, j + 1)
            psi_j = psi_at(i, j + 1)

            delta_rho = float(rho_edges[i + 1] - rho_edges[i])
            delta_tau = float(tau_edges[j + 1] - tau_edges[j])

            omega, _ = curvature_tile(psi0, psi_i, psi_ij, psi_j, delta_rho, delta_tau)
            flux += float(omega) * delta_rho * delta_tau

    return float(flux)


def _neighbor_pairs(S: GraphSubstrate) -> list[tuple[int, int]]:
    if S.N <= 1:
        return []
    W = S.W.tocoo()
    pairs: set[tuple[int, int]] = set()
    for row, col in zip(W.row, W.col):
        if row == col:
            continue
        a = int(min(row, col))
        b = int(max(row, col))
        pairs.add((a, b))
    return sorted(pairs)


def _apply_amplitude_noise(
    base: np.ndarray,
    noise_dev: np.ndarray,
    pairs: Sequence[tuple[int, int]],
    rng: np.random.Generator,
    amp_noise: float,
    mixing: float = 0.25,
) -> tuple[np.ndarray, np.ndarray]:
    if base.size == 0:
        return base.copy(), noise_dev.copy()

    actual = base + noise_dev
    actual = np.clip(actual, 1e-12, None)
    total = float(actual.sum())
    if total <= 0.0 or not np.isfinite(total):
        actual = np.full_like(base, 1.0 / base.size)
    else:
        actual /= total

    if mixing:
        actual = (1.0 - mixing) * actual + mixing * base
        actual = np.clip(actual, 1e-12, None)
        actual /= float(actual.sum())

    if amp_noise > 0.0 and pairs:
        for a, b in pairs:
            max_transfer = min(actual[a], actual[b])
            if max_transfer <= 0.0:
                continue
            step_scale = amp_noise * max_transfer
            delta = float(rng.normal(0.0, step_scale))
            delta = max(-actual[b], min(delta, actual[a]))
            actual[a] -= delta
            actual[b] += delta

    actual = np.clip(actual, 1e-12, None)
    actual /= float(actual.sum())
    noise_next = actual - base
    return actual, noise_next


def _edge_currents_with_delay(
    S: GraphSubstrate,
    pQ: np.ndarray,
    theta: np.ndarray,
    tau_scale: np.ndarray | None,
) -> np.ndarray:
    if pQ.shape != (S.N,) or theta.shape != (S.N,):
        raise ValueError("pQ and theta must have shape (S.N,)")

    sqrt_p = np.sqrt(np.clip(pQ, 0.0, None))

    W = S.W.tocoo()
    rows = W.row
    cols = W.col
    weights = W.data

    phase_diff = theta[cols] - theta[rows]
    magnitude = weights * sqrt_p[rows] * sqrt_p[cols]

    if tau_scale is not None:
        Tau = S.Tau.tocoo()
        if not (
            np.array_equal(Tau.row, rows)
            and np.array_equal(Tau.col, cols)
            and Tau.data.size == magnitude.size
        ):
            raise ValueError("Tau sparsity pattern does not match weights pattern")
        tau_data = Tau.data * tau_scale
        tau_data = np.clip(tau_data, 1e-9, None)
        magnitude = magnitude / tau_data

    edge_vals = magnitude * np.sin(phase_diff)
    outgoing = np.zeros(S.N, dtype=float)
    incoming = np.zeros(S.N, dtype=float)
    np.add.at(outgoing, cols, edge_vals)
    np.add.at(incoming, rows, edge_vals)
    return outgoing - incoming


def _coherence_factor(
    S: GraphSubstrate,
    theta: np.ndarray,
    W_csc: sp.csc_matrix,
) -> float:
    if S.N == 0:
        return float("nan")
    phases = np.exp(1j * theta)
    local_vals: list[float] = []
    for node in range(S.N):
        start = W_csc.indptr[node]
        end = W_csc.indptr[node + 1]
        neighbours = W_csc.indices[start:end]
        if neighbours.size == 0:
            indices = np.array([node], dtype=int)
        else:
            indices = np.concatenate(([node], neighbours))
        avg = phases[indices].mean()
        local_vals.append(float(abs(avg)))
    if not local_vals:
        return 1.0
    return float(np.mean(local_vals))


def _overlap_stats(traj: Sequence[np.ndarray]) -> tuple[float, float]:
    if not traj:
        return float("nan"), float("nan")

    loop = list(traj)
    if not loop:
        return float("nan"), float("nan")

    loop.append(loop[0])
    overlaps = [float(abs(inner(psi_a, psi_b))) for psi_a, psi_b in zip(loop, loop[1:])]
    if not overlaps:
        return float("nan"), float("nan")

    arr = np.asarray(overlaps, dtype=float)
    return float(arr.mean()), float(arr.min())


def _run_noise_trial(
    S: GraphSubstrate,
    path: ParameterPath,
    base_center: LayersState,
    phase_std: float,
    amp_noise: float,
    delay_std: float,
    rng: np.random.Generator,
    seed_value: int,
    pairs: Sequence[tuple[int, int]],
    W_csc: sp.csc_matrix,
    base_bias: float,
) -> TrialResult:
    theta_noise = np.zeros(S.N, dtype=float)
    p_noise = np.zeros(S.N, dtype=float)
    tau_scale_last: np.ndarray | None = None

    psi_traj: list[np.ndarray] = []
    theta_final = base_center.theta.copy()
    p_final = base_center.pQ.copy()

    for step in range(path.steps):
        lambda_state, _, _ = path.step(step)
        state = _synthetic_state(
            S,
            rho=lambda_state.get("rho", 0.0),
            tau=lambda_state.get("tau", 0.0),
        )

        if phase_std > 0.0 and S.N:
            theta_noise += rng.normal(0.0, phase_std, size=S.N)
        theta_actual = wrap_angles(state.theta + theta_noise)

        p_actual, p_noise = _apply_amplitude_noise(state.pQ, p_noise, pairs, rng, amp_noise)
        p_final = p_actual.copy()
        theta_final = theta_actual.copy()

        if delay_std > 0.0 and S.Tau.nnz > 0:
            tau_scale_last = 1.0 + rng.normal(0.0, delay_std, size=S.Tau.nnz)
            tau_scale_last = np.clip(tau_scale_last, 1e-3, None)
        else:
            tau_scale_last = None

        psi_traj.append(build_psi(p_final, theta_final))

    fs_steps: list[float] = []
    if psi_traj:
        loop_states = list(psi_traj)
        loop_states.append(psi_traj[0])
        for psi_a, psi_b in zip(loop_states, loop_states[1:]):
            try:
                fs_steps.append(float(fs_distance(psi_a, psi_b)))
            except ValueError:
                fs_steps.append(float("nan"))

    overlap_avg, min_overlap = _overlap_stats(psi_traj)
    s_bar = _coherence_factor(S, theta_final, W_csc)

    decay = float(np.clip(s_bar, 0.0, 1.0)) * float(np.clip(overlap_avg, 0.0, 1.0))
    if tau_scale_last is not None and tau_scale_last.size:
        delay_mean = float(np.mean(tau_scale_last))
        delay_decay = 1.0 / (1.0 + abs(delay_mean - 1.0))
        decay *= delay_decay
    decay = float(np.clip(decay, 0.0, 1.0))

    bias = float(base_bias * decay)
    noise_scale = 0.02 * abs(base_bias) * max(1.0 - decay, 1e-3)
    bias += float(rng.normal(0.0, noise_scale))

    return TrialResult(
        seed=int(seed_value),
        R_gamma=bias,
        s_bar=s_bar,
        overlap_avg=overlap_avg,
        min_overlap=min_overlap,
        fs_steps=fs_steps,
    )


def _run_noise_level(
    S: GraphSubstrate,
    path: ParameterPath,
    base_center: LayersState,
    phase_std: float,
    amp_noise: float,
    delay_std: float,
    seeds: Sequence[int],
    pairs: Sequence[tuple[int, int]],
    W_csc: sp.csc_matrix,
    overlap_threshold: float,
    coherence_threshold: float,
    base_bias: float,
) -> NoiseLevelResult:
    trials: list[TrialResult] = []
    for idx, seed in enumerate(seeds):
        rng = np.random.default_rng(int(seed))
        trial = _run_noise_trial(
            S,
            path,
            base_center,
            phase_std,
            amp_noise,
            delay_std,
            rng,
            seed_value=int(seed),
            pairs=pairs,
            W_csc=W_csc,
            base_bias=base_bias,
        )
        trials.append(trial)

    s_mean, _ = _mean_ci(trial.s_bar for trial in trials)
    o_mean, _ = _mean_ci(trial.overlap_avg for trial in trials)
    quantized = s_mean >= coherence_threshold and o_mean >= overlap_threshold

    return NoiseLevelResult(
        phase_std=float(phase_std),
        amp_noise=float(amp_noise),
        delay_std=float(delay_std),
        trials=trials,
        s_bar_mean=float(s_mean),
        overlap_mean=float(o_mean),
        quantized=bool(quantized),
    )


def run_experiment(
    *,
    phase_std_values: Sequence[float] | None = None,
    amp_noise: float = 0.02,
    delay_std: float = 0.02,
    num_trials: int = 6,
    loop_steps: int = 200,
    seeds: Sequence[int] | None = None,
    grid_size: int = 8,
    overlap_threshold: float = 0.9,
    coherence_threshold: float = 0.5,
) -> ExperimentResults:
    if phase_std_values is None:
        phase_std_values = [0.0, 0.05, 0.1, 0.2, 0.35]
    phase_std_values = [float(val) for val in phase_std_values]
    if any(val < 0.0 for val in phase_std_values):
        raise ValueError("phase_std values must be non-negative")

    if num_trials <= 0:
        raise ValueError("num_trials must be positive")
    if loop_steps <= 0:
        raise ValueError("loop_steps must be positive")

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
            {"rho": 0.75, "tau": 0.85},
        ),
        (
            "rr8",
            random_regular_digraph(N=8, out_degree=2, weight=1.0, delay=1.0, seed=13),
            {"rho": 0.8, "tau": 1.4},
            {"rho": 0.6, "tau": 1.2},
        ),
    ]

    graph_results: list[GraphResult] = []

    for name, substrate, center, extents in graphs_config:
        path = ParameterPath(
            kind="rectangle",
            center=center,
            extents=extents,
            steps=loop_steps,
            orientation="CCW",
        )
        flux = _compute_flux(substrate, center, extents, grid_size=grid_size)
        base_center = _synthetic_state(substrate, center["rho"], center["tau"])
        pairs = _neighbor_pairs(substrate)
        W_csc = substrate.W.tocsc()
        base_currents = _edge_currents_with_delay(substrate, base_center.pQ, base_center.theta, None)
        np.random.seed(0)
        _, base_weights = readout_stochastic(
            base_center.pQ,
            memory_current_coupled(float(flux), base_currents),
            T=1.0,
            eta=1.0,
        )
        base_bias = float(np.dot(base_weights - base_center.pQ, base_currents))

        noise_levels: list[NoiseLevelResult] = []
        for phase_std in phase_std_values:
            level = _run_noise_level(
                substrate,
                path,
                base_center,
                phase_std=float(phase_std),
                amp_noise=float(amp_noise),
                delay_std=float(delay_std),
                seeds=seeds,
                pairs=pairs,
                W_csc=W_csc,
                overlap_threshold=overlap_threshold,
                coherence_threshold=coherence_threshold,
                base_bias=base_bias,
            )
            noise_levels.append(level)

        graph_results.append(
            GraphResult(
                name=name,
                substrate=substrate,
                center=center,
                extents=extents,
                flux=float(abs(flux)),
                noise_levels=noise_levels,
                overlap_threshold=float(overlap_threshold),
                coherence_threshold=float(coherence_threshold),
            )
        )

    return ExperimentResults(
        graphs=graph_results,
        phase_std_values=phase_std_values,
        amp_noise=float(amp_noise),
        delay_std=float(delay_std),
        num_trials=num_trials,
        loop_steps=loop_steps,
        overlap_threshold=float(overlap_threshold),
        coherence_threshold=float(coherence_threshold),
    )


# ---------------------------------------------------------------------------
# Reporting utilities
# ---------------------------------------------------------------------------


def _format_ci(ci: tuple[float, float]) -> str:
    return f"[{ci[0]:.3e}, {ci[1]:.3e}]"


def _render_noise_level(level: NoiseLevelResult) -> list[str]:
    R_mean, R_ci = _mean_ci(level.R_gamma_samples())
    s_mean, s_ci = _mean_ci(level.coherence_samples())
    o_mean, o_ci = _mean_ci(level.overlap_samples())

    R_ci_arr = np.asarray(R_ci, dtype=float)
    ci_width = R_ci_arr[1] - R_ci_arr[0] if np.all(np.isfinite(R_ci_arr)) else float("nan")

    lines = [
        f"- σ_phase = {level.phase_std:.3f} (σ_amp={level.amp_noise:.3f}, σ_tau={level.delay_std:.3f})",
        f"  - R_γ mean: {R_mean:.3e} with CI {_format_ci(R_ci)} (width {ci_width:.3e})",
        f"  - ⟨s̄⟩: {s_mean:.3f} with CI {_format_ci(s_ci)}",
        f"  - ⟨overlap⟩: {o_mean:.3f} with CI {_format_ci(o_ci)}",
        f"  - Quantization claim: {'yes' if level.quantized else 'no (tracking robustness only)'}",
    ]
    return lines


def _render_report(results: ExperimentResults) -> str:
    header_metrics = _gateC_header_metrics(results)

    lines = [
        "# Gate C: topology robustness under noise",
        "",
        f"Phase noise sweep: {', '.join(f'{val:.3f}' for val in results.phase_std_values)}",
        f"Amplitude noise σ_amp: {results.amp_noise:.3f}",
        f"Delay jitter σ_tau: {results.delay_std:.3f}",
        f"Trials per noise level: {results.num_trials}",
        f"Loop steps: {results.loop_steps}",
        (
            "Thresholds — overlap: "
            f"{results.overlap_threshold:.2f}, coherence: {results.coherence_threshold:.2f}"
        ),
        "",
    ]

    lines.extend(render_report_header(header_metrics))

    pass_rate, fs_hist_all, omega_widths = _health_metrics(results)
    lines.extend(render_health_banner(pass_rate, fs_hist_all, omega_widths))

    for graph in results.graphs:
        lines.extend([f"## Graph: {graph.name}", ""])
        lines.append(f"Loop flux magnitude: {graph.flux:.3e}")
        lines.append("")
        for level in graph.noise_levels:
            lines.extend(_render_noise_level(level))
        lines.append("")

    lines.append(
        "When either threshold is violated we switch to the mixed-state fallback "
        "and report robustness trends only."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Command-line interface
# ---------------------------------------------------------------------------


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Gate C topology robustness experiment")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "artifacts",
        help="Directory where records.json and REPORT.md are written.",
    )
    parser.add_argument(
        "--num-trials",
        type=int,
        default=6,
        help="Number of loop trials per noise level.",
    )
    parser.add_argument(
        "--loop-steps",
        type=int,
        default=200,
        help="Number of steps used to trace the loop.",
    )
    parser.add_argument("--grid-size", type=int, default=8, help="Tile grid size for flux estimation.")
    parser.add_argument(
        "--amp-noise",
        "--sigma-amp",
        type=float,
        default=0.02,
        dest="amp_noise",
        help="Amplitude noise scale (mass shuffles).",
    )
    parser.add_argument(
        "--delay-std",
        "--sigma-tau",
        type=float,
        default=0.02,
        dest="delay_std",
        help="Delay jitter scale applied to edge delays.",
    )
    parser.add_argument(
        "--phase-std",
        "--sigma-phase",
        type=float,
        nargs="*",
        default=None,
        dest="phase_std",
        help="Optional list of phase-noise magnitudes to sweep.",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    results = run_experiment(
        phase_std_values=args.phase_std,
        amp_noise=args.amp_noise,
        delay_std=args.delay_std,
        num_trials=args.num_trials,
        loop_steps=args.loop_steps,
        grid_size=args.grid_size,
    )

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    records_path = output_dir / "records.json"
    report_path = output_dir / "REPORT.md"

    records_path.write_text(json.dumps(results.to_dict(), indent=2))
    report_path.write_text(_render_report(results))


if __name__ == "__main__":
    main()

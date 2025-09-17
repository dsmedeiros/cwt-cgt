"""Gate B experiment: critical ridge finder via metric trace hotspots."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from numpy.typing import ArrayLike
from scipy.sparse.linalg import ArpackNoConvergence, eigs
from scipy.stats import rankdata

from cwt.geometry.curvature import curvature_tile
from cwt.geometry.metric import metric_tile
from cwt.geometry.psi import build_psi
from cwt.graph.factories import random_regular_digraph
from cwt.graph.kernels import build_transport_kernel
from cwt.graph.substrate import GraphSubstrate, build_substrate
from cwt.layers.q_update import q_step
from cwt.layers.state import LayersState, wrap_angles
from cwt.layers.theta_update import build_J_from_W, omega_from_delays, theta_step

from ..report_helpers import ReportHeaderMetrics, render_report_header


@dataclass(frozen=True)
class SimulationConfig:
    """Configuration controlling the short-run layer dynamics."""

    transient_steps: int = 150
    sample_steps: int = 40
    eta_q: float = 0.6
    zeta: float = 1.2
    omega_scale: float = 1.0
    theta_noise: float = 0.02
    average_window: int = 10
    seed: int = 12345

    def total_steps(self) -> int:
        return int(self.transient_steps + self.sample_steps)


@dataclass(frozen=True)
class DetectionMetrics:
    """Summary statistics for the hotspot detector."""

    auc: float
    auc_ci: tuple[float, float]
    roc_fpr: np.ndarray
    roc_tpr: np.ndarray
    roc_thresholds: np.ndarray
    gap_threshold: float
    delta_r_threshold: float
    corr_trace_gap: float
    corr_trace_delta_r: float

    def to_json(self) -> Mapping[str, float | list[float]]:
        return {
            "auc": float(self.auc),
            "auc_ci": [float(x) for x in self.auc_ci],
            "gap_threshold": float(self.gap_threshold),
            "delta_r_threshold": float(self.delta_r_threshold),
            "corr_trace_gap": float(self.corr_trace_gap),
            "corr_trace_delta_r": float(self.corr_trace_delta_r),
        }


@dataclass
class GraphScanResult:
    """Container bundling all artefacts for a single graph substrate."""

    name: str
    substrate: GraphSubstrate
    rho_values: np.ndarray
    tau_values: np.ndarray
    trace_g: np.ndarray
    g_rho_rho: np.ndarray
    g_tau_tau: np.ndarray
    curvature_abs: np.ndarray
    spectral_gap: np.ndarray
    kuramoto_r: np.ndarray
    r_gradient: np.ndarray
    detection: DetectionMetrics

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "rho_values": self.rho_values.tolist(),
            "tau_values": self.tau_values.tolist(),
            "trace_g": self.trace_g.tolist(),
            "g_rho_rho": self.g_rho_rho.tolist(),
            "g_tau_tau": self.g_tau_tau.tolist(),
            "curvature_abs": self.curvature_abs.tolist(),
            "spectral_gap": self.spectral_gap.tolist(),
            "kuramoto_r": self.kuramoto_r.tolist(),
            "r_gradient": self.r_gradient.tolist(),
            "detection": self.detection.to_json(),
        }


# ---------------------------------------------------------------------------
# Utility functions
# ---------------------------------------------------------------------------


def _seed_for_point(config: SimulationConfig, rho: float, tau: float) -> int:
    """Generate a reproducible seed for a grid point."""

    base = int(config.seed)
    rho_term = int(round(abs(rho) * 1_000))
    tau_term = int(round(abs(tau) * 1_000))
    return base + 1319 * rho_term + 9721 * tau_term


def _initial_state(S: GraphSubstrate, rng: np.random.Generator) -> LayersState:
    """Return a smooth initial state used when no warm start is available."""

    N = S.N
    if N == 0:
        return LayersState(pQ=np.zeros((0,), dtype=float), theta=np.zeros((0,), dtype=float))

    pQ = np.full(N, 1.0 / N, dtype=float)
    base_angles = np.linspace(-np.pi, np.pi, num=N, endpoint=False)
    theta = wrap_angles(base_angles + rng.normal(0.0, 0.05, size=N))
    return LayersState(pQ=pQ, theta=theta)


def kuramoto_order_parameter(theta: ArrayLike) -> float:
    """Return the Kuramoto order parameter ``r`` for the supplied phases."""

    angles = np.asarray(theta, dtype=float)
    if angles.size == 0:
        return float("nan")
    order = np.mean(np.exp(1j * angles))
    return float(np.abs(order))


def markov_spectral_gap(K) -> float:
    """Return the spectral gap ``1 - |lambda_2|`` of a column-stochastic kernel."""

    N = K.shape[0]
    if N <= 1:
        return float("nan")

    if N <= 4:
        eigenvalues = np.linalg.eigvals(K.toarray().T)
    else:
        k = min(4, N - 1)
        if k <= 0:
            return float("nan")

        try:
            eigenvalues = eigs(K.T, k=k, which="LM", maxiter=10_000, return_eigenvectors=False)
        except ArpackNoConvergence as exc:  # pragma: no cover - defensive
            eigenvalues = exc.eigenvalues
            if eigenvalues.size == 0:
                return float("nan")

    magnitudes = np.abs(eigenvalues)
    if magnitudes.size == 0:
        return float("nan")

    magnitudes = np.asarray(magnitudes, dtype=float)
    magnitudes = np.concatenate([magnitudes, np.array([1.0], dtype=float)])
    magnitudes.sort()
    lambda2 = float(magnitudes[-2])
    lambda2 = min(lambda2, 1.0)
    gap = 1.0 - lambda2
    if gap < 0.0:
        gap = 0.0
    return float(gap)


def _smooth_average(series: Sequence[float], window: int) -> float:
    arr = np.asarray(series, dtype=float)
    if arr.size == 0:
        return float("nan")
    win = max(int(window), 1)
    win = min(win, arr.size)
    return float(np.mean(arr[-win:]))


def _gateB_header_metrics(
    results: Sequence[GraphScanResult],
    sim_config: SimulationConfig,
) -> ReportHeaderMetrics:
    """Aggregate diagnostic metrics for the universal report header."""

    curvature_values: list[np.ndarray] = []
    trace_values: list[np.ndarray] = []
    spectral_values: list[np.ndarray] = []
    grad_values: list[np.ndarray] = []
    rho_bounds: list[tuple[float, float]] = []
    tau_bounds: list[tuple[float, float]] = []
    flux_estimate = 0.0

    for result in results:
        curvature_values.append(np.asarray(result.curvature_abs, dtype=float))
        trace_values.append(np.asarray(result.trace_g, dtype=float))
        spectral_values.append(np.asarray(result.spectral_gap, dtype=float))
        grad_values.append(np.asarray(result.r_gradient, dtype=float))

        rho = np.asarray(result.rho_values, dtype=float)
        tau = np.asarray(result.tau_values, dtype=float)
        if rho.size:
            rho_bounds.append((float(np.min(rho)), float(np.max(rho))))
        if tau.size:
            tau_bounds.append((float(np.min(tau)), float(np.max(tau))))

        if rho.size > 1 and tau.size > 1:
            dr = float(np.abs(rho[1] - rho[0]))
            dt = float(np.abs(tau[1] - tau[0]))
            cell_area = dr * dt
            if cell_area > 0.0:
                flux_estimate += float(np.nansum(result.curvature_abs) * cell_area)

    def _flatten_clean(values: list[np.ndarray]) -> np.ndarray:
        if not values:
            return np.asarray([], dtype=float)
        arr = np.concatenate([val.ravel() for val in values])
        mask = np.isfinite(arr)
        return arr[mask]

    curvature_flat = _flatten_clean(curvature_values)
    trace_flat = _flatten_clean(trace_values)
    spectral_flat = _flatten_clean(spectral_values)
    grad_flat = _flatten_clean(grad_values)

    if rho_bounds:
        rho_min = min(bound[0] for bound in rho_bounds)
        rho_max = max(bound[1] for bound in rho_bounds)
    else:
        rho_min = rho_max = float("nan")

    if tau_bounds:
        tau_min = min(bound[0] for bound in tau_bounds)
        tau_max = max(bound[1] for bound in tau_bounds)
    else:
        tau_min = tau_max = float("nan")

    if (
        math.isfinite(rho_min)
        and math.isfinite(rho_max)
        and math.isfinite(tau_min)
        and math.isfinite(tau_max)
    ):
        geom_area = (rho_max - rho_min) * (tau_max - tau_min)
    else:
        geom_area = float("nan")

    extent_label = (
        f"ρ∈[{rho_min:.3f}, {rho_max:.3f}], τ∈[{tau_min:.3f}, {tau_max:.3f}]"
        if math.isfinite(rho_min) and math.isfinite(rho_max)
        else ""
    )

    return ReportHeaderMetrics(
        omega_abs_mean=float(curvature_flat.mean()) if curvature_flat.size else float("nan"),
        omega_abs_median=float(np.median(curvature_flat)) if curvature_flat.size else float("nan"),
        trace_mean=float(trace_flat.mean()) if trace_flat.size else float("nan"),
        trace_min=float(trace_flat.min()) if trace_flat.size else float("nan"),
        trace_max=float(trace_flat.max()) if trace_flat.size else float("nan"),
        phi_flux=flux_estimate if flux_estimate else float("nan"),
        geom_area=geom_area,
        extents=(extent_label,) if extent_label else (),
        steps=sim_config.total_steps(),
        spectral_gap=float(spectral_flat.mean()) if spectral_flat.size else float("nan"),
        grad_r=float(np.mean(np.abs(grad_flat))) if grad_flat.size else float("nan"),
    )


def simulate_state(
    S: GraphSubstrate,
    rho: float,
    tau_scale: float,
    config: SimulationConfig,
    warm_start: LayersState | None = None,
) -> tuple[LayersState, np.ndarray, float, float]:
    """Evolve the coupled layers for a small number of steps."""

    rng = np.random.default_rng(_seed_for_point(config, rho, tau_scale))

    if warm_start is None:
        state = _initial_state(S, rng)
    else:
        state = LayersState(pQ=warm_start.pQ.copy(), theta=warm_start.theta.copy())

    K = build_transport_kernel(S, rho=rho, tau_scale=tau_scale)
    gap = markov_spectral_gap(K)
    omega = omega_from_delays(S, rho=rho, tau_scale=tau_scale, omega_scale=config.omega_scale)
    zeta_eff = config.zeta * math.exp(-0.5 * float(rho)) / (1.0 + 0.5 * float(tau_scale))
    J = build_J_from_W(S, zeta=zeta_eff)

    p = np.asarray(state.pQ, dtype=float).copy()
    theta = np.asarray(state.theta, dtype=float).copy()
    r_series: list[float] = []

    for step in range(config.total_steps()):
        theta = theta_step(theta, omega, J)
        if config.theta_noise > 0.0 and theta.size:
            theta = wrap_angles(theta + rng.normal(0.0, config.theta_noise, size=theta.shape))
        p, _ = q_step(p, K, eta=config.eta_q)
        if step >= config.transient_steps:
            r_series.append(kuramoto_order_parameter(theta))

    theta_final = wrap_angles(theta)
    state = LayersState(pQ=p, theta=theta_final, last_lambda={"rho": rho, "tau": tau_scale})
    r_arr = np.asarray(r_series, dtype=float)
    r_mean = _smooth_average(r_arr, config.average_window)
    return state, r_arr, float(r_mean), gap


def build_wavefunction(state: LayersState) -> np.ndarray:
    """Construct the wavefunction associated with a layer state."""

    return build_psi(state.pQ, state.theta)


def compute_metric_and_curvature(
    psi_grid: Sequence[Sequence[np.ndarray]],
    rho_values: Sequence[float],
    tau_values: Sequence[float],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return trace(g), diagonal elements, and |Omega| for the grid."""

    n_rho = len(rho_values)
    n_tau = len(tau_values)
    g_rr = np.full((n_rho, n_tau), np.nan, dtype=float)
    g_tt = np.full((n_rho, n_tau), np.nan, dtype=float)
    curvature_abs = np.full((n_rho, n_tau), np.nan, dtype=float)

    for i in range(n_rho):
        for j in range(n_tau):
            psi0 = psi_grid[i][j]
            if psi0 is None or psi0.size == 0:
                continue

            if i + 1 < n_rho:
                psi_i = psi_grid[i + 1][j]
                delta_rho = float(rho_values[i + 1] - rho_values[i])
            elif i - 1 >= 0:
                psi_i = psi_grid[i - 1][j]
                delta_rho = float(rho_values[i - 1] - rho_values[i])
            else:
                psi_i = None
                delta_rho = 0.0

            if psi_i is not None and delta_rho != 0.0:
                g_rr[i, j] = metric_tile(psi0, psi_i, psi_i, delta_rho, delta_rho)

            if j + 1 < n_tau:
                psi_j = psi_grid[i][j + 1]
                delta_tau = float(tau_values[j + 1] - tau_values[j])
            elif j - 1 >= 0:
                psi_j = psi_grid[i][j - 1]
                delta_tau = float(tau_values[j - 1] - tau_values[j])
            else:
                psi_j = None
                delta_tau = 0.0

            if psi_j is not None and delta_tau != 0.0:
                g_tt[i, j] = metric_tile(psi0, psi_j, psi_j, delta_tau, delta_tau)

            if i + 1 < n_rho and j + 1 < n_tau:
                psi_r = psi_grid[i + 1][j]
                psi_rt = psi_grid[i + 1][j + 1]
                psi_t = psi_grid[i][j + 1]
                delta_r = float(rho_values[i + 1] - rho_values[i])
                delta_t = float(tau_values[j + 1] - tau_values[j])
                if delta_r != 0.0 and delta_t != 0.0:
                    omega, _ = curvature_tile(psi0, psi_r, psi_rt, psi_t, delta_r, delta_t)
                    curvature_abs[i, j] = abs(float(omega))

    trace_g = g_rr + g_tt
    return trace_g, g_rr, g_tt, curvature_abs


def gradient_magnitude(field: np.ndarray, rho: Sequence[float], tau: Sequence[float]) -> np.ndarray:
    """Return ||grad field|| using central differences along the grid."""

    grad_rho, grad_tau = np.gradient(field, rho, tau, edge_order=2)
    magnitude = np.sqrt(np.square(grad_rho) + np.square(grad_tau))
    return np.asarray(magnitude, dtype=float)


def finite_correlation(a: np.ndarray, b: np.ndarray) -> float:
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 3:
        return float("nan")
    corr = np.corrcoef(a[mask], b[mask])[0, 1]
    return float(corr)


def compute_auc(scores: np.ndarray, labels: np.ndarray) -> float:
    """Return the ROC AUC using rank statistics (handles ties)."""

    if scores.size == 0 or labels.size == 0:
        return float("nan")
    positives = labels == 1
    negatives = labels == 0
    n_pos = int(np.count_nonzero(positives))
    n_neg = int(np.count_nonzero(negatives))
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    ranks = rankdata(scores, method="average")
    sum_pos = float(np.sum(ranks[positives]))
    auc = (sum_pos - n_pos * (n_pos + 1) / 2.0) / (n_pos * n_neg)
    return float(auc)


def roc_curve_points(scores: np.ndarray, labels: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return FPR/TPR pairs along with the evaluated thresholds."""

    unique_thresholds = np.unique(scores)[::-1]
    positives = labels == 1
    negatives = labels == 0
    n_pos = int(np.count_nonzero(positives))
    n_neg = int(np.count_nonzero(negatives))
    if n_pos == 0 or n_neg == 0:
        return (
            np.array([0.0, 1.0], dtype=float),
            np.array([0.0, 1.0], dtype=float),
            np.array([np.inf, -np.inf], dtype=float),
        )

    fpr = [0.0]
    tpr = [0.0]
    thresholds = [np.inf]

    for thresh in unique_thresholds:
        preds = scores >= thresh
        tp = int(np.count_nonzero(preds & positives))
        fp = int(np.count_nonzero(preds & negatives))
        tpr.append(tp / n_pos)
        fpr.append(fp / n_neg)
        thresholds.append(float(thresh))

    fpr.append(1.0)
    tpr.append(1.0)
    thresholds.append(-np.inf)

    return (
        np.asarray(fpr, dtype=float),
        np.asarray(tpr, dtype=float),
        np.asarray(thresholds, dtype=float),
    )


def bootstrap_auc(
    scores: np.ndarray,
    labels: np.ndarray,
    n_bootstrap: int,
    rng: np.random.Generator,
) -> tuple[float, tuple[float, float]]:
    """Return mean and 95% CI of the AUC via bootstrap resampling."""

    auc_values: list[float] = []
    n = scores.size
    if n == 0:
        return float("nan"), (float("nan"), float("nan"))

    for _ in range(n_bootstrap):
        indices = rng.integers(0, n, size=n)
        auc_boot = compute_auc(scores[indices], labels[indices])
        if math.isfinite(auc_boot):
            auc_values.append(float(auc_boot))

    if not auc_values:
        return float("nan"), (float("nan"), float("nan"))

    arr = np.asarray(auc_values, dtype=float)
    lower = float(np.percentile(arr, 2.5))
    upper = float(np.percentile(arr, 97.5))
    return float(np.mean(arr)), (lower, upper)


def detection_from_trace(
    trace_g: np.ndarray,
    spectral_gap: np.ndarray,
    r_gradient: np.ndarray,
    bootstrap_samples: int,
    seed: int,
) -> DetectionMetrics:
    """Build ROC metrics treating trace(g) as the hotspot score."""

    scores = np.asarray(trace_g, dtype=float).ravel()
    gap_flat = np.asarray(spectral_gap, dtype=float).ravel()
    grad_flat = np.asarray(r_gradient, dtype=float).ravel()

    mask = np.isfinite(scores) & np.isfinite(gap_flat) & np.isfinite(grad_flat)
    scores = scores[mask]
    gap_flat = gap_flat[mask]
    grad_flat = grad_flat[mask]

    gap_threshold = float(np.nanpercentile(gap_flat, 25.0))
    grad_threshold = float(np.nanpercentile(grad_flat, 75.0))

    labels_gap = gap_flat <= gap_threshold
    labels_grad = grad_flat >= grad_threshold

    gap_span = float(np.nanmax(gap_flat) - np.nanmin(gap_flat)) if gap_flat.size else 0.0
    grad_span = float(np.nanmax(grad_flat) - np.nanmin(grad_flat)) if grad_flat.size else 0.0

    has_gap_variation = gap_span > 1e-8 and 0 < int(np.count_nonzero(labels_gap)) < labels_gap.size
    has_grad_variation = grad_span > 1e-8 and 0 < int(np.count_nonzero(labels_grad)) < labels_grad.size

    if has_gap_variation and has_grad_variation:
        labels = (labels_gap | labels_grad).astype(int)
    elif has_grad_variation:
        labels = labels_grad.astype(int)
    elif has_gap_variation:
        labels = labels_gap.astype(int)
    else:
        labels = np.zeros_like(scores, dtype=int)

    auc = compute_auc(scores, labels)
    fpr, tpr, thresholds = roc_curve_points(scores, labels)
    rng = np.random.default_rng(seed)
    _, ci = bootstrap_auc(scores, labels, bootstrap_samples, rng)

    corr_gap = finite_correlation(scores, gap_flat)
    corr_grad = finite_correlation(scores, grad_flat)

    return DetectionMetrics(
        auc=auc,
        auc_ci=ci,
        roc_fpr=fpr,
        roc_tpr=tpr,
        roc_thresholds=thresholds,
        gap_threshold=gap_threshold,
        delta_r_threshold=grad_threshold,
        corr_trace_gap=corr_gap,
        corr_trace_delta_r=corr_grad,
    )


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def save_heatmaps(
    result: GraphScanResult,
    out_dir: Path,
) -> None:
    """Persist heatmaps for trace(g), |Omega|, gap, and r."""

    ensure_dir(out_dir)
    extent = [
        result.tau_values[0],
        result.tau_values[-1],
        result.rho_values[0],
        result.rho_values[-1],
    ]

    fig, axes = plt.subplots(2, 2, figsize=(12, 10), constrained_layout=True)

    plots = [
        (result.trace_g, "trace g"),
        (result.curvature_abs, "|Omega|"),
        (result.spectral_gap, "spectral gap"),
        (result.kuramoto_r, "Kuramoto r"),
    ]

    for ax, (data, title) in zip(axes.flat, plots):
        masked = np.ma.masked_invalid(data)
        im = ax.imshow(masked, origin="lower", aspect="auto", extent=extent)
        ax.set_title(title)
        ax.set_xlabel("tau")
        ax.set_ylabel("rho")
        fig.colorbar(im, ax=ax)

    figure_path = out_dir / "heatmaps.png"
    fig.suptitle(f"Gate B ridge diagnostics — {result.name}")
    fig.savefig(figure_path, dpi=150)
    plt.close(fig)


def save_roc_curve(result: GraphScanResult, out_dir: Path) -> None:
    ensure_dir(out_dir)
    fig, ax = plt.subplots(figsize=(5, 5))
    detection = result.detection
    ax.plot(detection.roc_fpr, detection.roc_tpr, label=f"AUC = {detection.auc:.3f}")
    ax.plot([0, 1], [0, 1], linestyle="--", color="grey", linewidth=1.0)
    ax.set_xlabel("False positive rate")
    ax.set_ylabel("True positive rate")
    ax.set_title(f"Hotspot ROC — {result.name}")
    ax.legend(loc="lower right")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    fig.savefig(out_dir / "roc_curve.png", dpi=150)
    plt.close(fig)


def save_numpy_bundle(result: GraphScanResult, out_dir: Path) -> None:
    ensure_dir(out_dir)
    np.savez_compressed(
        out_dir / "metrics.npz",
        rho_values=result.rho_values,
        tau_values=result.tau_values,
        trace_g=result.trace_g,
        g_rho_rho=result.g_rho_rho,
        g_tau_tau=result.g_tau_tau,
        curvature_abs=result.curvature_abs,
        spectral_gap=result.spectral_gap,
        kuramoto_r=result.kuramoto_r,
        r_gradient=result.r_gradient,
        roc_fpr=result.detection.roc_fpr,
        roc_tpr=result.detection.roc_tpr,
        roc_thresholds=result.detection.roc_thresholds,
    )

    with (out_dir / "summary.json").open("w", encoding="utf-8") as fh:
        json.dump(result.detection.to_json(), fh, indent=2)


def scan_graph(
    name: str,
    substrate: GraphSubstrate,
    rho_values: np.ndarray,
    tau_values: np.ndarray,
    config: SimulationConfig,
    bootstrap_samples: int,
    detection_seed: int,
) -> GraphScanResult:
    """Run the Gate B sweep for a particular substrate."""

    n_rho = len(rho_values)
    n_tau = len(tau_values)

    states: list[list[LayersState]] = [[None for _ in range(n_tau)] for _ in range(n_rho)]  # type: ignore[list-item]
    psi_grid: list[list[np.ndarray]] = [[None for _ in range(n_tau)] for _ in range(n_rho)]  # type: ignore[list-item]
    spectral_gap = np.full((n_rho, n_tau), np.nan, dtype=float)
    kuramoto_r = np.full((n_rho, n_tau), np.nan, dtype=float)

    warm_column: list[LayersState | None] = [None for _ in range(n_tau)]

    for i, rho in enumerate(rho_values):
        warm_row: LayersState | None = None
        for j, tau in enumerate(tau_values):
            warm = warm_row if warm_row is not None else warm_column[j]
            state, r_series, r_mean, gap = simulate_state(substrate, float(rho), float(tau), config, warm)
            states[i][j] = state
            psi_grid[i][j] = build_wavefunction(state)
            spectral_gap[i, j] = gap
            kuramoto_r[i, j] = r_mean
            warm_row = state
        warm_column = [states[i][j] for j in range(n_tau)]

    trace_g, g_rr, g_tt, curvature_abs = compute_metric_and_curvature(psi_grid, rho_values, tau_values)
    r_gradient = gradient_magnitude(kuramoto_r, rho_values, tau_values)
    detection = detection_from_trace(trace_g, spectral_gap, r_gradient, bootstrap_samples, detection_seed)

    return GraphScanResult(
        name=name,
        substrate=substrate,
        rho_values=rho_values,
        tau_values=tau_values,
        trace_g=trace_g,
        g_rho_rho=g_rr,
        g_tau_tau=g_tt,
        curvature_abs=curvature_abs,
        spectral_gap=spectral_gap,
        kuramoto_r=kuramoto_r,
        r_gradient=r_gradient,
        detection=detection,
    )


def build_substrates(seed: int) -> list[tuple[str, GraphSubstrate]]:
    """Return the two canonical substrates used in Gate B."""

    rng = np.random.default_rng(seed)

    ring_graph = nx.DiGraph()
    ring_edges = [
        (0, 1, 1.0, 0.6),
        (1, 2, 1.0, 1.1),
        (2, 0, 1.0, 1.8),
    ]
    for u, v, weight, delay in ring_edges:
        ring_graph.add_edge(u, v, weight=weight, delay=delay)
    ring_substrate = build_substrate(ring_graph)

    base_random = random_regular_digraph(N=20, out_degree=3, seed=seed)
    random_graph = nx.DiGraph()
    for u, v, data in base_random.G.edges(data=True):
        weight = float(data.get("weight", 1.0)) * (0.9 + 0.2 * rng.random())
        delay = float(data.get("delay", 1.0)) * (0.5 + rng.random())
        random_graph.add_edge(u, v, weight=weight, delay=delay)
    random_substrate = build_substrate(random_graph)

    return [
        ("ring3", ring_substrate),
        ("random_regular", random_substrate),
    ]


def run_experiment(
    grid_size: int,
    rho_range: tuple[float, float],
    tau_range: tuple[float, float],
    sim_config: SimulationConfig,
    bootstrap_samples: int,
    seed: int,
    output_dir: Path,
) -> list[GraphScanResult]:
    """Execute the Gate B ridge finder across the canonical substrates."""

    rho_values = np.linspace(rho_range[0], rho_range[1], num=grid_size)
    tau_values = np.linspace(tau_range[0], tau_range[1], num=grid_size)

    results: list[GraphScanResult] = []
    for name, substrate in build_substrates(seed):
        result = scan_graph(
            name,
            substrate,
            rho_values,
            tau_values,
            sim_config,
            bootstrap_samples,
            detection_seed=seed + 17,
        )
        graph_dir = output_dir / name
        save_heatmaps(result, graph_dir)
        save_roc_curve(result, graph_dir)
        save_numpy_bundle(result, graph_dir)
        results.append(result)
    return results


def _render_graph_section(result: GraphScanResult) -> list[str]:
    curvature = np.asarray(result.curvature_abs, dtype=float)
    trace_g = np.asarray(result.trace_g, dtype=float)
    spectral = np.asarray(result.spectral_gap, dtype=float)
    grad_r = np.asarray(result.r_gradient, dtype=float)

    curvature_mean = float(np.nanmean(curvature)) if curvature.size else float("nan")
    trace_mean = float(np.nanmean(trace_g)) if trace_g.size else float("nan")
    spectral_mean = float(np.nanmean(spectral)) if spectral.size else float("nan")
    grad_mean = float(np.nanmean(np.abs(grad_r))) if grad_r.size else float("nan")

    detection = result.detection
    auc = detection.auc
    auc_ci = detection.auc_ci

    lines = [
        f"## Graph: {result.name}",
        "",
        f"- Mean |Ω|: {curvature_mean:.3e}",
        f"- Mean tr(g): {trace_mean:.3e}",
        f"- Spectral gap mean: {spectral_mean:.3e}",
        f"- |∇r| mean: {grad_mean:.3e}",
        f"- Hotspot AUC: {auc:.3f} (CI [{auc_ci[0]:.3f}, {auc_ci[1]:.3f}])",
        f"- corr(trace, gap): {detection.corr_trace_gap:.3f}",
        f"- corr(trace, |∇r|): {detection.corr_trace_delta_r:.3f}",
        "",
    ]
    return lines


def _render_report(
    results: Sequence[GraphScanResult],
    sim_config: SimulationConfig,
    bootstrap_samples: int,
) -> str:
    header_metrics = _gateB_header_metrics(results, sim_config)

    grid_shape = "n/a"
    rho_range_text = "ρ range: n/a"
    tau_range_text = "τ range: n/a"
    if results:
        grid_shape = f"{len(results[0].rho_values)} × {len(results[0].tau_values)}"
        rho_vals = np.asarray(results[0].rho_values, dtype=float)
        tau_vals = np.asarray(results[0].tau_values, dtype=float)
        if rho_vals.size:
            rho_range_text = f"ρ range: {float(rho_vals.min()):.3f} … {float(rho_vals.max()):.3f}"
        if tau_vals.size:
            tau_range_text = f"τ range: {float(tau_vals.min()):.3f} … {float(tau_vals.max()):.3f}"

    lines = [
        "# Gate B — Critical Ridge Finder",
        "",
        f"Grid size: {grid_shape}",
        rho_range_text,
        tau_range_text,
        f"Transient/sample steps: {sim_config.transient_steps} / {sim_config.sample_steps}",
        f"Bootstrap replicates: {bootstrap_samples}",
        "",
    ]

    lines.extend(render_report_header(header_metrics))

    for result in results:
        lines.extend(_render_graph_section(result))

    return "\n".join(lines)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Gate B critical ridge finder")
    parser.add_argument(
        "--grid-size",
        type=int,
        default=21,
        help="Number of samples per axis in the (rho, tau) grid",
    )
    parser.add_argument(
        "--rho-range",
        type=float,
        nargs=2,
        default=(0.0, 3.0),
        help="Range of rho values to scan",
    )
    parser.add_argument(
        "--tau-range",
        type=float,
        nargs=2,
        default=(0.5, 3.0),
        help="Range of tau values to scan",
    )
    parser.add_argument("--bootstrap", type=int, default=256, help="Bootstrap replicates for the AUC CI")
    parser.add_argument("--seed", type=int, default=7, help="Base seed controlling RNG usage")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "artifacts")
    parser.add_argument(
        "--transient-steps",
        type=int,
        default=150,
        help="Transient steps discarded before sampling",
    )
    parser.add_argument(
        "--sample-steps",
        type=int,
        default=40,
        help="Number of post-transient steps to sample",
    )
    parser.add_argument(
        "--eta-q",
        type=float,
        default=0.6,
        help="Mixing coefficient for the Q-layer update",
    )
    parser.add_argument("--zeta", type=float, default=1.2, help="Theta coupling strength")
    parser.add_argument(
        "--theta-noise",
        type=float,
        default=0.02,
        help="Gaussian noise amplitude for theta updates",
    )
    parser.add_argument(
        "--average-window",
        type=int,
        default=10,
        help="Window size for averaging the order parameter",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    output_dir = Path(args.output_dir)
    ensure_dir(output_dir)

    sim_config = SimulationConfig(
        transient_steps=args.transient_steps,
        sample_steps=args.sample_steps,
        eta_q=args.eta_q,
        zeta=args.zeta,
        theta_noise=args.theta_noise,
        average_window=args.average_window,
        seed=args.seed,
    )

    results = run_experiment(
        grid_size=args.grid_size,
        rho_range=(args.rho_range[0], args.rho_range[1]),
        tau_range=(args.tau_range[0], args.tau_range[1]),
        sim_config=sim_config,
        bootstrap_samples=args.bootstrap,
        seed=args.seed,
        output_dir=output_dir,
    )

    summary_path = output_dir / "summary.json"
    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(
            {result.name: result.detection.to_json() for result in results},
            fh,
            indent=2,
        )

    report_path = output_dir / "REPORT.md"
    report_path.write_text(_render_report(results, sim_config, args.bootstrap))

    for result in results:
        print(f"Graph: {result.name}")
        auc = result.detection.auc
        ci_low, ci_high = result.detection.auc_ci
        print(f"  AUC: {auc:.3f} (95% CI {ci_low:.3f}, {ci_high:.3f})")
        print(f"  corr(trace, gap): {result.detection.corr_trace_gap:.3f}")
        print(f"  corr(trace, |grad r|): {result.detection.corr_trace_delta_r:.3f}")


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    main()

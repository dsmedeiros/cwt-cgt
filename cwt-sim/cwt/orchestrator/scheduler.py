"""High-level orchestration utilities for driving layer updates.

The original project couples together a graph substrate, layer dynamics,
parameter-space geometry probes and optional readouts.  The implementation
below wires the existing building blocks into a reproducible stepping loop
that records all intermediate states in a :class:`RunRecord` data structure.
"""

from __future__ import annotations

import math
import zlib
from dataclasses import asdict, dataclass, field
from itertools import combinations
from typing import Any, Mapping, Sequence

import numpy as np

from ..geometry.adapt_mesh import PlaquetteResult, curvature_anytime
from ..geometry.fs_distance import fs_distance
from ..geometry.metric import metric_tile
from ..geometry.psi import build_psi
from ..graph.kernels import build_transport_kernel
from ..graph.substrate import GraphSubstrate
from ..layers.q_update import q_step
from ..layers.state import LayersState, normalize_prob, wrap_angles
from ..layers.theta_update import build_J_from_W, omega_from_delays, theta_step
from ..orchestrator.param_path import ParameterPath
from .with_geom import curvature_bias, nodewise_connection_a_i, phase_kick


@dataclass(slots=True)
class RunConfig:
    """Configuration bundle controlling the parameter loop execution."""

    eta_q: float = 0.5
    zeta: float = 0.0
    omega_scale: float = 1.0
    s_min: float = 0.6
    smooth_window: int = 1
    compute_metric: bool = False
    compute_curvature: bool = False
    adapt_levels: int = 1
    ci_tol: float = 0.05
    alpha: float = 1.0
    beta: float = 1.0
    delta_frac: dict[str, float] = field(default_factory=dict)
    xi_kind: dict[str, Any] = field(default_factory=dict)
    readout: dict[str, Any] = field(default_factory=dict)
    noise: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunRecord:
    """Structured log returned by :func:`run_parameter_loop`."""

    meta: dict[str, Any]
    lambda_path: list[dict[str, float]]
    delta_lambda: list[dict[str, float]]
    delta_area: list[float]
    pQ_traj: list[np.ndarray]
    theta_traj: list[np.ndarray]
    psi_traj: list[np.ndarray]
    fs_steps: list[float]
    overlaps_min: list[float]
    g_tiles: list[dict[str, Any]]
    omega_tiles: list[dict[str, Any]]
    phase_kicks: list[np.ndarray]
    curvature_biases: list[np.ndarray]
    clip_counts: list[int]
    readouts: list[dict[str, Any]]


def _as_1d_array(values: np.ndarray | Sequence[float], *, name: str) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.ndim != 1:
        arr = arr.reshape(-1)
    if not np.all(np.isfinite(arr)):
        raise ValueError(f"{name} must contain only finite entries.")
    return arr


def _normalize_complex(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if not math.isfinite(norm) or norm == 0.0:
        return np.zeros_like(vec)
    return vec / norm


def _direction_from_label(label: str, size: int) -> np.ndarray:
    """Return a deterministic phase direction vector for ``label``."""

    if size == 0:
        return np.zeros((0,), dtype=float)

    base = np.linspace(0.0, 2.0 * math.pi, num=max(size, 2), endpoint=False)[:size]
    seed = (zlib.crc32(label.encode("utf8")) & 0xFFFFFFFF) / 0xFFFFFFFF
    phase = seed * 2.0 * math.pi
    direction = np.sin(base + phase)
    if np.allclose(direction, 0.0):
        direction = np.cos(base + phase)
    if np.allclose(direction, 0.0):
        direction = np.ones(size, dtype=float)
    return direction.astype(float, copy=True)


def _phase_factor(direction: np.ndarray, delta: float) -> np.ndarray:
    return np.exp(1j * direction * float(delta))


def _xi_initial(pQ: np.ndarray, xi_cfg: Mapping[str, Any]) -> tuple[np.ndarray, bool]:
    """Return the initial susceptibility and whether it should track the run."""

    if pQ.size == 0:
        return pQ.copy(), False

    xi_type = str(xi_cfg.get("type", "static")).lower()
    if xi_type == "uniform":
        Xi = np.full_like(pQ, 1.0 / float(pQ.size))
        return Xi, False
    if xi_type == "dynamic":
        Xi = normalize_prob(pQ)
        return Xi, True
    if xi_type == "static":
        mode = str(xi_cfg.get("mode", "probability")).lower()
        if mode == "uniform":
            Xi = np.full_like(pQ, 1.0 / float(pQ.size))
        else:
            Xi = normalize_prob(pQ)
        return Xi, False

    Xi = normalize_prob(pQ)
    dynamic = xi_type in {"follow", "probability", "tracking"}
    return Xi, dynamic


def _noise_sigma(noise_cfg: Mapping[str, Any], key: str) -> float:
    value = noise_cfg.get(key, noise_cfg.get(f"{key}_std", 0.0))
    value = noise_cfg.get(f"{key}_sigma", value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _collect_readout(
    s: int,
    lambda_state: Mapping[str, float],
    pQ: np.ndarray,
    theta: np.ndarray,
    clip_count: int,
) -> dict[str, Any]:
    return {
        "step": int(s),
        "lambda": {k: float(v) for k, v in lambda_state.items()},
        "probability_sum": float(pQ.sum()),
        "theta_mean": float(theta.mean()) if theta.size else 0.0,
        "clip_count": int(clip_count),
    }


def _psi_sampler_factory(
    Psi0: np.ndarray,
    direction_i: np.ndarray,
    direction_j: np.ndarray,
) -> callable:
    Psi0_arr = np.asarray(Psi0, dtype=np.complex128)
    direction_i_arr = np.asarray(direction_i, dtype=float)
    direction_j_arr = np.asarray(direction_j, dtype=float)

    cache_i: dict[float, np.ndarray] = {}
    cache_j: dict[float, np.ndarray] = {}
    sample_cache: dict[tuple[float, float], tuple[np.ndarray, ...]] = {}

    def _quantize(delta: float) -> float:
        return round(float(delta), 12)

    def sampler(delta_i: float, delta_j: float) -> Sequence[np.ndarray]:
        key_i = _quantize(delta_i)
        key_j = _quantize(delta_j)
        cache_key = (key_i, key_j)

        if key_i not in cache_i:
            cache_i[key_i] = _phase_factor(direction_i_arr, float(delta_i))
        if key_j not in cache_j:
            cache_j[key_j] = _phase_factor(direction_j_arr, float(delta_j))

        if cache_key not in sample_cache:
            factor_i = cache_i[key_i]
            factor_j = cache_j[key_j]
            Psi_i = Psi0_arr * factor_i
            Psi_j = Psi0_arr * factor_j
            Psi_ij = Psi0_arr * factor_i * factor_j
            sample_cache[cache_key] = (Psi0_arr, Psi_i, Psi_ij, Psi_j)

        return sample_cache[cache_key]

    return sampler


def run_parameter_loop(
    S: GraphSubstrate,
    init_state: LayersState,
    path: ParameterPath,
    config: RunConfig,
    seed: int = 0,
) -> RunRecord:
    if not isinstance(S, GraphSubstrate):
        raise TypeError("S must be a GraphSubstrate instance.")
    if not isinstance(init_state, LayersState):
        raise TypeError("init_state must be a LayersState instance.")
    if not isinstance(path, ParameterPath):
        raise TypeError("path must be a ParameterPath instance.")

    N = S.N
    pQ = _as_1d_array(init_state.pQ, name="pQ") if N else np.asarray(init_state.pQ, dtype=float)
    theta = _as_1d_array(init_state.theta, name="theta") if N else np.asarray(init_state.theta, dtype=float)

    if pQ.shape != theta.shape:
        raise ValueError("pQ and theta must share the same shape.")
    if pQ.size != N:
        raise ValueError("Layer state size must match the substrate size.")

    pQ = normalize_prob(pQ)
    theta = wrap_angles(theta)

    rng = np.random.default_rng(seed)

    smooth_window = max(int(config.smooth_window), 1)
    smooth_alpha = 2.0 / (smooth_window + 1.0) if smooth_window > 1 else None

    def smooth_psi(current: np.ndarray, ema_state: np.ndarray | None) -> tuple[np.ndarray, np.ndarray | None]:
        if smooth_alpha is None:
            return current, ema_state
        if ema_state is None:
            ema_state = current.copy()
        else:
            ema_state = (1.0 - smooth_alpha) * ema_state + smooth_alpha * current
        return _normalize_complex(ema_state), ema_state

    psi_raw = build_psi(pQ, theta)
    psi_current, psi_ema = smooth_psi(psi_raw, None)

    lambda_path: list[dict[str, float]] = []
    delta_lambda_log: list[dict[str, float]] = []
    delta_area_log: list[float] = []
    pQ_traj: list[np.ndarray] = [pQ.copy()]
    theta_traj: list[np.ndarray] = [theta.copy()]
    psi_traj: list[np.ndarray] = [psi_current.copy()]
    fs_steps: list[float] = []
    overlaps_min: list[float] = []
    g_tiles: list[dict[str, Any]] = []
    omega_tiles: list[dict[str, Any]] = []
    phase_kicks: list[np.ndarray] = []
    curvature_biases: list[np.ndarray] = []
    clip_counts: list[int] = []
    readouts: list[dict[str, Any]] = []

    direction_cache: dict[str, np.ndarray] = {}
    phase_cache: dict[tuple[str, float], np.ndarray] = {}

    def direction_for(knob: str) -> np.ndarray:
        if knob not in direction_cache:
            direction_cache[knob] = _direction_from_label(knob, N)
        return direction_cache[knob]

    def phase_factor(knob: str, delta: float) -> np.ndarray:
        key = (knob, round(float(delta), 12))
        if key not in phase_cache:
            phase_cache[key] = _phase_factor(direction_for(knob), float(delta))
        return phase_cache[key]

    Xi, dynamic_xi = _xi_initial(pQ, config.xi_kind)

    J = build_J_from_W(S, zeta=float(config.zeta))

    noise_cfg = config.noise or {}
    theta_sigma = _noise_sigma(noise_cfg, "theta")
    prob_sigma = _noise_sigma(noise_cfg, "prob")
    clip_floor = float(noise_cfg.get("clip_floor", 0.0)) if noise_cfg else 0.0

    readout_cfg = config.readout or {}
    readout_steps = {
        int(step)
        for step in readout_cfg.get("steps", [])
        if isinstance(step, int) or (isinstance(step, float) and step.is_integer())
    }
    readout_interval = int(readout_cfg.get("interval", 0)) if readout_cfg.get("interval") else 0
    collect_final = bool(readout_cfg.get("final", False))

    for s in range(path.steps):
        lambda_state_raw, delta_lambda_raw, delta_area_val = path.step(s)
        lambda_state = {key: float(val) for key, val in lambda_state_raw.items()}
        delta_lambda = {key: float(val) for key, val in delta_lambda_raw.items()}
        delta_area = float(delta_area_val)

        lambda_path.append(lambda_state)
        delta_lambda_log.append(delta_lambda)
        delta_area_log.append(delta_area)

        rho = float(lambda_state.get("rho", 0.0))
        tau_scale = float(lambda_state.get("tau", 1.0)) or 1.0
        kappa = float(lambda_state.get("kappa", 1.0))

        if tau_scale <= 0.0:
            tau_scale = 1.0

        K = build_transport_kernel(S, rho=rho, tau_scale=tau_scale, kappa=kappa)
        omega_n = omega_from_delays(S, rho=rho, tau_scale=tau_scale, omega_scale=float(config.omega_scale))

        Psi0 = psi_current
        geometry_knobs = set(config.delta_frac.keys()) | set(delta_lambda.keys())

        knob_deltas: dict[str, float] = {}
        neighbor_states: dict[str, np.ndarray] = {}
        A_per_knob: dict[str, np.ndarray] = {}

        for knob in sorted(geometry_knobs):
            scale = abs(lambda_state.get(knob, 1.0))
            if scale == 0.0:
                scale = 1.0
            base_frac = float(config.delta_frac.get(knob, 0.0))
            delta_candidate = base_frac * scale
            if delta_candidate == 0.0 and knob in delta_lambda:
                delta_candidate = float(delta_lambda[knob])
            if delta_candidate == 0.0:
                A_per_knob[knob] = np.zeros(N, dtype=float)
                continue

            knob_deltas[knob] = float(delta_candidate)
            factor = phase_factor(knob, delta_candidate)
            Psi_i = Psi0 * factor
            neighbor_states[knob] = Psi_i
            A_per_knob[knob] = nodewise_connection_a_i(Psi0, Psi_i, delta_candidate)

        for knob in delta_lambda:
            if knob not in A_per_knob:
                A_per_knob[knob] = np.zeros(N, dtype=float)

        step_min_overlap: float = float("nan")
        if config.compute_metric and len(knob_deltas) >= 2:
            for knob_i, knob_j in combinations(sorted(knob_deltas), 2):
                delta_i = knob_deltas[knob_i]
                delta_j = knob_deltas[knob_j]
                Psi_i = neighbor_states[knob_i]
                Psi_j = neighbor_states[knob_j]
                gij = metric_tile(Psi0, Psi_i, Psi_j, delta_i, delta_j)
                g_tiles.append(
                    {
                        "lambda0": lambda_state.copy(),
                        "knobs": (knob_i, knob_j),
                        "g_ij": float(gij),
                        "tile_size": {knob_i: float(delta_i), knob_j: float(delta_j)},
                    }
                )

        Omega_ij: dict[tuple[str, str], float] = {}
        curvature_results: list[PlaquetteResult] = []
        if config.compute_curvature and len(knob_deltas) >= 2:
            max_levels = max(int(config.adapt_levels), 1)
            for knob_i, knob_j in combinations(sorted(knob_deltas), 2):
                delta_i = knob_deltas[knob_i]
                delta_j = knob_deltas[knob_j]
                sampler = _psi_sampler_factory(Psi0, direction_for(knob_i), direction_for(knob_j))
                plaquette = curvature_anytime(
                    sampler,
                    delta_i,
                    delta_j,
                    s_min=float(config.s_min),
                    ci_tol=float(config.ci_tol),
                    max_levels=max_levels,
                )
                curvature_results.append(plaquette)
                Omega_ij[(knob_i, knob_j)] = float(plaquette.omega_mean)
                omega_tiles.append(
                    {
                        "lambda0": lambda_state.copy(),
                        "knobs": (knob_i, knob_j),
                        "omega": float(plaquette.omega_mean),
                        "ci": tuple(float(x) for x in plaquette.omega_ci),
                        "min_overlap": float(plaquette.min_overlap),
                        "samples_used": int(plaquette.samples_used),
                        "depth_used": int(plaquette.depth_used),
                    }
                )

        if curvature_results:
            finite_overlaps = [res.min_overlap for res in curvature_results if math.isfinite(res.min_overlap)]
            if finite_overlaps:
                step_min_overlap = float(min(finite_overlaps))
            else:
                step_min_overlap = float("nan")
        overlaps_min.append(step_min_overlap)

        if dynamic_xi:
            Xi = normalize_prob(pQ)

        Gamma = np.zeros_like(pQ, dtype=float)
        if Omega_ij and delta_area != 0.0:
            Gamma = curvature_bias(Xi, Omega_ij, delta_area, float(config.alpha), float(config.beta))

        curvature_biases.append(Gamma.copy())

        delta_theta_geom = phase_kick(theta, A_per_knob, delta_lambda)
        phase_kicks.append(np.asarray(delta_theta_geom, dtype=float).copy())

        theta_next = theta_step(theta, omega_n, J, delta_theta_geom)

        pQ_next, stats = q_step(pQ, K, float(config.eta_q), geom_bias=Gamma, clip_floor=float(clip_floor))

        clip_count = int(stats.get("clipped_count", 0))
        clip_counts.append(clip_count)

        if theta_sigma > 0.0 and theta_next.size:
            theta_next = wrap_angles(theta_next + rng.normal(0.0, theta_sigma, size=theta_next.shape))
        if prob_sigma > 0.0 and pQ_next.size:
            perturb = rng.normal(0.0, prob_sigma, size=pQ_next.shape)
            pQ_next = normalize_prob(np.maximum(pQ_next + perturb, 0.0))

        theta = theta_next
        pQ = pQ_next

        pQ_traj.append(pQ.copy())
        theta_traj.append(theta.copy())

        psi_raw = build_psi(pQ, theta)
        psi_current, psi_ema = smooth_psi(psi_raw, psi_ema)

        fs_step = float("nan")
        prev_state = psi_traj[-1] if psi_traj else None
        if prev_state is not None and prev_state.size and psi_current.size:
            try:
                fs_step = float(fs_distance(prev_state, psi_current))
            except ValueError:
                fs_step = float("nan")
        fs_steps.append(fs_step)

        psi_traj.append(psi_current.copy())

        should_emit = False
        if readout_interval and (s + 1) % readout_interval == 0:
            should_emit = True
        if readout_steps and ((s + 1) in readout_steps or s in readout_steps):
            should_emit = True
        if should_emit:
            readouts.append(_collect_readout(s + 1, lambda_state, pQ, theta, clip_count))

        init_state.last_lambda = lambda_state

    if collect_final:
        final_lambda = lambda_path[-1] if lambda_path else {}
        final_clip = clip_counts[-1] if clip_counts else 0
        readouts.append(_collect_readout(path.steps, final_lambda, pQ, theta, final_clip))

    meta: dict[str, Any] = {
        "seed": int(seed),
        "rng": {"base": int(seed)},
        "steps": int(path.steps),
        "config": asdict(config),
        "substrate_size": int(N),
        "path": {"kind": path.kind, "steps": path.steps},
    }

    return RunRecord(
        meta=meta,
        lambda_path=lambda_path,
        delta_lambda=delta_lambda_log,
        delta_area=delta_area_log,
        pQ_traj=pQ_traj,
        theta_traj=theta_traj,
        psi_traj=psi_traj,
        fs_steps=fs_steps,
        overlaps_min=overlaps_min,
        g_tiles=g_tiles,
        omega_tiles=omega_tiles,
        phase_kicks=phase_kicks,
        curvature_biases=curvature_biases,
        clip_counts=clip_counts,
        readouts=readouts,
    )


__all__ = ["RunConfig", "RunRecord", "run_parameter_loop"]

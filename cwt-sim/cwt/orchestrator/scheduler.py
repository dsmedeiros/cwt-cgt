"""High-level orchestration utilities for driving layer updates.

The original project couples together a graph substrate, layer dynamics,
parameter-space geometry probes and optional readouts.  The implementation
below wires the existing building blocks into a reproducible stepping loop
that records all intermediate states in a :class:`RunRecord` data structure.
"""

from __future__ import annotations

import logging
import math
import warnings
import zlib
from collections import deque
from dataclasses import asdict, dataclass, field
from itertools import combinations
from typing import Any, Callable, Mapping, Sequence

import numpy as np

from ..geometry.adapt_mesh import PlaquetteResult, curvature_anytime
from ..geometry.fs_distance import fs_distance
from ..geometry.metric import metric_tile
from ..geometry.psi import build_psi
from ..graph.kernels import build_transport_kernel
from ..graph.substrate import GraphSubstrate
from ..layers.q_update import q_step
from ..layers.readouts import memory_uniform_charge
from ..layers.state import LayersState, normalize_prob, wrap_angles
from ..layers.theta_update import build_J_from_W, omega_from_delays, theta_step
from ..orchestrator.param_path import ParameterPath
from .with_geom import curvature_bias, make_phi_edge_ring3, nodewise_connection_a_i, phase_kick

_LOGGER = logging.getLogger(__name__)


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
    neighbor_settle_steps: int = 20
    snapshot_interval: int = 1
    geometry: dict[str, Any] = field(default_factory=dict)
    delta_frac: dict[str, float] = field(default_factory=dict)
    xi_kind: dict[str, Any] = field(default_factory=dict)
    readout: dict[str, Any] = field(default_factory=dict)
    noise: dict[str, Any] = field(default_factory=dict)
    fs_step_guard: dict[str, Any] = field(default_factory=dict)


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


def _should_abort_fs(
    m_bad: int,
    n_seen: int,
    total_steps: int,
    q: float = 0.95,
    *,
    start_fraction: float = 0.12,
    cushion: float = 0.01,
) -> bool:
    """Return ``True`` when the FS guard cannot be satisfied."""

    if total_steps <= 0:
        return False

    total = float(total_steps)
    start_fraction = max(0.0, float(start_fraction))
    min_seen = max(1, int(math.ceil(total * start_fraction)))
    if n_seen < min_seen:
        return False

    cushion = max(0.0, float(cushion))
    threshold = max(0.0, 1.0 - float(q)) + cushion
    if threshold >= 1.0:
        threshold = 1.0

    return (float(m_bad) / total) > threshold


def _coerce_bool(value: Any, *, default: bool = False) -> bool:
    """Return ``value`` interpreted as a boolean flag."""

    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, np.integer)):
        return bool(value)
    if isinstance(value, str):
        flag = value.strip().lower()
        if flag in {"1", "true", "yes", "on"}:
            return True
        if flag in {"0", "false", "no", "off"}:
            return False
        return default
    return default


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


def _quantize_delta(delta: float) -> float:
    """Return a rounded representation for caching keyed by ``delta``."""

    return round(float(delta), 12)


def _phi_edge_for_substrate(S: GraphSubstrate, lam: Mapping[str, float]) -> np.ndarray | None:
    """Return edge phase offsets derived from ``lam`` for the substrate."""

    zeta_phase = float(lam.get("zeta_phase", 0.0))
    if zeta_phase == 0.0:
        return None

    if S.N == 0:
        return np.zeros((0, 0), dtype=float)

    if S.N == 3 and S.G.number_of_edges() == 3:
        return make_phi_edge_ring3(zeta_phase)

    phi = np.zeros((S.N, S.N), dtype=float)
    index = S.node_index
    for source, target in S.G.edges():
        if source not in index or target not in index:
            continue
        row = index[target]
        col = index[source]
        phi[row, col] = float(zeta_phase)
    return phi


def _resolve_tau_scale(lam: Mapping[str, float], *, default: float = 1.0) -> float:
    """Return a positive delay scale derived from ``lam``.

    Parameters
    ----------
    lam:
        Mapping containing optional ``tau`` (absolute) and ``tau_scale`` (relative)
        knobs.
    default:
        Fallback value when neither knob provides a usable entry.
    """

    def _positive(name: str) -> float | None:
        if name not in lam:
            return None
        try:
            value = float(lam[name])
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value) or value <= 0.0:
            return None
        return value

    tau_abs = _positive("tau")
    tau_rel = _positive("tau_scale")

    if tau_abs is None and tau_rel is None:
        return float(default)
    if tau_abs is None:
        return tau_rel if tau_rel is not None else float(default)
    if tau_rel is None:
        return tau_abs
    if math.isclose(tau_abs, tau_rel, rel_tol=1e-9, abs_tol=1e-12):
        return tau_abs
    return tau_abs * tau_rel


def _psi_at(
    S: GraphSubstrate,
    lam: Mapping[str, float],
    pQ0: np.ndarray,
    th0: np.ndarray,
    cfg: RunConfig,
    *,
    steps: int = 20,
) -> np.ndarray:
    """Return the wavefunction after relaxing towards ``lam`` for ``steps`` updates."""

    p = np.asarray(pQ0, dtype=float).copy()
    theta = np.asarray(th0, dtype=float).copy()

    rho = float(lam.get("rho", 0.0))
    tau_val = _resolve_tau_scale(lam)
    kappa = float(lam.get("kappa", 1.0))
    omega_scale = float(lam.get("omega_scale", cfg.omega_scale))
    zeta = float(lam.get("zeta", cfg.zeta))

    phi_edge = _phi_edge_for_substrate(S, lam)

    K = build_transport_kernel(S, rho=rho, tau_scale=tau_val, kappa=kappa)
    omega = omega_from_delays(S, rho=rho, tau_scale=tau_val, omega_scale=omega_scale)
    J = build_J_from_W(S, zeta=zeta)

    for _ in range(max(int(steps), 1)):
        theta = theta_step(theta, omega, J, phase_kick=None, phi_edge=phi_edge)
        p, _ = q_step(p, K, cfg.eta_q, geom_bias=None)

    return build_psi(p, theta)


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


def _noise_sigma(noise_cfg: Mapping[str, Any], key: str, *, aliases: Sequence[str] = ()) -> float:
    keys = [key, f"{key}_std", f"{key}_sigma"]
    for alias in aliases:
        alias_str = str(alias)
        keys.extend([alias_str, f"{alias_str}_std", f"{alias_str}_sigma"])

    for name in keys:
        if name in noise_cfg:
            value = noise_cfg[name]
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
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


def _centrality_vector(S: GraphSubstrate, spec: Any) -> np.ndarray | None:
    """Return a centrality vector derived from ``spec`` if possible."""

    if spec is None:
        return None

    N = S.N
    if N == 0:
        return np.zeros((0,), dtype=float)

    ordered_nodes = [node for node, _ in sorted(S.node_index.items(), key=lambda item: item[1])]

    try:
        if isinstance(spec, str):
            key = spec.lower()
            if key in {"out_degree", "outdegree"}:
                return S.out_deg.astype(float, copy=True)
            if key in {"in_degree", "indegree"}:
                return np.asarray([S.G.in_degree(node) for node in ordered_nodes], dtype=float)
            if key in {"degree", "undirected_degree"}:
                degree_map = dict(S.G.to_undirected().degree(ordered_nodes))
                return np.asarray([float(degree_map.get(node, 0.0)) for node in ordered_nodes], dtype=float)
            return None

        if isinstance(spec, Mapping):
            arr = np.zeros(N, dtype=float)
            for node, value in spec.items():
                if node in S.node_index:
                    arr[S.node_index[node]] = float(value)
            return arr

        arr = np.asarray(spec, dtype=float)
        if arr.ndim != 1:
            arr = arr.reshape(-1)
        if arr.size != N:
            return None
        return arr.astype(float, copy=True)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return None


def _psi_sampler_factory_phase(
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

    def sampler(delta_i: float, delta_j: float) -> Sequence[np.ndarray]:
        key_i = _quantize_delta(delta_i)
        key_j = _quantize_delta(delta_j)
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


def _direct_neighbor_state_factory(
    S: GraphSubstrate,
    lambda_state: Mapping[str, float],
    pQ: np.ndarray,
    theta: np.ndarray,
    config: RunConfig,
    *,
    neighbor_steps: int = 1,
    settle_steps: int | None = None,
) -> Callable[[Mapping[str, float]], np.ndarray]:
    """Return a callable that synthesises neighbour states via direct stepping."""

    lam0 = {str(k): float(v) for k, v in lambda_state.items()}
    base_prob = np.asarray(pQ, dtype=float)
    base_theta = np.asarray(theta, dtype=float)
    try:
        settle_cfg = int(settle_steps if settle_steps is not None else config.neighbor_settle_steps)
    except (TypeError, ValueError):
        settle_cfg = 20
    try:
        base_steps = int(neighbor_steps)
    except (TypeError, ValueError):
        base_steps = 1
    base_steps = max(base_steps, 1)
    settle_steps = max(base_steps, settle_cfg)

    tau_default = float(lam0.get("tau", lam0.get("tau_scale", 1.0)))
    if tau_default <= 0.0:
        tau_default = 1.0

    defaults = {
        "rho": float(lam0.get("rho", 0.0)),
        "tau": tau_default,
        "tau_scale": float(lam0.get("tau_scale", tau_default)),
        "kappa": float(lam0.get("kappa", 1.0)),
        "omega_scale": float(lam0.get("omega_scale", config.omega_scale)),
        "zeta": float(lam0.get("zeta", config.zeta)),
        "zeta_phase": float(lam0.get("zeta_phase", 0.0)),
    }

    lam_base = defaults.copy()
    lam_base.update(lam0)

    tau_val = float(lam_base.get("tau", defaults["tau"]))
    if tau_val <= 0.0:
        tau_val = defaults["tau"]
    tau_scale_val = float(lam_base.get("tau_scale", tau_val))
    if tau_scale_val <= 0.0:
        tau_scale_val = tau_val
    lam_base["tau"] = tau_val
    lam_base["tau_scale"] = tau_scale_val

    def _base_value(knob: str) -> float:
        return float(lam_base.get(knob, 0.0))

    def _prepare_lambda(overrides: Mapping[str, float]) -> dict[str, float]:
        lam = {k: float(v) for k, v in lam_base.items()}
        for knob, delta in overrides.items():
            base_val = _base_value(str(knob))
            lam[str(knob)] = base_val + float(delta)

        if "tau" in lam and lam["tau"] <= 0.0:
            lam["tau"] = 1.0
        if "tau_scale" not in overrides and "tau" in overrides:
            lam["tau_scale"] = lam["tau"]
        if "tau_scale" in overrides and "tau" not in overrides:
            lam["tau"] = lam["tau_scale"]
        if lam.get("tau_scale", 0.0) <= 0.0:
            lam["tau_scale"] = lam.get("tau", 1.0) if lam.get("tau", 1.0) > 0.0 else 1.0
        return lam

    state_cache: dict[tuple[tuple[str, float], ...], np.ndarray] = {}

    def _cache_key(overrides: Mapping[str, float]) -> tuple[tuple[str, float], ...]:
        key_items: list[tuple[str, float]] = []
        for knob, delta in overrides.items():
            quant = _quantize_delta(delta)
            if quant == 0.0:
                continue
            key_items.append((str(knob), quant))
        key_items.sort()
        return tuple(key_items)

    def state_for(overrides: Mapping[str, float]) -> np.ndarray:
        key = _cache_key(overrides)
        if key in state_cache:
            return state_cache[key]

        lam = _prepare_lambda(overrides)
        state = _psi_at(S, lam, base_prob, base_theta, config, steps=settle_steps)
        state_cache[key] = state
        return state

    return state_for


def _psi_sampler_factory_direct(
    Psi0: np.ndarray,
    knob_i: str,
    knob_j: str,
    state_for: Callable[[Mapping[str, float]], np.ndarray],
) -> Callable[[float, float], Sequence[np.ndarray]]:
    """Return a sampler that queries direct-step neighbour states."""

    Psi0_arr = np.asarray(Psi0, dtype=np.complex128)
    sample_cache: dict[tuple[float, float], tuple[np.ndarray, ...]] = {}

    def sampler(delta_i: float, delta_j: float) -> Sequence[np.ndarray]:
        key_i = _quantize_delta(delta_i)
        key_j = _quantize_delta(delta_j)
        cache_key = (key_i, key_j)

        if cache_key not in sample_cache:
            Psi_i = state_for({knob_i: float(delta_i)})
            Psi_j = state_for({knob_j: float(delta_j)})
            Psi_ij = state_for({knob_i: float(delta_i), knob_j: float(delta_j)})
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

    geometry_cfg = config.geometry or {}
    sample_mode = str(geometry_cfg.get("sample_mode", "direct")).lower()
    if config.compute_curvature:
        sample_mode = "direct"
    elif sample_mode not in {"direct", "phase_factor"}:
        sample_mode = "direct"

    neighbor_steps_raw = geometry_cfg.get("neighbor_steps", 1)
    try:
        neighbor_steps = max(int(neighbor_steps_raw), 1)
    except (TypeError, ValueError):
        neighbor_steps = 1

    neighbor_settle_steps = max(int(config.neighbor_settle_steps), 20)

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

    guard_cfg = config.fs_step_guard or {}
    try:
        guard_threshold = float(guard_cfg.get("threshold", 0.1))
    except (TypeError, ValueError):
        guard_threshold = 0.1
    try:
        guard_fraction = float(guard_cfg.get("fraction", 0.25))
    except (TypeError, ValueError):
        guard_fraction = 0.25
    try:
        guard_window = int(guard_cfg.get("window", 32))
    except (TypeError, ValueError):
        guard_window = 32
    guard_window = max(guard_window, 0)
    try:
        guard_cooldown = int(guard_cfg.get("cooldown", guard_window))
    except (TypeError, ValueError):
        guard_cooldown = guard_window
    guard_cooldown = max(guard_cooldown, 0)
    guard_action = str(guard_cfg.get("action", "warn")).lower()
    if guard_action not in {"warn", "slow", "none"}:
        guard_action = "warn"
    guard_enforce_p95 = _coerce_bool(guard_cfg.get("enforce_p95"), default=False)
    if not guard_enforce_p95:
        guard_enforce_p95 = _coerce_bool(guard_cfg.get("abort"), default=False)

    try:
        guard_boundary = float(guard_cfg.get("boundary", 0.1))
    except (TypeError, ValueError):
        guard_boundary = 0.1
    if not math.isfinite(guard_boundary) or guard_boundary <= 0.0:
        guard_boundary = 0.1

    try:
        guard_throttle = float(guard_cfg.get("throttle_scale", 0.5))
    except (TypeError, ValueError):
        guard_throttle = 0.5
    if not math.isfinite(guard_throttle) or not (0.0 < guard_throttle < 1.0):
        guard_throttle = 0.5

    guard_enabled = (
        math.isfinite(guard_threshold)
        and guard_threshold > 0.0
        and math.isfinite(guard_fraction)
        and guard_fraction > 0.0
        and guard_window > 0
    )
    if guard_enabled:
        guard_fraction = min(guard_fraction, 1.0)
        fs_guard_history: deque[bool] | None = deque(maxlen=guard_window)
    else:
        fs_guard_history = None
    guard_exceedances = 0
    guard_events: list[dict[str, float]] = []
    guard_last_trigger = -math.inf
    guard_peak_ratio = 0.0
    fs_guard_bad_steps = 0
    fs_guard_abort_step: int | None = None
    fs_guard_abort_fraction = 0.0
    guard_abort_pending = False

    direction_cache: dict[str, np.ndarray] = {}
    phase_cache: dict[tuple[str, float], np.ndarray] = {}

    delta_frac_base = {key: float(val) for key, val in (config.delta_frac or {}).items()}
    delta_frac_scale = 1.0
    throttle_pending = False
    warned_delta_frac: set[str] = set()

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

    noise_cfg = config.noise or {}
    theta_sigma = _noise_sigma(noise_cfg, "theta", aliases=("phase",))
    prob_sigma = _noise_sigma(noise_cfg, "prob", aliases=("amp", "amp_noise"))
    delay_sigma = _noise_sigma(noise_cfg, "delay", aliases=("tau",))
    clip_floor = float(noise_cfg.get("clip_floor", 0.0)) if noise_cfg else 0.0

    readout_cfg = config.readout or {}
    readout_steps = {
        int(step)
        for step in readout_cfg.get("steps", [])
        if isinstance(step, int) or (isinstance(step, float) and step.is_integer())
    }
    readout_interval = int(readout_cfg.get("interval", 0)) if readout_cfg.get("interval") else 0
    collect_final = bool(readout_cfg.get("final", False))
    snapshot_interval = max(int(config.snapshot_interval), 1)
    kept_snapshot_steps: list[int] = [0]

    def should_snapshot(step: int, *, is_final: bool = False) -> bool:
        return is_final or (step % snapshot_interval == 0)

    for s in range(path.steps):
        if throttle_pending and delta_frac_base:
            delta_frac_scale = max(delta_frac_scale * guard_throttle, 1e-6)
            throttle_pending = False

        lambda_state_raw, delta_lambda_raw, delta_area_val = path.step(s)
        lambda_state = {key: float(val) for key, val in lambda_state_raw.items()}
        delta_lambda = {key: float(val) for key, val in delta_lambda_raw.items()}
        delta_area = float(delta_area_val)

        if "zeta" not in lambda_state:
            lambda_state["zeta"] = float(config.zeta)

        lambda_path.append(lambda_state)
        delta_lambda_log.append(delta_lambda)
        delta_area_log.append(delta_area)

        rho = float(lambda_state.get("rho", 0.0))
        tau_scale = _resolve_tau_scale(lambda_state)
        kappa = float(lambda_state.get("kappa", 1.0))
        omega_scale_val = float(lambda_state.get("omega_scale", config.omega_scale))
        zeta_eff = float(lambda_state.get("zeta", config.zeta))
        phi_edge = _phi_edge_for_substrate(S, lambda_state)

        if delay_sigma > 0.0:
            tau_jitter = rng.normal(0.0, delay_sigma)
            tau_scale_eff = max(tau_scale + tau_jitter, 1e-6)
        else:
            tau_scale_eff = tau_scale

        K = build_transport_kernel(S, rho=rho, tau_scale=tau_scale_eff, kappa=kappa)
        omega_n = omega_from_delays(S, rho=rho, tau_scale=tau_scale_eff, omega_scale=omega_scale_val)
        J = build_J_from_W(S, zeta=zeta_eff)

        Psi0 = psi_current
        geometry_knobs = set(delta_frac_base.keys()) | set(delta_lambda.keys())

        knob_deltas: dict[str, float] = {}
        neighbor_states: dict[str, np.ndarray] = {}
        A_per_knob: dict[str, np.ndarray] = {}

        direct_state_for: Callable[[Mapping[str, float]], np.ndarray] | None = None
        if sample_mode == "direct" and geometry_knobs:
            direct_state_for = _direct_neighbor_state_factory(
                S,
                lambda_state,
                pQ,
                theta,
                config,
                neighbor_steps=neighbor_steps,
                settle_steps=neighbor_settle_steps,
            )

        for knob in sorted(geometry_knobs):
            scale = abs(lambda_state.get(knob, 1.0))
            if scale == 0.0:
                scale = 1.0
            base_frac = float(delta_frac_base.get(knob, 0.0)) * delta_frac_scale
            if knob not in delta_frac_base and knob in delta_lambda and knob not in warned_delta_frac:
                warned_delta_frac.add(knob)
                _LOGGER.warning(
                    "delta_frac missing knob '%s'; falling back to delta_lambda for geometry sampling.",
                    knob,
                )
            delta_candidate = base_frac * scale
            if delta_candidate == 0.0 and knob in delta_lambda:
                delta_candidate = float(delta_lambda[knob])
            if delta_candidate == 0.0:
                A_per_knob[knob] = np.zeros(N, dtype=float)
                continue

            knob_deltas[knob] = float(delta_candidate)
            if sample_mode == "phase_factor":
                factor = phase_factor(knob, delta_candidate)
                Psi_i = Psi0 * factor
            else:
                if direct_state_for is None:
                    direct_state_for = _direct_neighbor_state_factory(
                        S,
                        lambda_state,
                        pQ,
                        theta,
                        config,
                        neighbor_steps=neighbor_steps,
                        settle_steps=neighbor_settle_steps,
                    )
                Psi_i = direct_state_for({knob: float(delta_candidate)})
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
                if sample_mode == "phase_factor":
                    sampler = _psi_sampler_factory_phase(Psi0, direction_for(knob_i), direction_for(knob_j))
                else:
                    if direct_state_for is None:
                        direct_state_for = _direct_neighbor_state_factory(
                            S,
                            lambda_state,
                            pQ,
                            theta,
                            config,
                            neighbor_steps=neighbor_steps,
                            settle_steps=neighbor_settle_steps,
                        )
                    sampler = _psi_sampler_factory_direct(Psi0, knob_i, knob_j, direct_state_for)
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
                        "tile_area": float(abs(delta_i * delta_j)),
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

        delta_theta_geom = phase_kick(theta, A_per_knob, delta_lambda)

        theta_next = theta_step(theta, omega_n, J, delta_theta_geom, phi_edge=phi_edge)

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

        snapshot_step = s + 1

        psi_raw = build_psi(pQ, theta)
        psi_current, psi_ema = smooth_psi(psi_raw, psi_ema)

        fs_step = float("nan")
        prev_state = Psi0
        if prev_state is not None and prev_state.size and psi_current.size:
            try:
                fs_step = float(fs_distance(prev_state, psi_current))
            except ValueError:
                fs_step = float("nan")
        fs_steps.append(fs_step)

        if guard_enabled and fs_guard_history is not None:
            exceeds = math.isfinite(fs_step) and fs_step > guard_threshold
            fs_guard_history.append(exceeds)
            if exceeds:
                guard_exceedances += 1
            if fs_guard_history.maxlen and len(fs_guard_history) == fs_guard_history.maxlen:
                ratio = sum(1 for flag in fs_guard_history if flag) / fs_guard_history.maxlen
                guard_peak_ratio = max(guard_peak_ratio, ratio)
                if ratio >= guard_fraction and (s + 1) - guard_last_trigger >= guard_cooldown:
                    guard_last_trigger = s + 1
                    guard_events.append({"step": int(s + 1), "ratio": float(ratio)})
                    if guard_action in {"warn", "slow"}:
                        warnings.warn(
                            (
                                f"FS step exceeded {guard_threshold:.3f} rad in "
                                f"{ratio:.0%} of the last {fs_guard_history.maxlen} steps; "
                                "consider reducing step sizes or enabling additional smoothing."
                            ),
                            RuntimeWarning,
                            stacklevel=2,
                        )
                    fs_guard_history.clear()

        exceeds_boundary = math.isfinite(fs_step) and fs_step > guard_boundary
        if exceeds_boundary:
            fs_guard_bad_steps += 1

        if guard_enforce_p95 and (
            fs_guard_abort_step is None
            and path.steps > 0
            and _should_abort_fs(
                fs_guard_bad_steps,
                s + 1,
                total_steps=int(path.steps),
                q=0.95,
            )
        ):
            fs_guard_abort_step = s + 1
            fs_guard_abort_fraction = float(fs_guard_bad_steps) / float(max(path.steps, 1))
            guard_abort_pending = True
            warnings.warn(
                (
                    "Aborting parameter loop: FS guard cannot be satisfied; "
                    f"{fs_guard_bad_steps} of {path.steps} steps already exceed "
                    f"boundary {guard_boundary:.3f} rad."
                ),
                RuntimeWarning,
                stacklevel=2,
            )

        if delta_frac_base and exceeds_boundary:
            throttle_pending = True

        is_final_step = guard_abort_pending or snapshot_step == path.steps
        if should_snapshot(snapshot_step, is_final=is_final_step):
            kept_snapshot_steps.append(snapshot_step)
            pQ_traj.append(pQ.copy())
            theta_traj.append(theta.copy())
            psi_traj.append(psi_current.copy())
            curvature_biases.append(Gamma.copy())
            phase_kicks.append(np.asarray(delta_theta_geom, dtype=float).copy())

        should_emit = False
        if readout_interval and (s + 1) % readout_interval == 0:
            should_emit = True
        if readout_steps and ((s + 1) in readout_steps or s in readout_steps):
            should_emit = True
        if should_emit:
            readouts.append(_collect_readout(s + 1, lambda_state, pQ, theta, clip_count))

        init_state.last_lambda = lambda_state

        if guard_abort_pending:
            break

    if collect_final:
        final_lambda = lambda_path[-1] if lambda_path else {}
        final_clip = clip_counts[-1] if clip_counts else 0
        readouts.append(_collect_readout(len(lambda_path), final_lambda, pQ, theta, final_clip))

    completed_steps = len(fs_steps)

    if guard_enabled and fs_guard_history is not None and completed_steps > 0:
        overall_fraction = guard_exceedances / float(completed_steps)
    else:
        overall_fraction = 0.0

    fs_steps_arr = np.asarray([step for step in fs_steps if math.isfinite(step)], dtype=float)
    fs_p95 = float(np.percentile(fs_steps_arr, 95)) if fs_steps_arr.size else float("nan")
    fs_boundary = guard_boundary
    fs_boundary_exceeded = bool(fs_steps_arr.size and fs_p95 > fs_boundary)
    if fs_boundary_exceeded:
        warnings.warn(
            (
                f"Fubini-Study step p95={fs_p95:.3f} rad exceeds boundary "
                f"{fs_boundary:.3f} rad; consider reducing loop step size or smoothing."
            ),
            RuntimeWarning,
            stacklevel=2,
        )
    guard_meta = {
        "enabled": bool(guard_enabled),
        "threshold": float(guard_threshold),
        "fraction": float(guard_fraction),
        "window": int(fs_guard_history.maxlen if fs_guard_history is not None else guard_window),
        "cooldown": int(guard_cooldown),
        "action": guard_action,
        "throttle_scale": float(guard_throttle),
        "total_exceedances": int(guard_exceedances),
        "overall_fraction": float(overall_fraction),
        "trigger_steps": guard_events,
        "peak_ratio": float(guard_peak_ratio),
        "p95": float(fs_p95),
        "boundary": float(fs_boundary),
        "boundary_exceeded": bool(fs_boundary_exceeded),
        "boundary_bad_steps": int(fs_guard_bad_steps),
        "completed_steps": int(completed_steps),
        "enforce_p95": bool(guard_enforce_p95),
        "early_abort": bool(guard_enforce_p95 and fs_guard_abort_step is not None),
        "early_abort_step": (
            None if not guard_enforce_p95 or fs_guard_abort_step is None else int(fs_guard_abort_step)
        ),
        "early_abort_fraction": (float(fs_guard_abort_fraction) if guard_enforce_p95 else 0.0),
    }

    phi_flux_total = 0.0
    phi_tiles_present = False
    if omega_tiles:
        for tile in omega_tiles:
            if not isinstance(tile, dict):
                continue
            try:
                omega_val = float(tile.get("omega", 0.0))
                area_val = float(tile.get("tile_area", 0.0))
            except (TypeError, ValueError):  # pragma: no cover - defensive guard
                continue
            if math.isfinite(omega_val) and math.isfinite(area_val):
                phi_tiles_present = True
                phi_flux_total += omega_val * area_val

    phi_flux_missing_tiles = not phi_tiles_present and bool(config.compute_curvature)
    if phi_flux_missing_tiles:
        phi_flux_total = 0.0

    if readouts:
        final_entry = readouts[-1]
        if isinstance(final_entry, dict) and final_entry.get("step") == completed_steps:
            final_entry["phi_flux"] = float(phi_flux_total)
            final_entry["phi_flux_missing_tiles"] = bool(phi_flux_missing_tiles)
            memory_form_cfg = str(readout_cfg.get("memory_form", "")).lower()
            readout_params = readout_cfg.get("params") or {}
            if memory_form_cfg == "uniform_charge":
                chi_param = readout_params.get("chi")
                chi_vec = None
                if chi_param is not None:
                    try:
                        chi_vec = np.asarray(chi_param, dtype=float)
                    except (TypeError, ValueError):  # pragma: no cover - defensive guard
                        chi_vec = None

                centrality_spec = readout_params.get("centrality")
                centrality_vec = _centrality_vector(S, centrality_spec)

                mode = str(readout_params.get("mode", "psi_amp")).lower()
                target = readout_params.get("target")
                try:
                    target_index = None if target is None else int(target)
                except (TypeError, ValueError):  # pragma: no cover - defensive guard
                    target_index = None

                source = str(readout_params.get("pQ_source", "psi")).lower()
                if source == "probability":
                    susceptibility_basis = pQ
                else:
                    susceptibility_basis = psi_current

                memory_vec = memory_uniform_charge(
                    phi_flux_total,
                    chi=chi_vec,
                    mode=mode,
                    target=target_index,
                    centrality=centrality_vec,
                    pQ=susceptibility_basis,
                )
                final_entry["memory_form"] = "uniform_charge"
                final_entry["memory"] = np.asarray(memory_vec, dtype=float).tolist()

    meta: dict[str, Any] = {
        "seed": int(seed),
        "rng": {"base": int(seed)},
        "steps": int(path.steps),
        "config": asdict(config),
        "substrate_size": int(N),
        "path": {
            "kind": path.kind,
            "steps": path.steps,
            "completed": int(completed_steps),
        },
    }

    meta["fs_step_guard"] = guard_meta
    meta["phi_flux_missing_tiles"] = bool(phi_flux_missing_tiles)
    meta["snapshot_cadence"] = {
        "interval": int(snapshot_interval),
        "kept_steps": kept_snapshot_steps,
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

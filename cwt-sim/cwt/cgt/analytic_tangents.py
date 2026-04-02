from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .benchmarks import get_benchmark


@dataclass(frozen=True)
class AnalyticBranchTangents:
    state: object
    branch_id: str
    dp_du: np.ndarray
    dp_dv: np.ndarray
    dtheta_du: np.ndarray
    dtheta_dv: np.ndarray
    dkernel_du: np.ndarray
    dkernel_dv: np.ndarray


def _clip_slope(raw: float, slope: float, low: float, high: float) -> float:
    return float(slope if (low < raw < high) else 0.0)


def _softmax_prob_and_derivative(logits: np.ndarray, dlogits: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    z = np.asarray(logits, dtype=float)
    z = z - float(np.max(z))
    expz = np.exp(z)
    p = expz / max(float(np.sum(expz)), 1e-15)
    dz = np.asarray(dlogits, dtype=float)
    dp = p * (dz - float(np.dot(p, dz)))
    return p, dp


def _alpha_slope(alpha: float, width: float) -> float:
    return 1.0 / width if (1e-9 < alpha < 1.0 - 1e-9) else 0.0


def _tangents_a(branch_id: str, u: float, v: float) -> AnalyticBranchTangents:
    benchmark = get_benchmark('benchmark_a')
    _cand = benchmark.resolve_candidate_by_id(u, v, branch_id)
    if _cand is None:
        raise ValueError(f"Branch ID {branch_id!r} not found in atlas")
    state = _cand.state
    raw_a = 0.18 + 0.10 * u
    raw_b = 0.18 - 0.10 * u
    a = float(state.kernel[0, 1])
    b = float(state.kernel[1, 0])
    da_du = _clip_slope(raw_a, 0.10, 0.05, 0.42)
    db_du = _clip_slope(raw_b, -0.10, 0.05, 0.42)
    denom = max(a + b, 1e-12)
    dp0_du = (db_du * denom - b * (da_du + db_du)) / (denom * denom)
    dp_du = np.array([dp0_du, -dp0_du], dtype=float)
    dkernel_du = np.array([[-da_du, da_du], [db_du, -db_du]], dtype=float)
    dkernel_dv = np.zeros_like(dkernel_du)
    return AnalyticBranchTangents(
        state=state,
        branch_id=branch_id,
        dp_du=dp_du,
        dp_dv=np.zeros(2, dtype=float),
        dtheta_du=np.zeros(2, dtype=float),
        dtheta_dv=np.array([1.0, 1.0], dtype=float),
        dkernel_du=dkernel_du,
        dkernel_dv=dkernel_dv,
    )


def _tangents_b(branch_id: str, u: float, v: float) -> AnalyticBranchTangents:
    benchmark = get_benchmark('benchmark_b')
    cand = benchmark.resolve_candidate_by_id(u, v, branch_id)
    if cand is None:
        raise ValueError(f"Branch ID {branch_id!r} not found in atlas")
    state = cand.state
    alpha = float(state.extras.get('alpha', 0.0))
    raw_l = 0.22 + 0.08 * v + 0.08 * u
    raw_r = 0.22 + 0.08 * v - 0.08 * u
    dk_left_du = _clip_slope(raw_l, 0.08, 0.04, 0.44)
    dk_left_dv = _clip_slope(raw_l, 0.08, 0.04, 0.44)
    dk_right_du = _clip_slope(raw_r, -0.08, 0.04, 0.44)
    dk_right_dv = _clip_slope(raw_r, 0.08, 0.04, 0.44)
    dkernel_du = np.array(
        [[-dk_left_du, dk_left_du, 0.0], [dk_left_du, -dk_left_du - dk_right_du, dk_right_du], [0.0, dk_right_du, -dk_right_du]],
        dtype=float,
    )
    dkernel_dv = np.array(
        [[-dk_left_dv, dk_left_dv, 0.0], [dk_left_dv, -dk_left_dv - dk_right_dv, dk_right_dv], [0.0, dk_right_dv, -dk_right_dv]],
        dtype=float,
    )

    alpha_dv = _alpha_slope(alpha, 0.42) if branch_id == 'B1' else 0.0
    phase_sign = float(state.extras.get('phase_sign', 1.0))
    tilt_shift = float(state.extras.get('tilt_shift', 0.0))
    dphase_sign_dv = 0.10 * alpha_dv if branch_id == 'B1' else 0.0
    dshift_dv = 0.08 * alpha_dv if branch_id == 'B1' else 0.0
    logits = np.array([0.42 * u + 0.28 * v + tilt_shift, -0.08 * u - 0.05 * v, -0.34 * u - 0.23 * v - tilt_shift], dtype=float)
    p, dp_du = _softmax_prob_and_derivative(logits, np.array([0.42, -0.08, -0.34], dtype=float))
    _, dp_dv = _softmax_prob_and_derivative(logits, np.array([0.28 + dshift_dv, -0.05, -0.23 - dshift_dv], dtype=float))
    # use state's p to stay consistent with chosen candidate normalization
    dp_du = dp_du + (np.asarray(state.p, dtype=float) - p) * 0.0
    dp_dv = dp_dv + (np.asarray(state.p, dtype=float) - p) * 0.0

    dphi_du = phase_sign * 0.18 * (1.0 + 0.30 * v)
    dphi_dv = dphase_sign_dv * 0.18 * u * (1.0 + 0.30 * v) + phase_sign * 0.18 * u * 0.30 + 0.04 * dshift_dv
    return AnalyticBranchTangents(
        state=state,
        branch_id=branch_id,
        dp_du=dp_du,
        dp_dv=dp_dv,
        dtheta_du=np.array([-dphi_du, 0.0, dphi_du], dtype=float),
        dtheta_dv=np.array([-dphi_dv, 0.0, dphi_dv], dtype=float),
        dkernel_du=dkernel_du,
        dkernel_dv=dkernel_dv,
    )


def _tangents_c(branch_id: str, u: float, v: float) -> AnalyticBranchTangents:
    benchmark = get_benchmark('benchmark_c')
    cand = benchmark.resolve_candidate_by_id(u, v, branch_id)
    if cand is None:
        raise ValueError(f"Branch ID {branch_id!r} not found in atlas")
    state = cand.state
    alpha = float(state.extras.get('alpha', 0.0))
    raw_cw = 0.18 + 0.10 * u
    raw_ccw = 0.18 - 0.10 * u
    dk_cw_du = _clip_slope(raw_cw, 0.10, 0.04, 0.40)
    dk_ccw_du = _clip_slope(raw_ccw, -0.10, 0.04, 0.40)
    dkernel_du = np.zeros((3, 3), dtype=float)
    dkernel_dv = np.zeros((3, 3), dtype=float)
    for node in range(3):
        dkernel_du[node, node] = -dk_cw_du - dk_ccw_du
        dkernel_du[node, (node + 1) % 3] = dk_cw_du
        dkernel_du[node, (node - 1) % 3] = dk_ccw_du

    alpha_dv = _alpha_slope(alpha, 0.40) if branch_id == 'C1' else 0.0
    chirality = float(state.extras.get('chirality', 1.0))
    tilt_shift = float(state.extras.get('tilt_shift', 0.0))
    dchirality_dv = 0.05 * alpha_dv if branch_id == 'C1' else 0.0
    dshift_dv = 0.10 * alpha_dv if branch_id == 'C1' else 0.0

    logits = np.array([0.85 * u + 0.50 * v + tilt_shift, -0.70 * u + 0.35 * u * v, -0.55 * v - 0.25 * u * v - tilt_shift], dtype=float)
    _, dp_du = _softmax_prob_and_derivative(logits, np.array([0.85, -0.70 + 0.35 * v, -0.25 * v], dtype=float))
    _, dp_dv = _softmax_prob_and_derivative(logits, np.array([0.50 + dshift_dv, 0.35 * u, -0.55 - 0.25 * u - dshift_dv], dtype=float))

    base_phase = 0.70 * v + 0.45 * u * v + 0.15 * u
    dphi_du = chirality * (0.45 * v + 0.15)
    dphi_dv = dchirality_dv * base_phase + chirality * (0.70 + 0.45 * u) + 0.06 * dshift_dv
    return AnalyticBranchTangents(
        state=state,
        branch_id=branch_id,
        dp_du=dp_du,
        dp_dv=dp_dv,
        dtheta_du=np.array([dphi_du, 0.0, -dphi_du], dtype=float),
        dtheta_dv=np.array([dphi_dv, 0.0, -dphi_dv], dtype=float),
        dkernel_du=dkernel_du,
        dkernel_dv=dkernel_dv,
    )


def _tangents_d(branch_id: str, u: float, v: float) -> AnalyticBranchTangents:
    benchmark = get_benchmark('benchmark_d')
    _cand = benchmark.resolve_candidate_by_id(u, v, branch_id)
    if _cand is None:
        raise ValueError(f"Branch ID {branch_id!r} not found in atlas")
    state = _cand.state
    raw_plus = v + u
    raw_minus = v - u
    k_plus = float(np.clip(raw_plus, 0.02, 0.46))
    k_minus = float(np.clip(raw_minus, 0.02, 0.46))
    dk_plus_du = _clip_slope(raw_plus, 1.0, 0.02, 0.46)
    dk_plus_dv = _clip_slope(raw_plus, 1.0, 0.02, 0.46)
    dk_minus_du = _clip_slope(raw_minus, -1.0, 0.02, 0.46)
    dk_minus_dv = _clip_slope(raw_minus, 1.0, 0.02, 0.46)

    dkernel_du = np.zeros((5, 5), dtype=float)
    dkernel_dv = np.zeros((5, 5), dtype=float)
    dkernel_du[0, 0] = -dk_plus_du; dkernel_du[0, 1] = dk_plus_du
    dkernel_dv[0, 0] = -dk_plus_dv; dkernel_dv[0, 1] = dk_plus_dv
    for node in range(1, 4):
        dkernel_du[node, node - 1] = dk_minus_du
        dkernel_du[node, node + 1] = dk_plus_du
        dkernel_du[node, node] = -dk_plus_du - dk_minus_du
        dkernel_dv[node, node - 1] = dk_minus_dv
        dkernel_dv[node, node + 1] = dk_plus_dv
        dkernel_dv[node, node] = -dk_plus_dv - dk_minus_dv
    dkernel_du[4, 3] = dk_minus_du; dkernel_du[4, 4] = -dk_minus_du
    dkernel_dv[4, 3] = dk_minus_dv; dkernel_dv[4, 4] = -dk_minus_dv

    ratio = max(k_plus / max(k_minus, 1e-12), 1e-12)
    idx = np.arange(5, dtype=float)
    logits = idx * np.log(ratio)
    dlogr_du = dk_plus_du / max(k_plus, 1e-12) - dk_minus_du / max(k_minus, 1e-12)
    dlogr_dv = dk_plus_dv / max(k_plus, 1e-12) - dk_minus_dv / max(k_minus, 1e-12)
    _, dp_du = _softmax_prob_and_derivative(logits, idx * dlogr_du)
    _, dp_dv = _softmax_prob_and_derivative(logits, idx * dlogr_dv)
    return AnalyticBranchTangents(
        state=state,
        branch_id=branch_id,
        dp_du=dp_du,
        dp_dv=dp_dv,
        dtheta_du=np.zeros(5, dtype=float),
        dtheta_dv=np.zeros(5, dtype=float),
        dkernel_du=dkernel_du,
        dkernel_dv=dkernel_dv,
    )


def _tangents_f(branch_id: str, u: float, v: float) -> AnalyticBranchTangents:
    benchmark = get_benchmark('benchmark_f')
    _cand = benchmark.resolve_candidate_by_id(u, v, branch_id)
    if _cand is None:
        raise ValueError(f"Branch ID {branch_id!r} not found in atlas")
    state = _cand.state
    sign = float(state.extras.get('sign', 1.0))
    sech2 = 1.0 / np.cosh(float(u)) ** 2
    raw_l = 0.20 + 0.04 * v + 0.03 * np.tanh(u)
    raw_r = 0.20 + 0.04 * v - 0.03 * np.tanh(u)
    dk_left_du = _clip_slope(raw_l, 0.03 * sech2, 0.04, 0.44)
    dk_left_dv = _clip_slope(raw_l, 0.04, 0.04, 0.44)
    dk_right_du = _clip_slope(raw_r, -0.03 * sech2, 0.04, 0.44)
    dk_right_dv = _clip_slope(raw_r, 0.04, 0.04, 0.44)
    dkernel_du = np.array(
        [[-dk_left_du, dk_left_du, 0.0], [dk_left_du, -dk_left_du - dk_right_du, dk_right_du], [0.0, dk_right_du, -dk_right_du]],
        dtype=float,
    )
    dkernel_dv = np.array(
        [[-dk_left_dv, dk_left_dv, 0.0], [dk_left_dv, -dk_left_dv - dk_right_dv, dk_right_dv], [0.0, dk_right_dv, -dk_right_dv]],
        dtype=float,
    )
    damp_du = 0.20 * np.sign(u) if abs(u) > 1e-12 else 0.0
    damp_dv = 0.35 if v > 0.0 else 0.0
    logits = np.array([sign * (0.75 + 0.35 * max(v, 0.0) + 0.20 * abs(u)) + 0.10 * u, 0.0, -sign * (0.75 + 0.35 * max(v, 0.0) + 0.20 * abs(u)) - 0.10 * u], dtype=float)
    _, dp_du = _softmax_prob_and_derivative(logits, np.array([sign * damp_du + 0.10, 0.0, -sign * damp_du - 0.10], dtype=float))
    _, dp_dv = _softmax_prob_and_derivative(logits, np.array([sign * damp_dv, 0.0, -sign * damp_dv], dtype=float))
    dphi_du = 0.08
    dphi_dv = sign * 0.25 if v > 0.0 else 0.0
    return AnalyticBranchTangents(
        state=state,
        branch_id=branch_id,
        dp_du=dp_du,
        dp_dv=dp_dv,
        dtheta_du=np.array([-dphi_du, 0.0, dphi_du], dtype=float),
        dtheta_dv=np.array([-dphi_dv, 0.0, dphi_dv], dtype=float),
        dkernel_du=dkernel_du,
        dkernel_dv=dkernel_dv,
    )


def analytic_branch_tangents(benchmark_id: str, branch_id: str, u: float, v: float) -> AnalyticBranchTangents:
    if benchmark_id == 'benchmark_a':
        return _tangents_a(branch_id, u, v)
    if benchmark_id == 'benchmark_b':
        return _tangents_b(branch_id, u, v)
    if benchmark_id == 'benchmark_c':
        return _tangents_c(branch_id, u, v)
    if benchmark_id == 'benchmark_d':
        return _tangents_d(branch_id, u, v)
    if benchmark_id == 'benchmark_f':
        return _tangents_f(branch_id, u, v)
    raise KeyError(f'No analytic tangent model for benchmark {benchmark_id}')

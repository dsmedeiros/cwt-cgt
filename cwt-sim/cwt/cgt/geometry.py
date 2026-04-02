from __future__ import annotations

import math
from typing import Iterable

import numpy as np


def normalize_probabilities(values: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return arr
    arr = np.maximum(arr, floor)
    total = float(arr.sum())
    if total <= 0.0:
        arr = np.full(arr.shape, 1.0 / arr.size, dtype=float)
    else:
        arr = arr / total
    return arr


def wrap_phase(values: np.ndarray | float) -> np.ndarray | float:
    arr = np.asarray(values, dtype=float)
    wrapped = (arr + np.pi) % (2.0 * np.pi) - np.pi
    if np.isscalar(values):
        return float(wrapped)
    return wrapped


def canonicalize_phase(theta: np.ndarray, p: np.ndarray | None = None) -> np.ndarray:
    theta_arr = np.asarray(theta, dtype=float)
    if p is None:
        offset = float(np.mean(theta_arr))
    else:
        p_arr = normalize_probabilities(np.asarray(p, dtype=float))
        offset = float(np.dot(p_arr, theta_arr))
    return np.asarray(wrap_phase(theta_arr - offset), dtype=float)


def psi_from_parts(p: np.ndarray, theta: np.ndarray) -> np.ndarray:
    p_arr = normalize_probabilities(np.asarray(p, dtype=float))
    theta_arr = canonicalize_phase(np.asarray(theta, dtype=float), p_arr)
    psi = np.sqrt(p_arr) * np.exp(1j * theta_arr)
    norm = np.linalg.norm(psi)
    if norm <= 0.0:
        return np.full(p_arr.shape, 1.0 / math.sqrt(p_arr.size), dtype=complex)
    return psi / norm


def psi_from_state(state) -> np.ndarray:
    return psi_from_parts(state.p, state.theta)


def overlap(psi_a: np.ndarray, psi_b: np.ndarray) -> float:
    a = np.asarray(psi_a, dtype=complex)
    b = np.asarray(psi_b, dtype=complex)
    return float(abs(np.vdot(a, b)))


def phase_coherence(state) -> float:
    p = normalize_probabilities(np.asarray(state.p, dtype=float))
    theta = canonicalize_phase(np.asarray(state.theta, dtype=float), p)
    return float(abs(np.sum(p * np.exp(1j * theta))))


def _projective_derivative(psi0: np.ndarray, derivative: np.ndarray) -> np.ndarray:
    return derivative - psi0 * np.vdot(psi0, derivative)


def projective_metric_trace_and_curvature(
    psi0: np.ndarray,
    psi_u_plus: np.ndarray,
    psi_u_minus: np.ndarray,
    psi_v_plus: np.ndarray,
    psi_v_minus: np.ndarray,
    du: float,
    dv: float,
) -> tuple[float, float]:
    dpsi_u = (np.asarray(psi_u_plus, dtype=complex) - np.asarray(psi_u_minus, dtype=complex)) / (2.0 * du)
    dpsi_v = (np.asarray(psi_v_plus, dtype=complex) - np.asarray(psi_v_minus, dtype=complex)) / (2.0 * dv)
    q_u = _projective_derivative(np.asarray(psi0, dtype=complex), dpsi_u)
    q_v = _projective_derivative(np.asarray(psi0, dtype=complex), dpsi_v)
    g_uu = float(np.real(np.vdot(q_u, q_u)))
    g_vv = float(np.real(np.vdot(q_v, q_v)))
    metric_trace = g_uu + g_vv
    c_uv = np.vdot(q_u, q_v)
    curvature = float(-2.0 * np.imag(c_uv))
    return metric_trace, curvature


def berry_loop_flux(states: Iterable) -> float:
    psi_states = [psi_from_state(state) for state in states]
    if len(psi_states) < 2:
        return 0.0
    prod = 1.0 + 0.0j
    for a, b in zip(psi_states[:-1], psi_states[1:]):
        ov = np.vdot(a, b)
        mag = abs(ov)
        if mag <= 1e-12:
            continue
        prod *= ov / mag
    return float(np.angle(prod))


def polygon_signed_area(path: list[tuple[float, float]]) -> float:
    if len(path) < 3:
        return 0.0
    area = 0.0
    for (x0, y0), (x1, y1) in zip(path[:-1], path[1:]):
        area += x0 * y1 - x1 * y0
    return 0.5 * area


def branch_distance(state_a, state_b, p_weight: float = 1.0, theta_weight: float = 0.55, kernel_weight: float = 0.15) -> float:
    p_a = normalize_probabilities(np.asarray(state_a.p, dtype=float))
    p_b = normalize_probabilities(np.asarray(state_b.p, dtype=float))
    p_term = float(np.linalg.norm(p_a - p_b, ord=1))

    theta_a = canonicalize_phase(np.asarray(state_a.theta, dtype=float), p_a)
    theta_b = canonicalize_phase(np.asarray(state_b.theta, dtype=float), p_b)
    theta_diff = np.asarray(wrap_phase(theta_a - theta_b), dtype=float)
    theta_term = float(np.linalg.norm(theta_diff) / max(math.sqrt(theta_diff.size) * np.pi, 1e-12))

    kernel_term = 0.0
    if getattr(state_a, 'kernel', None) is not None and getattr(state_b, 'kernel', None) is not None:
        ka = np.asarray(state_a.kernel, dtype=float)
        kb = np.asarray(state_b.kernel, dtype=float)
        kernel_term = float(np.linalg.norm(ka - kb) / max(ka.size, 1))

    return p_weight * p_term + theta_weight * theta_term + kernel_weight * kernel_term


def summarize(values: Iterable[float]) -> dict[str, float | int | None]:
    arr = np.asarray(list(values), dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return {'count': 0, 'min': None, 'max': None, 'mean': None, 'median': None}
    return {
        'count': int(arr.size),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'mean': float(np.mean(arr)),
        'median': float(np.median(arr)),
    }


def summarize_abs(values: Iterable[float]) -> dict[str, float | int | None]:
    arr = np.asarray(list(values), dtype=float)
    arr = np.abs(arr[np.isfinite(arr)])
    if arr.size == 0:
        return {'count': 0, 'min': None, 'max': None, 'mean': None, 'median': None}
    return {
        'count': int(arr.size),
        'min': float(np.min(arr)),
        'max': float(np.max(arr)),
        'mean': float(np.mean(arr)),
        'median': float(np.median(arr)),
    }

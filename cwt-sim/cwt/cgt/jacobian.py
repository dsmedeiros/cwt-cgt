from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ._geom_compat import canonicalize_phase, normalize_probabilities, psi_from_state, wrap_phase
from .modal import biorthogonal_modal_frame
from .models import BranchState


@dataclass(frozen=True)
class JacobianConfig:
    prob_relaxation: float = 0.82
    phase_relaxation: float = 0.58
    phase_transport_gain: float = 0.30
    phase_sync_gain: float = 0.22
    phase_probability_gain: float = 0.10
    state_eps: float = 1e-6
    control_eps: float = 2e-4


@dataclass(frozen=True)
class JacobianDiagnostics:
    dominant_eigenvalue: complex
    spectral_radius: float
    max_singular_value: float
    min_singular_i_minus_m: float
    inverse_min_singular_i_minus_m: float
    nonnormality_ratio: float
    stable: bool


def _state_parts(reference_state: BranchState) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    p_ref = normalize_probabilities(np.asarray(reference_state.p, dtype=float))
    theta_ref = canonicalize_phase(np.asarray(reference_state.theta, dtype=float), p_ref)
    kernel_ref = np.asarray(reference_state.kernel, dtype=float)
    return p_ref, theta_ref, kernel_ref


def state_vector(reference_state: BranchState) -> np.ndarray:
    p_ref, theta_ref, _ = _state_parts(reference_state)
    return np.concatenate([p_ref, theta_ref]).astype(float)


def unpack_state_vector(vector: np.ndarray, node_count: int) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(vector, dtype=float)
    p = normalize_probabilities(arr[:node_count])
    theta = canonicalize_phase(arr[node_count:], p)
    return p, theta


def _phase_modulated_kernel(
    kernel: np.ndarray, theta: np.ndarray, theta_ref: np.ndarray, gain: float
) -> np.ndarray:
    delta = np.sin((theta[None, :] - theta[:, None]) - (theta_ref[None, :] - theta_ref[:, None]))
    modulated = np.asarray(kernel, dtype=float) * (1.0 + gain * delta)
    modulated = np.maximum(modulated, 1e-9)
    modulated = modulated / modulated.sum(axis=1, keepdims=True)
    return modulated


def branch_map_step(
    vector: np.ndarray, reference_state: BranchState, config: JacobianConfig | None = None
) -> np.ndarray:
    cfg = config or JacobianConfig()
    p_ref, theta_ref, kernel_ref = _state_parts(reference_state)
    node_count = p_ref.size
    p, theta = unpack_state_vector(vector, node_count=node_count)

    kernel_mod = _phase_modulated_kernel(kernel_ref, theta, theta_ref, cfg.phase_transport_gain)
    transport = kernel_mod.T @ p
    p_next = normalize_probabilities((1.0 - cfg.prob_relaxation) * p + cfg.prob_relaxation * transport)

    local_phase_error = np.asarray(wrap_phase(theta - theta_ref), dtype=float)
    sync = np.sum(
        kernel_ref * np.sin((theta[None, :] - theta[:, None]) - (theta_ref[None, :] - theta_ref[:, None])),
        axis=1,
    )
    centered_prob = p - p_ref
    centered_prob = centered_prob - np.mean(centered_prob)
    theta_next = canonicalize_phase(
        theta
        - cfg.phase_relaxation * local_phase_error
        + cfg.phase_sync_gain * sync
        + cfg.phase_probability_gain * centered_prob,
        p_next,
    )
    return np.concatenate([p_next, theta_next]).astype(float)


def numerical_branch_jacobian(
    reference_state: BranchState, config: JacobianConfig | None = None
) -> np.ndarray:
    cfg = config or JacobianConfig()
    x0 = state_vector(reference_state)
    dim = x0.size
    jac = np.zeros((dim, dim), dtype=float)
    for idx in range(dim):
        delta = np.zeros(dim, dtype=float)
        delta[idx] = cfg.state_eps
        plus = branch_map_step(x0 + delta, reference_state, cfg)
        minus = branch_map_step(x0 - delta, reference_state, cfg)
        jac[:, idx] = (plus - minus) / (2.0 * cfg.state_eps)
    return jac


def _resolve_reference_state(
    benchmark, controls: tuple[float, float], branch_id: str, fallback_state: BranchState
) -> BranchState:
    candidate = benchmark.resolve_candidate_by_id(float(controls[0]), float(controls[1]), branch_id)
    if candidate is not None:
        return candidate.state
    return fallback_state


def _clip_controls(benchmark, controls: tuple[float, float]) -> tuple[float, float]:
    (u_min, u_max), (v_min, v_max) = benchmark.control_bounds
    return (min(max(float(controls[0]), u_min), u_max), min(max(float(controls[1]), v_min), v_max))


def control_coupling_vectors(
    benchmark,
    u: float,
    v: float,
    branch_id: str,
    reference_state: BranchState,
    config: JacobianConfig | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    cfg = config or JacobianConfig()
    x0 = state_vector(reference_state)
    plus_u = _resolve_reference_state(
        benchmark, _clip_controls(benchmark, (u + cfg.control_eps, v)), branch_id, reference_state
    )
    minus_u = _resolve_reference_state(
        benchmark, _clip_controls(benchmark, (u - cfg.control_eps, v)), branch_id, reference_state
    )
    plus_v = _resolve_reference_state(
        benchmark, _clip_controls(benchmark, (u, v + cfg.control_eps)), branch_id, reference_state
    )
    minus_v = _resolve_reference_state(
        benchmark, _clip_controls(benchmark, (u, v - cfg.control_eps)), branch_id, reference_state
    )

    bu = (branch_map_step(x0, plus_u, cfg) - branch_map_step(x0, minus_u, cfg)) / (2.0 * cfg.control_eps)
    bv = (branch_map_step(x0, plus_v, cfg) - branch_map_step(x0, minus_v, cfg)) / (2.0 * cfg.control_eps)
    return bu.astype(float), bv.astype(float)


def solve_branch_response(jacobian: np.ndarray, control_vector: np.ndarray) -> np.ndarray:
    matrix = np.eye(jacobian.shape[0], dtype=float) - np.asarray(jacobian, dtype=float)
    rhs = np.asarray(control_vector, dtype=float)
    solution, *_ = np.linalg.lstsq(matrix, rhs, rcond=None)
    return solution.astype(float)


def response_vectors(
    benchmark,
    u: float,
    v: float,
    branch_id: str,
    reference_state: BranchState,
    config: JacobianConfig | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    jac = numerical_branch_jacobian(reference_state, config=config)
    bu, bv = control_coupling_vectors(
        benchmark, u=u, v=v, branch_id=branch_id, reference_state=reference_state, config=config
    )
    du = solve_branch_response(jac, bu)
    dv = solve_branch_response(jac, bv)
    return jac, du, dv


def vector_to_dpsi(reference_state: BranchState, response_vector: np.ndarray) -> np.ndarray:
    p_ref, theta_ref, _ = _state_parts(reference_state)
    node_count = p_ref.size
    delta_p = np.asarray(response_vector[:node_count], dtype=float)
    delta_theta = np.asarray(response_vector[node_count:], dtype=float)
    delta_theta = delta_theta - float(np.dot(p_ref, delta_theta))
    prefactor = np.exp(1j * theta_ref)
    amplitude_term = 0.5 * delta_p / np.sqrt(np.maximum(p_ref, 1e-12))
    phase_term = 1j * np.sqrt(p_ref) * delta_theta
    return prefactor * (amplitude_term + phase_term)


def response_metric_trace_and_curvature(
    reference_state: BranchState, du_vec: np.ndarray, dv_vec: np.ndarray
) -> tuple[float, float]:
    psi0 = psi_from_state(reference_state)
    dpsi_u = vector_to_dpsi(reference_state, du_vec)
    dpsi_v = vector_to_dpsi(reference_state, dv_vec)
    q_u = dpsi_u - psi0 * np.vdot(psi0, dpsi_u)
    q_v = dpsi_v - psi0 * np.vdot(psi0, dpsi_v)
    metric_trace = float(np.real(np.vdot(q_u, q_u)) + np.real(np.vdot(q_v, q_v)))
    curvature = float(2.0 * np.imag(np.vdot(q_u, q_v)))
    return metric_trace, curvature


def jacobian_diagnostics(jacobian: np.ndarray) -> JacobianDiagnostics:
    matrix = np.asarray(jacobian, dtype=float)
    eigvals = np.linalg.eigvals(matrix)
    singular = np.linalg.svd(matrix, compute_uv=False)
    i_minus = np.eye(matrix.shape[0], dtype=float) - matrix
    s_i_minus = np.linalg.svd(i_minus, compute_uv=False)
    spectral_radius = float(np.max(np.abs(eigvals))) if eigvals.size else 0.0
    max_singular = float(np.max(singular)) if singular.size else 0.0
    min_singular_i_minus = float(np.min(s_i_minus)) if s_i_minus.size else 0.0
    dominant_index = int(np.argmin(np.abs(eigvals - 1.0))) if eigvals.size else 0
    dominant_eigenvalue = eigvals[dominant_index] if eigvals.size else 0.0 + 0.0j
    return JacobianDiagnostics(
        dominant_eigenvalue=dominant_eigenvalue,
        spectral_radius=spectral_radius,
        max_singular_value=max_singular,
        min_singular_i_minus_m=min_singular_i_minus,
        inverse_min_singular_i_minus_m=float(1.0 / max(min_singular_i_minus, 1e-12)),
        nonnormality_ratio=float(max_singular / max(spectral_radius, 1e-12)),
        stable=bool(spectral_radius < 1.0),
    )


def jacobian_modal_frame(jacobian: np.ndarray):
    return biorthogonal_modal_frame(np.asarray(jacobian, dtype=complex), dominant_target=1.0 + 0.0j)

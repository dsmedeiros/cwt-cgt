from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cwt.geometry.mixed_state import density_from_state, offdiag_norm, project_to_density

from ._geom_compat import canonicalize_phase


@dataclass(frozen=True)
class OpenSystemConfig:
    dt: float = 0.18
    coherent_scale: float = 1.05
    edge_jump_scale: float = 0.20
    site_potential_scale: float = 0.18
    depolarizing: float = 0.008
    branch_steps: int = 3
    fixed_point_max_iter: int = 160
    fixed_point_tol: float = 1e-10
    dephasing_values: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
    coherence_switch_floor: float = 0.20
    scan_mesh: int = 9


def _unitary_from_hermitian(hamiltonian: np.ndarray, dt: float) -> np.ndarray:
    evals, evecs = np.linalg.eigh(0.5 * (hamiltonian + hamiltonian.conj().T))
    phases = np.exp(-1j * dt * evals)
    return evecs @ np.diag(phases) @ evecs.conj().T


def branch_hamiltonian(state, config: OpenSystemConfig) -> np.ndarray:
    kernel = np.asarray(state.kernel, dtype=float)
    p = np.asarray(state.p, dtype=float)
    theta = canonicalize_phase(np.asarray(state.theta, dtype=float), p)
    n = p.size
    h = np.zeros((n, n), dtype=complex)
    diag = -config.site_potential_scale * (np.log(np.maximum(p, 1e-12)) - float(np.mean(np.log(np.maximum(p, 1e-12)))))
    h += np.diag(diag)
    for i in range(n):
        for j in range(i + 1, n):
            sym = 0.5 * (kernel[i, j] + kernel[j, i])
            if sym <= 0.0:
                continue
            phase = 0.5 * (theta[j] - theta[i])
            entry = config.coherent_scale * sym * np.exp(1j * phase)
            h[i, j] = entry
            h[j, i] = np.conj(entry)
    return h


def _safe_no_jump_operator(sum_term: np.ndarray) -> np.ndarray:
    ident = np.eye(sum_term.shape[0], dtype=complex)
    evals, evecs = np.linalg.eigh(0.5 * ((ident - sum_term) + (ident - sum_term).conj().T))
    evals = np.clip(np.real(evals), 0.0, None)
    return evecs @ np.diag(np.sqrt(evals)) @ evecs.conj().T


def local_kraus_operators(state, config: OpenSystemConfig, dephasing: float) -> list[np.ndarray]:
    kernel = np.asarray(state.kernel, dtype=float)
    n = kernel.shape[0]
    dt = config.dt
    unitary = _unitary_from_hermitian(branch_hamiltonian(state, config), dt)

    jump_ops: list[np.ndarray] = []
    sum_term = np.zeros((n, n), dtype=complex)
    for src in range(n):
        for dst in range(n):
            if src == dst:
                continue
            rate = max(kernel[src, dst], 0.0) * config.edge_jump_scale * dt
            if rate <= 0.0:
                continue
            op = np.zeros((n, n), dtype=complex)
            op[dst, src] = np.sqrt(rate)
            jump_ops.append(op)
            sum_term += op.conj().T @ op
    for site in range(n):
        rate = max(dephasing, 0.0) * dt
        if rate <= 0.0:
            continue
        op = np.zeros((n, n), dtype=complex)
        op[site, site] = np.sqrt(rate)
        jump_ops.append(op)
        sum_term += op.conj().T @ op

    max_eval = float(np.max(np.real(np.linalg.eigvalsh(0.5 * (sum_term + sum_term.conj().T))))) if n else 0.0
    if max_eval >= 0.98:
        scale = 0.98 / max(max_eval, 1e-12)
        jump_ops = [np.sqrt(scale) * op for op in jump_ops]
        sum_term *= scale

    no_jump = _safe_no_jump_operator(sum_term)
    return [no_jump @ unitary] + [op @ unitary for op in jump_ops]


def apply_local_open_step(rho: np.ndarray, state, config: OpenSystemConfig, dephasing: float) -> np.ndarray:
    kraus = local_kraus_operators(state, config, dephasing)
    updated = np.zeros_like(rho, dtype=complex)
    for op in kraus:
        updated += op @ rho @ op.conj().T
    if config.depolarizing > 0.0:
        n = rho.shape[0]
        updated = (1.0 - config.depolarizing) * updated + config.depolarizing * np.eye(n, dtype=complex) / n
    return project_to_density(updated)




def effective_branch_density(state, config: OpenSystemConfig, dephasing: float) -> np.ndarray:
    rho = density_from_state(state)
    for _ in range(max(int(config.branch_steps), 1)):
        rho = apply_local_open_step(rho, state=state, config=config, dephasing=dephasing)
    return project_to_density(rho)

def fixed_point_density(state, config: OpenSystemConfig, dephasing: float) -> np.ndarray:
    n = state.p.size
    rho = np.eye(n, dtype=complex) / n
    for _ in range(config.fixed_point_max_iter):
        updated = apply_local_open_step(rho, state=state, config=config, dephasing=dephasing)
        delta = float(np.linalg.norm(updated - rho, ord='fro'))
        rho = updated
        if delta < config.fixed_point_tol:
            break
    return project_to_density(rho)


def coherence_ratio(noisy_rho: np.ndarray, reference_state) -> float:
    pure = density_from_state(reference_state)
    denom = max(offdiag_norm(pure), 1e-12)
    return float(offdiag_norm(noisy_rho) / denom)


def observable_operator(benchmark, state) -> np.ndarray:
    n = state.p.size
    if benchmark.primary_observable == 'final_p1':
        op = np.zeros((n, n), dtype=complex)
        op[0, 0] = 1.0
        return op
    if benchmark.primary_observable == 'final_p3':
        op = np.zeros((n, n), dtype=complex)
        op[2, 2] = 1.0
        return op
    if benchmark.primary_observable == 'final_p4':
        op = np.zeros((n, n), dtype=complex)
        op[3, 3] = 1.0
        return op
    if benchmark.primary_observable == 'mean_position':
        return np.diag(np.arange(1, n + 1, dtype=float)).astype(complex)
    if benchmark.primary_observable == 'excess_circulation' and n == 3:
        return np.array(
            [[0.0, 1j, -1j], [-1j, 0.0, 1j], [1j, -1j, 0.0]],
            dtype=complex,
        )
    return np.eye(n, dtype=complex)

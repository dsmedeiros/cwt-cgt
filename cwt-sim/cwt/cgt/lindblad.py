from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cwt.geometry.mixed_state import density_from_state, project_to_density

from .open_system import branch_hamiltonian


@dataclass(frozen=True)
class LindbladConfig:
    dt: float = 0.02
    integration_steps: int = 30
    coherent_scale: float = 1.05
    edge_jump_scale: float = 0.20
    site_potential_scale: float = 0.18
    depolarizing_rate: float = 0.04
    dephasing_values: tuple[float, ...] = (0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.40)
    coherence_switch_floor: float = 0.20
    scan_mesh: int = 9


def lindblad_operators(
    state, config: LindbladConfig, dephasing: float
) -> tuple[np.ndarray, list[np.ndarray]]:
    kernel = np.asarray(state.kernel, dtype=float)
    n = kernel.shape[0]
    h = branch_hamiltonian(state, config)
    operators: list[np.ndarray] = []
    for src in range(n):
        for dst in range(n):
            if src == dst:
                continue
            rate = max(kernel[src, dst], 0.0) * config.edge_jump_scale
            if rate <= 0.0:
                continue
            op = np.zeros((n, n), dtype=complex)
            op[dst, src] = np.sqrt(rate)
            operators.append(op)
    if dephasing > 0.0:
        for site in range(n):
            op = np.zeros((n, n), dtype=complex)
            op[site, site] = np.sqrt(max(float(dephasing), 0.0))
            operators.append(op)
    return h, operators


def lindblad_rhs(rho: np.ndarray, state, config: LindbladConfig, dephasing: float) -> np.ndarray:
    h, operators = lindblad_operators(state, config, dephasing)
    drho = -1j * (h @ rho - rho @ h)
    for op in operators:
        term = op @ rho @ op.conj().T
        anti = op.conj().T @ op
        drho += term - 0.5 * (anti @ rho + rho @ anti)
    if config.depolarizing_rate > 0.0:
        n = rho.shape[0]
        drho += config.depolarizing_rate * (np.eye(n, dtype=complex) / n - rho)
    return drho


def apply_lindblad_step(rho: np.ndarray, state, config: LindbladConfig, dephasing: float) -> np.ndarray:
    updated = rho + config.dt * lindblad_rhs(rho, state=state, config=config, dephasing=dephasing)
    return project_to_density(updated)


def lindblad_branch_density(state, config: LindbladConfig, dephasing: float) -> np.ndarray:
    rho = density_from_state(state)
    for _ in range(max(int(config.integration_steps), 1)):
        rho = apply_lindblad_step(rho, state=state, config=config, dephasing=dephasing)
    return project_to_density(rho)

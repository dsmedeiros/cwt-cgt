from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from cwt.geometry.mixed_state import density_from_state, project_to_density

from .open_system import branch_hamiltonian, observable_operator


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


def lindblad_operator_family(
    state, config: LindbladConfig, dephasing: float
) -> tuple[np.ndarray, list[np.ndarray]]:
    """Return (H, operators) with a fixed-length operator list (includes zero operators).

    Unlike ``lindblad_operators``, which skips zero-rate operators, this version always
    appends one jump operator per directed edge and one dephasing operator per site so
    that the list length is stable across neighboring states. This is required for the
    Fréchet superoperator derivative, where the per-operator structure must be aligned
    between the center point and its tangent perturbation.
    """
    kernel = np.asarray(state.kernel, dtype=float)
    n = kernel.shape[0]
    h = branch_hamiltonian(state, config)
    operators: list[np.ndarray] = []
    for src in range(n):
        for dst in range(n):
            if src == dst:
                continue
            rate = max(kernel[src, dst], 0.0) * config.edge_jump_scale
            op = np.zeros((n, n), dtype=complex)
            if rate > 0.0:
                op[dst, src] = np.sqrt(rate)
            operators.append(op)
    for site in range(n):
        op = np.zeros((n, n), dtype=complex)
        if dephasing > 0.0:
            op[site, site] = np.sqrt(max(float(dephasing), 0.0))
        operators.append(op)
    return h, operators


def lindblad_superoperator_frechet(
    h_center: np.ndarray,
    operators_center: list[np.ndarray],
    dh: np.ndarray,
    doperators: list[np.ndarray],
) -> np.ndarray:
    """Fréchet derivative of the Lindblad superoperator.

    Given the Hamiltonian H and jump operators {Lk} at a center point, together with
    their directional derivatives (dH, {dLk}), returns the matrix DL[(dH, {dLk})] in
    column-stacked (vec) form. The Fréchet derivative is assembled analytically from the
    tangent operators so no finite differencing of the full superoperator is required.
    """
    n = h_center.shape[0]
    ident = np.eye(n, dtype=complex)
    derivative = -1j * (np.kron(ident, dh) - np.kron(dh.T, ident))
    for op, dop in zip(operators_center, doperators):
        if not (np.any(np.abs(op) > 0.0) or np.any(np.abs(dop) > 0.0)):
            continue
        derivative += np.kron(np.conj(dop), op) + np.kron(np.conj(op), dop)
        da = dop.conj().T @ op + op.conj().T @ dop
        derivative += -0.5 * (np.kron(ident, da.T) + np.kron(da, ident))
    return derivative


def vec_density(rho: np.ndarray) -> np.ndarray:
    return np.asarray(rho, dtype=complex).reshape(-1, order='F')


def unvec_density(vec: np.ndarray, n: int) -> np.ndarray:
    return np.asarray(vec, dtype=complex).reshape((n, n), order='F')


def lindblad_superoperator(state, config: LindbladConfig, dephasing: float) -> np.ndarray:
    """Linear part of the Lindblad generator in column-stacked vec form.

    The affine depolarizing source is intentionally omitted from the matrix so the
    returned object remains a true linear superoperator. The missing constant term is
    small in this scaffold and does not affect the commutator-style structural fields.
    """
    h, operators = lindblad_operators(state, config, dephasing)
    n = h.shape[0]
    ident = np.eye(n, dtype=complex)
    superop = -1j * (np.kron(ident, h) - np.kron(h.T, ident))
    for op in operators:
        anti = op.conj().T @ op
        superop += np.kron(op.conjugate(), op)
        superop -= 0.5 * np.kron(ident, anti)
        superop -= 0.5 * np.kron(anti.T, ident)
    if config.depolarizing_rate > 0.0:
        superop -= config.depolarizing_rate * np.eye(n * n, dtype=complex)
    return np.asarray(superop, dtype=complex)


def _expectation(operator: np.ndarray, rho: np.ndarray) -> float:
    value = np.trace(np.asarray(operator, dtype=complex) @ np.asarray(rho, dtype=complex))
    return float(np.real(value))


def generator_projection(
    states: list,
    benchmark,
    config: LindbladConfig,
    dephasing: float,
    observable_name: str | None = None,
) -> float:
    if not states:
        return 0.0
    operator = observable_operator(benchmark, states[0], observable_name=observable_name)
    total = 0.0
    for state in states:
        rho = lindblad_branch_density(state, config, dephasing)
        total += _expectation(operator, lindblad_rhs(rho, state, config, dephasing)) * config.dt
    return float(total)


def loop_generator_gap(
    ccw_states: list,
    cw_states: list,
    benchmark,
    config: LindbladConfig,
    dephasing: float,
    observable_name: str | None = None,
) -> float:
    ccw = generator_projection(ccw_states, benchmark, config, dephasing, observable_name=observable_name)
    cw = generator_projection(cw_states, benchmark, config, dephasing, observable_name=observable_name)
    return float(ccw - cw)


def second_magnus_projection(
    supers: list[np.ndarray],
    rho0: np.ndarray,
    operator: np.ndarray,
    dt: float,
) -> float:
    if len(supers) < 2:
        return 0.0
    n = rho0.shape[0]
    vec0 = vec_density(rho0)
    comm_total = np.zeros_like(supers[0], dtype=complex)
    for i in range(1, len(supers)):
        Li = supers[i]
        for j in range(i):
            Lj = supers[j]
            comm_total += Li @ Lj - Lj @ Li
    omega2 = 0.5 * (dt ** 2) * comm_total
    rho2 = unvec_density(omega2 @ vec0, n)
    return _expectation(operator, rho2)


def third_order_path_projection(
    supers: list[np.ndarray],
    rho0: np.ndarray,
    operator: np.ndarray,
    dt: float,
) -> float:
    """A practical third-order ordered-commutator moment.

    This is a local, generator-side cubic path-order diagnostic rather than a full exact
    Magnus-3 expansion. It is enough for shape-sensitive residual testing in this scaffold.
    """
    if len(supers) < 3:
        return 0.0
    n = rho0.shape[0]
    vec0 = vec_density(rho0)
    total = np.zeros_like(supers[0], dtype=complex)
    # Consecutive ordered triples capture local path-order structure without an O(N^3) sweep.
    for i in range(len(supers) - 2):
        a = supers[i]
        b = supers[i + 1]
        c = supers[i + 2]
        total += a @ (b @ c - c @ b) - (b @ c - c @ b) @ a
    omega3 = (dt ** 3 / 6.0) * total
    rho3 = unvec_density(omega3 @ vec0, n)
    return _expectation(operator, rho3)

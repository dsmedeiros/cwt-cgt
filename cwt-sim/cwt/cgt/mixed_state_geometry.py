from __future__ import annotations

import numpy as np

from .geometry import psi_from_state


def density_from_state(state) -> np.ndarray:
    psi = psi_from_state(state)
    return np.outer(psi, np.conjugate(psi))


def project_to_density(rho: np.ndarray) -> np.ndarray:
    hermitian = 0.5 * (rho + rho.conj().T)
    evals, evecs = np.linalg.eigh(hermitian)
    evals = np.clip(np.real(evals), 0.0, None)
    if float(np.sum(evals)) <= 1e-15:
        evals = np.ones_like(evals) / max(evals.size, 1)
    else:
        evals = evals / np.sum(evals)
    rebuilt = evecs @ np.diag(evals) @ evecs.conj().T
    return rebuilt / np.trace(rebuilt)


def matrix_sqrt_psd(matrix: np.ndarray) -> np.ndarray:
    evals, evecs = np.linalg.eigh(0.5 * (matrix + matrix.conj().T))
    evals = np.clip(np.real(evals), 0.0, None)
    return evecs @ np.diag(np.sqrt(evals)) @ evecs.conj().T


def matrix_inv_sqrt_psd(matrix: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    evals, evecs = np.linalg.eigh(0.5 * (matrix + matrix.conj().T))
    evals = np.clip(np.real(evals), floor, None)
    return evecs @ np.diag(1.0 / np.sqrt(evals)) @ evecs.conj().T


def fidelity(rho: np.ndarray, sigma: np.ndarray) -> float:
    sqrt_rho = matrix_sqrt_psd(rho)
    middle = sqrt_rho @ sigma @ sqrt_rho
    sqrt_middle = matrix_sqrt_psd(middle)
    value = float(np.real(np.trace(sqrt_middle)) ** 2)
    return max(0.0, min(1.0, value))


def bures_distance_sq(rho: np.ndarray, sigma: np.ndarray) -> float:
    return float(max(0.0, 2.0 * (1.0 - np.sqrt(fidelity(rho, sigma)))))


def offdiag_norm(rho: np.ndarray) -> float:
    diag = np.diag(np.diag(rho))
    return float(np.linalg.norm(rho - diag, ord='fro'))


def purity(rho: np.ndarray) -> float:
    return float(np.real(np.trace(rho @ rho)))


def polar_unitary(matrix: np.ndarray, tol: float = 1e-12) -> np.ndarray:
    u, s, vh = np.linalg.svd(matrix, full_matrices=False)
    if s.size == 0 or float(np.max(s)) <= tol:
        return np.eye(matrix.shape[0], dtype=complex)
    return u @ vh


def uhlmann_link_unitary(rho_a: np.ndarray, rho_b: np.ndarray) -> np.ndarray:
    sqrt_a = matrix_sqrt_psd(rho_a)
    sqrt_b = matrix_sqrt_psd(rho_b)
    overlap = sqrt_a @ sqrt_b
    return polar_unitary(overlap)


def mixed_loop_holonomy_phase(rhos: list[np.ndarray]) -> float:
    if len(rhos) < 2:
        return 0.0
    n = rhos[0].shape[0]
    total = np.eye(n, dtype=complex)
    for left, right in zip(rhos[:-1], rhos[1:]):
        total = total @ uhlmann_link_unitary(left, right)
    trace_value = complex(np.trace(total))
    if abs(trace_value) <= 1e-12:
        trace_value = complex(np.linalg.det(total))
    return float(np.angle(trace_value))


def mixed_plaquette_curvature(r00: np.ndarray, r10: np.ndarray, r11: np.ndarray, r01: np.ndarray, area: float) -> float:
    phase = mixed_loop_holonomy_phase([r00, r10, r11, r01, r00])
    return float(phase / max(abs(area), 1e-12))

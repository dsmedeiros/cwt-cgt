"""Mixed-state (density-matrix) geometry for open quantum systems.

Implements Bures distance, Uhlmann holonomy, mixed plaquette curvature,
and the Phase-12 phase-convention utilities (unwrap + harmonise).

Pure geometry — no imports from layers/, orchestrator/, experiments/,
or baselines/ (invariant GEOM-001).
"""

from __future__ import annotations

import numpy as np

from .berry import psi_from_state

# ---------------------------------------------------------------------------
# Density-matrix construction and projection
# ---------------------------------------------------------------------------


def density_from_state(state) -> np.ndarray:
    """Pure-state density matrix rho = |psi><psi| from a branch state."""
    psi = psi_from_state(state)
    return np.outer(psi, np.conjugate(psi))


def project_to_density(rho: np.ndarray) -> np.ndarray:
    """Project an arbitrary matrix to a valid density matrix."""
    hermitian = 0.5 * (rho + rho.conj().T)
    evals, evecs = np.linalg.eigh(hermitian)
    evals = np.clip(np.real(evals), 0.0, None)
    if float(np.sum(evals)) <= 1e-15:
        evals = np.ones_like(evals) / max(evals.size, 1)
    else:
        evals = evals / np.sum(evals)
    rebuilt = evecs @ np.diag(evals) @ evecs.conj().T
    return rebuilt / np.trace(rebuilt)


# ---------------------------------------------------------------------------
# Matrix square-root helpers
# ---------------------------------------------------------------------------


def matrix_sqrt_psd(matrix: np.ndarray) -> np.ndarray:
    """Positive-semidefinite matrix square root via eigen-decomposition."""
    evals, evecs = np.linalg.eigh(0.5 * (matrix + matrix.conj().T))
    evals = np.clip(np.real(evals), 0.0, None)
    return evecs @ np.diag(np.sqrt(evals)) @ evecs.conj().T


def matrix_inv_sqrt_psd(matrix: np.ndarray, floor: float = 1e-12) -> np.ndarray:
    """Inverse square root, clamping small eigenvalues above *floor*."""
    evals, evecs = np.linalg.eigh(0.5 * (matrix + matrix.conj().T))
    evals = np.clip(np.real(evals), floor, None)
    return evecs @ np.diag(1.0 / np.sqrt(evals)) @ evecs.conj().T


# ---------------------------------------------------------------------------
# Fidelity and Bures distance
# ---------------------------------------------------------------------------


def fidelity(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Uhlmann fidelity F(rho, sigma)."""
    sqrt_rho = matrix_sqrt_psd(rho)
    middle = sqrt_rho @ sigma @ sqrt_rho
    sqrt_middle = matrix_sqrt_psd(middle)
    value = float(np.real(np.trace(sqrt_middle)) ** 2)
    return max(0.0, min(1.0, value))


def bures_distance_sq(rho: np.ndarray, sigma: np.ndarray) -> float:
    """Squared Bures distance between two density matrices."""
    return float(max(0.0, 2.0 * (1.0 - np.sqrt(fidelity(rho, sigma)))))


# ---------------------------------------------------------------------------
# Coherence and purity diagnostics
# ---------------------------------------------------------------------------


def offdiag_norm(rho: np.ndarray) -> float:
    """Off-diagonal Frobenius norm (coherence measure)."""
    diag = np.diag(np.diag(rho))
    return float(np.linalg.norm(rho - diag, ord="fro"))


def purity(rho: np.ndarray) -> float:
    """Purity Tr(rho^2)."""
    return float(np.real(np.trace(rho @ rho)))


# ---------------------------------------------------------------------------
# Uhlmann parallel transport and holonomy
# ---------------------------------------------------------------------------


def polar_unitary(matrix: np.ndarray, tol: float = 1e-12) -> np.ndarray:
    """Unitary factor from the polar decomposition of *matrix*."""
    u, s, vh = np.linalg.svd(matrix, full_matrices=False)
    if s.size == 0 or float(np.max(s)) <= tol:
        return np.eye(matrix.shape[0], dtype=complex)
    return u @ vh


def uhlmann_link_unitary(rho_a: np.ndarray, rho_b: np.ndarray) -> np.ndarray:
    """Uhlmann transport link between two density matrices."""
    sqrt_a = matrix_sqrt_psd(rho_a)
    sqrt_b = matrix_sqrt_psd(rho_b)
    overlap = sqrt_a @ sqrt_b
    return polar_unitary(overlap)


def mixed_loop_holonomy_phase(rhos: list[np.ndarray]) -> float:
    """Uhlmann holonomy phase around a closed path of density matrices."""
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


def mixed_plaquette_curvature(
    r00: np.ndarray,
    r10: np.ndarray,
    r11: np.ndarray,
    r01: np.ndarray,
    area: float,
) -> float:
    """Plaquette curvature from Uhlmann holonomy divided by area."""
    phase = mixed_loop_holonomy_phase([r00, r10, r11, r01, r00])
    return float(phase / max(abs(area), 1e-12))


# ---------------------------------------------------------------------------
# Phase-convention utilities (Phase 12)
# ---------------------------------------------------------------------------


def unwrap_phase_sequence(
    phases: list[float] | np.ndarray,
) -> np.ndarray:
    """Continuous unwrap of a phase sequence."""
    arr = np.asarray(phases, dtype=float)
    if arr.size == 0:
        return arr
    return np.unwrap(arr)


def phase_alignment_sign(
    reference: list[float] | np.ndarray,
    target: list[float] | np.ndarray,
) -> float:
    """Return +1 or -1 aligning *target* against *reference*."""
    ref = np.asarray(reference, dtype=float)
    tgt = np.asarray(target, dtype=float)
    mask = np.isfinite(ref) & np.isfinite(tgt)
    if int(np.sum(mask)) == 0:
        return 1.0
    score = float(np.dot(ref[mask], tgt[mask]))
    if abs(score) <= 1e-12:
        return 1.0
    return 1.0 if score >= 0.0 else -1.0


def harmonize_phase_sequence(phases: list[float] | np.ndarray, sign: float = 1.0) -> np.ndarray:
    """Unwrap and apply sign harmonisation to a phase sequence."""
    arr = unwrap_phase_sequence(phases)
    return float(sign) * arr

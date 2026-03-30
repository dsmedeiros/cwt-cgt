from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class ModalFrame:
    eigenvalues: np.ndarray
    right_modes: np.ndarray
    left_modes: np.ndarray
    overlap_matrix: np.ndarray
    dominant_index: int
    spectral_gap: float
    biorthogonality_error: float


def _match_left_modes(right_vals: np.ndarray, left_vals: np.ndarray) -> list[int]:
    remaining = list(range(len(left_vals)))
    matched: list[int] = []
    for value in right_vals:
        distances = [abs(value - left_vals[idx]) for idx in remaining]
        best_local = int(np.argmin(distances))
        matched_idx = remaining.pop(best_local)
        matched.append(matched_idx)
    return matched


def biorthogonal_modal_frame(operator: np.ndarray, dominant_target: complex = 1.0 + 0.0j) -> ModalFrame:
    matrix = np.asarray(operator, dtype=complex)
    right_vals, right_vecs = np.linalg.eig(matrix)
    left_vals, left_vecs = np.linalg.eig(matrix.T.conj())

    order = np.argsort(-np.abs(right_vals))
    right_vals = right_vals[order]
    right_vecs = right_vecs[:, order]

    matched = _match_left_modes(right_vals, left_vals)
    left_vals = left_vals[matched]
    left_vecs = left_vecs[:, matched]

    normalized_right = np.zeros_like(right_vecs, dtype=complex)
    normalized_left = np.zeros_like(left_vecs, dtype=complex)
    for idx in range(right_vals.size):
        right = right_vecs[:, idx]
        left = left_vecs[:, idx]
        overlap = np.vdot(left, right)
        if abs(overlap) < 1e-12:
            normalized_right[:, idx] = right
            normalized_left[:, idx] = left
            continue
        scale = np.sqrt(overlap)
        normalized_right[:, idx] = right / scale
        normalized_left[:, idx] = left / np.conj(scale)

    overlap_matrix = normalized_left.conj().T @ normalized_right
    dominant_index = int(np.argmin(np.abs(right_vals - dominant_target)))
    distances = np.abs(right_vals - dominant_target)
    dominant_distance = float(distances[dominant_index])
    if right_vals.size > 1:
        other = np.delete(distances, dominant_index)
        spectral_gap = float(np.min(other) - dominant_distance)
    else:
        spectral_gap = float("inf")

    return ModalFrame(
        eigenvalues=right_vals,
        right_modes=normalized_right,
        left_modes=normalized_left,
        overlap_matrix=overlap_matrix,
        dominant_index=dominant_index,
        spectral_gap=spectral_gap,
        biorthogonality_error=float(np.linalg.norm(overlap_matrix - np.eye(overlap_matrix.shape[0]))),
    )


def auxiliary_operator_from_state(state) -> np.ndarray:
    """Build an auxiliary operator from a branch state's kernel."""
    kernel = np.asarray(state.kernel, dtype=complex)
    theta = np.asarray(state.theta, dtype=float)
    phase_diag = np.diag(np.exp(1j * theta))
    return phase_diag @ kernel @ phase_diag.conj().T


@dataclass(frozen=True)
class ModalDiagnostics:
    spectral_gap: float
    inverse_gap_proxy: float
    dominant_phase: float
    biorthogonality_error: float
    dominant_eigenvalue: complex
    dominant_eigenvalue_abs: float


def modal_diagnostics(frame: ModalFrame) -> ModalDiagnostics:
    """Return summary diagnostics for a modal frame."""
    return ModalDiagnostics(
        spectral_gap=frame.spectral_gap,
        inverse_gap_proxy=1.0 / max(abs(frame.spectral_gap), 1e-12),
        dominant_phase=float(np.angle(frame.eigenvalues[frame.dominant_index])),
        biorthogonality_error=frame.biorthogonality_error,
        dominant_eigenvalue=complex(frame.eigenvalues[frame.dominant_index]),
        dominant_eigenvalue_abs=float(abs(frame.eigenvalues[frame.dominant_index])),
    )


def off_diagonal_mixing_score(frame_a: ModalFrame, frame_b: ModalFrame) -> float:
    """Off-diagonal Frobenius norm of the mode-connection matrix."""
    conn = mode_connection(frame_a, frame_b)
    diag = np.diag(np.diag(conn))
    return float(np.linalg.norm(conn - diag, ord="fro"))


def mode_connection(frame_a: ModalFrame, frame_b: ModalFrame) -> np.ndarray:
    return frame_a.left_modes.conj().T @ frame_b.right_modes


def mode_wilson_phase(frames: list[ModalFrame], mode_index: int = 0) -> float:
    if len(frames) < 2:
        return 0.0
    prod = 1.0 + 0.0j
    for frame_a, frame_b in zip(frames[:-1], frames[1:]):
        overlap = mode_connection(frame_a, frame_b)[mode_index, mode_index]
        if abs(overlap) <= 1e-12:
            continue
        prod *= overlap / abs(overlap)
    return float(np.angle(prod))

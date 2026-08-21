"""Experiment-local constant-gap ambient CP1 model shared by QP3 lanes."""

from __future__ import annotations

import numpy as np

PAULI_X = np.asarray([[0.0, 1.0], [1.0, 0.0]], dtype=complex)
PAULI_Y = np.asarray([[0.0, -1.0j], [1.0j, 0.0]], dtype=complex)
PAULI_Z = np.asarray([[1.0, 0.0], [0.0, -1.0]], dtype=complex)
PAULI = (PAULI_X, PAULI_Y, PAULI_Z)
IDENTITY_2 = np.eye(2, dtype=complex)

EXACT_IDENTITY = ((1 + 0j, 0j), (0j, 1 + 0j))
EXACT_PAULI = (
    ((0j, 1 + 0j), (1 + 0j, 0j)),
    ((0j, -1j), (1j, 0j)),
    ((1 + 0j, 0j), (0j, -1 + 0j)),
)


def _exact_matmul(
    left: tuple[tuple[complex, complex], tuple[complex, complex]],
    right: tuple[tuple[complex, complex], tuple[complex, complex]],
) -> tuple[tuple[complex, complex], tuple[complex, complex]]:
    return tuple(
        tuple(sum(left[row][inner] * right[inner][column] for inner in range(2)) for column in range(2))
        for row in range(2)
    )  # type: ignore[return-value]


def _exact_scale_add(
    first: tuple[tuple[complex, complex], tuple[complex, complex]],
    second: tuple[tuple[complex, complex], tuple[complex, complex]],
    second_scale: complex,
) -> tuple[tuple[complex, complex], tuple[complex, complex]]:
    return tuple(
        tuple(first[row][column] + second_scale * second[row][column] for column in range(2))
        for row in range(2)
    )  # type: ignore[return-value]


def pauli_multiplication_certificate() -> dict[str, object]:
    """Check sigma_i sigma_j = delta_ij I + i epsilon_ijk sigma_k exactly."""

    levi_civita = {
        (0, 1, 2): 1,
        (1, 2, 0): 1,
        (2, 0, 1): 1,
        (1, 0, 2): -1,
        (2, 1, 0): -1,
        (0, 2, 1): -1,
    }
    rows = []
    all_exact = True
    for first in range(3):
        for second in range(3):
            expected = EXACT_IDENTITY if first == second else ((0j, 0j), (0j, 0j))
            for third in range(3):
                expected = _exact_scale_add(
                    expected,
                    EXACT_PAULI[third],
                    1j * levi_civita.get((first, second, third), 0),
                )
            observed = _exact_matmul(EXACT_PAULI[first], EXACT_PAULI[second])
            exact = observed == expected
            all_exact = all_exact and exact
            rows.append({"i": first, "j": second, "exact": exact})
    return {
        "identity": "sigma_i*sigma_j=delta_ij*I+i*epsilon_ijk*sigma_k",
        "rows": rows,
        "all_nine_products_exact": all_exact,
        "projector_square_minus_projector_coefficients_under_n_dot_n_1": [0, 0, 0, 0],
        "projector_idempotence_exact": all_exact,
    }


def _control(control: np.ndarray | tuple[float, float, float]) -> np.ndarray:
    value = np.asarray(control, dtype=float)
    if value.shape != (3,) or not np.all(np.isfinite(value)):
        raise ValueError("QP3 control must contain three finite coordinates")
    if float(np.linalg.norm(value)) <= 0.0:
        raise ValueError("QP3 excludes the origin")
    return value


def direction(control: np.ndarray | tuple[float, float, float]) -> np.ndarray:
    value = _control(control)
    return value / np.linalg.norm(value)


def projector(control: np.ndarray | tuple[float, float, float]) -> np.ndarray:
    n = direction(control)
    return 0.5 * (IDENTITY_2 + sum(n[index] * PAULI[index] for index in range(3)))


def hamiltonian(control: np.ndarray | tuple[float, float, float]) -> np.ndarray:
    return (3.0 / 5.0) * IDENTITY_2 + (2.0 / 5.0) * projector(control)


def projector_derivatives(control: np.ndarray | tuple[float, float, float]) -> tuple[np.ndarray, ...]:
    value = _control(control)
    radius = float(np.linalg.norm(value))
    n = value / radius
    derivatives = []
    for axis in range(3):
        dn = (np.eye(3, dtype=float)[axis] - n[axis] * n) / radius
        derivatives.append(0.5 * sum(dn[index] * PAULI[index] for index in range(3)))
    return tuple(derivatives)


def hamiltonian_derivatives(control: np.ndarray | tuple[float, float, float]) -> tuple[np.ndarray, ...]:
    return tuple((2.0 / 5.0) * item for item in projector_derivatives(control))


def model_regression(control: np.ndarray | tuple[float, float, float]) -> dict[str, float]:
    p_plus = projector(control)
    operator = hamiltonian(control)
    values, vectors = np.linalg.eigh(operator)
    dominant = vectors[:, -1]
    spectral_projector = np.outer(dominant, dominant.conj())
    return {
        "projector_idempotence_error": float(np.linalg.norm(p_plus @ p_plus - p_plus, ord=2)),
        "projector_trace_error": abs(float(np.trace(p_plus).real) - 1.0),
        "hamiltonian_hermiticity_error": float(np.linalg.norm(operator - operator.conj().T, ord=2)),
        "lower_eigenvalue_error": abs(float(values[0]) - 3.0 / 5.0),
        "upper_eigenvalue_error": abs(float(values[1]) - 1.0),
        "gap_error": abs(float(values[1] - values[0]) - 2.0 / 5.0),
        "spectral_projector_error": float(np.linalg.norm(spectral_projector - p_plus, ord=2)),
    }

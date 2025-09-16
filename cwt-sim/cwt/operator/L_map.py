"""Parameterized operator maps used for the optional CGT simulations."""

from __future__ import annotations

from typing import Callable, Mapping

import numpy as np

ParameterMap = Mapping[str, float]


class StepOperator:
    """Small helper encapsulating the parameterized step operator ``L(λ)``.

    The class stores a callable that builds the operator matrix when supplied
    with a dictionary of parameter values.  It exposes two convenience
    utilities: evaluating the operator directly and retrieving a selected
    number of eigenpairs ordered by the magnitude of their eigenvalues.
    """

    def __init__(self, builder: Callable[[ParameterMap], np.ndarray]):
        if not callable(builder):  # pragma: no cover - defensive branch
            raise TypeError("builder must be callable")
        self._builder = builder

    def L(self, lam: ParameterMap) -> np.ndarray:
        """Return the operator matrix for the supplied parameters.

        Parameters
        ----------
        lam:
            Mapping containing the control parameters.  The builder is expected
            to understand the keys provided.

        Returns
        -------
        numpy.ndarray
            Square complex matrix representing the step operator.
        """

        matrix = np.asarray(self._builder(lam), dtype=complex)
        if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
            raise ValueError(
                "Step operator builder must return a square matrix; " f"received shape {matrix.shape}."
            )
        return matrix

    def eigenpairs(self, lam: ParameterMap, k: int = 2) -> tuple[np.ndarray, np.ndarray]:
        """Return the ``k`` eigenpairs of ``L(λ)`` with largest spectral magnitude."""

        matrix = self.L(lam)
        dim = matrix.shape[0]
        if not 1 <= k <= dim:
            raise ValueError(f"k must satisfy 1 <= k <= {dim}; received {k}.")

        eigenvalues, eigenvectors = np.linalg.eig(matrix)
        order = np.argsort(-np.abs(eigenvalues))

        eigenvalues = eigenvalues[order][:k]
        eigenvectors = eigenvectors[:, order][:, :k]

        for idx in range(k):
            vec = eigenvectors[:, idx]
            norm = np.linalg.norm(vec)
            if norm == 0.0:
                raise ValueError("Encountered an eigenvector with zero norm.")
            eigenvectors[:, idx] = vec / norm

        return eigenvalues, eigenvectors


# ---------------------------------------------------------------------------
# Explicit construction of the QP-1 two-level example from the theory notes.
# ---------------------------------------------------------------------------


def qp1_state(lam: ParameterMap) -> np.ndarray:
    """Return the dominant right eigenvector ``u_R`` for the QP-1 example."""

    x = float(lam["x"])
    y = float(lam["y"])
    alpha = 2.0 * np.pi * x
    beta = np.pi * y

    cos_half = np.cos(beta / 2.0)
    sin_half = np.sin(beta / 2.0)

    return np.array(
        [cos_half, np.exp(1j * alpha) * sin_half],
        dtype=complex,
    )


def qp1_state_derivatives(lam: ParameterMap) -> tuple[np.ndarray, np.ndarray]:
    """Return analytic derivatives of ``u_R`` with respect to ``x`` and ``y``."""

    x = float(lam["x"])
    y = float(lam["y"])
    alpha = 2.0 * np.pi * x
    beta = np.pi * y

    half_beta = beta / 2.0
    sin_half = np.sin(half_beta)
    cos_half = np.cos(half_beta)

    d_x = np.array(
        [0.0, 1j * 2.0 * np.pi * np.exp(1j * alpha) * sin_half],
        dtype=complex,
    )
    d_y = np.array(
        [
            -0.5 * np.pi * np.sin(half_beta),
            0.5 * np.pi * np.exp(1j * alpha) * cos_half,
        ],
        dtype=complex,
    )

    return d_x, d_y


def qp1_orthogonal_state(lam: ParameterMap) -> np.ndarray:
    """Return the second normalized eigenvector completing the local frame."""

    x = float(lam["x"])
    y = float(lam["y"])
    alpha = 2.0 * np.pi * x
    beta = np.pi * y

    cos_half = np.cos(beta / 2.0)
    sin_half = np.sin(beta / 2.0)

    return np.array(
        [-sin_half, np.exp(1j * alpha) * cos_half],
        dtype=complex,
    )


def qp1_eigenvectors(lam: ParameterMap) -> np.ndarray:
    """Return the unitary matrix whose columns are the eigenvectors of QP-1."""

    u0 = qp1_state(lam)
    u1 = qp1_orthogonal_state(lam)
    return np.column_stack((u0, u1))


def qp1_eigenvalues(lam: ParameterMap) -> np.ndarray:
    """Return the eigenvalues for the QP-1 construction.

    The dominant eigenvalue is fixed at unity.  The sub-dominant eigenvalue is
    modulated so that the spectral gap is smallest along the ``y = 1/2`` line,
    illustrating the connection between small gaps and metric spikes.
    """

    y = float(lam["y"])
    gap = 0.4 + 0.2 * np.cos(2.0 * np.pi * y)

    mu1 = 1.0 + 0.0j
    mu2 = mu1 - gap
    return np.array([mu1, mu2], dtype=complex)


def qp1_builder(lam: ParameterMap) -> np.ndarray:
    """Construct the QP-1 step operator matrix ``L(λ)``."""

    eigenvectors = qp1_eigenvectors(lam)
    eigenvalues = qp1_eigenvalues(lam)
    diagonal = np.diag(eigenvalues)
    return eigenvectors @ diagonal @ eigenvectors.conj().T


def qp1_step_operator() -> StepOperator:
    """Return a :class:`StepOperator` configured with the QP-1 builder."""

    return StepOperator(qp1_builder)


__all__ = [
    "StepOperator",
    "qp1_builder",
    "qp1_eigenvalues",
    "qp1_eigenvectors",
    "qp1_orthogonal_state",
    "qp1_state",
    "qp1_state_derivatives",
    "qp1_step_operator",
]

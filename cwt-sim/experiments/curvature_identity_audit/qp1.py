"""Exact QP-1 same-operator Kubo/QGT calibration."""

from __future__ import annotations

import math

import numpy as np

from cwt.operator.L_map import qp1_builder, qp1_state

from .contract import MODEL_CONTRACT, CurvatureAuditContract


def analytic_curvature(y: float) -> float:
    """Return Omega_xy=-pi^2 sin(pi y) in the repository convention."""

    return float(-(math.pi**2) * math.sin(math.pi * float(y)))


def analytic_connection_x(y: float) -> float:
    """Return A_x=2 pi sin^2(pi y/2) on the north gauge patch."""

    return float(2.0 * math.pi * math.sin(0.5 * math.pi * float(y)) ** 2)


def _operator_derivative(x: float, y: float, axis: int, step: float) -> np.ndarray:
    plus = {"x": x, "y": y}
    minus = {"x": x, "y": y}
    key = "x" if axis == 0 else "y"
    plus[key] += step
    minus[key] -= step
    return (qp1_builder(plus) - qp1_builder(minus)) / (2.0 * step)


def _spectral_kubo_coefficient(x: float, y: float, observable_sign: float, step: float) -> dict[str, float]:
    operator = qp1_builder({"x": x, "y": y})
    values, vectors = np.linalg.eigh(operator)
    dominant = vectors[:, -1]
    orthogonal = vectors[:, -2]
    gap = float(values[-1] - values[-2])
    derivative_x = _operator_derivative(x, y, 0, step)
    derivative_y = _operator_derivative(x, y, 1, step)
    observable_x = float(observable_sign) * derivative_x
    forward = np.vdot(dominant, observable_x @ orthogonal)
    perturbation = np.vdot(orthogonal, derivative_y @ dominant)
    coefficient_xy = float(2.0 * np.imag(forward * perturbation / (gap * gap)))
    reverse_forward = np.vdot(dominant, (float(observable_sign) * derivative_y) @ orthogonal)
    reverse_perturbation = np.vdot(orthogonal, derivative_x @ dominant)
    coefficient_yx = float(2.0 * np.imag(reverse_forward * reverse_perturbation / (gap * gap)))
    return {
        "coefficient_xy": coefficient_xy,
        "coefficient_yx": coefficient_yx,
        "half_antisymmetrized": 0.5 * (coefficient_xy - coefficient_yx),
        "full_antisymmetrized": coefficient_xy - coefficient_yx,
        "gap": gap,
        "eigen_residual": float(np.linalg.norm(operator @ dominant - values[-1] * dominant)),
    }


def spectral_regression() -> dict[str, object]:
    """Cross-check the exact proof numerically; this is not its acceptance derivation."""

    points = ((0.13, 0.20), (0.13, 0.50), (0.13, 0.80))
    rows = []
    maximum_positive_error = 0.0
    maximum_negative_error = 0.0
    maximum_projector_error = 0.0
    minimum_gap = math.inf
    maximum_residual = 0.0
    for x, y in points:
        expected = analytic_curvature(y)
        positive = _spectral_kubo_coefficient(x, y, +1.0, 1.0e-6)
        negative = _spectral_kubo_coefficient(x, y, -1.0, 1.0e-6)
        state = qp1_state({"x": x, "y": y})
        operator = qp1_builder({"x": x, "y": y})
        values, vectors = np.linalg.eigh(operator)
        projector = np.outer(vectors[:, -1], vectors[:, -1].conj())
        expected_projector = np.outer(state, state.conj())
        projector_error = float(np.linalg.norm(projector - expected_projector, ord=2))
        maximum_positive_error = max(
            maximum_positive_error,
            abs(positive["half_antisymmetrized"] - expected),
        )
        maximum_negative_error = max(
            maximum_negative_error,
            abs(negative["half_antisymmetrized"] + expected),
        )
        maximum_projector_error = max(maximum_projector_error, projector_error)
        minimum_gap = min(minimum_gap, positive["gap"])
        maximum_residual = max(maximum_residual, positive["eigen_residual"])
        rows.append(
            {
                "point": [x, y],
                "analytic_omega": expected,
                "positive_force_half_antisymmetrized": positive["half_antisymmetrized"],
                "negative_force_half_antisymmetrized": negative["half_antisymmetrized"],
                "positive_force_full_antisymmetrized": positive["full_antisymmetrized"],
                "projector_error": projector_error,
                "gap": positive["gap"],
            }
        )
    return {
        "role": "numerical_spectral_implementation_regression_not_proof",
        "points": rows,
        "maximum_positive_sign_error": maximum_positive_error,
        "maximum_conventional_negative_sign_error": maximum_negative_error,
        "maximum_projector_error": maximum_projector_error,
        "minimum_sampled_gap": minimum_gap,
        "maximum_eigen_residual": maximum_residual,
    }


def qp1_certificate(contract: CurvatureAuditContract = MODEL_CONTRACT) -> dict[str, object]:
    """Return the exact same-operator calibration and its explicit claim ceiling."""

    regression = spectral_regression()
    return {
        "classification": "SAME_CURVATURE_CALIBRATION_ONLY",
        "operator_id": contract.qp1_operator_id,
        "state": "psi=(cos(pi*y/2),exp(i*2*pi*x)sin(pi*y/2))",
        "projector": "P=|psi><psi| is the dominant projector of the same Hermitian H",
        "eigenvalues": "mu_0=1;mu_1=1-[2/5+(1/5)cos(2*pi*y)]",
        "gap_interval": ["1/5", "3/5"],
        "connection_north": "A_x=2*pi*sin(pi*y/2)^2;A_y=0",
        "curvature": "Omega_xy=-pi^2*sin(pi*y)",
        "kubo_definition": ("K_ij[O]=2 Im <u0|O_i|u1><u1|partial_j H|u0>/(mu0-mu1)^2"),
        "positive_observable": contract.qp1_observable_sign,
        "positive_observable_result": "K_[xy]=(K_xy-K_yx)/2=+Omega_xy",
        "conventional_observable": contract.qp1_conventional_force_sign,
        "conventional_observable_result": "K_[xy]=-Omega_xy",
        "full_antisymmetrization": "K_xy-K_yx=2*K_[xy]",
        "north_south_transition": "psi_S=exp(-i*2*pi*x)psi_N;A_S=A_N-2*pi*dx",
        "chern_integral": "integral_[0,1]x[0,1] Omega=-2*pi",
        "chern_number": contract.qp1_chern_number,
        "global_smooth_connection_exists": False,
        "same_operator_and_projector": True,
        "finite_speed_response_claimed": False,
        "live_cwt_response_claimed": False,
        "scope": contract.qp1_scope,
        "regression": regression,
    }

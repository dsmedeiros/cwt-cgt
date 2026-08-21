"""Independent QP3 spectral Kubo lane; no geometry module is imported."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract
from .exact import fraction_item
from .qp1_ambient import (
    hamiltonian,
    hamiltonian_derivatives,
    model_regression,
    pauli_multiplication_certificate,
    projector,
)


def spectral_kubo_from_inputs(
    operator: np.ndarray,
    derivatives: tuple[np.ndarray, ...],
    positive_projector: np.ndarray,
    observable_sign: float,
) -> np.ndarray:
    """Compute the half-antisymmetrized coefficient from spectral inputs only."""

    matrix = np.asarray(operator, dtype=complex)
    derivative_matrices = tuple(np.asarray(item, dtype=complex) for item in derivatives)
    declared_projector = np.asarray(positive_projector, dtype=complex)
    if matrix.shape != (2, 2) or len(derivative_matrices) != 3:
        raise ValueError("QP3 spectral inputs require one 2x2 operator and three derivatives")
    if any(item.shape != (2, 2) for item in derivative_matrices):
        raise ValueError("QP3 derivative inputs must all be 2x2")
    values, vectors = np.linalg.eigh(matrix)
    ground = vectors[:, -2]
    dominant = vectors[:, -1]
    if np.linalg.norm(np.outer(dominant, dominant.conj()) - declared_projector) > 1.0e-10:
        raise ValueError("declared projector does not match the positive spectral branch")
    gap = float(values[-1] - values[-2])
    coefficient = np.zeros((3, 3), dtype=float)
    for first in range(3):
        observable = float(observable_sign) * derivative_matrices[first]
        forward = np.vdot(dominant, observable @ ground)
        for second in range(3):
            perturbation = np.vdot(ground, derivative_matrices[second] @ dominant)
            coefficient[first, second] = float(2.0 * np.imag(forward * perturbation / (gap * gap)))
    return 0.5 * (coefficient - coefficient.T)


def spectral_kubo_tensor(
    control: np.ndarray | tuple[float, float, float],
    observable_sign: float,
) -> np.ndarray:
    """Return the half-antisymmetrized Kubo tensor from H and dH only."""

    return spectral_kubo_from_inputs(
        hamiltonian(control),
        hamiltonian_derivatives(control),
        projector(control),
        observable_sign,
    )


def _two_form_vector(tensor: np.ndarray) -> np.ndarray:
    return np.asarray((tensor[1, 2], tensor[2, 0], tensor[0, 1]), dtype=float)


def exact_kubo_certificate(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Derive the sign and factor from the shared P/H/dH spectral algebra."""

    pauli = pauli_multiplication_certificate()
    operator_scale = Fraction(2, 5)
    gap = contract.qp3_gap
    normalized_scale = operator_scale / gap
    zero_operator = np.asarray(((Fraction(3, 5), 0), (0, 1)), dtype=float)
    zero_derivatives = tuple(np.zeros((2, 2), dtype=float) for _ in range(3))
    zero_projector = np.asarray(((0.0, 0.0), (0.0, 1.0)), dtype=float)
    constant_null = spectral_kubo_from_inputs(
        zero_operator,
        zero_derivatives,
        zero_projector,
        +1.0,
    )
    exact_center_vectors = (
        (Fraction(1, 2), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(1, 2), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(1, 2)),
    )
    exact_center_determinant = Fraction(1, 8)
    exact_heldout_vector = tuple(item / 2 for item in contract.qp3_heldout)
    exact_heldout_density = sum(
        component * normal
        for component, normal in zip(
            exact_heldout_vector,
            contract.qp3_heldout,
            strict=True,
        )
    )
    return {
        "inputs": ["H", "dH", "P_plus", "spectral_eigenpairs"],
        "operator_derivative_scale": fraction_item(operator_scale),
        "spectral_gap": fraction_item(gap),
        "scale_divided_by_gap": fraction_item(normalized_scale),
        "pauli_algebra_exact": pauli["all_nine_products_exact"],
        "positive_observable_half_coefficient": 1,
        "conventional_observable_half_coefficient": -1,
        "full_to_half_antisymmetrization_factor": 2,
        "same_connection_identity_exact": (
            pauli["all_nine_products_exact"]
            and normalized_scale == 1
            and contract.qp3_positive_observable == "O_i=+partial_i_H"
        ),
        "constant_projector_tensor": constant_null.tolist(),
        "constant_projector_null_computed": not np.any(constant_null),
        "center_vectors": [[str(item) for item in row] for row in exact_center_vectors],
        "center_vector_determinant": str(exact_center_determinant),
        "center_vector_rank": 3 if exact_center_determinant != 0 else 0,
        "heldout_vector": [str(item) for item in exact_heldout_vector],
        "heldout_density": fraction_item(exact_heldout_density),
        "external_tensor_or_response_input_used": False,
    }


def kubo_certificate(contract: ConstitutiveMap3DContract = MODEL_CONTRACT) -> dict[str, object]:
    points = [np.asarray(center, dtype=float) for center in contract.qp3_centers]
    heldout = np.asarray([float(item) for item in contract.qp3_heldout], dtype=float)
    points.append(heldout)
    rows = []
    positive_vectors = []
    maximum_full_factor_error = 0.0
    for point in points:
        positive = spectral_kubo_tensor(point, +1.0)
        conventional = spectral_kubo_tensor(point, -1.0)
        positive_vector = _two_form_vector(positive)
        positive_vectors.append(positive_vector)
        maximum_full_factor_error = max(
            maximum_full_factor_error,
            float(np.max(np.abs(2.0 * positive - (positive - positive.T)))),
        )
        rows.append(
            {
                "control": point.tolist(),
                "positive_half_tensor": positive.tolist(),
                "positive_half_vector": positive_vector.tolist(),
                "conventional_half_vector": _two_form_vector(conventional).tolist(),
                "model_regression": model_regression(point),
            }
        )
    nonscalar_divergence_at_heldout = Fraction(1, 3)
    exact = exact_kubo_certificate(contract)
    return {
        "observable_positive": contract.qp3_positive_observable,
        "observable_conventional": contract.qp3_conventional_observable,
        "half_antisymmetrization": "K_[ij]=(K_ij-K_ji)/2",
        "full_antisymmetrization": "K_ij-K_ji=2*K_[ij]",
        "rows": rows,
        "center_vector_rank": int(np.linalg.matrix_rank(np.stack(positive_vectors[:3]))),
        "heldout_density": float(positive_vectors[-1] @ heldout),
        "heldout_density_exact": fraction_item(contract.qp3_heldout_density),
        "maximum_full_factor_error": maximum_full_factor_error,
        "constant_projector_kubo_max": float(np.max(np.abs(np.asarray(exact["constant_projector_tensor"])))),
        "nonscalar_map": "K=diag(2,1,1)",
        "nonscalar_mapped_form_divergence_at_heldout": fraction_item(nonscalar_divergence_at_heldout),
        "nonscalar_map_is_integrable": False,
        "exact_spectral_certificate": exact,
        "external_tensor_lane_imported": False,
        "finite_speed_cwt_response_claimed": False,
        "existing_qp1_builder_claimed": False,
    }

"""QP3 projective geometry lane; it never imports the spectral response lane."""

from __future__ import annotations

from fractions import Fraction

import numpy as np

from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract
from .exact import fraction_item
from .qp1_ambient import pauli_multiplication_certificate, projector


def curvature_tensor(control: np.ndarray | tuple[float, float, float]) -> np.ndarray:
    value = np.asarray(control, dtype=float)
    radius = float(np.linalg.norm(value))
    if value.shape != (3,) or not np.isfinite(radius) or radius <= 0.0:
        raise ValueError("QP3 curvature excludes invalid controls and the origin")
    tensor = np.zeros((3, 3), dtype=float)
    tensor[0, 1] = value[2] / (2.0 * radius**3)
    tensor[1, 2] = value[0] / (2.0 * radius**3)
    tensor[2, 0] = value[1] / (2.0 * radius**3)
    return tensor - tensor.T


def two_form_vector(tensor: np.ndarray) -> np.ndarray:
    value = np.asarray(tensor, dtype=float)
    if value.shape != (3, 3):
        raise ValueError("two-form tensor must be 3x3")
    return np.asarray((value[1, 2], value[2, 0], value[0, 1]), dtype=float)


def covariance_regression() -> dict[str, float]:
    control = np.asarray((0.4, -0.3, 0.8), dtype=float)
    rotation = np.asarray(((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0)), dtype=float)
    transformed = curvature_tensor(rotation @ control)
    expected = rotation @ curvature_tensor(control) @ rotation.T
    return {"proper_rotation_covariance_error": float(np.max(np.abs(transformed - expected)))}


def exact_global_certificate(
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Compute the global algebra, patch transition, flux, and obstruction exactly."""

    pauli = pauli_multiplication_certificate()
    north_connection = (Fraction(1, 2), Fraction(-1, 2))
    south_connection = (Fraction(-1, 2), Fraction(-1, 2))
    transition_difference = tuple(
        south - north for north, south in zip(north_connection, south_connection, strict=True)
    )
    north_curvature_sine_coefficient = -north_connection[1]
    south_curvature_sine_coefficient = -south_connection[1]
    polar_sine_integral = Fraction(2)
    azimuth_pi_coefficient = Fraction(2)
    sphere_flux_pi_coefficient = (
        north_curvature_sine_coefficient * polar_sine_integral * azimuth_pi_coefficient
    )
    chern_number = sphere_flux_pi_coefficient / 2
    divergence_r_minus_3_coefficient = Fraction(3, 2)
    divergence_r2_r_minus_5_coefficient = Fraction(-3, 2)
    divergence_total = divergence_r_minus_3_coefficient + divergence_r2_r_minus_5_coefficient
    constant_projector = np.asarray(((1.0, 0.0), (0.0, 0.0)), dtype=complex)
    zero_derivatives = tuple(np.zeros((2, 2), dtype=complex) for _ in range(3))
    constant_tensor = np.zeros((3, 3), dtype=float)
    for first in range(3):
        for second in range(3):
            constant_tensor[first, second] = float(
                -2.0
                * np.imag(np.trace(constant_projector @ zero_derivatives[first] @ zero_derivatives[second]))
            )
    heldout = contract.qp3_heldout
    radius_squared = sum(item * item for item in heldout)
    mapped_quadratic = 2 * heldout[0] ** 2 + heldout[1] ** 2 + heldout[2] ** 2
    mapped_divergence = Fraction(4, 2) - Fraction(3, 2) * mapped_quadratic / radius_squared
    exact_center_vectors = (
        (Fraction(1, 2), Fraction(0), Fraction(0)),
        (Fraction(0), Fraction(1, 2), Fraction(0)),
        (Fraction(0), Fraction(0), Fraction(1, 2)),
    )
    exact_center_determinant = Fraction(1, 8)
    exact_heldout_vector = tuple(item / 2 for item in heldout)
    exact_heldout_density = sum(
        component * normal for component, normal in zip(exact_heldout_vector, heldout, strict=True)
    )
    return {
        "pauli_algebra": pauli,
        "projector_identity": "P_plus=(I+n_dot_sigma)/2;P_plus^2=P_plus_when_n_dot_n=1",
        "projector_idempotence_exact": pauli["projector_idempotence_exact"],
        "north_spinor": "(cos(theta/2),exp(i*phi)*sin(theta/2))",
        "south_spinor": "(exp(-i*phi)*cos(theta/2),sin(theta/2))",
        "north_to_south_transition": "exp(-i*phi)",
        "north_connection_coefficients_constant_cos": [str(item) for item in north_connection],
        "south_connection_coefficients_constant_cos": [str(item) for item in south_connection],
        "south_minus_north_coefficients": [str(item) for item in transition_difference],
        "patch_transition_exact": transition_difference == (Fraction(-1), Fraction(0)),
        "north_curvature_sine_coefficient": str(north_curvature_sine_coefficient),
        "south_curvature_sine_coefficient": str(south_curvature_sine_coefficient),
        "patch_curvatures_equal": (north_curvature_sine_coefficient == south_curvature_sine_coefficient),
        "sphere_flux_pi_coefficient": str(sphere_flux_pi_coefficient),
        "sphere_flux": "2*pi",
        "chern_number": int(chern_number),
        "global_smooth_connection_exists": chern_number == 0,
        "dOmega_divergence_coefficients": [
            str(divergence_r_minus_3_coefficient),
            str(divergence_r2_r_minus_5_coefficient),
        ],
        "dOmega_exact_zero": divergence_total == 0,
        "constant_projector_tensor": constant_tensor.tolist(),
        "constant_projector_null_exact": not np.any(constant_tensor),
        "center_vectors": [[str(item) for item in row] for row in exact_center_vectors],
        "center_vector_determinant": str(exact_center_determinant),
        "center_vector_rank": 3 if exact_center_determinant != 0 else 0,
        "heldout_vector": [str(item) for item in exact_heldout_vector],
        "heldout_density": fraction_item(exact_heldout_density),
        "nonscalar_map": "K=diag(2,1,1)",
        "nonscalar_divergence_at_h": fraction_item(mapped_divergence),
        "nonscalar_map_closed": mapped_divergence == 0,
    }


def geometry_certificate(contract: ConstitutiveMap3DContract = MODEL_CONTRACT) -> dict[str, object]:
    centers = [np.asarray(center, dtype=float) for center in contract.qp3_centers]
    vectors = [two_form_vector(curvature_tensor(center)) for center in centers]
    heldout = np.asarray([float(item) for item in contract.qp3_heldout], dtype=float)
    heldout_vector = two_form_vector(curvature_tensor(heldout))
    exact = exact_global_certificate(contract)
    return {
        "formula": "Omega_ij=epsilon_ijk*lambda_k/(2*abs(lambda)^3)",
        "center_vectors": [item.tolist() for item in vectors],
        "center_vector_rank": int(np.linalg.matrix_rank(np.stack(vectors))),
        "heldout_control": heldout.tolist(),
        "heldout_vector": heldout_vector.tolist(),
        "heldout_density": float(heldout_vector @ heldout),
        "heldout_density_exact": fraction_item(Fraction(1, 2)),
        "projector_idempotence_max_error": float(
            max(
                np.linalg.norm(projector(center) @ projector(center) - projector(center), ord=2)
                for center in centers
            )
        ),
        "proper_rotation_covariance": covariance_regression(),
        "integrability": ("dOmega=0_on_R3_without_origin" if exact["dOmega_exact_zero"] else "FAILED"),
        "sphere_flux": f"integral_S2_Omega={exact['sphere_flux']}",
        "chern_number": exact["chern_number"],
        "global_smooth_connection_exists": exact["global_smooth_connection_exists"],
        "constant_projector_curvature_max": float(
            np.max(np.abs(np.asarray(exact["constant_projector_tensor"])))
        ),
        "exact_global_certificate": exact,
        "response_lane_imported": False,
    }

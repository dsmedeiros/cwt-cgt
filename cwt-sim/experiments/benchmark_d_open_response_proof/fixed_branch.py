"""Certified fixed branch and tangent-response calculations for the affine reduction."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .adapter import (
    affine_population_components,
    core_config,
    raw_core_step,
    theorem_d0_state,
)
from .contract import MODEL_CONTRACT, ModelContract


class ContractionCertificateError(ValueError):
    """Raised when strict contraction cannot be certified from depolarization."""


@dataclass(frozen=True)
class FixedBranchBundle:
    """Fixed population and its two exact implicit derivatives in float arithmetic."""

    population: np.ndarray
    derivative_bias: np.ndarray
    derivative_diffusion: np.ndarray
    matrix: np.ndarray
    offset: np.ndarray


def contraction_certificate(depolarizing: float) -> dict[str, float | str]:
    """Return the global CPTP trace/L1 contraction certificate or refuse it."""

    if not np.isfinite(depolarizing) or not 0.0 < depolarizing < 1.0:
        raise ContractionCertificateError("strict contraction requires 0 < depolarizing < 1")
    return {
        "norm": "trace_norm_global_and_l1_on_diagonal_populations",
        "factor": 1.0 - depolarizing,
        "proof": (
            "Differences pass through the CPTP Kraus channel and are then multiplied by "
            "1-depolarizing; trace distance is CPTP contractive."
        ),
    }


def _matrix_derivatives(contract: ModelContract = MODEL_CONTRACT) -> tuple[np.ndarray, np.ndarray]:
    """Return exact constant derivatives dM/db and dM/dd on the unclipped box."""

    kernel_bias = np.zeros((5, 5), dtype=float)
    kernel_diffusion = np.zeros((5, 5), dtype=float)
    kernel_bias[0, 0], kernel_bias[0, 1] = -1.0, 1.0
    kernel_diffusion[0, 0], kernel_diffusion[0, 1] = -1.0, 1.0
    for node in range(1, 4):
        kernel_bias[node, node - 1] = -1.0
        kernel_bias[node, node + 1] = 1.0
        kernel_diffusion[node, node - 1] = 1.0
        kernel_diffusion[node, node + 1] = 1.0
        kernel_diffusion[node, node] = -2.0
    kernel_bias[4, 3], kernel_bias[4, 4] = -1.0, 1.0
    kernel_diffusion[4, 3], kernel_diffusion[4, 4] = 1.0, -1.0
    scale = float(contract.contraction_factor * contract.jump_probability_scale)
    return scale * kernel_bias.T, scale * kernel_diffusion.T


def fixed_branch_bundle(
    bias: float,
    diffusion: float,
    contract: ModelContract = MODEL_CONTRACT,
) -> FixedBranchBundle:
    """Solve the true affine fixed branch and implicit first derivatives."""

    matrix, offset = affine_population_components(bias, diffusion, contract)
    operator = np.eye(contract.node_count) - matrix
    population = np.linalg.solve(operator, offset)
    matrix_bias, matrix_diffusion = _matrix_derivatives(contract)
    derivative_bias = np.linalg.solve(operator, matrix_bias @ population)
    derivative_diffusion = np.linalg.solve(operator, matrix_diffusion @ population)
    return FixedBranchBundle(
        population=population,
        derivative_bias=derivative_bias,
        derivative_diffusion=derivative_diffusion,
        matrix=matrix,
        offset=offset,
    )


def response_one_form(
    bias: float,
    diffusion: float,
    readout: np.ndarray | None = None,
    contract: ModelContract = MODEL_CONTRACT,
) -> np.ndarray:
    """Compute ``B_i=-H(I-M)^-1 M X_i`` without geometry inputs."""

    bundle = fixed_branch_bundle(bias, diffusion, contract)
    operator = np.eye(contract.node_count) - bundle.matrix
    if readout is None:
        readout = np.arange(1, contract.node_count + 1, dtype=float)
    readout = np.asarray(readout, dtype=float)
    return np.asarray(
        [
            -readout @ np.linalg.solve(operator, bundle.matrix @ bundle.derivative_bias),
            -readout @ np.linalg.solve(operator, bundle.matrix @ bundle.derivative_diffusion),
        ],
        dtype=float,
    )


def analytic_response_curvature(
    bias: float,
    diffusion: float,
    readout: np.ndarray | None = None,
    contract: ModelContract = MODEL_CONTRACT,
) -> float:
    """Evaluate ``F_bd=partial_b B_d-partial_d B_b`` analytically."""

    bundle = fixed_branch_bundle(bias, diffusion, contract)
    matrix_bias, matrix_diffusion = _matrix_derivatives(contract)
    operator = np.eye(contract.node_count) - bundle.matrix
    if readout is None:
        readout = np.arange(1, contract.node_count + 1, dtype=float)
    readout = np.asarray(readout, dtype=float)
    mixed = np.linalg.solve(
        operator,
        matrix_bias @ bundle.derivative_diffusion + matrix_diffusion @ bundle.derivative_bias,
    )
    lag_bias = np.linalg.solve(operator, bundle.matrix @ bundle.derivative_bias)
    lag_diffusion = np.linalg.solve(operator, bundle.matrix @ bundle.derivative_diffusion)
    derivative_bias_of_diffusion = -readout @ np.linalg.solve(
        operator,
        matrix_bias @ lag_diffusion + matrix_bias @ bundle.derivative_diffusion + bundle.matrix @ mixed,
    )
    derivative_diffusion_of_bias = -readout @ np.linalg.solve(
        operator,
        matrix_diffusion @ lag_bias + matrix_diffusion @ bundle.derivative_bias + bundle.matrix @ mixed,
    )
    return float(derivative_bias_of_diffusion - derivative_diffusion_of_bias)


def numerical_response_curvature(step: float = 1e-5) -> float:
    """Independent central-difference curl of the computed one-form."""

    bias = float(MODEL_CONTRACT.center_bias)
    diffusion = float(MODEL_CONTRACT.center_diffusion)
    derivative_bias_of_diffusion = (
        response_one_form(bias + step, diffusion)[1] - response_one_form(bias - step, diffusion)[1]
    ) / (2.0 * step)
    derivative_diffusion_of_bias = (
        response_one_form(bias, diffusion + step)[0] - response_one_form(bias, diffusion - step)[0]
    ) / (2.0 * step)
    return float(derivative_bias_of_diffusion - derivative_diffusion_of_bias)


def fixed_branch_certificates(mesh: int = 5) -> dict[str, float]:
    """Check residual and sampled variation; full rank uses the exact global floor."""

    contract = MODEL_CONTRACT
    biases = np.linspace(float(contract.box.bias_min), float(contract.box.bias_max), mesh)
    diffusions = np.linspace(
        float(contract.box.diffusion_min),
        float(contract.box.diffusion_max),
        mesh,
    )
    populations: list[np.ndarray] = []
    max_residual = 0.0
    max_trace_error = 0.0
    min_eigenvalue = float("inf")
    max_projection_delta = 0.0
    config = core_config(contract)
    for bias in biases:
        for diffusion in diffusions:
            bundle = fixed_branch_bundle(float(bias), float(diffusion), contract)
            population = bundle.population
            populations.append(population)
            residual = bundle.matrix @ population + bundle.offset - population
            max_residual = max(max_residual, float(np.linalg.norm(residual, ord=1)))
            max_trace_error = max(max_trace_error, abs(float(np.sum(population)) - 1.0))
            min_eigenvalue = min(min_eigenvalue, float(np.min(population)))
            state = theorem_d0_state(float(bias), float(diffusion))
            raw = raw_core_step(
                np.diag(population).astype(complex),
                state,
                config,
                float(contract.dephasing),
            )
            projected_delta = float(np.linalg.norm(raw - np.diag(population), ord="fro"))
            max_projection_delta = max(max_projection_delta, projected_delta)
    stack = np.asarray(populations)
    variation = float(np.max(np.linalg.norm(stack - stack[0], axis=1)))
    factor = float(contract.contraction_factor)
    return {
        "sampled_mesh_points_per_axis": float(mesh),
        "max_fixed_residual_l1": max_residual,
        "banach_error_upper_bound_l1": max_residual / (1.0 - factor),
        "max_trace_error": max_trace_error,
        "sampled_minimum_fixed_eigenvalue": min_eigenvalue,
        "sampled_fixed_branch_variation_l2": variation,
        "max_raw_fixed_step_delta_fro": max_projection_delta,
        "global_depolarizing_eigenvalue_floor": float(contract.depolarizing_floor),
    }

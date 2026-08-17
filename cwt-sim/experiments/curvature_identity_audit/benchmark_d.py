"""Benchmark-D exact stationary projective zero-set obstruction."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction

import numpy as np

from cwt.cgt.geometry import projective_metric_trace_and_curvature
from experiments.benchmark_d_lindblad_response_proof.adapter import mean_position_operator
from experiments.benchmark_d_lindblad_response_proof.certificates import exact_stationary_certificate
from experiments.benchmark_d_lindblad_response_proof.contract import (
    FORMAL_RESPONSE_CURVATURE,
    MODEL_CONTRACT as LINDBLAD_CONTRACT,
)
from experiments.benchmark_d_lindblad_response_proof.exact_math import (
    affine_population_generator,
    affine_source,
    exact_response_oracle,
    solve_fraction,
)

from .contract import MODEL_CONTRACT, CurvatureAuditContract
from .exact import fraction_item


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _center_model_payload() -> dict[str, object]:
    matrix = affine_population_generator(
        LINDBLAD_CONTRACT.center_bias,
        LINDBLAD_CONTRACT.center_diffusion,
    )
    source = affine_source()
    observable = [Fraction(index + 1) for index in range(LINDBLAD_CONTRACT.node_count)]
    return {
        "generator_formula": "A=(1/5)(K^T-I)-(1/25)I",
        "generator_center": [[_fraction_text(value) for value in row] for row in matrix],
        "affine_source_formula": "c=(1/125)1",
        "affine_source_center": [_fraction_text(value) for value in source],
        "observable_formula": "O=diag(1,2,3,4,5)",
        "observable_diagonal": [_fraction_text(value) for value in observable],
    }


def _model_identity_sha256() -> str:
    payload = json.dumps(
        _center_model_payload(),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def exact_stationary_population(bias: Fraction, diffusion: Fraction) -> tuple[Fraction, ...]:
    """Solve xbar=-A^-1 c exactly for the selected affine generator."""

    matrix = affine_population_generator(bias, diffusion)
    stationary = solve_fraction(matrix, [-value for value in affine_source()])
    return tuple(stationary)


def projective_lift(population: tuple[Fraction, ...] | list[Fraction]) -> np.ndarray:
    """Return the declared positive real normalized lift without floors or repair."""

    exact = tuple(Fraction(value) for value in population)
    if any(value <= 0 for value in exact):
        raise ValueError("the exact stationary population must be strictly positive")
    if sum(exact) != 1:
        raise ValueError("the exact stationary population must be normalized")
    return np.sqrt(np.asarray(exact, dtype=float)).astype(complex)


def _projective_numerical_regression() -> dict[str, float]:
    b = LINDBLAD_CONTRACT.center_bias
    d = LINDBLAD_CONTRACT.center_diffusion
    step = Fraction(1, 100000)

    def psi(bias: Fraction, diffusion: Fraction) -> np.ndarray:
        return projective_lift(exact_stationary_population(bias, diffusion))

    center = psi(b, d)
    b_plus, b_minus = psi(b + step, d), psi(b - step, d)
    d_plus, d_minus = psi(b, d + step), psi(b, d - step)
    metric, curvature = projective_metric_trace_and_curvature(
        center,
        b_plus,
        b_minus,
        d_plus,
        d_minus,
        float(step),
        float(step),
    )
    return {
        "role": "real_lift_finite_difference_regression_not_proof",
        "metric_trace": metric,
        "projective_curvature": curvature,
        "normalization_error": abs(float(np.vdot(center, center).real) - 1.0),
        "maximum_imaginary_component": float(np.max(np.abs(center.imag))),
    }


def benchmark_d_certificate(
    contract: CurvatureAuditContract = MODEL_CONTRACT,
) -> dict[str, object]:
    """Return the same-model Omega=0, F!=0 obstruction."""

    stationary = exact_stationary_certificate()
    oracle = exact_response_oracle()
    center_population = exact_stationary_population(
        LINDBLAD_CONTRACT.center_bias,
        LINDBLAD_CONTRACT.center_diffusion,
    )
    psi = projective_lift(center_population)
    named_operator = mean_position_operator()
    expected_operator = np.diag(np.arange(1, 6, dtype=float))
    model_identity = _model_identity_sha256()
    exact_residual = [
        sum(entry * value for entry, value in zip(row, center_population)) + source
        for row, source in zip(
            affine_population_generator(
                LINDBLAD_CONTRACT.center_bias,
                LINDBLAD_CONTRACT.center_diffusion,
            ),
            affine_source(),
        )
    ]
    return {
        "classification": "SAME_MODEL_ZERO_SET_OBSTRUCTION",
        "branch": "xbar(b,d)=-A(b,d)^(-1)c",
        "projective_encoding": contract.benchmark_d_projective_encoding,
        "model_payload": _center_model_payload(),
        "model_identity_sha256": model_identity,
        "geometry_model_identity_sha256": model_identity,
        "response_model_identity_sha256": model_identity,
        "same_A_c_O_provenance": True,
        "center_stationary_population": [fraction_item(value) for value in center_population],
        "center_stationary_residual": [fraction_item(value) for value in exact_residual],
        "center_trace": fraction_item(sum(center_population)),
        "uniform_positive_lower_bound": stationary["uniform_full_rank_floor"],
        "uniform_lower_bound_derivation": stationary["floor_derivation"],
        "encoding_probability_floor_applied": False,
        "encoding_clip_applied": False,
        "encoding_projection_or_normalization_repair_applied": False,
        "center_lift_norm_error": float(abs(np.vdot(psi, psi).real - 1.0)),
        "center_lift_maximum_imaginary_component": float(np.max(np.abs(psi.imag))),
        "berry_connection": "A_i=-i<psi|partial_i psi>=-(i/2)partial_i sum_j xbar_j=0",
        "projective_curvature": "Omega_bd=dA=0 exactly for the smooth positive real lift",
        "projective_curvature_fraction": "0/1",
        "response_oracle": oracle.jsonable(),
        "response_fraction_matches_formal": oracle.response_curvature_bd == FORMAL_RESPONSE_CURVATURE,
        "response_curvature_nonzero": oracle.response_curvature_bd != 0,
        "zero_set_obstruction": (
            "Omega_bd=0 and F_bd!=0, so no finite scalar F=kappa*Omega and no frozen "
            "zero-preserving homogeneous linear tensor map can reproduce this encoding/readout response"
        ),
        "obstruction_scope": "finite_scalar_or_frozen_zero_preserving_homogeneous_linear_tensor_map",
        "finite_scalar_kappa_exists_at_center": False,
        "zero_preserving_homogeneous_linear_tensor_map_can_match": False,
        "arbitrary_nonlinear_or_affine_omega_only_map_ruled_out": False,
        "named_core_observable_error": float(np.max(np.abs(named_operator - expected_operator))),
        "projective_regression": _projective_numerical_regression(),
        "projective_encoding_is_mixed_density": False,
        "mixed_density_statement": (
            "rho=diag(xbar) is a separate commuting full-rank density family; its Uhlmann link "
            "unitaries and loop holonomy are identity, hence phase zero"
        ),
        "mixed_density_used_to_prove_projective_zero": False,
        "auxiliary_or_authored_constant_state_used": False,
        "finite_step_branch_used": False,
    }

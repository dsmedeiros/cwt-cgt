"""Analytic contract, stationary, loop, null, and interval certificates."""

from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
from math import cos, pi, sin

import numpy as np

from .adapter import (
    benchmark_c_unital_null_certificate,
    core_affine_equivalence_certificate,
    core_binding_certificate,
    explicit_projective_no_go_certificate,
    mean_position_operator,
)
from .contract import FORMAL_RESPONSE_CURVATURE, MODEL_CONTRACT, contract_issues
from .exact_math import (
    affine_population_generator,
    affine_source,
    dynamic_ladder_certificate,
    exact_response_oracle,
    fraction_item,
    solve_fraction,
)


def exact_stationary_certificate() -> dict[str, object]:
    """Solve the true affine fixed branch and prove a uniform full-rank floor."""

    box = MODEL_CONTRACT.box
    points = tuple(
        (bias, diffusion)
        for bias in (box.bias_min, box.bias_max, MODEL_CONTRACT.center_bias)
        for diffusion in (
            box.diffusion_min,
            box.diffusion_max,
            MODEL_CONTRACT.center_diffusion,
        )
    )
    residuals: list[Fraction] = []
    minimum_component: Fraction | None = None
    maximum_trace_error = Fraction(0)
    for bias, diffusion in points:
        matrix = affine_population_generator(bias, diffusion)
        stationary = solve_fraction(matrix, [-value for value in affine_source()])
        residual = [
            value + source
            for value, source in zip(
                [sum(entry * item for entry, item in zip(row, stationary)) for row in matrix],
                affine_source(),
            )
        ]
        residuals.extend(abs(value) for value in residual)
        current_minimum = min(stationary)
        minimum_component = (
            current_minimum if minimum_component is None else min(minimum_component, current_minimum)
        )
        maximum_trace_error = max(maximum_trace_error, abs(sum(stationary) - 1))

    center_oracle = exact_response_oracle()
    floor = Fraction(4, 69)
    return {
        "center_stationary_population": [
            fraction_item(value) for value in center_oracle.stationary_population
        ],
        "maximum_exact_stationary_residual": fraction_item(max(residuals)),
        "maximum_exact_trace_error": fraction_item(maximum_trace_error),
        "sampled_box_minimum_component": fraction_item(minimum_component or Fraction(0)),
        "uniform_full_rank_floor": fraction_item(floor),
        "floor_derivation": (
            "x_i=(5/6)(K^T x)_i+1/30 and K_ii>=51/100 imply " "x_i>=(1/30)/(1-(5/6)(51/100))=4/69"
        ),
        "uniform_floor_below_sampled_minimum": floor <= (minimum_component or Fraction(0)),
    }


def contraction_certificate() -> dict[str, object]:
    """State the exact trace-norm semigroup and inverse bounds."""

    rate = MODEL_CONTRACT.depolarizing_rate
    return {
        "norm": "trace_norm_on_traceless_Hermitian_matrices",
        "propagator_bound": "||U(t,s)||_1<=exp(-(t-s)/25)",
        "M": fraction_item(Fraction(1)),
        "tau": fraction_item(1 / rate),
        "inverse_bound_KJ": fraction_item(1 / rate),
        "proof": (
            "jump-plus-dephasing evolution is CPTP and trace-norm contractive; "
            "depolarization factors every traceless deviation by exp(-t/25)"
        ),
    }


def loop_convention_certificate(sample_count: int = 256) -> dict[str, object]:
    """Check the exact analytic circle, reverse path, and endpoint convention."""

    box = MODEL_CONTRACT.box
    scale_exact = MODEL_CONTRACT.circle_scale
    bias_min_exact = MODEL_CONTRACT.center_bias - scale_exact
    bias_max_exact = MODEL_CONTRACT.center_bias + scale_exact
    diffusion_min_exact = MODEL_CONTRACT.center_diffusion - scale_exact
    diffusion_max_exact = MODEL_CONTRACT.center_diffusion + scale_exact
    exact_margins = (
        bias_min_exact - box.bias_min,
        box.bias_max - bias_max_exact,
        diffusion_min_exact - box.diffusion_min,
        box.diffusion_max - diffusion_max_exact,
    )
    exact_containment = (
        box.bias_min < bias_min_exact <= bias_max_exact < box.bias_max
        and box.diffusion_min < diffusion_min_exact <= diffusion_max_exact < box.diffusion_max
        and all(margin == Fraction(1, 100) for margin in exact_margins)
    )
    center = np.asarray([float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion)])
    scale = float(MODEL_CONTRACT.circle_scale)
    ccw = np.asarray(
        [
            center
            + scale * np.asarray([cos(2 * pi * index / sample_count), sin(2 * pi * index / sample_count)])
            for index in range(sample_count)
        ]
    )
    cw = np.asarray([ccw[(-index) % sample_count] for index in range(sample_count)])
    exact_reverse_error = max(
        np.max(np.abs(cw[index] - ccw[(-index) % sample_count])) for index in range(sample_count)
    )
    in_box = bool(
        np.all(ccw[:, 0] >= float(box.bias_min))
        and np.all(ccw[:, 0] <= float(box.bias_max))
        and np.all(ccw[:, 1] >= float(box.diffusion_min))
        and np.all(ccw[:, 1] <= float(box.diffusion_max))
    )
    return {
        "parameterization": "gamma_ccw(u)=c+s(cos(2*pi*u),sin(2*pi*u)), u in [0,1)",
        "reverse": "gamma_cw(u)=gamma_ccw(1-u)",
        "sample_count_for_contract_check": sample_count,
        "duplicate_endpoint_stored": False,
        "exact_reverse_maximum_error": float(exact_reverse_error),
        "every_sampled_loop_point_inside_box": in_box,
        "sampling_role": "diagnostic_only_not_domain_acceptance",
        "analytic_bias_extrema": [fraction_item(bias_min_exact), fraction_item(bias_max_exact)],
        "analytic_diffusion_extrema": [
            fraction_item(diffusion_min_exact),
            fraction_item(diffusion_max_exact),
        ],
        "exact_face_margins": [fraction_item(margin) for margin in exact_margins],
        "analytic_extrema_inside_box": exact_containment,
        "right_handed_area_sign": "positive_ccw_db_wedge_dd",
        "qanti_definition": "(Q_ccw-Q_cw)/2",
        "ordinary_difference_in_differences": "Q_ccw-Q_cw=2*Qanti",
    }


def null_and_covariance_certificates() -> dict[str, object]:
    """Compute exact readout nulls/covariance and mandatory model refusals."""

    identity = [Fraction(1)] * MODEL_CONTRACT.node_count
    primary = exact_response_oracle()
    identity_oracle = exact_response_oracle(identity)
    scaled_oracles = {
        str(scale): exact_response_oracle(
            [scale * Fraction(index + 1) for index in range(MODEL_CONTRACT.node_count)]
        ).response_curvature_bd
        for scale in (Fraction(-2), Fraction(3))
    }
    source = affine_source()
    omitted_source_norm = sum(abs(value) for value in source)
    invalid_contracts = {
        "zero_depolarization": replace(MODEL_CONTRACT, depolarizing_rate=Fraction(0)),
        "nonzero_coherent": replace(MODEL_CONTRACT, coherent_scale=Fraction(1, 10)),
        "nonzero_site_gauge": replace(MODEL_CONTRACT, site_potential_scale=Fraction(1, 10)),
        "euler_projection_backend": replace(MODEL_CONTRACT, flow_backend="euler_plus_psd_projection"),
        "wrong_dt": replace(MODEL_CONTRACT, dt=Fraction(1, 10)),
        "wrong_reversal": replace(MODEL_CONTRACT, reversal_convention="independent_clockwise_path"),
        "wrong_initialization": replace(MODEL_CONTRACT, initialization="arbitrary_state"),
        "nonuniform_clock": replace(
            MODEL_CONTRACT,
            slow_drive_clock_id="nonuniform_quadratic_clock_v1",
            slow_drive_clock_definition="u=(t/T)^2;lambda_plus(t)=gamma_plus(u)",
        ),
    }
    return {
        "identity_readout_curvature": fraction_item(identity_oracle.response_curvature_bd),
        "scaled_readout_curvatures": {key: fraction_item(value) for key, value in scaled_oracles.items()},
        "scaled_covariance_exact": all(
            scaled_oracles[str(scale)] == scale * primary.response_curvature_bd
            for scale in (Fraction(-2), Fraction(3))
        ),
        "affine_source_l1_norm": fraction_item(omitted_source_norm),
        "affine_source_omission_changes_fixed_equation": omitted_source_norm > 0,
        "invalid_contract_issues": {key: contract_issues(value) for key, value in invalid_contracts.items()},
        "every_invalid_variant_refused": all(contract_issues(value) for value in invalid_contracts.values()),
    }


def all_certificates() -> dict[str, object]:
    """Compute the complete deterministic theorem-certificate payload."""

    oracle = exact_response_oracle()
    return {
        "core_binding": core_binding_certificate(),
        "core_affine_equivalence": core_affine_equivalence_certificate(),
        "stationary": exact_stationary_certificate(),
        "contraction": contraction_certificate(),
        "exact_response": oracle.jsonable(),
        "formal_fraction_matches": oracle.response_curvature_bd == FORMAL_RESPONSE_CURVATURE,
        "loop_convention": loop_convention_certificate(),
        "dynamic": dynamic_ladder_certificate(),
        "nulls_and_covariance": null_and_covariance_certificates(),
        "benchmark_c_null": benchmark_c_unital_null_certificate(),
        "projective_no_go": explicit_projective_no_go_certificate(),
        "named_readout_execution_probe": float(
            np.real(
                np.trace(
                    mean_position_operator()
                    @ np.diag(np.asarray(exact_response_oracle().stationary_population, dtype=float))
                )
            )
        ),
    }

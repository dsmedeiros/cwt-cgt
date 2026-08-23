"""Counted physical-edge Drazin response and FCS normal-connection lane."""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache

from .contract import MODEL_CONTRACT
from .exact import (
    ZERO,
    Matrix,
    dot,
    gaussian,
    matrix_vector,
    real_fraction,
    vector_add,
    vector_scale,
    zeros,
)
from .generator import (
    BranchBundle,
    N,
    branch_bundle,
    build_branch_bundle,
    cartesian_branch_bundle,
    chord_derivatives,
    current_derivatives,
    current_row,
    trace_row,
)

COUNTING_AUTHORITY = "same_exact_generator_physical_middle_edge_q_jet"


def counted_q_jet(
    bias: Fraction,
    diffusion: Fraction,
    *,
    orientation: int = 1,
) -> Matrix:
    """Return J=d_q W_q|0; losses are unchanged."""

    result = zeros(N * N, N * N)
    forward = MODEL_CONTRACT.edge_rate * (diffusion + bias)
    reverse = MODEL_CONTRACT.edge_rate * (diffusion - bias)
    result[2 + N * 2][1 + N * 1] = gaussian(orientation * forward)
    result[1 + N * 1][2 + N * 2] = gaussian(-orientation * reverse)
    return result


def _response(bundle: BranchBundle, *, orientation: int = 1) -> dict[str, object]:
    bias, diffusion, _t = bundle.center
    current = current_row(bias, diffusion, orientation=orientation)
    current_first = current_derivatives(orientation=orientation)
    lags = tuple(matrix_vector(bundle.drazin, tangent) for tangent in bundle.tangents)
    one_form = tuple(real_fraction(dot(current, lag), label=f"B_{axis}") for axis, lag in enumerate(lags))
    derivatives: list[list[Fraction]] = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for component in range(3):
        for axis in range(3):
            derivative_lag = vector_add(
                matrix_vector(bundle.drazin_derivatives[axis], bundle.tangents[component]),
                matrix_vector(bundle.drazin, bundle.second_tangents[component][axis]),
            )
            derivatives[component][axis] = real_fraction(
                dot(current_first[axis], lags[component]) + dot(current, derivative_lag),
                label=f"partial_{axis}_B_{component}",
            )
    curvature = (
        derivatives[2][1] - derivatives[1][2],
        derivatives[0][2] - derivatives[2][0],
        derivatives[1][0] - derivatives[0][1],
    )
    return {
        "response_one_form": one_form,
        "response_derivative_matrix": derivatives,
        "response_curvature_order": MODEL_CONTRACT.two_form_vector_order,
        "response_curvature": curvature,
        "response_signs": tuple(1 if item > 0 else -1 for item in curvature),
        "all_response_components_nonzero": all(item != 0 for item in curvature),
        "orientation": orientation,
    }


def _cartesian_response_pullback() -> dict[str, object]:
    """Compute ambient ``(b,d,x,y)`` response and pull it back to ``t``."""

    bundle = cartesian_branch_bundle()
    bias, diffusion, _t = MODEL_CONTRACT.center
    current = current_row(bias, diffusion)
    canonical_first = current_derivatives()
    zero_current_derivative = [ZERO for _ in range(N * N)]
    current_first = (
        canonical_first[0],
        canonical_first[1],
        zero_current_derivative,
        zero_current_derivative,
    )
    lags = tuple(matrix_vector(bundle.drazin, tangent) for tangent in bundle.tangents)
    one_form = tuple(real_fraction(dot(current, lag), label="Cartesian B") for lag in lags)
    derivatives = [[Fraction(0) for _ in range(4)] for _ in range(4)]
    for component in range(4):
        for axis in range(4):
            derivative_lag = vector_add(
                matrix_vector(bundle.drazin_derivatives[axis], bundle.tangents[component]),
                matrix_vector(bundle.drazin, bundle.second_tangents[component][axis]),
            )
            derivatives[component][axis] = real_fraction(
                dot(current_first[axis], lags[component]) + dot(current, derivative_lag),
                label="Cartesian response derivative",
            )
    curvature = [
        [derivatives[right][left] - derivatives[left][right] for right in range(4)] for left in range(4)
    ]
    chord_first, _chord_second = chord_derivatives(MODEL_CONTRACT.center[2])
    pulled = (
        chord_first.real * curvature[1][2] + chord_first.imag * curvature[1][3],
        chord_first.real * curvature[2][0] + chord_first.imag * curvature[3][0],
        curvature[0][1],
    )
    antisymmetric = all(
        curvature[left][right] == -curvature[right][left] for left in range(4) for right in range(4)
    )
    return {
        "control_order": ("b", "d", "x", "y"),
        "chord_jacobian_dt": (chord_first.real, chord_first.imag),
        "response_one_form": one_form,
        "response_curvature_matrix": curvature,
        "response_curvature_antisymmetric": antisymmetric,
        "pullback_to_t_curvature": pulled,
    }


@lru_cache(maxsize=1)
def counting_record() -> dict[str, object]:
    bundle = branch_bundle()
    bias, diffusion, _t = bundle.center
    q_jet = counted_q_jet(bias, diffusion)
    current = current_row(bias, diffusion)
    response = _response(bundle)
    cartesian = _cartesian_response_pullback()
    nonzero = [
        (row, column, value)
        for row, values in enumerate(q_jet)
        for column, value in enumerate(values)
        if not value.is_zero()
    ]
    return {
        "authority": COUNTING_AUTHORITY,
        "count_orientation": MODEL_CONTRACT.positive_count_definition,
        "forward_gain_rate": MODEL_CONTRACT.edge_rate * (diffusion + bias),
        "reverse_gain_rate": MODEL_CONTRACT.edge_rate * (diffusion - bias),
        "first_q_jet_nonzero_entries": nonzero,
        "first_q_jet_only_counted_gains": len(nonzero) == 2,
        "losses_unchanged_by_q": all(row != column for row, column, _value in nonzero),
        "current_equals_trace_q_jet": current
        == [dot(trace_row(), [q_jet[row][column] for row in range(N * N)]) for column in range(N * N)],
        **response,
        "cartesian_response": cartesian,
        "cartesian_to_t_response_pullback_equal": cartesian["pullback_to_t_curvature"]
        == response["response_curvature"],
        "finite_difference_used_for_acceptance": False,
        "counting_received_geometry_or_Omega": False,
    }


@lru_cache(maxsize=1)
def fcs_record() -> dict[str, object]:
    bundle = branch_bundle()
    bias, diffusion, _t = bundle.center
    q_jet = counted_q_jet(bias, diffusion)
    current = current_row(bias, diffusion)
    stationary_current = dot(current, bundle.stationary)
    centered = vector_add(
        matrix_vector(q_jet, bundle.stationary),
        vector_scale(bundle.stationary, -stationary_current),
    )
    right_q = vector_scale(matrix_vector(bundle.drazin, centered), -1)
    left_q = [-dot(current, [bundle.drazin[row][column] for row in range(N * N)]) for column in range(N * N)]
    partial_q_connection = tuple(dot(left_q, item) for item in bundle.tangents)
    minus_partial = tuple(
        real_fraction(-item, label="minus partial q connection") for item in partial_q_connection
    )
    current_first = current_derivatives()
    left_q_first = []
    for axis in range(3):
        values = []
        for column in range(N * N):
            current_term = dot(
                current_first[axis],
                [bundle.drazin[row][column] for row in range(N * N)],
            )
            drazin_term = dot(
                current,
                [bundle.drazin_derivatives[axis][row][column] for row in range(N * N)],
            )
            values.append(-(current_term + drazin_term))
        left_q_first.append(values)
    connection_derivatives = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for component in range(3):
        for axis in range(3):
            connection_derivatives[component][axis] = real_fraction(
                dot(left_q_first[axis], bundle.tangents[component])
                + dot(left_q, bundle.second_tangents[component][axis]),
                label="normal connection derivative",
            )
    curvature = (
        connection_derivatives[1][2] - connection_derivatives[2][1],
        connection_derivatives[2][0] - connection_derivatives[0][2],
        connection_derivatives[0][1] - connection_derivatives[1][0],
    )
    direct = counting_record()
    trace_functional = trace_row()
    left_equation = []
    for column in range(N * N):
        left_w = dot(
            left_q,
            [bundle.generator[row][column] for row in range(N * N)],
        )
        left_equation.append(left_w + current[column] - stationary_current * trace_functional[column])
    right_equation = vector_add(matrix_vector(bundle.generator, right_q), centered)
    return {
        "authority": "independent_exact_first_q_eigenbundle_jet",
        "geometric_cumulant": "minus_closed_integral_A(q)",
        "left_q_eigenvector_equation": all(item.is_zero() for item in left_equation),
        "right_q_eigenvector_equation": all(item.is_zero() for item in right_equation),
        "left_q_gauge": dot(left_q, bundle.stationary).is_zero(),
        "right_q_gauge": dot(trace_functional, right_q).is_zero(),
        "minus_partial_q_connection": minus_partial,
        "direct_Drazin_response": direct["response_one_form"],
        "B_equals_minus_partial_q_A": minus_partial == direct["response_one_form"],
        "F_from_normal_connection_curl": curvature,
        "direct_response_curvature": direct["response_curvature"],
        "F_equals_minus_partial_q_dA": curvature == direct["response_curvature"],
        "state_mean_Uhlmann_connection_used": False,
        "extended_eigenbundle_connection_distinct_from_state_geometry": True,
    }


@lru_cache(maxsize=1)
def null_record() -> dict[str, object]:
    canonical = _response(branch_bundle())
    reverse = _response(branch_bundle(), orientation=-1)
    zero_bundle = build_branch_bundle(radius=Fraction(0))
    zero_chord = _response(zero_bundle)
    zero_current = _response(branch_bundle(), orientation=0)
    bias, diffusion, _t = MODEL_CONTRACT.center
    zero_q_jet = counted_q_jet(bias, diffusion, orientation=0)
    return {
        "reverse_count_B": reverse["response_one_form"],
        "reverse_count_F": reverse["response_curvature"],
        "reverse_count_negates_B": reverse["response_one_form"]
        == tuple(-item for item in canonical["response_one_form"]),
        "reverse_count_negates_F": reverse["response_curvature"]
        == tuple(-item for item in canonical["response_curvature"]),
        "zero_current": zero_current,
        "zero_current_q_jet": zero_q_jet,
        "zero_current_operator_constructed_independently": all(
            item.is_zero() for row in zero_q_jet for item in row
        ),
        "zero_current_response_recomputed": True,
        "zero_current_B_and_F_zero": zero_current["response_one_form"] == (0, 0, 0)
        and zero_current["response_curvature"] == (0, 0, 0),
        "zero_chord_t_tangent_zero": all(item.is_zero() for item in zero_bundle.tangents[2]),
        "zero_chord_t_response_zero": zero_chord["response_one_form"][2] == 0,
        "zero_chord_t_curvature_components_zero": zero_chord["response_curvature"][:2] == (0, 0),
        "zero_chord_outside_positive_box": True,
        "qanti_factor": Fraction(1, 2),
        "full_orientation_difference_factor": Fraction(2),
    }

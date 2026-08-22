"""Authenticated counting-field, Drazin-response, and FCS connection lane."""

from __future__ import annotations

from fractions import Fraction
from functools import lru_cache

from .exact import dot, gaussian, matrix_vector, real_fraction, vector_add, vector_scale
from .generator import (
    NODE_COUNT,
    ExactBranchResponse,
    current_row,
    drazin_identity_errors,
    exact_branch_response,
    liouvillian,
    t0_response,
    t1_response,
    tilted_generator_q_jet,
    trace_row,
)

COUNTING_AUTHORITY = "same_exact_D0_Lindblad_jump_gains"
COUNT_ORIENTATION = "positive_q_counts_index_1_to_2_physical_nodes_2_to_3"
TWO_FORM_VECTOR_ORDER = ("F_d_third", "F_third_b", "F_b_d")


def _reverse_count_response(response: ExactBranchResponse) -> ExactBranchResponse:
    def reverse_current(bias: Fraction, diffusion: Fraction, _third: Fraction):
        return vector_scale(current_row(bias, diffusion), -1)

    if response.control_names == ("b", "d", "delta"):

        def generator_builder(bias: Fraction, diffusion: Fraction, delta: Fraction):
            return liouvillian(bias, diffusion, Fraction(0), delta)

    elif response.control_names == ("b", "d", "h"):

        def generator_builder(bias: Fraction, diffusion: Fraction, coherent: Fraction):
            return liouvillian(bias, diffusion, coherent, Fraction(1, 25))

    else:
        raise RuntimeError("unknown reverse-count control chart")
    return exact_branch_response(
        control_names=response.control_names,
        center=response.center,
        generator_builder=generator_builder,
        current_builder=reverse_current,
    )


def _response_record(response: ExactBranchResponse) -> dict[str, object]:
    first, second, third = response.response_curvature
    antisymmetric = (
        (Fraction(0), third, -second),
        (-third, Fraction(0), first),
        (second, -first, Fraction(0)),
    )
    return {
        "control_names": response.control_names,
        "center": response.center,
        "response_one_form": response.response_one_form,
        "response_curvature_vector_order": TWO_FORM_VECTOR_ORDER,
        "response_curvature": response.response_curvature,
        "response_curvature_antisymmetric_matrix": antisymmetric,
        "antisymmetry_exact": all(
            antisymmetric[left][right] == -antisymmetric[right][left]
            for left in range(3)
            for right in range(3)
        ),
        "local_curvature_definition": "F_R=d_parameter_B_R_at_frozen_center",
        "all_curvature_components_nonzero": all(value != 0 for value in response.response_curvature),
        "all_curvature_components_negative": all(value < 0 for value in response.response_curvature),
        "drazin_identities": drazin_identity_errors(response),
        "finite_difference_used_for_acceptance": False,
    }


@lru_cache(maxsize=1)
def t0_counting_certificate() -> dict[str, object]:
    record = _response_record(t0_response())
    record.update(
        {
            "authority": COUNTING_AUTHORITY,
            "count_orientation": COUNT_ORIENTATION,
            "classification": "SAME_GENERATOR_CLASSICAL_THREE_CONTROL_ZERO_SET_OBSTRUCTION",
        }
    )
    return record


@lru_cache(maxsize=1)
def t1_counting_certificate() -> dict[str, object]:
    record = _response_record(t1_response())
    record.update(
        {
            "authority": COUNTING_AUTHORITY,
            "count_orientation": COUNT_ORIENTATION,
            "classification": "SAME_GENERATOR_COHERENT_THREE_CONTROL_ZERO_SET_OBSTRUCTION",
        }
    )
    return record


def _fcs_connection_identity(response: ExactBranchResponse) -> dict[str, object]:
    """Derive B=-partial_q A|0 from exact left/right eigenvector jets."""

    bias, diffusion, _third = response.center
    tilted_jet = tilted_generator_q_jet(response.generator, bias, diffusion)
    jump_derivative = tilted_jet.first_q_derivative
    trace_functional = trace_row()
    current = current_row(bias, diffusion)
    stationary_current = dot(current, response.stationary)
    centered_jump_on_state = vector_add(
        matrix_vector(jump_derivative, response.stationary),
        vector_scale(response.stationary, -stationary_current),
    )
    right_q_derivative = vector_scale(matrix_vector(response.drazin, centered_jump_on_state), -1)
    left_q_derivative = [
        -dot(current, [response.drazin[row][column] for row in range(NODE_COUNT**2)])
        for column in range(NODE_COUNT**2)
    ]
    connection_q_derivatives = tuple(dot(left_q_derivative, tangent) for tangent in response.tangents)
    derived_response = tuple(
        real_fraction(-value, label=f"-partial_q_A_{axis}")
        for axis, value in enumerate(connection_q_derivatives)
    )

    def row_matrix(row, matrix):
        return [
            dot(row, [matrix[inner][column] for inner in range(NODE_COUNT**2)])
            for column in range(NODE_COUNT**2)
        ]

    left_q_parameter_derivatives = []
    for axis in range(3):
        current_term = row_matrix(response.current_derivatives[axis], response.drazin)
        drazin_term = row_matrix(current, response.drazin_derivatives[axis])
        left_q_parameter_derivatives.append(
            [-(left + right) for left, right in zip(current_term, drazin_term, strict=True)]
        )
    connection_parameter_derivatives: list[list[Fraction]] = [
        [Fraction(0) for _ in range(3)] for _ in range(3)
    ]
    for component in range(3):
        for axis in range(3):
            value = dot(left_q_parameter_derivatives[axis], response.tangents[component]) + dot(
                left_q_derivative,
                response.second_tangents[component][axis],
            )
            connection_parameter_derivatives[component][axis] = real_fraction(
                value,
                label=f"partial_{axis}_partial_q_A_{component}",
            )
    curvature_from_normal_connection = (
        connection_parameter_derivatives[1][2] - connection_parameter_derivatives[2][1],
        connection_parameter_derivatives[2][0] - connection_parameter_derivatives[0][2],
        connection_parameter_derivatives[0][1] - connection_parameter_derivatives[1][0],
    )

    # Directly check both differentiated eigenvector equations and gauge normalizations.
    left_equation = []
    for column in range(NODE_COUNT**2):
        left_w = dot(left_q_derivative, [response.generator[row][column] for row in range(NODE_COUNT**2)])
        left_equation.append(left_w + current[column] - stationary_current * trace_functional[column])
    right_equation = vector_add(
        matrix_vector(response.generator, right_q_derivative),
        centered_jump_on_state,
    )
    reverse = _reverse_count_response(response)
    reverse_response = reverse.response_one_form
    reverse_curvature = reverse.response_curvature
    nonzero_q_jet_entries = [
        (row, column, value)
        for row, values in enumerate(jump_derivative)
        for column, value in enumerate(values)
        if not value.is_zero()
    ]
    return {
        "tilted_generator": "Wq gain terms exp(q*d_mn); losses unchanged",
        "positive_count": COUNT_ORIENTATION,
        "Wq_at_q0_equals_W": tilted_jet.base == response.generator,
        "first_q_jet_nonzero_entries": nonzero_q_jet_entries,
        "first_q_jet_has_only_forward_and_reverse_counted_gains": (
            nonzero_q_jet_entries
            == [
                (
                    1 + NODE_COUNT * 1,
                    2 + NODE_COUNT * 2,
                    gaussian(-tilted_jet.reverse_gain_rate),
                ),
                (
                    2 + NODE_COUNT * 2,
                    1 + NODE_COUNT * 1,
                    gaussian(tilted_jet.forward_gain_rate),
                ),
            ]
        ),
        "first_q_jet_losses_unchanged": all(row != column for row, column, _value in nonzero_q_jet_entries),
        "trace_W_at_q0_zero": all(
            dot(trace_functional, [response.generator[row][column] for row in range(NODE_COUNT**2)]).is_zero()
            for column in range(NODE_COUNT**2)
        ),
        "J_equals_partial_q_Wq_at_q0": current == response.current,
        "stationary_current": real_fraction(stationary_current, label="stationary current"),
        "left_q_eigenvector_equation_exact": all(value.is_zero() for value in left_equation),
        "right_q_eigenvector_equation_exact": all(value.is_zero() for value in right_equation),
        "left_q_normalization_exact": dot(left_q_derivative, response.stationary).is_zero(),
        "right_q_trace_gauge_exact": dot(trace_functional, right_q_derivative).is_zero(),
        "partial_q_connection": tuple(
            real_fraction(value, label=f"partial_q_A_{axis}")
            for axis, value in enumerate(connection_q_derivatives)
        ),
        "partial_parameter_partial_q_connection": connection_parameter_derivatives,
        "minus_partial_q_connection": derived_response,
        "direct_Drazin_response": response.response_one_form,
        "B_equals_minus_partial_q_A": derived_response == response.response_one_form,
        "F_from_independent_normal_connection_curl": curvature_from_normal_connection,
        "F_equals_minus_partial_q_dA": curvature_from_normal_connection == response.response_curvature,
        "F_value": curvature_from_normal_connection,
        "reverse_count_B": reverse_response,
        "reverse_count_F": reverse_curvature,
        "reverse_count_B_recomputed_independently": reverse_response
        == tuple(-value for value in response.response_one_form),
        "reverse_count_F_recomputed_independently": reverse_curvature
        == tuple(-value for value in response.response_curvature),
        "reverse_count_negates_B_and_F": (
            reverse_response == tuple(-value for value in response.response_one_form)
            and reverse_curvature == tuple(-value for value in response.response_curvature)
        ),
        "qanti_factor": Fraction(1, 2),
        "full_orientation_difference_factor": Fraction(2),
        "geometric_cumulant": "minus_closed_integral_A(q)",
        "state_CGT_connection_used": False,
        "extended_eigenbundle_normal_jet_is_distinct_from_state_CGT": True,
    }


@lru_cache(maxsize=1)
def t2_fcs_certificate() -> dict[str, object]:
    return {
        "authority": COUNTING_AUTHORITY,
        "classification": "FCS_EXTENDED_EIGENBUNDLE_RESPONSE_IDENTITY_DISTINCT_FROM_STATE_CGT",
        "T0": _fcs_connection_identity(t0_response()),
        "T1": _fcs_connection_identity(t1_response()),
    }


@lru_cache(maxsize=1)
def zero_current_null_certificate() -> dict[str, object]:
    """Derive the zero-current null from the same exact T1 generator branch."""

    def zero_current(_bias: Fraction, _diffusion: Fraction, _coherent: Fraction):
        return [value * 0 for value in current_row(Fraction(0), Fraction(1, 4))]

    canonical = t1_response()
    response = exact_branch_response(
        control_names=("b", "d", "h"),
        center=canonical.center,
        generator_builder=lambda bias, diffusion, coherent: liouvillian(
            bias,
            diffusion,
            coherent,
            Fraction(1, 25),
        ),
        current_builder=zero_current,
    )
    return {
        "authority": COUNTING_AUTHORITY,
        "same_exact_stationary_branch": response.stationary == canonical.stationary,
        "response_one_form": response.response_one_form,
        "response_curvature": response.response_curvature,
        "B_and_F_zero_exact": response.response_one_form == (0, 0, 0)
        and response.response_curvature == (0, 0, 0),
    }

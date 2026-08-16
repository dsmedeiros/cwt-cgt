"""Exact Fraction oracle for the diagonal Benchmark D affine response model."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Sequence

from .contract import FORMAL_RESPONSE_CURVATURE, MODEL_CONTRACT, ModelContract

Vector = list[Fraction]
Matrix = list[list[Fraction]]


def _identity(size: int) -> Matrix:
    return [[Fraction(int(row == column)) for column in range(size)] for row in range(size)]


def _transpose(matrix: Matrix) -> Matrix:
    return [list(row) for row in zip(*matrix)]


def _scale(value: Fraction, matrix: Matrix) -> Matrix:
    return [[value * item for item in row] for row in matrix]


def _add(left: Matrix, right: Matrix) -> Matrix:
    return [
        [left[row][column] + right[row][column] for column in range(len(left))] for row in range(len(left))
    ]


def _matvec(matrix: Matrix, vector: Sequence[Fraction]) -> Vector:
    return [sum(row[column] * vector[column] for column in range(len(vector))) for row in matrix]


def _solve(matrix: Matrix, vector: Sequence[Fraction]) -> Vector:
    """Gauss-Jordan solve over exact rational scalars."""

    size = len(vector)
    augmented = [matrix[row][:] + [vector[row]] for row in range(size)]
    for column in range(size):
        pivot = next(row for row in range(column, size) if augmented[row][column] != 0)
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        divisor = augmented[column][column]
        augmented[column] = [entry / divisor for entry in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            multiplier = augmented[row][column]
            if multiplier:
                augmented[row] = [
                    augmented[row][index] - multiplier * augmented[column][index] for index in range(size + 1)
                ]
    return [augmented[row][-1] for row in range(size)]


def _kernel_and_derivatives(bias: Fraction, diffusion: Fraction) -> tuple[Matrix, Matrix, Matrix]:
    size = MODEL_CONTRACT.node_count
    kernel = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    derivative_bias = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    derivative_diffusion = [[Fraction(0) for _ in range(size)] for _ in range(size)]
    k_plus = diffusion + bias
    k_minus = diffusion - bias
    kernel[0][0], kernel[0][1] = 1 - k_plus, k_plus
    derivative_bias[0][0], derivative_bias[0][1] = -1, 1
    derivative_diffusion[0][0], derivative_diffusion[0][1] = -1, 1
    for node in range(1, 4):
        kernel[node][node - 1] = k_minus
        kernel[node][node + 1] = k_plus
        kernel[node][node] = 1 - k_plus - k_minus
        derivative_bias[node][node - 1] = -1
        derivative_bias[node][node + 1] = 1
        derivative_diffusion[node][node - 1] = 1
        derivative_diffusion[node][node + 1] = 1
        derivative_diffusion[node][node] = -2
    kernel[4][3], kernel[4][4] = k_minus, 1 - k_minus
    derivative_bias[4][3], derivative_bias[4][4] = -1, 1
    derivative_diffusion[4][3], derivative_diffusion[4][4] = 1, -1
    return kernel, derivative_bias, derivative_diffusion


def _affine_matrices(
    bias: Fraction,
    diffusion: Fraction,
    contract: ModelContract,
) -> tuple[Matrix, Matrix, Matrix, Vector]:
    size = contract.node_count
    identity = _identity(size)
    kernel, derivative_bias, derivative_diffusion = _kernel_and_derivatives(bias, diffusion)
    jump = contract.jump_probability_scale
    transition = _add(_scale(1 - jump, identity), _scale(jump, kernel))
    matrix = _scale(contract.contraction_factor, _transpose(transition))
    matrix_bias = _scale(contract.contraction_factor * jump, _transpose(derivative_bias))
    matrix_diffusion = _scale(
        contract.contraction_factor * jump,
        _transpose(derivative_diffusion),
    )
    offset = [contract.depolarizing_floor for _ in range(size)]
    return matrix, matrix_bias, matrix_diffusion, offset


@dataclass(frozen=True)
class ExactResponseOracle:
    """Exact center fixed branch, one-form, and response-curvature certificate."""

    fixed_population: tuple[Fraction, ...]
    response_one_form_bias: Fraction
    response_one_form_diffusion: Fraction
    derivative_bias_of_B_diffusion: Fraction
    derivative_diffusion_of_B_bias: Fraction
    response_curvature_bd: Fraction

    @property
    def matches_formal_fraction(self) -> bool:
        return self.response_curvature_bd == FORMAL_RESPONSE_CURVATURE

    def jsonable(self) -> dict[str, object]:
        def item(value: Fraction) -> dict[str, object]:
            return {
                "fraction": f"{value.numerator}/{value.denominator}",
                "numerator": value.numerator,
                "denominator": value.denominator,
                "float": float(value),
            }

        return {
            "fixed_population": [item(value) for value in self.fixed_population],
            "response_one_form_bias": item(self.response_one_form_bias),
            "response_one_form_diffusion": item(self.response_one_form_diffusion),
            "derivative_bias_of_B_diffusion": item(self.derivative_bias_of_B_diffusion),
            "derivative_diffusion_of_B_bias": item(self.derivative_diffusion_of_B_bias),
            "response_curvature_bd": item(self.response_curvature_bd),
            "matches_formal_fraction": self.matches_formal_fraction,
        }


def exact_response_oracle(contract: ModelContract = MODEL_CONTRACT) -> ExactResponseOracle:
    """Recompute the rational response curvature from the frozen matrices."""

    size = contract.node_count
    matrix, matrix_bias, matrix_diffusion, offset = _affine_matrices(
        contract.center_bias,
        contract.center_diffusion,
        contract,
    )
    identity = _identity(size)
    fixed_operator = [
        [identity[row][column] - matrix[row][column] for column in range(size)] for row in range(size)
    ]
    fixed = _solve(fixed_operator, offset)
    fixed_bias = _solve(fixed_operator, _matvec(matrix_bias, fixed))
    fixed_diffusion = _solve(fixed_operator, _matvec(matrix_diffusion, fixed))
    fixed_mixed = _solve(
        fixed_operator,
        [
            left + right
            for left, right in zip(
                _matvec(matrix_bias, fixed_diffusion),
                _matvec(matrix_diffusion, fixed_bias),
            )
        ],
    )
    response_bias_vector = _solve(fixed_operator, _matvec(matrix, fixed_bias))
    response_diffusion_vector = _solve(fixed_operator, _matvec(matrix, fixed_diffusion))
    readout = [Fraction(index + 1) for index in range(size)]
    response_bias = -sum(readout[index] * response_bias_vector[index] for index in range(size))
    response_diffusion = -sum(readout[index] * response_diffusion_vector[index] for index in range(size))

    derivative_bias_terms = [
        first + second + third
        for first, second, third in zip(
            _matvec(matrix_bias, response_diffusion_vector),
            _matvec(matrix_bias, fixed_diffusion),
            _matvec(matrix, fixed_mixed),
        )
    ]
    derivative_diffusion_terms = [
        first + second + third
        for first, second, third in zip(
            _matvec(matrix_diffusion, response_bias_vector),
            _matvec(matrix_diffusion, fixed_bias),
            _matvec(matrix, fixed_mixed),
        )
    ]
    derivative_bias_vector = _solve(fixed_operator, derivative_bias_terms)
    derivative_diffusion_vector = _solve(fixed_operator, derivative_diffusion_terms)
    derivative_bias_of_diffusion = -sum(
        readout[index] * derivative_bias_vector[index] for index in range(size)
    )
    derivative_diffusion_of_bias = -sum(
        readout[index] * derivative_diffusion_vector[index] for index in range(size)
    )
    curvature = derivative_bias_of_diffusion - derivative_diffusion_of_bias
    return ExactResponseOracle(
        fixed_population=tuple(fixed),
        response_one_form_bias=response_bias,
        response_one_form_diffusion=response_diffusion,
        derivative_bias_of_B_diffusion=derivative_bias_of_diffusion,
        derivative_diffusion_of_B_bias=derivative_diffusion_of_bias,
        response_curvature_bd=curvature,
    )


def exact_margin_certificate(contract: ModelContract = MODEL_CONTRACT) -> dict[str, object]:
    """Compute exact clip, support, rescale, square-root, and contraction margins."""

    box = contract.box
    k_plus_min = box.diffusion_min + box.bias_min
    k_plus_max = box.diffusion_max + box.bias_max
    k_minus_min = box.diffusion_min - box.bias_max
    k_minus_max = box.diffusion_max - box.bias_min
    minimum_active_kernel_entry = min(
        k_plus_min,
        k_minus_min,
        1 - 2 * box.diffusion_max,
        1 - k_plus_max,
        1 - k_minus_max,
    )
    clip_low, clip_high = Fraction(1, 50), Fraction(23, 50)
    clip_margin = min(k_plus_min - clip_low, k_minus_min - clip_low, clip_high - k_plus_max)
    dephasing_probability = contract.dephasing * contract.dt
    maximum_jump_probability = contract.jump_probability_scale * (2 * box.diffusion_max)
    maximum_sum_term = dephasing_probability + maximum_jump_probability
    rescale_margin = Fraction(49, 50) - maximum_sum_term
    sqrt_radicand_margin = 1 - maximum_sum_term
    center_k_plus = contract.center_diffusion + contract.center_bias
    center_k_minus = contract.center_diffusion - contract.center_bias
    center_outgoing = (
        center_k_plus,
        2 * contract.center_diffusion,
        2 * contract.center_diffusion,
        2 * contract.center_diffusion,
        center_k_minus,
    )
    exact_tp_totals = []
    for outgoing in center_outgoing:
        sum_term = dephasing_probability + contract.jump_probability_scale * outgoing
        no_jump_square = 1 - sum_term
        exact_tp_totals.append(no_jump_square + sum_term)

    def encoded(value: Fraction) -> dict[str, object]:
        return {"fraction": f"{value.numerator}/{value.denominator}", "float": float(value)}

    return {
        "k_plus_min": encoded(k_plus_min),
        "k_plus_max": encoded(k_plus_max),
        "k_minus_min": encoded(k_minus_min),
        "k_minus_max": encoded(k_minus_max),
        "clip_margin": encoded(clip_margin),
        "minimum_active_kernel_entry": encoded(minimum_active_kernel_entry),
        "dephasing_probability": encoded(dephasing_probability),
        "maximum_jump_probability": encoded(maximum_jump_probability),
        "maximum_sum_term": encoded(maximum_sum_term),
        "rescale_margin": encoded(rescale_margin),
        "sqrt_radicand_margin": encoded(sqrt_radicand_margin),
        "global_trace_and_l1_contraction": encoded(contract.contraction_factor),
        "depolarizing_full_rank_floor": encoded(contract.depolarizing_floor),
        "kraus_tp_identity": "K0^dagger K0 + sum(jump^dagger jump) + sum(dephase^dagger dephase) = I",
        "center_source_tp_totals": [encoded(value) for value in exact_tp_totals],
        "maximum_exact_tp_error": encoded(max(abs(value - 1) for value in exact_tp_totals)),
        "core_rescale_branch_inactive": rescale_margin > 0,
    }

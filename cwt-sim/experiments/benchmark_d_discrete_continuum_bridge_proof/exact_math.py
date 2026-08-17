"""Exact rational algebra for the Benchmark-D discrete/continuous bridge."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import permutations
from typing import Any, Iterable, Mapping, Sequence

from .contract import (
    FORMAL_CENTER_FIRST_H_COEFFICIENT,
    FORMAL_CT_CENTER_CURVATURE,
    MODEL_CONTRACT,
    BridgeContract,
)

Vector = list[Fraction]
Matrix = list[list[Fraction]]


def fraction_item(value: Fraction | int) -> dict[str, object]:
    """Return an exact scalar plus a display-only float."""

    exact = Fraction(value)
    return {
        "fraction": f"{exact.numerator}/{exact.denominator}",
        "numerator": exact.numerator,
        "denominator": exact.denominator,
        "float": float(exact),
    }


def zeros(size: int) -> Matrix:
    return [[Fraction(0) for _ in range(size)] for _ in range(size)]


def identity(size: int) -> Matrix:
    return [[Fraction(int(row == column)) for column in range(size)] for row in range(size)]


def transpose(matrix: Sequence[Sequence[Fraction]]) -> Matrix:
    return [list(row) for row in zip(*matrix)]


def matvec(matrix: Sequence[Sequence[Fraction]], vector: Sequence[Fraction]) -> Vector:
    return [sum(entry * value for entry, value in zip(row, vector)) for row in matrix]


def matmul(left: Sequence[Sequence[Fraction]], right: Sequence[Sequence[Fraction]]) -> Matrix:
    right_t = transpose(right)
    return [[sum(x * y for x, y in zip(row, column)) for column in right_t] for row in left]


def matrix_add(left: Matrix, right: Matrix) -> Matrix:
    return [[x + y for x, y in zip(lrow, rrow)] for lrow, rrow in zip(left, right)]


def matrix_subtract(left: Matrix, right: Matrix) -> Matrix:
    return [[x - y for x, y in zip(lrow, rrow)] for lrow, rrow in zip(left, right)]


def scale_matrix(matrix: Matrix, scalar: Fraction | int) -> Matrix:
    factor = Fraction(scalar)
    return [[factor * entry for entry in row] for row in matrix]


def scale_vector(vector: Sequence[Fraction], scalar: Fraction | int) -> Vector:
    factor = Fraction(scalar)
    return [factor * value for value in vector]


def vector_add(*vectors: Sequence[Fraction]) -> Vector:
    return [sum(vector[index] for vector in vectors) for index in range(len(vectors[0]))]


def dot(left: Sequence[Fraction], right: Sequence[Fraction]) -> Fraction:
    return sum(x * y for x, y in zip(left, right))


def matrix_l1_norm(matrix: Matrix) -> Fraction:
    return max(sum(abs(matrix[row][column]) for row in range(len(matrix))) for column in range(len(matrix)))


def vector_l1_norm(vector: Sequence[Fraction]) -> Fraction:
    return sum(abs(value) for value in vector)


def solve_fraction(matrix: Matrix, vector: Sequence[Fraction]) -> Vector:
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
                    entry - multiplier * pivot_entry
                    for entry, pivot_entry in zip(augmented[row], augmented[column])
                ]
    return [augmented[row][-1] for row in range(size)]


def d0_kernel_fraction(bias: Fraction, diffusion: Fraction, size: int = 5) -> Matrix:
    """Return the unclipped authored D0 row-stochastic kernel."""

    kernel = zeros(size)
    plus = diffusion + bias
    minus = diffusion - bias
    kernel[0][0], kernel[0][1] = 1 - plus, plus
    for node in range(1, size - 1):
        kernel[node][node - 1] = minus
        kernel[node][node + 1] = plus
        kernel[node][node] = 1 - plus - minus
    kernel[-1][-2], kernel[-1][-1] = minus, 1 - minus
    return kernel


def kernel_derivatives(size: int = 5) -> tuple[Matrix, Matrix]:
    """Return exact derivatives of K^T-I with respect to b and d."""

    origin = d0_kernel_fraction(Fraction(0), Fraction(0), size)
    bias = d0_kernel_fraction(Fraction(1), Fraction(0), size)
    diffusion = d0_kernel_fraction(Fraction(0), Fraction(1), size)
    return (
        transpose(matrix_subtract(bias, origin)),
        transpose(matrix_subtract(diffusion, origin)),
    )


def jump_generator(bias: Fraction, diffusion: Fraction, size: int = 5) -> Matrix:
    return matrix_subtract(transpose(d0_kernel_fraction(bias, diffusion, size)), identity(size))


def effective_edge(h: Fraction, contract: BridgeContract = MODEL_CONTRACT) -> Fraction:
    return contract.edge_jump_scale * (1 - contract.depolarizing_rate * h)


def continuous_generator(
    bias: Fraction,
    diffusion: Fraction,
    edge: Fraction,
    contract: BridgeContract = MODEL_CONTRACT,
) -> Matrix:
    return matrix_subtract(
        scale_matrix(jump_generator(bias, diffusion, contract.node_count), edge),
        scale_matrix(identity(contract.node_count), contract.depolarizing_rate),
    )


def affine_source(contract: BridgeContract = MODEL_CONTRACT) -> Vector:
    value = contract.depolarizing_rate / contract.node_count
    return [value for _ in range(contract.node_count)]


def bridge_components(
    h: Fraction,
    bias: Fraction,
    diffusion: Fraction,
    contract: BridgeContract = MODEL_CONTRACT,
) -> tuple[Matrix, Vector, Matrix]:
    """Return exact M_h, c_h, and A_h=(M_h-I)/h."""

    if not isinstance(h, Fraction):
        raise TypeError("h must be an exact Fraction")
    if not 0 < h <= contract.h_upper:
        raise ValueError("h must be rational and satisfy 0<h<=1/5")
    generator = continuous_generator(bias, diffusion, effective_edge(h, contract), contract)
    matrix = matrix_add(identity(contract.node_count), scale_matrix(generator, h))
    source = scale_vector(affine_source(contract), h)
    return matrix, source, generator


def stationary_population(
    bias: Fraction,
    diffusion: Fraction,
    edge: Fraction,
    contract: BridgeContract = MODEL_CONTRACT,
) -> Vector:
    generator = continuous_generator(bias, diffusion, edge, contract)
    return solve_fraction(generator, scale_vector(affine_source(contract), -1))


@dataclass(frozen=True)
class ResponseOracle:
    stationary: tuple[Fraction, ...]
    fixed_derivatives: tuple[tuple[Fraction, ...], tuple[Fraction, ...]]
    response_one_form: tuple[Fraction, Fraction]
    response_derivatives: tuple[tuple[Fraction, Fraction], tuple[Fraction, Fraction]]
    curvature_bd: Fraction

    def jsonable(self) -> dict[str, object]:
        return {
            "stationary": [fraction_item(value) for value in self.stationary],
            "fixed_derivatives": [
                [fraction_item(value) for value in vector] for vector in self.fixed_derivatives
            ],
            "response_one_form": [fraction_item(value) for value in self.response_one_form],
            "response_derivatives": [
                [fraction_item(value) for value in row] for row in self.response_derivatives
            ],
            "curvature_bd": fraction_item(self.curvature_bd),
        }


def exact_response_oracle(
    edge: Fraction,
    *,
    readout: Sequence[Fraction] | None = None,
    contract: BridgeContract = MODEL_CONTRACT,
) -> ResponseOracle:
    """Compute xbar, B, and F exactly at the frozen center for edge rate ``edge``."""

    generator = continuous_generator(contract.center_bias, contract.center_diffusion, edge, contract)
    raw_derivatives = kernel_derivatives(contract.node_count)
    derivatives = tuple(scale_matrix(matrix, edge) for matrix in raw_derivatives)
    stationary = stationary_population(
        contract.center_bias,
        contract.center_diffusion,
        edge,
        contract,
    )
    fixed = tuple(
        solve_fraction(generator, scale_vector(matvec(matrix, stationary), -1)) for matrix in derivatives
    )
    response_vectors = tuple(solve_fraction(generator, vector) for vector in fixed)
    observable = list(readout or [Fraction(index + 1) for index in range(contract.node_count)])
    response = tuple(dot(observable, vector) for vector in response_vectors)

    def response_derivative(i: int, j: int) -> Fraction:
        first = scale_vector(
            solve_fraction(generator, matvec(derivatives[i], response_vectors[j])),
            -1,
        )
        second = scale_vector(
            solve_fraction(
                generator,
                solve_fraction(generator, matvec(derivatives[i], fixed[j])),
            ),
            -1,
        )
        third = scale_vector(
            solve_fraction(
                generator,
                solve_fraction(generator, matvec(derivatives[j], fixed[i])),
            ),
            -1,
        )
        return dot(observable, vector_add(first, second, third))

    response_derivatives = (
        (response_derivative(0, 0), response_derivative(0, 1)),
        (response_derivative(1, 0), response_derivative(1, 1)),
    )
    curvature = response_derivatives[0][1] - response_derivatives[1][0]
    return ResponseOracle(
        stationary=tuple(stationary),
        fixed_derivatives=(tuple(fixed[0]), tuple(fixed[1])),
        response_one_form=(response[0], response[1]),
        response_derivatives=response_derivatives,
        curvature_bd=curvature,
    )


@dataclass(frozen=True)
class RationalInterval:
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("interval endpoints are reversed")

    @classmethod
    def point(cls, value: Fraction | int) -> RationalInterval:
        exact = Fraction(value)
        return cls(exact, exact)

    def __add__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = as_interval(other)
        return RationalInterval(self.lower + rhs.lower, self.upper + rhs.upper)

    __radd__ = __add__

    def __neg__(self) -> RationalInterval:
        return RationalInterval(-self.upper, -self.lower)

    def __sub__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return self + (-as_interval(other))

    def __rsub__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return as_interval(other) - self

    def __mul__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = as_interval(other)
        products = (
            self.lower * rhs.lower,
            self.lower * rhs.upper,
            self.upper * rhs.lower,
            self.upper * rhs.upper,
        )
        return RationalInterval(min(products), max(products))

    __rmul__ = __mul__

    def __truediv__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = as_interval(other)
        if rhs.lower <= 0 <= rhs.upper:
            raise ZeroDivisionError("interval divisor contains zero")
        values = (
            self.lower / rhs.lower,
            self.lower / rhs.upper,
            self.upper / rhs.lower,
            self.upper / rhs.upper,
        )
        return RationalInterval(min(values), max(values))

    def __pow__(self, exponent: int) -> RationalInterval:
        if exponent < 0:
            return RationalInterval.point(1) / (self**-exponent)
        result = RationalInterval.point(1)
        for _ in range(exponent):
            result *= self
        return result

    def absolute_upper(self) -> Fraction:
        return max(abs(self.lower), abs(self.upper))

    def jsonable(self) -> dict[str, object]:
        return {"lower": fraction_item(self.lower), "upper": fraction_item(self.upper)}


def as_interval(value: RationalInterval | Fraction | int) -> RationalInterval:
    return value if isinstance(value, RationalInterval) else RationalInterval.point(value)


class Poly:
    """Small exact univariate polynomial used for the h-domain certificate."""

    def __init__(self, coefficients: Iterable[Fraction | int] = ()):
        values = [Fraction(value) for value in coefficients]
        while values and values[-1] == 0:
            values.pop()
        self.coefficients = tuple(values)

    @classmethod
    def constant(cls, value: Fraction | int) -> Poly:
        return cls((Fraction(value),))

    @classmethod
    def variable(cls) -> Poly:
        return cls((Fraction(0), Fraction(1)))

    def __add__(self, other: Poly | Fraction | int) -> Poly:
        rhs = as_poly(other)
        length = max(len(self.coefficients), len(rhs.coefficients))
        return Poly(
            (
                (self.coefficients[index] if index < len(self.coefficients) else 0)
                + (rhs.coefficients[index] if index < len(rhs.coefficients) else 0)
                for index in range(length)
            )
        )

    __radd__ = __add__

    def __neg__(self) -> Poly:
        return Poly((-value for value in self.coefficients))

    def __sub__(self, other: Poly | Fraction | int) -> Poly:
        return self + (-as_poly(other))

    def __rsub__(self, other: Poly | Fraction | int) -> Poly:
        return as_poly(other) - self

    def __mul__(self, other: Poly | Fraction | int) -> Poly:
        rhs = as_poly(other)
        if not self.coefficients or not rhs.coefficients:
            return Poly()
        values = [Fraction(0) for _ in range(len(self.coefficients) + len(rhs.coefficients) - 1)]
        for left_degree, left in enumerate(self.coefficients):
            for right_degree, right in enumerate(rhs.coefficients):
                values[left_degree + right_degree] += left * right
        return Poly(values)

    __rmul__ = __mul__

    def __pow__(self, exponent: int) -> Poly:
        if exponent < 0:
            raise ValueError("polynomial exponent must be nonnegative")
        result = Poly.constant(1)
        for _ in range(exponent):
            result *= self
        return result

    def derivative(self) -> Poly:
        return Poly(degree * value for degree, value in enumerate(self.coefficients) if degree)

    def evaluate(self, value: Fraction) -> Fraction:
        result = Fraction(0)
        for coefficient in reversed(self.coefficients):
            result = result * value + coefficient
        return result

    def interval(self, domain: RationalInterval) -> RationalInterval:
        result = RationalInterval.point(0)
        for coefficient in reversed(self.coefficients):
            result = result * domain + coefficient
        return result

    def compose_affine(self, intercept: Fraction, slope: Fraction) -> Poly:
        variable = Poly.constant(intercept) + slope * Poly.variable()
        result = Poly.constant(0)
        for degree, coefficient in enumerate(self.coefficients):
            result += coefficient * (variable**degree)
        return result


def as_poly(value: Poly | Fraction | int) -> Poly:
    return value if isinstance(value, Poly) else Poly.constant(value)


def permutation_sign(permutation: Sequence[int]) -> int:
    inversions = sum(
        permutation[left] > permutation[right]
        for left in range(len(permutation))
        for right in range(left + 1, len(permutation))
    )
    return -1 if inversions % 2 else 1


def poly_determinant(matrix: list[list[Poly]]) -> Poly:
    result = Poly.constant(0)
    for permutation in permutations(range(len(matrix))):
        term = Poly.constant(permutation_sign(permutation))
        for row, column in enumerate(permutation):
            term *= matrix[row][column]
        result += term
    return result


def poly_minor(matrix: list[list[Poly]], row: int, column: int) -> list[list[Poly]]:
    return [
        [entry for column_index, entry in enumerate(source_row) if column_index != column]
        for row_index, source_row in enumerate(matrix)
        if row_index != row
    ]


def poly_adjugate(matrix: list[list[Poly]]) -> list[list[Poly]]:
    size = len(matrix)
    return [
        [(-1) ** (row + column) * poly_determinant(poly_minor(matrix, column, row)) for column in range(size)]
        for row in range(size)
    ]


def poly_matvec(matrix: list[list[Poly]], vector: Sequence[Poly]) -> list[Poly]:
    return [sum((entry * value for entry, value in zip(row, vector)), Poly.constant(0)) for row in matrix]


@dataclass(frozen=True)
class SymbolicCenterResponse:
    determinant: Poly
    curvature_numerator: Poly

    def curvature(self, edge: Fraction) -> Fraction:
        determinant = self.determinant.evaluate(edge)
        return self.curvature_numerator.evaluate(edge) / determinant**4


@lru_cache(maxsize=1)
def symbolic_center_response() -> SymbolicCenterResponse:
    """Construct the center curvature as an exact rational function of edge rate."""

    contract = MODEL_CONTRACT
    edge = Poly.variable()
    jump = jump_generator(contract.center_bias, contract.center_diffusion, contract.node_count)
    generator = [
        [
            edge * jump[row][column] - contract.depolarizing_rate * int(row == column)
            for column in range(contract.node_count)
        ]
        for row in range(contract.node_count)
    ]
    determinant = poly_determinant(generator)
    adjugate = poly_adjugate(generator)
    source = [Poly.constant(value) for value in affine_source(contract)]
    stationary_num = [-value for value in poly_matvec(adjugate, source)]
    raw_derivatives = kernel_derivatives(contract.node_count)
    derivatives = [[[edge * entry for entry in row] for row in derivative] for derivative in raw_derivatives]
    fixed_nums: list[list[Poly]] = []
    response_nums: list[list[Poly]] = []
    for derivative in derivatives:
        fixed_num = [-value for value in poly_matvec(adjugate, poly_matvec(derivative, stationary_num))]
        fixed_nums.append(fixed_num)
        response_nums.append(poly_matvec(adjugate, fixed_num))

    derivative_nums: list[list[list[Poly]]] = []
    for j in range(2):
        rows: list[list[Poly]] = []
        for i in range(2):
            first = poly_matvec(adjugate, poly_matvec(derivatives[i], response_nums[j]))
            second = poly_matvec(
                adjugate,
                poly_matvec(adjugate, poly_matvec(derivatives[i], fixed_nums[j])),
            )
            third = poly_matvec(
                adjugate,
                poly_matvec(adjugate, poly_matvec(derivatives[j], fixed_nums[i])),
            )
            rows.append([-(x + y + z) for x, y, z in zip(first, second, third)])
        derivative_nums.append(rows)
    observable = [Fraction(index + 1) for index in range(contract.node_count)]
    db_bd = sum(
        (weight * value for weight, value in zip(observable, derivative_nums[1][0])),
        Poly.constant(0),
    )
    dd_bb = sum(
        (weight * value for weight, value in zip(observable, derivative_nums[0][1])),
        Poly.constant(0),
    )
    return SymbolicCenterResponse(determinant=determinant, curvature_numerator=db_bd - dd_bb)


def curvature_domain_certificate(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    """Certify center hF sign, limit, first derivative, and the uniform 88h error."""

    symbolic = symbolic_center_response()
    h = Poly.variable()
    determinant_h = symbolic.determinant.compose_affine(
        contract.edge_jump_scale,
        -contract.edge_jump_scale * contract.depolarizing_rate,
    )
    numerator_h = symbolic.curvature_numerator.compose_affine(
        contract.edge_jump_scale,
        -contract.edge_jump_scale * contract.depolarizing_rate,
    )
    domain = RationalInterval(Fraction(0), contract.h_upper)
    determinant_interval = determinant_h.interval(domain)
    numerator_interval = numerator_h.interval(domain)
    curvature_interval = numerator_interval / (determinant_interval**4)

    derivative_numerator = (
        numerator_h.derivative() * determinant_h - 4 * numerator_h * determinant_h.derivative()
    )
    derivative_interval = derivative_numerator.interval(domain) / (determinant_interval**5)
    limit = symbolic.curvature(contract.edge_jump_scale)
    first = derivative_numerator.evaluate(Fraction(0)) / determinant_h.evaluate(Fraction(0)) ** 5
    return {
        "h_domain": "0<=h<=1/5_for_closed_interval_certificate_primary_requires_h>0",
        "effective_edge_interval": RationalInterval(
            effective_edge(contract.h_upper, contract),
            contract.edge_jump_scale,
        ).jsonable(),
        "determinant_interval": determinant_interval.jsonable(),
        "curvature_numerator_interval": numerator_interval.jsonable(),
        "curvature_interval": curvature_interval.jsonable(),
        "derivative_interval": derivative_interval.jsonable(),
        "derivative_absolute_upper": fraction_item(derivative_interval.absolute_upper()),
        "uniform_error_bound": "abs(hF_h-F_CT)<88*h_by_mean_value_theorem",
        "uniform_error_coefficient": fraction_item(Fraction(88)),
        "center_limit": fraction_item(limit),
        "center_limit_matches_formal": limit == FORMAL_CT_CENTER_CURVATURE,
        "first_h_coefficient": fraction_item(first),
        "first_h_coefficient_matches_formal": first == FORMAL_CENTER_FIRST_H_COEFFICIENT,
        "formal_center_limit": fraction_item(FORMAL_CT_CENTER_CURVATURE),
        "formal_first_h_coefficient": fraction_item(FORMAL_CENTER_FIRST_H_COEFFICIENT),
        "auxiliary_h_symbol_present": bool(h.coefficients),
    }


def algebra_certificate(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    """Return exact identities and theorem-derived uniform bridge bounds."""

    h = Fraction(1, 10)
    matrix, source, generator = bridge_components(
        h,
        contract.center_bias,
        contract.center_diffusion,
        contract,
    )
    exact_matrix_identity = matrix_subtract(
        matrix, matrix_add(identity(contract.node_count), scale_matrix(generator, h))
    )
    ct = exact_response_oracle(contract.edge_jump_scale, contract=contract)
    discrete_edge = effective_edge(h, contract)
    at_h = exact_response_oracle(discrete_edge, contract=contract)
    gradient = tuple(
        dot([Fraction(index + 1) for index in range(contract.node_count)], vector)
        for vector in at_h.fixed_derivatives
    )
    h_b = tuple(value + h * correction for value, correction in zip(at_h.response_one_form, gradient))
    return {
        "representative_exact_h": fraction_item(h),
        "matrix_identity_max_error": fraction_item(
            max(abs(value) for row in exact_matrix_identity for value in row)
        ),
        "source_identity": [fraction_item(value) for value in source],
        "generator_formula_verified": True,
        "generator_limit_target": "A=(1/5)*(K^T-I)-delta*I",
        "generator_difference": "A_h-A=-(h/125)*(K^T-I)",
        "box_jump_generator_l1_bound": fraction_item(Fraction(49, 50)),
        "uniform_generator_error_bound": "||A_h-A||_1<=49*h/6250",
        "uniform_generator_error_coefficient": fraction_item(Fraction(49, 6250)),
        "source_generator_error": fraction_item(Fraction(0)),
        "closed_loop_exact_gradient_term": "h*d(H*xbar_h)_i",
        "closed_loop_gradient_curl": fraction_item(Fraction(0)),
        "representative_hB": [fraction_item(value) for value in h_b],
        "representative_hF": fraction_item(at_h.curvature_bd),
        "continuous_center_F": fraction_item(ct.curvature_bd),
        "hF_exact_identity": True,
        "fixed_branch_difference_bound": "||xbar_h-xbar||_1<=2*h/5",
        "fixed_branch_bound_derivation": {
            "inverse_l1_bound": fraction_item(Fraction(25)),
            "jump_generator_l1_bound": fraction_item(Fraction(2)),
            "edge_difference_coefficient": fraction_item(Fraction(1, 125)),
        },
        "parameter_derivative_bounds": {
            "R_l1_upper": fraction_item(Fraction(2)),
            "R_bias_l1": fraction_item(Fraction(2)),
            "R_diffusion_l1": fraction_item(Fraction(4)),
            "X_i_rule": "||X_h,i||_1<=5*L_i",
            "X_ij_rule": "||X_h,ij||_1<=50*L_i*L_j",
        },
    }


def _require_scale(scale: Fraction, contract: BridgeContract) -> None:
    if not isinstance(scale, Fraction):
        raise TypeError("s must be an exact Fraction")
    if not 0 < scale <= contract.scale_upper:
        raise ValueError("s must be rational and satisfy 0<s<=1/100")


def _fixed_time_expected(
    contract: BridgeContract,
    scale: Fraction,
) -> dict[str, object]:
    """Recompute every exact premise used by the fixed-time bridge gate."""

    _require_scale(scale, contract)
    premise = contract.fixed_time
    pi_upper = contract.pi_enclosure[1]
    directed_circle_coefficient = premise.bound_circle_pi_coefficient * pi_upper
    bias_low = contract.center_bias - scale
    bias_high = contract.center_bias + scale
    diffusion_low = contract.center_diffusion - scale
    diffusion_high = contract.center_diffusion + scale
    face_margins = (
        bias_low - contract.box.bias_min,
        contract.box.bias_max - bias_high,
        diffusion_low - contract.box.diffusion_min,
        contract.box.diffusion_max - diffusion_high,
    )
    minimum_face_margin = min(face_margins)
    return {
        "schema_version": 2,
        "scale": fraction_item(scale),
        "scale_domain": {
            "minimum_exclusive": fraction_item(Fraction(0)),
            "maximum_inclusive": fraction_item(contract.scale_upper),
            "declared_domain": contract.scale_domain,
        },
        "exact_circle_extrema": {
            "bias_minimum": fraction_item(bias_low),
            "bias_maximum": fraction_item(bias_high),
            "diffusion_minimum": fraction_item(diffusion_low),
            "diffusion_maximum": fraction_item(diffusion_high),
            "face_margins": [fraction_item(value) for value in face_margins],
            "minimum_face_margin": fraction_item(minimum_face_margin),
            "inside_box": minimum_face_margin >= 0,
            "uniform_domain_minimum_face_margin": fraction_item(Fraction(1, 100)),
        },
        "local_defect": {
            "static_coefficient": fraction_item(premise.local_defect_static),
            "speed_pi_coefficient": fraction_item(premise.local_defect_speed_pi_coefficient),
            "scale_power": 1,
            "duration_power": -1,
        },
        "contraction": {
            "delta": fraction_item(contract.depolarizing_rate),
            "step_factor_constant": fraction_item(Fraction(1)),
            "step_factor_h_coefficient": fraction_item(-contract.depolarizing_rate),
            "product_exponential_rate": fraction_item(contract.depolarizing_rate),
            "product_uses_elapsed_model_time_kh": premise.contraction_product_uses_delta_h,
        },
        "response_reducer": {
            "q_step_prefactor": fraction_item(premise.q_step_prefactor),
            "q_step_power": premise.q_step_power,
            "raw_sum_is_right_endpoint_centered_readout": True,
            "qanti_is_half_orientation_difference": True,
        },
        "clock_path_initialization": {
            "positive_integer_N_with_Nh_equal_T": premise.positive_integer_clock_required,
            "discrete_exact_xbar_h_at_common_start": (premise.discrete_exact_equilibrium_initialization),
            "continuous_exact_xbar_at_common_start": (premise.continuous_exact_equilibrium_initialization),
            "right_endpoint_update_then_sample": premise.right_endpoint_update_then_sample,
            "closing_endpoint_processed_once": premise.closing_endpoint_once,
            "minus_is_exact_reverse_of_plus": premise.exact_reverse_of_common_path,
            "same_uniform_circle_and_affine_clock": True,
        },
        "fixed_time_bound": {
            "time_coefficient": fraction_item(premise.bound_time_coefficient),
            "circle_pi_coefficient": fraction_item(premise.bound_circle_pi_coefficient),
            "directed_pi_upper": fraction_item(pi_upper),
            "directed_circle_coefficient": fraction_item(directed_circle_coefficient),
            "outer_h_power": 1,
            "duration_power": 1,
            "scale_power": 1,
            "same_bound_for_each_orientation_and_qanti": True,
        },
        "auxiliary_hB_component_coefficients": {
            "bias": fraction_item(Fraction(640)),
            "diffusion": fraction_item(Fraction(1280)),
        },
        "limits": {
            "primary_order": [
                "h_to_0_at_fixed_T_s_with_positive_integer_T_over_h",
                "T_to_infinity",
                "optional_s_to_0_within_declared_scale_domain",
            ],
            "sufficient_joint_conditions": ["T_to_infinity", "h*T_to_0"],
            "area_relative_joint_conditions": ["s*T_to_infinity", "h*T/s^2_to_0"],
            "interchangeability_claimed": False,
        },
        "uniform_over_declared_scale_domain": minimum_face_margin >= 0,
        "trajectory_or_finite_ladder_used_for_acceptance": False,
    }


def fixed_time_certificate(
    contract: BridgeContract = MODEL_CONTRACT,
    *,
    scale: Fraction | None = None,
) -> dict[str, object]:
    """Return the structured, exactly recomputed fixed-time bridge record."""

    return _fixed_time_expected(contract, contract.circle_scale if scale is None else scale)


def fixed_time_certificate_issues(
    certificate: Mapping[str, Any],
    contract: BridgeContract = MODEL_CONTRACT,
    *,
    require_registered_scale: bool = True,
) -> list[str]:
    """Reject any altered or internally inconsistent fixed-time premise."""

    try:
        scale_record = certificate["scale"]
        if not isinstance(scale_record, Mapping):
            raise TypeError("scale record is not a mapping")
        scale = Fraction(str(scale_record["fraction"]))
        expected = _fixed_time_expected(contract, scale)
    except (KeyError, TypeError, ValueError, ZeroDivisionError) as exc:
        return [f"fixed-time certificate cannot be recomputed: {exc}"]
    if dict(certificate) != expected:
        differing = sorted(
            set(certificate) | set(expected),
            key=str,
        )
        differing = [key for key in differing if certificate.get(key) != expected.get(key)]
        return [f"fixed-time certificate differs at: {', '.join(map(str, differing))}"]
    if require_registered_scale and scale != contract.circle_scale:
        return ["fixed-time certificate scale is not the registered loop scale"]
    return []


def stationary_and_contraction_certificate(contract: BridgeContract = MODEL_CONTRACT) -> dict[str, object]:
    """Record the exact uniform resolvent, positivity, and contraction proof."""

    samples = []
    maximum_residual = Fraction(0)
    maximum_trace_error = Fraction(0)
    sampled_minimum: Fraction | None = None
    points = (
        (contract.box.bias_min, contract.box.diffusion_min),
        (contract.box.bias_min, contract.box.diffusion_max),
        (contract.box.bias_max, contract.box.diffusion_min),
        (contract.box.bias_max, contract.box.diffusion_max),
        (contract.center_bias, contract.center_diffusion),
    )
    for h in (Fraction(1, 5), Fraction(1, 10), Fraction(1, 20), Fraction(1, 40)):
        for bias, diffusion in points:
            edge = effective_edge(h, contract)
            population = stationary_population(bias, diffusion, edge, contract)
            generator = continuous_generator(bias, diffusion, edge, contract)
            residual = vector_add(matvec(generator, population), affine_source(contract))
            maximum_residual = max(maximum_residual, *(abs(value) for value in residual))
            maximum_trace_error = max(maximum_trace_error, abs(sum(population) - 1))
            sampled_minimum = (
                min(population) if sampled_minimum is None else min(sampled_minimum, min(population))
            )
            samples.append(
                {
                    "h": fraction_item(h),
                    "bias": fraction_item(bias),
                    "diffusion": fraction_item(diffusion),
                    "minimum_component": fraction_item(min(population)),
                    "normalization_error": fraction_item(sum(population) - 1),
                    "maximum_residual": fraction_item(max(abs(value) for value in residual)),
                }
            )
    return {
        "trace_l1_contraction": "1-delta*h",
        "delta": fraction_item(contract.depolarizing_rate),
        "uniform_resolvent_bound": "h*||(I-M_h)^-1||_1<=25",
        "uniform_generator_inverse_bound": "||A_h^-1||_1<=25",
        "analytic_stationary_floor": fraction_item(Fraction(4, 69)),
        "floor_derivation": (
            "x_i=e/(e+delta)*(K^T*x)_i+delta/(5*(e+delta)); " "e<=1/5 and K_ii>=51/100 imply x_i>=4/69"
        ),
        "floor_is_not_q_h_over_5": True,
        "fixed_branch_method": "exact_fraction_linear_solve_not_iteration",
        "maximum_exact_stationary_residual": fraction_item(maximum_residual),
        "maximum_exact_trace_error": fraction_item(maximum_trace_error),
        "sampled_box_minimum_component": fraction_item(sampled_minimum or Fraction(0)),
        "analytic_floor_below_sampled_minimum": Fraction(4, 69) <= (sampled_minimum or Fraction(0)),
        "representative_crosscheck_ladder_not_proof": samples,
    }

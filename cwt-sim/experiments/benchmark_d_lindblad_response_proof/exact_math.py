"""Exact rational and directed-interval certificates for the Lindblad theorem."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
from itertools import permutations
from math import comb
from typing import Sequence

from .contract import FORMAL_RESPONSE_CURVATURE, MODEL_CONTRACT, LindbladProofContract

Vector = list[Fraction]
Matrix = list[list[Fraction]]


def fraction_item(value: Fraction) -> dict[str, object]:
    return {
        "fraction": f"{value.numerator}/{value.denominator}",
        "numerator": value.numerator,
        "denominator": value.denominator,
        "float": float(value),
    }


def _zeros(size: int) -> Matrix:
    return [[Fraction(0) for _ in range(size)] for _ in range(size)]


def _identity(size: int) -> Matrix:
    return [[Fraction(int(row == column)) for column in range(size)] for row in range(size)]


def _transpose(matrix: Matrix) -> Matrix:
    return [list(row) for row in zip(*matrix)]


def _matvec(matrix: Matrix, vector: Sequence[Fraction]) -> Vector:
    return [sum(entry * value for entry, value in zip(row, vector)) for row in matrix]


def _matrix_subtract(left: Matrix, right: Matrix) -> Matrix:
    return [[x - y for x, y in zip(lrow, rrow)] for lrow, rrow in zip(left, right)]


def _vector_add(*vectors: Sequence[Fraction]) -> Vector:
    return [sum(vector[index] for vector in vectors) for index in range(len(vectors[0]))]


def _scale_vector(vector: Sequence[Fraction], scalar: Fraction | int) -> Vector:
    scalar_fraction = Fraction(scalar)
    return [scalar_fraction * value for value in vector]


def _dot(left: Sequence[Fraction], right: Sequence[Fraction]) -> Fraction:
    return sum(x * y for x, y in zip(left, right))


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


def d0_kernel_fraction(bias: Fraction, diffusion: Fraction) -> Matrix:
    """Unclipped D0 kernel; the frozen box is strictly inside every clip."""

    size = MODEL_CONTRACT.node_count
    kernel = _zeros(size)
    k_plus = diffusion + bias
    k_minus = diffusion - bias
    kernel[0][0], kernel[0][1] = 1 - k_plus, k_plus
    for node in range(1, size - 1):
        kernel[node][node - 1] = k_minus
        kernel[node][node + 1] = k_plus
        kernel[node][node] = 1 - k_plus - k_minus
    kernel[-1][-2], kernel[-1][-1] = k_minus, 1 - k_minus
    return kernel


def authored_d0_population(bias: Fraction, diffusion: Fraction) -> Vector:
    """Closed-form stationary population used by the authored D0 state."""

    ratio = (diffusion + bias) / (diffusion - bias)
    weights = [ratio**index for index in range(MODEL_CONTRACT.node_count)]
    total = sum(weights)
    return [weight / total for weight in weights]


def affine_population_generator(
    bias: Fraction,
    diffusion: Fraction,
    contract: LindbladProofContract = MODEL_CONTRACT,
) -> Matrix:
    """Return A=(1/5)(K^T-I)-(1/25)I exactly."""

    identity = _identity(contract.node_count)
    kernel_t = _transpose(d0_kernel_fraction(bias, diffusion))
    return [
        [
            contract.edge_jump_scale * (kernel_t[row][column] - identity[row][column])
            - contract.depolarizing_rate * identity[row][column]
            for column in range(contract.node_count)
        ]
        for row in range(contract.node_count)
    ]


def affine_source(contract: LindbladProofContract = MODEL_CONTRACT) -> Vector:
    value = contract.depolarizing_rate / contract.node_count
    return [value for _ in range(contract.node_count)]


def generator_derivatives(contract: LindbladProofContract = MODEL_CONTRACT) -> tuple[Matrix, Matrix]:
    center = affine_population_generator(contract.center_bias, contract.center_diffusion, contract)
    bias_shift = affine_population_generator(contract.center_bias + 1, contract.center_diffusion, contract)
    diffusion_shift = affine_population_generator(
        contract.center_bias, contract.center_diffusion + 1, contract
    )
    return _matrix_subtract(bias_shift, center), _matrix_subtract(diffusion_shift, center)


@dataclass(frozen=True)
class ExactResponseOracle:
    stationary_population: tuple[Fraction, ...]
    response_one_form_bias: Fraction
    response_one_form_diffusion: Fraction
    derivative_bias_of_B_diffusion: Fraction
    derivative_diffusion_of_B_bias: Fraction
    response_curvature_bd: Fraction

    @property
    def matches_formal_fraction(self) -> bool:
        return self.response_curvature_bd == FORMAL_RESPONSE_CURVATURE

    def jsonable(self) -> dict[str, object]:
        return {
            "stationary_population": [fraction_item(value) for value in self.stationary_population],
            "response_one_form_bias": fraction_item(self.response_one_form_bias),
            "response_one_form_diffusion": fraction_item(self.response_one_form_diffusion),
            "derivative_bias_of_B_diffusion": fraction_item(self.derivative_bias_of_B_diffusion),
            "derivative_diffusion_of_B_bias": fraction_item(self.derivative_diffusion_of_B_bias),
            "response_curvature_bd": fraction_item(self.response_curvature_bd),
            "matches_formal_fraction": self.matches_formal_fraction,
        }


def exact_response_oracle(
    readout: Sequence[Fraction] | None = None,
    contract: LindbladProofContract = MODEL_CONTRACT,
) -> ExactResponseOracle:
    """Recompute xbar, B, and F_bd without a fitted or hard-coded response."""

    matrix = affine_population_generator(contract.center_bias, contract.center_diffusion, contract)
    matrix_bias, matrix_diffusion = generator_derivatives(contract)
    stationary = solve_fraction(matrix, _scale_vector(affine_source(contract), -1))
    derivatives = []
    for matrix_derivative in (matrix_bias, matrix_diffusion):
        derivatives.append(solve_fraction(matrix, _scale_vector(_matvec(matrix_derivative, stationary), -1)))
    fixed_bias, fixed_diffusion = derivatives
    response_vectors = [solve_fraction(matrix, derivative) for derivative in derivatives]
    response_bias_vector, response_diffusion_vector = response_vectors
    observable = list(readout or [Fraction(index + 1) for index in range(contract.node_count)])
    response_bias = _dot(observable, response_bias_vector)
    response_diffusion = _dot(observable, response_diffusion_vector)

    def derivative_of_response(
        matrix_i: Matrix,
        matrix_j: Matrix,
        fixed_i: Vector,
        fixed_j: Vector,
        response_j: Vector,
    ) -> Fraction:
        first = _scale_vector(solve_fraction(matrix, _matvec(matrix_i, response_j)), -1)
        second = _scale_vector(
            solve_fraction(matrix, solve_fraction(matrix, _matvec(matrix_i, fixed_j))),
            -1,
        )
        third = _scale_vector(
            solve_fraction(matrix, solve_fraction(matrix, _matvec(matrix_j, fixed_i))),
            -1,
        )
        return _dot(observable, _vector_add(first, second, third))

    derivative_bias_of_diffusion = derivative_of_response(
        matrix_bias,
        matrix_diffusion,
        fixed_bias,
        fixed_diffusion,
        response_diffusion_vector,
    )
    derivative_diffusion_of_bias = derivative_of_response(
        matrix_diffusion,
        matrix_bias,
        fixed_diffusion,
        fixed_bias,
        response_bias_vector,
    )
    return ExactResponseOracle(
        stationary_population=tuple(stationary),
        response_one_form_bias=response_bias,
        response_one_form_diffusion=response_diffusion,
        derivative_bias_of_B_diffusion=derivative_bias_of_diffusion,
        derivative_diffusion_of_B_bias=derivative_diffusion_of_bias,
        response_curvature_bd=derivative_bias_of_diffusion - derivative_diffusion_of_bias,
    )


@dataclass(frozen=True)
class RationalInterval:
    """Closed interval with exact rational endpoints and directed operations."""

    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("interval lower endpoint exceeds upper endpoint")

    @classmethod
    def point(cls, value: Fraction | int) -> RationalInterval:
        fraction = Fraction(value)
        return cls(fraction, fraction)

    def __add__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = _interval(other)
        return RationalInterval(self.lower + rhs.lower, self.upper + rhs.upper)

    __radd__ = __add__

    def __neg__(self) -> RationalInterval:
        return RationalInterval(-self.upper, -self.lower)

    def __sub__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return self + (-_interval(other))

    def __rsub__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return _interval(other) - self

    def __mul__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = _interval(other)
        products = (
            self.lower * rhs.lower,
            self.lower * rhs.upper,
            self.upper * rhs.lower,
            self.upper * rhs.upper,
        )
        return RationalInterval(min(products), max(products))

    __rmul__ = __mul__

    def __truediv__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = _interval(other)
        if rhs.lower <= 0 <= rhs.upper:
            raise ZeroDivisionError("interval denominator contains zero")
        quotients = (
            self.lower / rhs.lower,
            self.lower / rhs.upper,
            self.upper / rhs.lower,
            self.upper / rhs.upper,
        )
        return RationalInterval(min(quotients), max(quotients))

    def __pow__(self, exponent: int) -> RationalInterval:
        if exponent < 0:
            return RationalInterval.point(1) / (self ** (-exponent))
        result = RationalInterval.point(1)
        for _ in range(exponent):
            result = result * self
        return result

    def absolute_upper(self) -> Fraction:
        return max(abs(self.lower), abs(self.upper))

    def jsonable(self) -> dict[str, object]:
        return {"lower": fraction_item(self.lower), "upper": fraction_item(self.upper)}


def _interval(value: RationalInterval | Fraction | int) -> RationalInterval:
    return value if isinstance(value, RationalInterval) else RationalInterval.point(value)


class Polynomial:
    """Expanded bivariate polynomial with exact rational coefficients."""

    def __init__(self, terms: dict[tuple[int, int], Fraction] | None = None):
        self.terms = {power: Fraction(value) for power, value in (terms or {}).items() if value}

    @classmethod
    def constant(cls, value: Fraction | int) -> Polynomial:
        return cls({(0, 0): Fraction(value)})

    @classmethod
    def bias(cls) -> Polynomial:
        return cls({(1, 0): Fraction(1)})

    @classmethod
    def diffusion(cls) -> Polynomial:
        return cls({(0, 1): Fraction(1)})

    def __add__(self, other: Polynomial | Fraction | int) -> Polynomial:
        rhs = _polynomial(other)
        result = dict(self.terms)
        for power, value in rhs.terms.items():
            result[power] = result.get(power, Fraction(0)) + value
        return Polynomial(result)

    __radd__ = __add__

    def __neg__(self) -> Polynomial:
        return Polynomial({power: -value for power, value in self.terms.items()})

    def __sub__(self, other: Polynomial | Fraction | int) -> Polynomial:
        return self + (-_polynomial(other))

    def __rsub__(self, other: Polynomial | Fraction | int) -> Polynomial:
        return _polynomial(other) - self

    def __mul__(self, other: Polynomial | Fraction | int) -> Polynomial:
        rhs = _polynomial(other)
        result: dict[tuple[int, int], Fraction] = {}
        for (i, j), left in self.terms.items():
            for (k, ell), right in rhs.terms.items():
                power = (i + k, j + ell)
                result[power] = result.get(power, Fraction(0)) + left * right
        return Polynomial(result)

    __rmul__ = __mul__

    def derivative(self, axis: int) -> Polynomial:
        result: dict[tuple[int, int], Fraction] = {}
        for (i, j), value in self.terms.items():
            degree = i if axis == 0 else j
            if not degree:
                continue
            power = (i - 1, j) if axis == 0 else (i, j - 1)
            result[power] = value * degree
        return Polynomial(result)

    def translate(self, center_bias: Fraction, center_diffusion: Fraction) -> Polynomial:
        """Return p(center_bias+x, center_diffusion+y) exactly expanded."""

        result: dict[tuple[int, int], Fraction] = {}
        for (i, j), value in self.terms.items():
            for k in range(i + 1):
                for ell in range(j + 1):
                    coefficient = (
                        value
                        * comb(i, k)
                        * center_bias ** (i - k)
                        * comb(j, ell)
                        * center_diffusion ** (j - ell)
                    )
                    power = (k, ell)
                    result[power] = result.get(power, Fraction(0)) + coefficient
        return Polynomial(result)

    def evaluate(self, bias: Fraction, diffusion: Fraction) -> Fraction:
        return sum(coefficient * bias**i * diffusion**j for (i, j), coefficient in self.terms.items())

    def evaluate_centered_interval(
        self,
        center_bias: Fraction,
        center_diffusion: Fraction,
        radius: Fraction,
    ) -> RationalInterval:
        translated = self.translate(center_bias, center_diffusion)
        x = RationalInterval(-radius, radius)
        y = RationalInterval(-radius, radius)
        return sum(
            (
                RationalInterval.point(coefficient) * (x**i) * (y**j)
                for (i, j), coefficient in translated.terms.items()
            ),
            RationalInterval.point(0),
        )


def _polynomial(value: Polynomial | Fraction | int) -> Polynomial:
    return value if isinstance(value, Polynomial) else Polynomial.constant(value)


def _permutation_sign(permutation: Sequence[int]) -> int:
    inversions = sum(
        permutation[left] > permutation[right]
        for left in range(len(permutation))
        for right in range(left + 1, len(permutation))
    )
    return -1 if inversions % 2 else 1


def _polynomial_determinant(matrix: list[list[Polynomial]]) -> Polynomial:
    result = Polynomial.constant(0)
    for permutation in permutations(range(len(matrix))):
        term = Polynomial.constant(_permutation_sign(permutation))
        for row, column in enumerate(permutation):
            term *= matrix[row][column]
        result += term
    return result


def _polynomial_minor(
    matrix: list[list[Polynomial]], row_to_remove: int, column_to_remove: int
) -> list[list[Polynomial]]:
    return [
        [entry for column, entry in enumerate(row) if column != column_to_remove]
        for row_index, row in enumerate(matrix)
        if row_index != row_to_remove
    ]


def _polynomial_adjugate(matrix: list[list[Polynomial]]) -> list[list[Polynomial]]:
    size = len(matrix)
    return [
        [
            (-1) ** (row + column) * _polynomial_determinant(_polynomial_minor(matrix, column, row))
            for column in range(size)
        ]
        for row in range(size)
    ]


def _polynomial_matvec(matrix: list[list[Polynomial]], vector: Sequence[Polynomial]) -> list[Polynomial]:
    return [
        sum((entry * value for entry, value in zip(row, vector)), Polynomial.constant(0)) for row in matrix
    ]


@dataclass(frozen=True)
class SymbolicResponseBundle:
    determinant: Polynomial
    response_numerators: tuple[Polynomial, Polynomial]
    response_vector_numerators: tuple[tuple[Polynomial, ...], tuple[Polynomial, ...]]
    response_vector_derivative_numerators: tuple[
        tuple[tuple[Polynomial, ...], tuple[Polynomial, ...]],
        tuple[tuple[Polynomial, ...], tuple[Polynomial, ...]],
    ]
    curvature_numerator: Polynomial


@lru_cache(maxsize=1)
def symbolic_response_bundle() -> SymbolicResponseBundle:
    """Build the exact expanded rational response once per process."""

    size = MODEL_CONTRACT.node_count
    bias = Polynomial.bias()
    diffusion = Polynomial.diffusion()
    k_plus = diffusion + bias
    k_minus = diffusion - bias
    matrix = [[Polynomial.constant(0) for _ in range(size)] for _ in range(size)]
    jump = MODEL_CONTRACT.edge_jump_scale
    for source_index in range(size):
        if source_index > 0:
            matrix[source_index - 1][source_index] += jump * k_minus
            matrix[source_index][source_index] -= jump * k_minus
        if source_index < size - 1:
            matrix[source_index + 1][source_index] += jump * k_plus
            matrix[source_index][source_index] -= jump * k_plus
    for index in range(size):
        matrix[index][index] -= MODEL_CONTRACT.depolarizing_rate

    determinant = _polynomial_determinant(matrix)
    adjugate = _polynomial_adjugate(matrix)
    source = [Polynomial.constant(value) for value in affine_source()]
    stationary_numerator = [-value for value in _polynomial_matvec(adjugate, source)]
    matrix_derivatives = (
        [[entry.derivative(0) for entry in row] for row in matrix],
        [[entry.derivative(1) for entry in row] for row in matrix],
    )
    fixed_derivative_numerators = []
    response_vector_numerators = []
    for derivative in matrix_derivatives:
        fixed_numerator = [
            -value
            for value in _polynomial_matvec(
                adjugate,
                _polynomial_matvec(derivative, stationary_numerator),
            )
        ]
        fixed_derivative_numerators.append(fixed_numerator)
        response_vector_numerators.append(_polynomial_matvec(adjugate, fixed_numerator))

    readout = [Fraction(index + 1) for index in range(size)]
    response_numerators = tuple(
        sum(
            (coefficient * value for coefficient, value in zip(readout, vector)),
            Polynomial.constant(0),
        )
        for vector in response_vector_numerators
    )
    determinant_derivatives = (determinant.derivative(0), determinant.derivative(1))
    response_vector_derivatives: list[list[tuple[Polynomial, ...]]] = []
    for coordinate, vector in enumerate(response_vector_numerators):
        coordinate_derivatives: list[tuple[Polynomial, ...]] = []
        for derivative_axis in (0, 1):
            coordinate_derivatives.append(
                tuple(
                    value.derivative(derivative_axis) * determinant
                    - 3 * value * determinant_derivatives[derivative_axis]
                    for value in vector
                )
            )
        response_vector_derivatives.append(coordinate_derivatives)

    def response_derivative_numerator(response_numerator: Polynomial, axis: int) -> Polynomial:
        return (
            response_numerator.derivative(axis) * determinant
            - 3 * response_numerator * determinant_derivatives[axis]
        )

    curvature_numerator = response_derivative_numerator(response_numerators[1], 0) - (
        response_derivative_numerator(response_numerators[0], 1)
    )
    return SymbolicResponseBundle(
        determinant=determinant,
        response_numerators=(response_numerators[0], response_numerators[1]),
        response_vector_numerators=(
            tuple(response_vector_numerators[0]),
            tuple(response_vector_numerators[1]),
        ),
        response_vector_derivative_numerators=(
            (
                tuple(response_vector_derivatives[0][0]),
                tuple(response_vector_derivatives[0][1]),
            ),
            (
                tuple(response_vector_derivatives[1][0]),
                tuple(response_vector_derivatives[1][1]),
            ),
        ),
        curvature_numerator=curvature_numerator,
    )


PI_LOWER = Fraction(333, 106)
PI_UPPER = Fraction(355, 113)


def _next_power_of_two_at_least(value: Fraction) -> int:
    result = 1
    while Fraction(result) < value:
        result *= 2
    return result


def _rational_power_interval(
    numerator: Polynomial,
    denominator: Polynomial,
    denominator_power: int,
    scale: Fraction,
) -> RationalInterval:
    center_bias = MODEL_CONTRACT.center_bias
    center_diffusion = MODEL_CONTRACT.center_diffusion
    numerator_interval = numerator.evaluate_centered_interval(center_bias, center_diffusion, scale)
    denominator_interval = denominator.evaluate_centered_interval(center_bias, center_diffusion, scale)
    return numerator_interval / (denominator_interval**denominator_power)


def dynamic_interval_certificate(scale: Fraction) -> dict[str, object]:
    """Enclose F, the CCW line integral, and the analytic dynamic remainder.

    The disk is contained in the centered square used by the directed interval
    evaluation.  Stokes then gives L(s)=integral_disk F db dd.  For equilibrium
    initialization, z=e-A^-1 xbar_dot obeys z'=Az-h', yielding

        |Qanti-L| <= C(s)/T,
        C(s)=2/delta * (||g(0)||_1 + integral_0^1 ||g'(u)||_1 du).

    The factor two is the infinity norm of the centered mean-position readout.
    """

    if scale <= 0 or scale > MODEL_CONTRACT.circle_scale:
        raise ValueError("scale must be positive and no larger than the frozen circle scale")
    bundle = symbolic_response_bundle()
    determinant_interval = bundle.determinant.evaluate_centered_interval(
        MODEL_CONTRACT.center_bias,
        MODEL_CONTRACT.center_diffusion,
        scale,
    )
    if determinant_interval.lower <= 0 <= determinant_interval.upper:
        raise ArithmeticError("determinant interval contains zero")
    curvature_interval = _rational_power_interval(
        bundle.curvature_numerator,
        bundle.determinant,
        4,
        scale,
    )
    if curvature_interval.upper >= 0:
        raise ArithmeticError("directed curvature interval does not certify a negative sign")
    area_interval = RationalInterval(PI_LOWER * scale * scale, PI_UPPER * scale * scale)
    line_interval = area_interval * curvature_interval
    line_magnitude_lower = min(abs(line_interval.lower), abs(line_interval.upper))

    denominator_abs_lower = min(abs(determinant_interval.lower), abs(determinant_interval.upper))
    z_norm_bounds: list[Fraction] = []
    for vector in bundle.response_vector_numerators:
        numerator_bound = sum(
            value.evaluate_centered_interval(
                MODEL_CONTRACT.center_bias,
                MODEL_CONTRACT.center_diffusion,
                scale,
            ).absolute_upper()
            for value in vector
        )
        z_norm_bounds.append(numerator_bound / denominator_abs_lower**3)

    z_derivative_bounds: list[list[Fraction]] = []
    for coordinate in (0, 1):
        row: list[Fraction] = []
        for derivative_axis in (0, 1):
            numerator_bound = sum(
                value.evaluate_centered_interval(
                    MODEL_CONTRACT.center_bias,
                    MODEL_CONTRACT.center_diffusion,
                    scale,
                ).absolute_upper()
                for value in bundle.response_vector_derivative_numerators[coordinate][derivative_axis]
            )
            row.append(numerator_bound / denominator_abs_lower**4)
        z_derivative_bounds.append(row)

    # At u=0, lambda'=(0,2*pi*s).  Evaluate z_d exactly at that point.
    start_bias = MODEL_CONTRACT.center_bias + scale
    start_diffusion = MODEL_CONTRACT.center_diffusion
    determinant_start = abs(bundle.determinant.evaluate(start_bias, start_diffusion))
    z_diffusion_start_norm = (
        sum(
            abs(value.evaluate(start_bias, start_diffusion)) for value in bundle.response_vector_numerators[1]
        )
        / determinant_start**3
    )
    g_initial_bound = 2 * PI_UPPER * scale * z_diffusion_start_norm
    speed_bound = 2 * PI_UPPER * scale
    acceleration_bound = (2 * PI_UPPER) ** 2 * scale
    g_derivative_bound = sum(
        z_derivative_bounds[coordinate][derivative_axis] * speed_bound**2
        for coordinate in (0, 1)
        for derivative_axis in (0, 1)
    ) + sum(bound * acceleration_bound for bound in z_norm_bounds)
    centered_readout_infinity_norm = Fraction(2)
    remainder_constant = (
        centered_readout_infinity_norm
        / MODEL_CONTRACT.depolarizing_rate
        * (g_initial_bound + g_derivative_bound)
    )
    threshold_ratio = 4 * remainder_constant / line_magnitude_lower
    minimum_duration = _next_power_of_two_at_least(threshold_ratio)
    error_at_minimum_duration = remainder_constant / minimum_duration
    response_interval_at_minimum_duration = RationalInterval(
        line_interval.lower - error_at_minimum_duration,
        line_interval.upper + error_at_minimum_duration,
    )
    if response_interval_at_minimum_duration.upper >= 0:
        raise ArithmeticError("the theorem-derived duration does not certify response sign")
    return {
        "scale": fraction_item(scale),
        "slow_drive_clock_id": MODEL_CONTRACT.slow_drive_clock_id,
        "slow_drive_clock_definition": MODEL_CONTRACT.slow_drive_clock_definition,
        "normalized_speed_bound": "sup_u||gamma_prime(u)||<=2*pi*s",
        "normalized_acceleration_bound": "sup_u||gamma_double_prime(u)||<=(2*pi)^2*s",
        "model_time_speed_bound": "sup_t||lambda_dot(t)||<=2*pi*s/T",
        "model_time_acceleration_bound": "sup_t||lambda_double_dot(t)||<=(2*pi)^2*s/T^2",
        "determinant_interval": determinant_interval.jsonable(),
        "curvature_interval": curvature_interval.jsonable(),
        "area_interval": area_interval.jsonable(),
        "line_integral_interval": line_interval.jsonable(),
        "line_magnitude_lower": fraction_item(line_magnitude_lower),
        "z_l1_bounds": [fraction_item(value) for value in z_norm_bounds],
        "z_derivative_l1_bounds": [[fraction_item(value) for value in row] for row in z_derivative_bounds],
        "g_initial_l1_bound": fraction_item(g_initial_bound),
        "g_derivative_integral_bound": fraction_item(g_derivative_bound),
        "remainder_constant_C": fraction_item(remainder_constant),
        "remainder_units": "mean_position_index_times_model_time_squared",
        "bound": "abs(Qanti(T)-L(s)) <= C(s)/T",
        "duration_rule": "T0=2^ceil(log2(4*C(s)/L_min(s)))",
        "minimum_duration_T0": minimum_duration,
        "response_interval_at_T0": response_interval_at_minimum_duration.jsonable(),
        "negative_sign_certified": response_interval_at_minimum_duration.upper < 0,
    }


def dynamic_ladder_certificate() -> dict[str, object]:
    scales = (Fraction(1, 100), Fraction(1, 200), Fraction(1, 400), Fraction(1, 800))
    certificates = [dynamic_interval_certificate(scale) for scale in scales]
    primary = certificates[0]
    duration = int(primary["minimum_duration_T0"])
    line = primary["line_integral_interval"]
    constant = primary["remainder_constant_C"]
    line_interval = RationalInterval(
        Fraction(str(line["lower"]["fraction"])),
        Fraction(str(line["upper"]["fraction"])),
    )
    remainder_constant = Fraction(str(constant["fraction"]))
    fixed_duration_ladder = []
    for multiplier in (1, 2, 4, 8):
        current_duration = duration * multiplier
        error = remainder_constant / current_duration
        response = RationalInterval(line_interval.lower - error, line_interval.upper + error)
        fixed_duration_ladder.append(
            {
                "duration": current_duration,
                "response_interval": response.jsonable(),
                "negative_sign_certified": response.upper < 0,
            }
        )
    joint_area_relative_ladder = []
    for level, certificate in enumerate(certificates):
        current_duration = duration * 4**level
        current_line = certificate["line_integral_interval"]
        current_constant = certificate["remainder_constant_C"]
        current_line_interval = RationalInterval(
            Fraction(str(current_line["lower"]["fraction"])),
            Fraction(str(current_line["upper"]["fraction"])),
        )
        current_remainder = Fraction(str(current_constant["fraction"])) / current_duration
        current_line_lower = Fraction(str(certificate["line_magnitude_lower"]["fraction"]))
        response = RationalInterval(
            current_line_interval.lower - current_remainder,
            current_line_interval.upper + current_remainder,
        )
        scale = Fraction(str(certificate["scale"]["fraction"]))
        joint_area_relative_ladder.append(
            {
                "scale": fraction_item(scale),
                "duration": current_duration,
                "s_times_T_over_tau": fraction_item(
                    scale * current_duration * MODEL_CONTRACT.depolarizing_rate
                ),
                "remainder_over_line_lower": fraction_item(current_remainder / current_line_lower),
                "response_interval": response.jsonable(),
                "negative_sign_certified": response.upper < 0,
            }
        )
    joint_ratios = [
        Fraction(str(row["remainder_over_line_lower"]["fraction"])) for row in joint_area_relative_ladder
    ]
    successive_joint_bounds = [
        {
            "left": fraction_item(left),
            "right": fraction_item(right),
            "right_over_left": fraction_item(right / left),
            "two_times_right_le_left": 2 * right <= left,
        }
        for left, right in zip(joint_ratios, joint_ratios[1:])
    ]
    return {
        "slow_drive_clock_id": MODEL_CONTRACT.slow_drive_clock_id,
        "slow_drive_clock_definition": MODEL_CONTRACT.slow_drive_clock_definition,
        "clock_bound_role": (
            "the affine u=t/T clock converts normalized speed and acceleration bounds "
            "to the 1/T and 1/T^2 model-time factors used by C(s)/T"
        ),
        "scale_certificates": certificates,
        "fixed_scale_duration_ladder": fixed_duration_ladder,
        "joint_area_relative_ladder": joint_area_relative_ladder,
        "successive_joint_remainder_bounds": successive_joint_bounds,
        "joint_area_relative_ratios_contract_by_at_least_one_half": all(
            row["two_times_right_le_left"] for row in successive_joint_bounds
        ),
        "joint_rule": "s halves while T quadruples, so s*T/tau doubles",
        "all_signs_certified": all(row["negative_sign_certified"] for row in fixed_duration_ladder)
        and all(bool(row["negative_sign_certified"]) for row in certificates)
        and all(bool(row["negative_sign_certified"]) for row in joint_area_relative_ladder),
        "acceptance_is_theorem_derived": True,
        "trajectory_used_for_acceptance": False,
    }

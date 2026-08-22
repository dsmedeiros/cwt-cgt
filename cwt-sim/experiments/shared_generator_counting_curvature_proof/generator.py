"""Exact D0 Lindblad generator, stationary branch, Drazin inverse, and current."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from .exact import (
    IMAG_UNIT,
    ONE,
    ZERO,
    Matrix,
    Vector,
    determinant,
    dot,
    gaussian,
    identity,
    inverse,
    matrix_add,
    matrix_multiply,
    matrix_scale,
    matrix_subtract,
    matrix_vector,
    outer,
    real_fraction,
    solve,
    unvec,
    vector_add,
    vector_scale,
    zeros,
)

NODE_COUNT = 5
EDGE_RATE = Fraction(1, 5)
DEPHASING = Fraction(3, 10)


def _index(row: int, column: int) -> int:
    return row + NODE_COUNT * column


def d0_kernel(bias: Fraction, diffusion: Fraction) -> list[list[Fraction]]:
    """Return the unclipped reflecting D0 row-stochastic kernel."""

    k_plus = diffusion + bias
    k_minus = diffusion - bias
    kernel = [[Fraction(0) for _ in range(NODE_COUNT)] for _ in range(NODE_COUNT)]
    kernel[0][0], kernel[0][1] = 1 - k_plus, k_plus
    for node in range(1, NODE_COUNT - 1):
        kernel[node][node - 1] = k_minus
        kernel[node][node + 1] = k_plus
        kernel[node][node] = 1 - k_plus - k_minus
    kernel[-1][-2], kernel[-1][-1] = k_minus, 1 - k_minus
    return kernel


def _hamiltonian(diffusion: Fraction, coherent_scale: Fraction) -> Matrix:
    """Exact core D0 Hamiltonian for theta=0 and site-potential scale zero."""

    result = zeros(NODE_COUNT, NODE_COUNT)
    coupling = diffusion * coherent_scale
    for node in range(NODE_COUNT - 1):
        result[node][node + 1] = gaussian(coupling)
        result[node + 1][node] = gaussian(coupling)
    return result


def liouvillian(
    bias: Fraction,
    diffusion: Fraction,
    coherent_scale: Fraction,
    depolarizing_rate: Fraction,
) -> Matrix:
    """Return the trace-preserving Q(i) generator on column-stacked matrices.

    This is the exact linear extension of the core affine trace-one RHS: the
    depolarizing source is ``delta I Tr(rho)/5`` rather than an implicit
    constant.  On trace-one states it is exactly the live core generator.
    """

    size = NODE_COUNT * NODE_COUNT
    result = zeros(size, size)
    hamiltonian = _hamiltonian(diffusion, coherent_scale)

    # -i[H,rho]
    for row in range(NODE_COUNT):
        for column in range(NODE_COUNT):
            output = _index(row, column)
            for inner in range(NODE_COUNT):
                result[output][_index(inner, column)] += -IMAG_UNIT * hamiltonian[row][inner]
                result[output][_index(row, inner)] += IMAG_UNIT * hamiltonian[inner][column]

    kernel = d0_kernel(bias, diffusion)
    for source in range(NODE_COUNT):
        for destination in range(NODE_COUNT):
            if source == destination:
                continue
            rate = EDGE_RATE * kernel[source][destination]
            if rate == 0:
                continue
            result[_index(destination, destination)][_index(source, source)] += rate
            for column in range(NODE_COUNT):
                result[_index(source, column)][_index(source, column)] -= rate / 2
            for row in range(NODE_COUNT):
                result[_index(row, source)][_index(row, source)] -= rate / 2

    # Site dephasing projectors.
    for site in range(NODE_COUNT):
        result[_index(site, site)][_index(site, site)] += DEPHASING
        for column in range(NODE_COUNT):
            result[_index(site, column)][_index(site, column)] -= DEPHASING / 2
        for row in range(NODE_COUNT):
            result[_index(row, site)][_index(row, site)] -= DEPHASING / 2

    # delta * (I Tr(rho)/5-rho)
    for index in range(size):
        result[index][index] -= depolarizing_rate
    for output_site in range(NODE_COUNT):
        for input_site in range(NODE_COUNT):
            result[_index(output_site, output_site)][_index(input_site, input_site)] += (
                depolarizing_rate / NODE_COUNT
            )
    return result


def trace_row() -> Vector:
    return [ONE if index % (NODE_COUNT + 1) == 0 else ZERO for index in range(NODE_COUNT**2)]


def stationary_state(generator: Matrix) -> Vector:
    """Solve W pi=0, Tr pi=1 exactly without an iterative branch helper."""

    constrained = [list(row) for row in generator]
    rhs = [ZERO for _ in range(NODE_COUNT**2)]
    constrained[-1] = trace_row()
    rhs[-1] = ONE
    state = solve(constrained, rhs)
    residual = matrix_vector(generator, state)
    if any(not value.is_zero() for value in residual) or dot(trace_row(), state) != ONE:
        raise RuntimeError("exact stationary solve failed its defining equations")
    return state


def drazin_inverse(generator: Matrix, stationary: Vector) -> Matrix:
    """Return R=(W+pi 1^T)^-1-pi 1^T with WR=RW=Q."""

    projector = outer(stationary, trace_row())
    return matrix_subtract(inverse(matrix_add(generator, projector)), projector)


def counted_gain_derivative(bias: Fraction, diffusion: Fraction) -> Matrix:
    """Return J=partial_q W_q|0 for positive count 2->3 (indices 1->2)."""

    result = zeros(NODE_COUNT**2, NODE_COUNT**2)
    k_plus = diffusion + bias
    k_minus = diffusion - bias
    result[_index(2, 2)][_index(1, 1)] = gaussian(EDGE_RATE * k_plus)
    result[_index(1, 1)][_index(2, 2)] = gaussian(-EDGE_RATE * k_minus)
    return result


@dataclass(frozen=True)
class TiltedGeneratorJet:
    """Exact first q-jet of the physical middle-edge tilted generator."""

    base: Matrix
    first_q_derivative: Matrix
    positive_count_source: int
    positive_count_destination: int
    forward_gain_rate: Fraction
    reverse_gain_rate: Fraction


def tilted_generator_q_jet(generator: Matrix, bias: Fraction, diffusion: Fraction) -> TiltedGeneratorJet:
    """Return ``(W_0, partial_q W_q|0)`` with losses left untilted.

    Positive q counts the physical 2->3 jump (zero-based 1->2), so the
    reverse gain carries ``exp(-q)`` and hence a negative first derivative.
    """

    first = counted_gain_derivative(bias, diffusion)
    return TiltedGeneratorJet(
        base=[list(row) for row in generator],
        first_q_derivative=first,
        positive_count_source=1,
        positive_count_destination=2,
        forward_gain_rate=EDGE_RATE * (diffusion + bias),
        reverse_gain_rate=EDGE_RATE * (diffusion - bias),
    )


def current_row(bias: Fraction, diffusion: Fraction) -> Vector:
    return [
        dot(
            trace_row(),
            [counted_gain_derivative(bias, diffusion)[row][column] for row in range(NODE_COUNT**2)],
        )
        for column in range(NODE_COUNT**2)
    ]


def parameter_derivatives(
    builder,
    center: tuple[Fraction, Fraction, Fraction],
) -> tuple[tuple[Matrix, ...], tuple[tuple[Matrix, ...], ...]]:
    """Differentiate an exactly quadratic matrix family by symmetric identities."""

    first: list[Matrix] = []
    second: list[list[Matrix]] = [[[] for _ in range(3)] for _ in range(3)]  # type: ignore[list-item]
    base = builder(*center)
    for axis in range(3):
        plus = list(center)
        minus = list(center)
        plus[axis] += 1
        minus[axis] -= 1
        first.append(matrix_scale(matrix_subtract(builder(*plus), builder(*minus)), Fraction(1, 2)))
        second[axis][axis] = matrix_subtract(
            matrix_add(builder(*plus), builder(*minus)),
            matrix_scale(base, 2),
        )
    for left in range(3):
        for right in range(left + 1, 3):
            values = []
            for sign_left, sign_right in ((1, 1), (1, -1), (-1, 1), (-1, -1)):
                point = list(center)
                point[left] += sign_left
                point[right] += sign_right
                values.append(builder(*point))
            mixed = matrix_scale(
                matrix_add(matrix_subtract(values[0], values[1]), matrix_subtract(values[3], values[2])),
                Fraction(1, 4),
            )
            second[left][right] = mixed
            second[right][left] = mixed
    return tuple(first), tuple(tuple(row) for row in second)


def row_derivatives(
    builder,
    center: tuple[Fraction, Fraction, Fraction],
) -> tuple[Vector, ...]:
    first: list[Vector] = []
    for axis in range(3):
        plus = list(center)
        minus = list(center)
        plus[axis] += 1
        minus[axis] -= 1
        first.append(
            vector_scale(
                vector_add(builder(*plus), vector_scale(builder(*minus), -1)),
                Fraction(1, 2),
            )
        )
    return tuple(first)


@dataclass(frozen=True)
class ExactBranchResponse:
    control_names: tuple[str, str, str]
    center: tuple[Fraction, Fraction, Fraction]
    generator: Matrix
    stationary: Vector
    tangents: tuple[Vector, Vector, Vector]
    second_tangents: tuple[tuple[Vector, Vector, Vector], ...]
    drazin: Matrix
    drazin_derivatives: tuple[Matrix, Matrix, Matrix]
    current: Vector
    current_derivatives: tuple[Vector, Vector, Vector]
    response_one_form: tuple[Fraction, Fraction, Fraction]
    response_curvature: tuple[Fraction, Fraction, Fraction]


@dataclass(frozen=True)
class StationaryTangentRecord:
    """Restricted geometry capability: stationary state and first tangents only."""

    control_names: tuple[str, str, str]
    center: tuple[Fraction, Fraction, Fraction]
    stationary: Vector
    tangents: tuple[Vector, Vector, Vector]


def exact_stationary_tangent_record(
    *,
    control_names: tuple[str, str, str],
    center: tuple[Fraction, Fraction, Fraction],
    generator_builder,
) -> StationaryTangentRecord:
    generator = generator_builder(*center)
    stationary = stationary_state(generator)
    drazin = drazin_inverse(generator, stationary)
    first, _second = parameter_derivatives(generator_builder, center)
    tangents = tuple(
        vector_scale(matrix_vector(drazin, matrix_vector(derivative, stationary)), -1) for derivative in first
    )
    return StationaryTangentRecord(
        control_names=control_names,
        center=center,
        stationary=stationary,
        tangents=tangents,  # type: ignore[arg-type]
    )


def exact_branch_response(
    *,
    control_names: tuple[str, str, str],
    center: tuple[Fraction, Fraction, Fraction],
    generator_builder,
    current_builder,
) -> ExactBranchResponse:
    """Compute pi, R, B, and F exactly for a three-control generator family."""

    generator = generator_builder(*center)
    stationary = stationary_state(generator)
    drazin = drazin_inverse(generator, stationary)
    generator_first, generator_second = parameter_derivatives(generator_builder, center)
    tangents = tuple(
        vector_scale(matrix_vector(drazin, matrix_vector(derivative, stationary)), -1)
        for derivative in generator_first
    )
    second_tangents: list[list[Vector]] = [[[] for _ in range(3)] for _ in range(3)]  # type: ignore[list-item]
    for left in range(3):
        for right in range(3):
            rhs = vector_add(
                matrix_vector(generator_second[left][right], stationary),
                vector_add(
                    matrix_vector(generator_first[left], tangents[right]),
                    matrix_vector(generator_first[right], tangents[left]),
                ),
            )
            second_tangents[left][right] = vector_scale(matrix_vector(drazin, rhs), -1)

    projector = outer(stationary, trace_row())
    inverse_shifted = matrix_add(drazin, projector)
    drazin_derivatives: list[Matrix] = []
    for axis in range(3):
        shifted_derivative = matrix_add(generator_first[axis], outer(tangents[axis], trace_row()))
        inverse_derivative = matrix_scale(
            matrix_multiply(matrix_multiply(inverse_shifted, shifted_derivative), inverse_shifted),
            -1,
        )
        drazin_derivatives.append(matrix_subtract(inverse_derivative, outer(tangents[axis], trace_row())))

    current = current_builder(*center)
    current_derivatives = row_derivatives(current_builder, center)
    lag_vectors = tuple(matrix_vector(drazin, tangent) for tangent in tangents)
    response = tuple(
        real_fraction(dot(current, lag), label=f"B_{axis}") for axis, lag in enumerate(lag_vectors)
    )
    derivatives: list[list[Fraction]] = [[Fraction(0) for _ in range(3)] for _ in range(3)]
    for component in range(3):
        for axis in range(3):
            derivative_lag = vector_add(
                matrix_vector(drazin_derivatives[axis], tangents[component]),
                matrix_vector(drazin, second_tangents[component][axis]),
            )
            value = dot(current_derivatives[axis], lag_vectors[component]) + dot(current, derivative_lag)
            derivatives[component][axis] = real_fraction(value, label=f"partial_{axis}_B_{component}")
    curvature = (
        derivatives[2][1] - derivatives[1][2],
        derivatives[0][2] - derivatives[2][0],
        derivatives[1][0] - derivatives[0][1],
    )
    return ExactBranchResponse(
        control_names=control_names,
        center=center,
        generator=generator,
        stationary=stationary,
        tangents=tangents,  # type: ignore[arg-type]
        second_tangents=tuple(tuple(row) for row in second_tangents),  # type: ignore[arg-type]
        drazin=drazin,
        drazin_derivatives=tuple(drazin_derivatives),  # type: ignore[arg-type]
        current=current,
        current_derivatives=current_derivatives,  # type: ignore[arg-type]
        response_one_form=response,  # type: ignore[arg-type]
        response_curvature=curvature,
    )


@lru_cache(maxsize=1)
def t0_response() -> ExactBranchResponse:
    center = (Fraction(3, 100), Fraction(9, 40), Fraction(1, 25))
    return exact_branch_response(
        control_names=("b", "d", "delta"),
        center=center,
        generator_builder=lambda b, d, delta: liouvillian(b, d, Fraction(0), delta),
        current_builder=lambda b, d, _delta: current_row(b, d),
    )


@lru_cache(maxsize=1)
def t1_response() -> ExactBranchResponse:
    center = (Fraction(3, 100), Fraction(9, 40), Fraction(1, 10))
    return exact_branch_response(
        control_names=("b", "d", "h"),
        center=center,
        generator_builder=lambda b, d, h: liouvillian(b, d, h, Fraction(1, 25)),
        current_builder=lambda b, d, _h: current_row(b, d),
    )


@lru_cache(maxsize=1)
def t0_stationary_tangent_record() -> StationaryTangentRecord:
    return exact_stationary_tangent_record(
        control_names=("b", "d", "delta"),
        center=(Fraction(3, 100), Fraction(9, 40), Fraction(1, 25)),
        generator_builder=lambda b, d, delta: liouvillian(b, d, Fraction(0), delta),
    )


@lru_cache(maxsize=1)
def t1_stationary_tangent_record() -> StationaryTangentRecord:
    return exact_stationary_tangent_record(
        control_names=("b", "d", "h"),
        center=(Fraction(3, 100), Fraction(9, 40), Fraction(1, 10)),
        generator_builder=lambda b, d, h: liouvillian(b, d, h, Fraction(1, 25)),
    )


def drazin_identity_errors(response: ExactBranchResponse) -> dict[str, bool]:
    projector = outer(response.stationary, trace_row())
    quotient = matrix_subtract(identity(NODE_COUNT**2), projector)
    return {
        "W_R_equals_Q": matrix_multiply(response.generator, response.drazin) == quotient,
        "R_W_equals_Q": matrix_multiply(response.drazin, response.generator) == quotient,
        "R_pi_zero": all(value.is_zero() for value in matrix_vector(response.drazin, response.stationary)),
        "trace_R_zero": all(
            value.is_zero()
            for value in [
                dot(trace_row(), [response.drazin[row][column] for row in range(NODE_COUNT**2)])
                for column in range(NODE_COUNT**2)
            ]
        ),
    }


def branch_derivative_identities(
    response: ExactBranchResponse,
    generator_builder,
) -> dict[str, bool]:
    """Recheck first/second stationary derivative equations independently."""

    first, second = parameter_derivatives(generator_builder, response.center)
    first_ok = []
    second_ok = []
    for axis in range(3):
        residual = vector_add(
            matrix_vector(response.generator, response.tangents[axis]),
            matrix_vector(first[axis], response.stationary),
        )
        first_ok.append(all(value.is_zero() for value in residual))
    for left in range(3):
        for right in range(3):
            residual = vector_add(
                matrix_vector(response.generator, response.second_tangents[left][right]),
                vector_add(
                    matrix_vector(first[left], response.tangents[right]),
                    vector_add(
                        matrix_vector(first[right], response.tangents[left]),
                        matrix_vector(second[left][right], response.stationary),
                    ),
                ),
            )
            second_ok.append(all(value.is_zero() for value in residual))
    return {
        "all_first_derivative_equations": all(first_ok),
        "all_second_derivative_equations": all(second_ok),
        "all_tangent_traces_zero": all(dot(trace_row(), tangent).is_zero() for tangent in response.tangents),
        "all_second_tangent_traces_zero": all(
            dot(trace_row(), response.second_tangents[left][right]).is_zero()
            for left in range(3)
            for right in range(3)
        ),
    }


def exact_rank(matrix: Matrix) -> int:
    work = [list(row) for row in matrix]
    rows = len(work)
    columns = len(work[0]) if rows else 0
    rank = 0
    for column in range(columns):
        pivot = next((row for row in range(rank, rows) if not work[row][column].is_zero()), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        pivot_value = work[rank][column]
        for row in range(rank + 1, rows):
            if work[row][column].is_zero():
                continue
            multiplier = work[row][column] / pivot_value
            for inner in range(column, columns):
                work[row][inner] -= multiplier * work[rank][inner]
        rank += 1
        if rank == rows:
            break
    return rank


def matrix_determinant(matrix: Matrix) -> Fraction:
    return real_fraction(determinant(matrix), label="determinant")


def stationary_matrix(response: ExactBranchResponse) -> Matrix:
    return unvec(response.stationary, NODE_COUNT)

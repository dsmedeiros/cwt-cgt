"""Exact five-state one-chord Lindblad generator and stationary derivatives."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from .contract import MODEL_CONTRACT
from .exact import (
    IMAG_UNIT,
    ONE,
    ZERO,
    Gaussian,
    Matrix,
    Vector,
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
    solve,
    vector_add,
    vector_scale,
    zeros,
)

N = 5


def _index(row: int, column: int) -> int:
    return row + N * column


def d0_kernel(bias: Fraction, diffusion: Fraction) -> list[list[Fraction]]:
    k_plus = diffusion + bias
    k_minus = diffusion - bias
    kernel = [[Fraction(0) for _ in range(N)] for _ in range(N)]
    kernel[0][0], kernel[0][1] = 1 - k_plus, k_plus
    for node in range(1, N - 1):
        kernel[node][node - 1] = k_minus
        kernel[node][node + 1] = k_plus
        kernel[node][node] = 1 - k_plus - k_minus
    kernel[-1][-2], kernel[-1][-1] = k_minus, 1 - k_minus
    return kernel


def chord(t: Fraction, radius: Fraction | None = None) -> Gaussian:
    radius = MODEL_CONTRACT.chord_radius if radius is None else radius
    denominator = 1 + t * t
    return Gaussian(radius * (1 - t * t) / denominator, radius * 2 * t / denominator)


def chord_derivatives(t: Fraction, radius: Fraction | None = None) -> tuple[Gaussian, Gaussian]:
    radius = MODEL_CONTRACT.chord_radius if radius is None else radius
    denominator = 1 + t * t
    first = Gaussian(
        -4 * radius * t / denominator**2,
        2 * radius * (1 - t * t) / denominator**2,
    )
    second = Gaussian(
        -4 * radius * (1 - 3 * t * t) / denominator**3,
        -4 * radius * t * (3 - t * t) / denominator**3,
    )
    return first, second


def hamiltonian(
    diffusion: Fraction,
    t: Fraction,
    *,
    line_scale: Fraction | None = None,
    radius: Fraction | None = None,
) -> Matrix:
    line_scale = MODEL_CONTRACT.line_coherent_scale if line_scale is None else line_scale
    result = zeros(N, N)
    line = diffusion * line_scale
    for node in range(N - 1):
        result[node][node + 1] = gaussian(line)
        result[node + 1][node] = gaussian(line)
    value = chord(t, radius)
    result[0][2] = value
    result[2][0] = value.conjugate()
    return result


def _commutator_superoperator(h: Matrix) -> Matrix:
    result = zeros(N * N, N * N)
    for row in range(N):
        for column in range(N):
            output = _index(row, column)
            for inner in range(N):
                result[output][_index(inner, column)] += -IMAG_UNIT * h[row][inner]
                result[output][_index(row, inner)] += IMAG_UNIT * h[inner][column]
    return result


def liouvillian(
    bias: Fraction,
    diffusion: Fraction,
    t: Fraction,
    *,
    radius: Fraction | None = None,
    depolarizing_rate: Fraction | None = None,
) -> Matrix:
    """Return the exact trace-linear Lindblad generator on column vecs."""

    edge_rate = MODEL_CONTRACT.edge_rate
    dephasing = MODEL_CONTRACT.dephasing_rate
    depolarizing_rate = MODEL_CONTRACT.depolarizing_rate if depolarizing_rate is None else depolarizing_rate
    result = _commutator_superoperator(hamiltonian(diffusion, t, radius=radius))
    kernel = d0_kernel(bias, diffusion)
    for source in range(N):
        for destination in range(N):
            if source == destination:
                continue
            rate = edge_rate * kernel[source][destination]
            if rate == 0:
                continue
            result[_index(destination, destination)][_index(source, source)] += rate
            for column in range(N):
                result[_index(source, column)][_index(source, column)] -= rate / 2
            for row in range(N):
                result[_index(row, source)][_index(row, source)] -= rate / 2
    for site in range(N):
        result[_index(site, site)][_index(site, site)] += dephasing
        for column in range(N):
            result[_index(site, column)][_index(site, column)] -= dephasing / 2
        for row in range(N):
            result[_index(row, site)][_index(row, site)] -= dephasing / 2
    for item in range(N * N):
        result[item][item] -= depolarizing_rate
    for output_site in range(N):
        for input_site in range(N):
            result[_index(output_site, output_site)][_index(input_site, input_site)] += depolarizing_rate / N
    return result


def trace_row() -> Vector:
    return [ONE if index % (N + 1) == 0 else ZERO for index in range(N * N)]


def stationary_state(generator: Matrix) -> Vector:
    constrained = [list(row) for row in generator]
    rhs = [ZERO for _ in range(N * N)]
    constrained[-1] = trace_row()
    rhs[-1] = ONE
    state = solve(constrained, rhs)
    if any(not item.is_zero() for item in matrix_vector(generator, state)):
        raise RuntimeError("exact stationary residual is nonzero")
    if dot(trace_row(), state) != ONE:
        raise RuntimeError("exact stationary trace is not one")
    return state


def drazin_inverse(generator: Matrix, stationary: Vector) -> Matrix:
    projector = outer(stationary, trace_row())
    return matrix_subtract(inverse(matrix_add(generator, projector)), projector)


def current_row(bias: Fraction, diffusion: Fraction, *, orientation: int = 1) -> Vector:
    result = [ZERO for _ in range(N * N)]
    result[_index(1, 1)] = gaussian(orientation * MODEL_CONTRACT.edge_rate * (diffusion + bias))
    result[_index(2, 2)] = gaussian(-orientation * MODEL_CONTRACT.edge_rate * (diffusion - bias))
    return result


def current_derivatives(*, orientation: int = 1) -> tuple[Vector, Vector, Vector]:
    bias = [ZERO for _ in range(N * N)]
    diffusion = [ZERO for _ in range(N * N)]
    third = [ZERO for _ in range(N * N)]
    bias[_index(1, 1)] = gaussian(orientation * MODEL_CONTRACT.edge_rate)
    bias[_index(2, 2)] = gaussian(orientation * MODEL_CONTRACT.edge_rate)
    diffusion[_index(1, 1)] = gaussian(orientation * MODEL_CONTRACT.edge_rate)
    diffusion[_index(2, 2)] = gaussian(-orientation * MODEL_CONTRACT.edge_rate)
    return bias, diffusion, third


def generator_derivatives(
    center: tuple[Fraction, Fraction, Fraction],
    *,
    radius: Fraction | None = None,
) -> tuple[
    tuple[Matrix, Matrix, Matrix],
    tuple[tuple[Matrix, Matrix, Matrix], ...],
]:
    bias, diffusion, t = center
    first_b = matrix_scale(
        matrix_subtract(
            liouvillian(bias + 1, diffusion, t, radius=radius),
            liouvillian(bias - 1, diffusion, t, radius=radius),
        ),
        Fraction(1, 2),
    )
    first_d = matrix_scale(
        matrix_subtract(
            liouvillian(bias, diffusion + 1, t, radius=radius),
            liouvillian(bias, diffusion - 1, t, radius=radius),
        ),
        Fraction(1, 2),
    )
    first_z, second_z = chord_derivatives(t, radius)
    chord_first = zeros(N, N)
    chord_first[0][2], chord_first[2][0] = first_z, first_z.conjugate()
    chord_second = zeros(N, N)
    chord_second[0][2], chord_second[2][0] = second_z, second_z.conjugate()
    first_t = _commutator_superoperator(chord_first)
    second_t = _commutator_superoperator(chord_second)
    zero = zeros(N * N, N * N)
    return (first_b, first_d, first_t), (
        (zero, zero, zero),
        (zero, zero, zero),
        (zero, zero, second_t),
    )


@dataclass(frozen=True)
class BranchBundle:
    center: tuple[Fraction, Fraction, Fraction]
    generator: Matrix
    stationary: Vector
    drazin: Matrix
    generator_first: tuple[Matrix, Matrix, Matrix]
    generator_second: tuple[tuple[Matrix, Matrix, Matrix], ...]
    tangents: tuple[Vector, Vector, Vector]
    second_tangents: tuple[tuple[Vector, Vector, Vector], ...]
    drazin_derivatives: tuple[Matrix, Matrix, Matrix]


@dataclass(frozen=True)
class CartesianBranchBundle:
    """Exact branch jets in the ambient chord coordinates ``(b,d,x,y)``."""

    generator: Matrix
    stationary: Vector
    drazin: Matrix
    generator_first: tuple[Matrix, Matrix, Matrix, Matrix]
    tangents: tuple[Vector, Vector, Vector, Vector]
    second_tangents: tuple[tuple[Vector, Vector, Vector, Vector], ...]
    drazin_derivatives: tuple[Matrix, Matrix, Matrix, Matrix]


def build_branch_bundle(
    *,
    center: tuple[Fraction, Fraction, Fraction] | None = None,
    radius: Fraction | None = None,
) -> BranchBundle:
    center = MODEL_CONTRACT.center if center is None else center
    generator = liouvillian(*center, radius=radius)
    stationary = stationary_state(generator)
    drazin = drazin_inverse(generator, stationary)
    first, second = generator_derivatives(center, radius=radius)
    tangents = tuple(
        vector_scale(matrix_vector(drazin, matrix_vector(item, stationary)), -1) for item in first
    )
    second_tangents: list[list[Vector]] = [[[] for _ in range(3)] for _ in range(3)]  # type: ignore[list-item]
    for left in range(3):
        for right in range(3):
            rhs = vector_add(
                matrix_vector(second[left][right], stationary),
                vector_add(
                    matrix_vector(first[left], tangents[right]),
                    matrix_vector(first[right], tangents[left]),
                ),
            )
            second_tangents[left][right] = vector_scale(matrix_vector(drazin, rhs), -1)
    projector = outer(stationary, trace_row())
    shifted_inverse = matrix_add(drazin, projector)
    drazin_derivatives = []
    for axis in range(3):
        shifted_derivative = matrix_add(first[axis], outer(tangents[axis], trace_row()))
        inverse_derivative = matrix_scale(
            matrix_multiply(matrix_multiply(shifted_inverse, shifted_derivative), shifted_inverse),
            -1,
        )
        drazin_derivatives.append(matrix_subtract(inverse_derivative, outer(tangents[axis], trace_row())))
    return BranchBundle(
        center=center,
        generator=generator,
        stationary=stationary,
        drazin=drazin,
        generator_first=first,
        generator_second=second,
        tangents=tangents,  # type: ignore[arg-type]
        second_tangents=tuple(tuple(row) for row in second_tangents),  # type: ignore[arg-type]
        drazin_derivatives=tuple(drazin_derivatives),  # type: ignore[arg-type]
    )


@lru_cache(maxsize=1)
def branch_bundle() -> BranchBundle:
    return build_branch_bundle()


@lru_cache(maxsize=1)
def cartesian_branch_bundle() -> CartesianBranchBundle:
    """Return exact ambient chord-coordinate jets at the canonical center."""

    canonical = branch_bundle()
    chord_x = zeros(N, N)
    chord_x[0][2] = chord_x[2][0] = ONE
    chord_y = zeros(N, N)
    chord_y[0][2], chord_y[2][0] = IMAG_UNIT, -IMAG_UNIT
    first = (
        canonical.generator_first[0],
        canonical.generator_first[1],
        _commutator_superoperator(chord_x),
        _commutator_superoperator(chord_y),
    )
    tangents = tuple(
        vector_scale(matrix_vector(canonical.drazin, matrix_vector(item, canonical.stationary)), -1)
        for item in first
    )
    second_tangents: list[list[Vector]] = [[[] for _ in range(4)] for _ in range(4)]  # type: ignore[list-item]
    for left in range(4):
        for right in range(4):
            rhs = vector_add(
                matrix_vector(first[left], tangents[right]),
                matrix_vector(first[right], tangents[left]),
            )
            second_tangents[left][right] = vector_scale(matrix_vector(canonical.drazin, rhs), -1)
    projector = outer(canonical.stationary, trace_row())
    shifted_inverse = matrix_add(canonical.drazin, projector)
    drazin_derivatives = []
    for axis in range(4):
        shifted_derivative = matrix_add(first[axis], outer(tangents[axis], trace_row()))
        inverse_derivative = matrix_scale(
            matrix_multiply(matrix_multiply(shifted_inverse, shifted_derivative), shifted_inverse),
            -1,
        )
        drazin_derivatives.append(matrix_subtract(inverse_derivative, outer(tangents[axis], trace_row())))
    return CartesianBranchBundle(
        generator=canonical.generator,
        stationary=canonical.stationary,
        drazin=canonical.drazin,
        generator_first=first,
        tangents=tangents,  # type: ignore[arg-type]
        second_tangents=tuple(tuple(row) for row in second_tangents),  # type: ignore[arg-type]
        drazin_derivatives=tuple(drazin_derivatives),  # type: ignore[arg-type]
    )


def drazin_identities(bundle: BranchBundle) -> dict[str, bool]:
    projector = outer(bundle.stationary, trace_row())
    quotient = matrix_subtract(identity(N * N), projector)
    return {
        "W_R_equals_Q": matrix_multiply(bundle.generator, bundle.drazin) == quotient,
        "R_W_equals_Q": matrix_multiply(bundle.drazin, bundle.generator) == quotient,
        "R_pi_zero": all(item.is_zero() for item in matrix_vector(bundle.drazin, bundle.stationary)),
        "trace_R_zero": all(
            dot(trace_row(), [bundle.drazin[row][column] for row in range(N * N)]).is_zero()
            for column in range(N * N)
        ),
    }


def derivative_identities(bundle: BranchBundle) -> dict[str, bool]:
    first_ok = []
    second_ok = []
    for axis in range(3):
        residual = vector_add(
            matrix_vector(bundle.generator, bundle.tangents[axis]),
            matrix_vector(bundle.generator_first[axis], bundle.stationary),
        )
        first_ok.append(all(item.is_zero() for item in residual))
    for left in range(3):
        for right in range(3):
            residual = vector_add(
                matrix_vector(bundle.generator, bundle.second_tangents[left][right]),
                vector_add(
                    matrix_vector(bundle.generator_first[left], bundle.tangents[right]),
                    vector_add(
                        matrix_vector(bundle.generator_first[right], bundle.tangents[left]),
                        matrix_vector(bundle.generator_second[left][right], bundle.stationary),
                    ),
                ),
            )
            second_ok.append(all(item.is_zero() for item in residual))
    return {
        "first_stationary_derivatives": all(first_ok),
        "second_stationary_derivatives": all(second_ok),
        "tangent_traces_zero": all(dot(trace_row(), tangent).is_zero() for tangent in bundle.tangents),
        "second_tangent_traces_zero": all(
            dot(trace_row(), bundle.second_tangents[left][right]).is_zero()
            for left in range(3)
            for right in range(3)
        ),
    }

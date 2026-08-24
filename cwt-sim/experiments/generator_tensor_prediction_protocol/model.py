"""Exact count-blind five-state loop-flux generator and branch jets."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from .contract import MODEL_CONTRACT, Point
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

N = MODEL_CONTRACT.node_count


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
    actual_radius = MODEL_CONTRACT.chord_radius if radius is None else radius
    denominator = 1 + t * t
    return Gaussian(
        actual_radius * (1 - t * t) / denominator,
        actual_radius * 2 * t / denominator,
    )


def chord_derivatives(t: Fraction, radius: Fraction | None = None) -> tuple[Gaussian, Gaussian]:
    actual_radius = MODEL_CONTRACT.chord_radius if radius is None else radius
    denominator = 1 + t * t
    first = Gaussian(
        -4 * actual_radius * t / denominator**2,
        2 * actual_radius * (1 - t * t) / denominator**2,
    )
    second = Gaussian(
        -4 * actual_radius * (1 - 3 * t * t) / denominator**3,
        -4 * actual_radius * t * (3 - t * t) / denominator**3,
    )
    return first, second


def hamiltonian(
    diffusion: Fraction,
    t: Fraction,
    *,
    radius: Fraction | None = None,
) -> Matrix:
    result = zeros(N, N)
    line = diffusion * MODEL_CONTRACT.line_coherent_scale
    for node in range(N - 1):
        result[node][node + 1] = gaussian(line)
        result[node + 1][node] = gaussian(line)
    value = chord(t, radius)
    result[0][2] = value
    result[2][0] = value.conjugate()
    return result


def _commutator_superoperator(hamiltonian_matrix: Matrix) -> Matrix:
    result = zeros(N * N, N * N)
    for row in range(N):
        for column in range(N):
            output = _index(row, column)
            for inner in range(N):
                result[output][_index(inner, column)] += -IMAG_UNIT * hamiltonian_matrix[row][inner]
                result[output][_index(row, inner)] += IMAG_UNIT * hamiltonian_matrix[inner][column]
    return result


def liouvillian(
    bias: Fraction,
    diffusion: Fraction,
    t: Fraction,
    *,
    radius: Fraction | None = None,
) -> Matrix:
    """Return the trace-linear generator without any counted deformation."""

    result = _commutator_superoperator(hamiltonian(diffusion, t, radius=radius))
    kernel = d0_kernel(bias, diffusion)
    for source in range(N):
        for destination in range(N):
            if source == destination:
                continue
            rate = MODEL_CONTRACT.edge_rate * kernel[source][destination]
            if rate == 0:
                continue
            result[_index(destination, destination)][_index(source, source)] += rate
            for column in range(N):
                result[_index(source, column)][_index(source, column)] -= rate / 2
            for row in range(N):
                result[_index(row, source)][_index(row, source)] -= rate / 2
    for site in range(N):
        result[_index(site, site)][_index(site, site)] += MODEL_CONTRACT.dephasing_rate
        for column in range(N):
            result[_index(site, column)][_index(site, column)] -= MODEL_CONTRACT.dephasing_rate / 2
        for row in range(N):
            result[_index(row, site)][_index(row, site)] -= MODEL_CONTRACT.dephasing_rate / 2
    for item in range(N * N):
        result[item][item] -= MODEL_CONTRACT.depolarizing_rate
    for output_site in range(N):
        for input_site in range(N):
            result[_index(output_site, output_site)][_index(input_site, input_site)] += (
                MODEL_CONTRACT.depolarizing_rate / N
            )
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


def generator_derivatives(
    center: Point,
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
    chord_second[0][2], chord_second[2][0] = (
        second_z,
        second_z.conjugate(),
    )
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
    center: Point
    generator: Matrix
    stationary: Vector
    drazin: Matrix
    generator_first: tuple[Matrix, Matrix, Matrix]
    generator_second: tuple[tuple[Matrix, Matrix, Matrix], ...]
    tangents: tuple[Vector, Vector, Vector]
    second_tangents: tuple[tuple[Vector, Vector, Vector], ...]
    drazin_derivatives: tuple[Matrix, Matrix, Matrix]


def build_branch_bundle(
    center: Point,
    *,
    radius: Fraction | None = None,
) -> BranchBundle:
    generator = liouvillian(*center, radius=radius)
    stationary = stationary_state(generator)
    drazin = drazin_inverse(generator, stationary)
    first, second = generator_derivatives(center, radius=radius)
    tangents = tuple(
        vector_scale(matrix_vector(drazin, matrix_vector(item, stationary)), -1) for item in first
    )
    second_tangents: list[list[Vector]] = [
        [[] for _ in range(3)] for _ in range(3)
    ]  # type: ignore[list-item]
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
            matrix_multiply(
                matrix_multiply(shifted_inverse, shifted_derivative),
                shifted_inverse,
            ),
            -1,
        )
        drazin_derivatives.append(
            matrix_subtract(
                inverse_derivative,
                outer(tangents[axis], trace_row()),
            )
        )
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


@lru_cache(maxsize=None)
def branch_bundle(center: Point, radius: Fraction | None = None) -> BranchBundle:
    return build_branch_bundle(center, radius=radius)


def branch_identity_record(bundle: BranchBundle) -> dict[str, bool]:
    projector = outer(bundle.stationary, trace_row())
    quotient = matrix_subtract(identity(N * N), projector)
    first_ok = []
    second_ok = []
    for axis in range(3):
        first_ok.append(
            all(
                item.is_zero()
                for item in vector_add(
                    matrix_vector(bundle.generator, bundle.tangents[axis]),
                    matrix_vector(bundle.generator_first[axis], bundle.stationary),
                )
            )
        )
    for left in range(3):
        for right in range(3):
            residual = vector_add(
                matrix_vector(bundle.generator, bundle.second_tangents[left][right]),
                vector_add(
                    matrix_vector(bundle.generator_first[left], bundle.tangents[right]),
                    vector_add(
                        matrix_vector(bundle.generator_first[right], bundle.tangents[left]),
                        matrix_vector(
                            bundle.generator_second[left][right],
                            bundle.stationary,
                        ),
                    ),
                ),
            )
            second_ok.append(all(item.is_zero() for item in residual))
    return {
        "W_R_equals_Q": matrix_multiply(bundle.generator, bundle.drazin) == quotient,
        "R_W_equals_Q": matrix_multiply(bundle.drazin, bundle.generator) == quotient,
        "R_pi_zero": all(item.is_zero() for item in matrix_vector(bundle.drazin, bundle.stationary)),
        "first_stationary_derivatives": all(first_ok),
        "second_stationary_derivatives": all(second_ok),
        "tangent_traces_zero": all(dot(trace_row(), tangent).is_zero() for tangent in bundle.tangents),
    }

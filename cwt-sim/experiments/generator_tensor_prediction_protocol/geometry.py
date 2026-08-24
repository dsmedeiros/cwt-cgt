"""Count-blind stationary, SLD, Drazin-friction, and scalar geometry."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache

from .contract import MODEL_CONTRACT, Point
from .exact import (
    IMAG_UNIT,
    Matrix,
    RationalMatrix,
    matrix_add,
    matrix_multiply,
    matrix_scale,
    matrix_subtract,
    matrix_vector,
    rational_inverse,
    real_fraction,
    solve,
    trace,
    unvec,
    vec,
    vector_add,
    zeros,
)
from .model import BranchBundle, N, branch_bundle

RationalVector = tuple[Fraction, Fraction, Fraction]


@dataclass(frozen=True)
class GeometryJet:
    center: Point
    radius: Fraction
    metric: tuple[tuple[Fraction, ...], ...]
    friction: tuple[tuple[Fraction, ...], ...]
    metric_derivatives: tuple[tuple[tuple[Fraction, ...], ...], ...]
    friction_derivatives: tuple[tuple[tuple[Fraction, ...], ...], ...]
    omega: RationalVector
    omega_derivatives: tuple[RationalVector, RationalVector, RationalVector]
    purity: Fraction
    purity_derivatives: RationalVector


@dataclass(frozen=True)
class PurityJet:
    center: Point
    radius: Fraction
    purity: Fraction
    derivatives: RationalVector


def _trace_product(left: Matrix, right: Matrix):
    return trace(matrix_multiply(left, right))


def _commutator(left: Matrix, right: Matrix) -> Matrix:
    return matrix_subtract(matrix_multiply(left, right), matrix_multiply(right, left))


def _jordan(left: Matrix, right: Matrix) -> Matrix:
    return matrix_scale(
        matrix_add(matrix_multiply(left, right), matrix_multiply(right, left)),
        Fraction(1, 2),
    )


def _sld(rho: Matrix, tangent: Matrix) -> Matrix:
    size = N * N
    system = zeros(size, size)
    for row in range(N):
        for column in range(N):
            output = row + N * column
            for inner in range(N):
                system[output][inner + N * column] += rho[row][inner] / 2
                system[output][row + N * inner] += rho[inner][column] / 2
    return unvec(solve(system, vec(tangent)), N)


def _tuple_matrix(matrix: RationalMatrix) -> tuple[tuple[Fraction, ...], ...]:
    return tuple(tuple(row) for row in matrix)


def _geometry_jet_from_bundle(bundle: BranchBundle, radius: Fraction) -> GeometryJet:
    rho = unvec(bundle.stationary, N)
    tangents = tuple(unvec(item, N) for item in bundle.tangents)
    second_tangents = tuple(
        tuple(unvec(bundle.second_tangents[i][axis], N) for axis in range(3)) for i in range(3)
    )
    slds = tuple(_sld(rho, tangent) for tangent in tangents)
    sld_derivatives = tuple(
        tuple(
            _sld(
                rho,
                matrix_subtract(
                    second_tangents[i][axis],
                    _jordan(tangents[axis], slds[i]),
                ),
            )
            for axis in range(3)
        )
        for i in range(3)
    )
    metric = [
        [
            real_fraction(
                (_trace_product(tangents[i], slds[j]) + _trace_product(tangents[j], slds[i])) / 2,
                label="metric",
            )
            for j in range(3)
        ]
        for i in range(3)
    ]
    metric_derivatives = []
    for axis in range(3):
        metric_derivatives.append(
            [
                [
                    real_fraction(
                        (
                            _trace_product(second_tangents[i][axis], slds[j])
                            + _trace_product(tangents[i], sld_derivatives[j][axis])
                            + _trace_product(second_tangents[j][axis], slds[i])
                            + _trace_product(tangents[j], sld_derivatives[i][axis])
                        )
                        / 2,
                        label="metric derivative",
                    )
                    for j in range(3)
                ]
                for i in range(3)
            ]
        )
    omega_matrix = [
        [
            real_fraction(
                _trace_product(rho, _commutator(slds[i], slds[j])) / (4 * IMAG_UNIT),
                label="mean Uhlmann curvature",
            )
            for j in range(3)
        ]
        for i in range(3)
    ]
    omega_derivative_matrices = []
    for axis in range(3):
        derivative = []
        for i in range(3):
            row = []
            for j in range(3):
                value = _trace_product(tangents[axis], _commutator(slds[i], slds[j])) + _trace_product(
                    rho,
                    matrix_add(
                        _commutator(sld_derivatives[i][axis], slds[j]),
                        _commutator(slds[i], sld_derivatives[j][axis]),
                    ),
                )
                row.append(
                    real_fraction(
                        value / (4 * IMAG_UNIT),
                        label="mean Uhlmann derivative",
                    )
                )
            derivative.append(row)
        omega_derivative_matrices.append(derivative)
    lag_tangents = tuple(unvec(matrix_vector(bundle.drazin, bundle.tangents[j]), N) for j in range(3))
    lag_derivatives = tuple(
        tuple(
            unvec(
                vector_add(
                    matrix_vector(bundle.drazin_derivatives[axis], bundle.tangents[j]),
                    matrix_vector(bundle.drazin, bundle.second_tangents[j][axis]),
                ),
                N,
            )
            for axis in range(3)
        )
        for j in range(3)
    )
    friction = [
        [
            real_fraction(
                -(_trace_product(slds[i], lag_tangents[j]) + _trace_product(slds[j], lag_tangents[i])) / 2,
                label="Drazin friction",
            )
            for j in range(3)
        ]
        for i in range(3)
    ]
    friction_derivatives = []
    for axis in range(3):
        friction_derivatives.append(
            [
                [
                    real_fraction(
                        -(
                            _trace_product(sld_derivatives[i][axis], lag_tangents[j])
                            + _trace_product(slds[i], lag_derivatives[j][axis])
                            + _trace_product(sld_derivatives[j][axis], lag_tangents[i])
                            + _trace_product(slds[j], lag_derivatives[i][axis])
                        )
                        / 2,
                        label="Drazin friction derivative",
                    )
                    for j in range(3)
                ]
                for i in range(3)
            ]
        )
    purity = real_fraction(_trace_product(rho, rho), label="purity")
    purity_derivatives = tuple(
        real_fraction(
            2 * _trace_product(rho, tangents[axis]),
            label="purity derivative",
        )
        for axis in range(3)
    )
    return GeometryJet(
        center=bundle.center,
        radius=radius,
        metric=_tuple_matrix(metric),
        friction=_tuple_matrix(friction),
        metric_derivatives=tuple(_tuple_matrix(item) for item in metric_derivatives),
        friction_derivatives=tuple(_tuple_matrix(item) for item in friction_derivatives),
        omega=(omega_matrix[1][2], omega_matrix[2][0], omega_matrix[0][1]),
        omega_derivatives=tuple(
            (
                item[1][2],
                item[2][0],
                item[0][1],
            )
            for item in omega_derivative_matrices
        ),  # type: ignore[arg-type]
        purity=purity,
        purity_derivatives=purity_derivatives,  # type: ignore[arg-type]
    )


@lru_cache(maxsize=None)
def geometry_jet(center: Point, radius: Fraction | None = None) -> GeometryJet:
    actual_radius = MODEL_CONTRACT.chord_radius if radius is None else radius
    return _geometry_jet_from_bundle(branch_bundle(center, actual_radius), actual_radius)


@lru_cache(maxsize=None)
def purity_jet(center: Point, radius: Fraction | None = None) -> PurityJet:
    actual_radius = MODEL_CONTRACT.chord_radius if radius is None else radius
    bundle = branch_bundle(center, actual_radius)
    rho = unvec(bundle.stationary, N)
    tangents = tuple(unvec(item, N) for item in bundle.tangents)
    return PurityJet(
        center=center,
        radius=actual_radius,
        purity=real_fraction(_trace_product(rho, rho), label="purity"),
        derivatives=tuple(
            real_fraction(
                2 * _trace_product(rho, tangent),
                label="purity derivative",
            )
            for tangent in tangents
        ),  # type: ignore[arg-type]
    )


def rational_matrix_multiply(left: RationalMatrix, right: RationalMatrix) -> RationalMatrix:
    return [[sum(left[i][inner] * right[inner][j] for inner in range(3)) for j in range(3)] for i in range(3)]


def rational_matrix_vector(matrix: RationalMatrix, values: RationalVector) -> RationalVector:
    return tuple(
        sum(matrix[i][inner] * values[inner] for inner in range(3)) for i in range(3)
    )  # type: ignore[return-value]


def rational_matrix_add(left: RationalMatrix, right: RationalMatrix) -> RationalMatrix:
    return [[left[i][j] + right[i][j] for j in range(3)] for i in range(3)]


def rational_matrix_scale(matrix: RationalMatrix, factor: Fraction) -> RationalMatrix:
    return [[factor * value for value in row] for row in matrix]


def normalized_metric_and_friction(
    jet: GeometryJet,
) -> tuple[RationalMatrix, RationalMatrix]:
    scales = MODEL_CONTRACT.coordinate_scales
    metric = [[scales[i] * scales[j] * jet.metric[i][j] for j in range(3)] for i in range(3)]
    friction = [[scales[i] * scales[j] * jet.friction[i][j] for j in range(3)] for i in range(3)]
    return metric, friction


def dimensionless_endomorphism(jet: GeometryJet) -> RationalMatrix:
    metric, friction = normalized_metric_and_friction(jet)
    return rational_matrix_scale(
        rational_matrix_multiply(rational_inverse(metric), friction),
        MODEL_CONTRACT.depolarizing_rate,
    )


def two_form_pullback(endomorphism: RationalMatrix) -> RationalMatrix:
    """Return Lambda^2(S*) by explicit minors, without assuming S invertible."""

    result: RationalMatrix = []
    for output in range(3):
        row = []
        for source in range(3):
            kept_rows = [index for index in range(3) if index != source]
            kept_columns = [index for index in range(3) if index != output]
            minor = (
                endomorphism[kept_rows[0]][kept_columns[0]] * endomorphism[kept_rows[1]][kept_columns[1]]
                - endomorphism[kept_rows[0]][kept_columns[1]] * endomorphism[kept_rows[1]][kept_columns[0]]
            )
            row.append((Fraction(-1) ** (output + source)) * minor)
        result.append(row)
    return result


def two_form_pullback_derivative(
    endomorphism: RationalMatrix,
    derivative: RationalMatrix,
) -> RationalMatrix:
    """Differentiate the explicit-minor exterior-square formula."""

    result: RationalMatrix = []
    for output in range(3):
        row = []
        for source in range(3):
            kept_rows = [index for index in range(3) if index != source]
            kept_columns = [index for index in range(3) if index != output]
            r0, r1 = kept_rows
            c0, c1 = kept_columns
            minor_derivative = (
                derivative[r0][c0] * endomorphism[r1][c1]
                + endomorphism[r0][c0] * derivative[r1][c1]
                - derivative[r0][c1] * endomorphism[r1][c0]
                - endomorphism[r0][c1] * derivative[r1][c0]
            )
            row.append((Fraction(-1) ** (output + source)) * minor_derivative)
        result.append(row)
    return result


def normalized_omega(jet: GeometryJet) -> RationalVector:
    b_scale, d_scale, t_scale = MODEL_CONTRACT.coordinate_scales
    return (
        d_scale * t_scale * jet.omega[0],
        t_scale * b_scale * jet.omega[1],
        b_scale * d_scale * jet.omega[2],
    )


def normalized_omega_derivatives(
    jet: GeometryJet,
) -> tuple[RationalVector, RationalVector, RationalVector]:
    b_scale, d_scale, t_scale = MODEL_CONTRACT.coordinate_scales
    pair_scales = (
        d_scale * t_scale,
        t_scale * b_scale,
        b_scale * d_scale,
    )
    return tuple(
        tuple(
            pair_scales[component]
            * MODEL_CONTRACT.coordinate_scales[axis]
            * jet.omega_derivatives[axis][component]
            for component in range(3)
        )
        for axis in range(3)
    )  # type: ignore[return-value]


def wilson_scalar_jet(
    center: Point, radius: Fraction | None = None
) -> tuple[Fraction, Fraction, RationalVector, RationalVector]:
    """Return fixed-reference normalized Wilson scalars and gradients."""

    _, diffusion, t = center
    actual_radius = MODEL_CONTRACT.chord_radius if radius is None else radius
    ratio = actual_radius / MODEL_CONTRACT.chord_radius
    denominator = 1 + t * t
    u = ratio * diffusion**2 * (1 - t * t) / denominator
    v = ratio * diffusion**2 * 2 * t / denominator
    du = (
        Fraction(0),
        ratio * 2 * diffusion * (1 - t * t) / denominator,
        ratio * diffusion**2 * (-4 * t) / denominator**2,
    )
    dv = (
        Fraction(0),
        ratio * 4 * diffusion * t / denominator,
        ratio * diffusion**2 * 2 * (1 - t * t) / denominator**2,
    )
    scales = MODEL_CONTRACT.coordinate_scales
    return (
        u,
        v,
        tuple(scales[index] * du[index] for index in range(3)),  # type: ignore[arg-type]
        tuple(scales[index] * dv[index] for index in range(3)),  # type: ignore[arg-type]
    )


def normalized_purity_derivative(jet: GeometryJet | PurityJet) -> RationalVector:
    derivatives = jet.purity_derivatives if type(jet) is GeometryJet else jet.derivatives
    return tuple(
        MODEL_CONTRACT.coordinate_scales[index] * derivatives[index] for index in range(3)
    )  # type: ignore[return-value]

"""Small exact Gaussian-rational linear-algebra kernel."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class Gaussian:
    """A member of Q(i), stored without floating-point conversion."""

    real: Fraction = Fraction(0)
    imag: Fraction = Fraction(0)

    @classmethod
    def coerce(cls, value: Gaussian | Fraction | int) -> Gaussian:
        if isinstance(value, cls):
            return value
        return cls(Fraction(value), Fraction(0))

    def __add__(self, other: Gaussian | Fraction | int) -> Gaussian:
        rhs = self.coerce(other)
        return Gaussian(self.real + rhs.real, self.imag + rhs.imag)

    __radd__ = __add__

    def __neg__(self) -> Gaussian:
        return Gaussian(-self.real, -self.imag)

    def __sub__(self, other: Gaussian | Fraction | int) -> Gaussian:
        return self + (-self.coerce(other))

    def __rsub__(self, other: Gaussian | Fraction | int) -> Gaussian:
        return self.coerce(other) - self

    def __mul__(self, other: Gaussian | Fraction | int) -> Gaussian:
        rhs = self.coerce(other)
        return Gaussian(
            self.real * rhs.real - self.imag * rhs.imag,
            self.real * rhs.imag + self.imag * rhs.real,
        )

    __rmul__ = __mul__

    def inverse(self) -> Gaussian:
        denominator = self.real * self.real + self.imag * self.imag
        if denominator == 0:
            raise ZeroDivisionError("zero Gaussian rational")
        return Gaussian(self.real / denominator, -self.imag / denominator)

    def __truediv__(self, other: Gaussian | Fraction | int) -> Gaussian:
        return self * self.coerce(other).inverse()

    def __rtruediv__(self, other: Gaussian | Fraction | int) -> Gaussian:
        return self.coerce(other) / self

    def conjugate(self) -> Gaussian:
        return Gaussian(self.real, -self.imag)

    def is_zero(self) -> bool:
        return self.real == 0 and self.imag == 0

    def l1_abs(self) -> Fraction:
        """Return the rational upper bound |Re z|+|Im z| >= |z|."""

        return abs(self.real) + abs(self.imag)

    def jsonable(self) -> dict[str, object]:
        return {
            "real": fraction_item(self.real),
            "imag": fraction_item(self.imag),
        }


ZERO = Gaussian()
ONE = Gaussian(Fraction(1))
IMAG_UNIT = Gaussian(Fraction(0), Fraction(1))

Vector = list[Gaussian]
Matrix = list[list[Gaussian]]


def fraction_item(value: Fraction) -> dict[str, object]:
    return {
        "fraction": f"{value.numerator}/{value.denominator}",
        "numerator": value.numerator,
        "denominator": value.denominator,
        "float": float(value),
    }


def gaussian(value: Gaussian | Fraction | int) -> Gaussian:
    return Gaussian.coerce(value)


def zeros(rows: int, columns: int) -> Matrix:
    return [[ZERO for _ in range(columns)] for _ in range(rows)]


def identity(size: int) -> Matrix:
    result = zeros(size, size)
    for index in range(size):
        result[index][index] = ONE
    return result


def vector(values: Iterable[Gaussian | Fraction | int]) -> Vector:
    return [gaussian(value) for value in values]


def matrix_add(left: Matrix, right: Matrix) -> Matrix:
    return [
        [a + b for a, b in zip(row_a, row_b, strict=True)] for row_a, row_b in zip(left, right, strict=True)
    ]


def matrix_subtract(left: Matrix, right: Matrix) -> Matrix:
    return [
        [a - b for a, b in zip(row_a, row_b, strict=True)] for row_a, row_b in zip(left, right, strict=True)
    ]


def matrix_scale(matrix: Matrix, scalar: Gaussian | Fraction | int) -> Matrix:
    factor = gaussian(scalar)
    return [[factor * value for value in row] for row in matrix]


def vector_add(left: Vector, right: Vector) -> Vector:
    return [a + b for a, b in zip(left, right, strict=True)]


def vector_scale(values: Vector, scalar: Gaussian | Fraction | int) -> Vector:
    factor = gaussian(scalar)
    return [factor * value for value in values]


def dot(left: Sequence[Gaussian], right: Sequence[Gaussian]) -> Gaussian:
    return sum((a * b for a, b in zip(left, right, strict=True)), ZERO)


def matrix_vector(matrix: Matrix, values: Vector) -> Vector:
    return [dot(row, values) for row in matrix]


def matrix_multiply(left: Matrix, right: Matrix) -> Matrix:
    columns = list(zip(*right, strict=True))
    return [[dot(row, column) for column in columns] for row in left]


def outer(left: Sequence[Gaussian], right: Sequence[Gaussian]) -> Matrix:
    return [[a * b for b in right] for a in left]


def solve(matrix: Matrix, rhs: Vector) -> Vector:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix) or len(rhs) != size:
        raise ValueError("solve requires a nonempty square matrix and matching vector")
    augmented = [list(row) + [rhs[index]] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = next((row for row in range(column, size) if not augmented[row][column].is_zero()), None)
        if pivot is None:
            raise ValueError("singular exact matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            multiplier = augmented[row][column]
            if multiplier.is_zero():
                continue
            augmented[row] = [
                value - multiplier * pivot_entry
                for value, pivot_entry in zip(augmented[row], augmented[column], strict=True)
            ]
    return [augmented[row][-1] for row in range(size)]


def inverse(matrix: Matrix) -> Matrix:
    size = len(matrix)
    if size == 0 or any(len(row) != size for row in matrix):
        raise ValueError("inverse requires a nonempty square matrix")
    augmented = [list(row) + identity(size)[index] for index, row in enumerate(matrix)]
    for column in range(size):
        pivot = next((row for row in range(column, size) if not augmented[row][column].is_zero()), None)
        if pivot is None:
            raise ValueError("singular exact matrix")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(size):
            if row == column:
                continue
            multiplier = augmented[row][column]
            if multiplier.is_zero():
                continue
            augmented[row] = [
                value - multiplier * pivot_entry
                for value, pivot_entry in zip(augmented[row], augmented[column], strict=True)
            ]
    return [row[size:] for row in augmented]


def determinant(matrix: Matrix) -> Gaussian:
    size = len(matrix)
    work = [list(row) for row in matrix]
    result = ONE
    sign = 1
    for column in range(size):
        pivot = next((row for row in range(column, size) if not work[row][column].is_zero()), None)
        if pivot is None:
            return ZERO
        if pivot != column:
            work[column], work[pivot] = work[pivot], work[column]
            sign *= -1
        pivot_value = work[column][column]
        result *= pivot_value
        for row in range(column + 1, size):
            multiplier = work[row][column] / pivot_value
            for index in range(column, size):
                work[row][index] -= multiplier * work[column][index]
    return result * sign


def trace(matrix: Matrix) -> Gaussian:
    return sum((matrix[index][index] for index in range(len(matrix))), ZERO)


def conjugate_transpose(matrix: Matrix) -> Matrix:
    return [
        [matrix[row][column].conjugate() for row in range(len(matrix))] for column in range(len(matrix[0]))
    ]


def vec(matrix: Matrix) -> Vector:
    size = len(matrix)
    return [matrix[row][column] for column in range(size) for row in range(size)]


def unvec(values: Vector, size: int) -> Matrix:
    if len(values) != size * size:
        raise ValueError("vector length does not match matrix size")
    return [[values[row + size * column] for column in range(size)] for row in range(size)]


def real_fraction(value: Gaussian, *, label: str) -> Fraction:
    if value.imag != 0:
        raise ValueError(f"{label} is not exactly real: {value}")
    return value.real

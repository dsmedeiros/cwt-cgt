"""Strict exact schemas and small rational-linear-algebra helpers."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from types import MappingProxyType
from typing import Mapping, Sequence

Vector = tuple[Fraction, ...]
Matrix = tuple[tuple[Fraction, ...], ...]


def require_fraction(value: object, *, label: str) -> Fraction:
    if type(value) is not Fraction:
        raise TypeError(f"{label} must be an exact Fraction")
    return value


def require_vector(value: object, *, length: int, label: str) -> Vector:
    if type(value) is not tuple or len(value) != length:
        raise TypeError(f"{label} must be an exact tuple of length {length}")
    return tuple(require_fraction(item, label=f"{label}[{index}]") for index, item in enumerate(value))


def require_matrix(value: object, *, rows: int, columns: int, label: str) -> Matrix:
    if type(value) is not tuple or len(value) != rows:
        raise TypeError(f"{label} must have exactly {rows} rows")
    return tuple(
        require_vector(row, length=columns, label=f"{label}[{index}]") for index, row in enumerate(value)
    )


def strict_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) in {tuple, list}:
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            strict_equal(a, b) for a, b in zip(left, right, strict=True)  # type: ignore[arg-type]
        )
    if type(left) in {dict, MappingProxyType}:
        return tuple(left) == tuple(right) and all(  # type: ignore[arg-type]
            strict_equal(left[key], right[key]) for key in left  # type: ignore[index,union-attr]
        )
    return bool(left == right)


def _jsonable(value: object) -> object:
    if value is None or type(value) in {str, bool, int}:
        return value
    if type(value) is Fraction:
        numerator = (
            f"-{format(-value.numerator, 'x')}" if value.numerator < 0 else format(value.numerator, "x")
        )
        return {
            "denominator_hex": format(value.denominator, "x"),
            "numerator_hex": numerator,
        }
    if type(value) is tuple:
        return [_jsonable(item) for item in value]
    if type(value) is list:
        return [_jsonable(item) for item in value]
    if type(value) in {dict, MappingProxyType}:
        if any(type(key) is not str for key in value):  # type: ignore[union-attr]
            raise TypeError("canonical records require string keys")
        return {key: _jsonable(value[key]) for key in sorted(value)}  # type: ignore[index,union-attr]
    raise TypeError(f"unsupported canonical exact type: {type(value).__name__}")


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            _jsonable(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def transpose(matrix: Matrix) -> Matrix:
    if not matrix or not matrix[0]:
        raise ValueError("empty matrix")
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise ValueError("ragged matrix")
    return tuple(tuple(matrix[row][column] for row in range(len(matrix))) for column in range(width))


def matrix_multiply(left: Matrix, right: Matrix) -> Matrix:
    if not left or not right or len(left[0]) != len(right):
        raise ValueError("matrix dimensions do not compose")
    right_t = transpose(right)
    return tuple(
        tuple(sum(a * b for a, b in zip(row, column, strict=True)) for column in right_t) for row in left
    )


def matrix_vector(matrix: Matrix, vector: Vector) -> Vector:
    if any(len(row) != len(vector) for row in matrix):
        raise ValueError("matrix/vector dimensions do not compose")
    return tuple(sum(a * b for a, b in zip(row, vector, strict=True)) for row in matrix)


def determinant_three(matrix: Matrix) -> Fraction:
    matrix = require_matrix(matrix, rows=3, columns=3, label="determinant matrix")
    a, b, c = matrix
    return (
        a[0] * (b[1] * c[2] - b[2] * c[1])
        - a[1] * (b[0] * c[2] - b[2] * c[0])
        + a[2] * (b[0] * c[1] - b[1] * c[0])
    )


def solve_three(matrix: Matrix, rhs: Vector) -> Vector:
    matrix = require_matrix(matrix, rows=3, columns=3, label="solve matrix")
    rhs = require_vector(rhs, length=3, label="solve rhs")
    augmented = [list(row) + [rhs[index]] for index, row in enumerate(matrix)]
    for column in range(3):
        pivot = next((row for row in range(column, 3) if augmented[row][column] != 0), None)
        if pivot is None:
            raise ValueError("rank-deficient exact system")
        augmented[column], augmented[pivot] = augmented[pivot], augmented[column]
        pivot_value = augmented[column][column]
        augmented[column] = [value / pivot_value for value in augmented[column]]
        for row in range(3):
            if row == column:
                continue
            factor = augmented[row][column]
            augmented[row] = [
                value - factor * pivot_item
                for value, pivot_item in zip(augmented[row], augmented[column], strict=True)
            ]
    return tuple(augmented[index][3] for index in range(3))


def stack_rows(matrices: Sequence[Matrix]) -> Matrix:
    return tuple(row for matrix in matrices for row in matrix)


def freeze_mapping(record: Mapping[str, object]) -> MappingProxyType:
    return MappingProxyType(dict(record))

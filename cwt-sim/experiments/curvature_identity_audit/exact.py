"""Small exact-arithmetic helpers for the analytic audit."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import factorial
from typing import Mapping


def fraction_item(value: Fraction | int) -> dict[str, object]:
    """Return an exact scalar with an explicitly secondary float view."""

    item = Fraction(value)
    return {
        "fraction": f"{item.numerator}/{item.denominator}",
        "numerator": item.numerator,
        "denominator": item.denominator,
        "float": float(item),
    }


@dataclass(frozen=True)
class Jet2:
    """Truncated ordinary bivariate Taylor polynomial over exact rationals."""

    terms: Mapping[tuple[int, int], Fraction]
    degree: int = 3

    def __post_init__(self) -> None:
        cleaned = {
            (int(i), int(j)): Fraction(value)
            for (i, j), value in self.terms.items()
            if value and i >= 0 and j >= 0 and i + j <= self.degree
        }
        object.__setattr__(self, "terms", cleaned)

    @classmethod
    def constant(cls, value: Fraction | int, degree: int = 3) -> Jet2:
        return cls({(0, 0): Fraction(value)}, degree=degree)

    @classmethod
    def variable(cls, axis: int, degree: int = 3) -> Jet2:
        if axis not in (0, 1):
            raise ValueError("Jet2 axis must be zero or one")
        return cls({(1, 0) if axis == 0 else (0, 1): Fraction(1)}, degree=degree)

    def coefficient(self, i: int, j: int) -> Fraction:
        return self.terms.get((i, j), Fraction(0))

    def _coerce(self, other: Jet2 | Fraction | int) -> Jet2:
        if isinstance(other, Jet2):
            if other.degree != self.degree:
                raise ValueError("Jet2 degrees must match")
            return other
        return Jet2.constant(other, self.degree)

    def __add__(self, other: Jet2 | Fraction | int) -> Jet2:
        rhs = self._coerce(other)
        result = dict(self.terms)
        for power, value in rhs.terms.items():
            result[power] = result.get(power, Fraction(0)) + value
        return Jet2(result, self.degree)

    __radd__ = __add__

    def __neg__(self) -> Jet2:
        return Jet2({power: -value for power, value in self.terms.items()}, self.degree)

    def __sub__(self, other: Jet2 | Fraction | int) -> Jet2:
        return self + (-self._coerce(other))

    def __rsub__(self, other: Jet2 | Fraction | int) -> Jet2:
        return self._coerce(other) - self

    def __mul__(self, other: Jet2 | Fraction | int) -> Jet2:
        rhs = self._coerce(other)
        result: dict[tuple[int, int], Fraction] = {}
        for (i, j), left in self.terms.items():
            for (k, ell), right in rhs.terms.items():
                if i + j + k + ell <= self.degree:
                    power = (i + k, j + ell)
                    result[power] = result.get(power, Fraction(0)) + left * right
        return Jet2(result, self.degree)

    __rmul__ = __mul__

    def __pow__(self, exponent: int) -> Jet2:
        if exponent < 0:
            return self.inverse() ** (-exponent)
        result = Jet2.constant(1, self.degree)
        for _ in range(exponent):
            result = result * self
        return result

    def __truediv__(self, other: Jet2 | Fraction | int) -> Jet2:
        return self * self._coerce(other).inverse()

    def inverse(self) -> Jet2:
        constant = self.coefficient(0, 0)
        if not constant:
            raise ZeroDivisionError("Jet2 inverse requires a nonzero constant term")
        remainder = (self - constant) * (Fraction(1) / constant)
        result = Jet2.constant(1, self.degree)
        for exponent in range(1, self.degree + 1):
            result += ((-1) ** exponent) * (remainder**exponent)
        return result * (Fraction(1) / constant)

    def derivative(self, axis: int) -> Jet2:
        if axis not in (0, 1):
            raise ValueError("Jet2 axis must be zero or one")
        result = {}
        for (i, j), value in self.terms.items():
            if axis == 0 and i:
                result[(i - 1, j)] = value * i
            if axis == 1 and j:
                result[(i, j - 1)] = value * j
        return Jet2(result, self.degree)

    def exp_zero_constant(self) -> Jet2:
        if self.coefficient(0, 0):
            raise ValueError("exact exponential helper requires zero constant term")
        result = Jet2.constant(1, self.degree)
        for exponent in range(1, self.degree + 1):
            result += (self**exponent) * Fraction(1, factorial(exponent))
        return result

    def cos_zero_constant(self) -> Jet2:
        if self.coefficient(0, 0):
            raise ValueError("exact cosine helper requires zero constant term")
        result = Jet2.constant(1, self.degree)
        for exponent in range(1, self.degree // 2 + 1):
            order = 2 * exponent
            result += (self**order) * Fraction((-1) ** exponent, factorial(order))
        return result

    def sin_zero_constant(self) -> Jet2:
        if self.coefficient(0, 0):
            raise ValueError("exact sine helper requires zero constant term")
        result = Jet2.constant(0, self.degree)
        for exponent in range((self.degree + 1) // 2):
            order = 2 * exponent + 1
            result += (self**order) * Fraction((-1) ** exponent, factorial(order))
        return result

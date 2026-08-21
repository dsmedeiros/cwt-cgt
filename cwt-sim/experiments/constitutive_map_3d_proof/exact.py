"""Exact rational and directed interval helpers."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from math import factorial
from typing import Any


def fraction_item(value: Fraction | int) -> dict[str, object]:
    item = Fraction(value)
    return {
        "fraction": f"{item.numerator}/{item.denominator}",
        "numerator": item.numerator,
        "denominator": item.denominator,
        "float": float(item),
    }


@dataclass(frozen=True)
class RationalInterval:
    """Closed rational interval with outward-only arithmetic."""

    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        object.__setattr__(self, "lower", Fraction(self.lower))
        object.__setattr__(self, "upper", Fraction(self.upper))
        if self.lower > self.upper:
            raise ValueError("interval lower bound exceeds upper bound")

    @classmethod
    def point(cls, value: Fraction | int) -> RationalInterval:
        item = Fraction(value)
        return cls(item, item)

    def _coerce(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return other if isinstance(other, RationalInterval) else RationalInterval.point(other)

    def __add__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = self._coerce(other)
        return RationalInterval(self.lower + rhs.lower, self.upper + rhs.upper)

    __radd__ = __add__

    def __neg__(self) -> RationalInterval:
        return RationalInterval(-self.upper, -self.lower)

    def __sub__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return self + (-self._coerce(other))

    def __rsub__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return self._coerce(other) - self

    def __mul__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        rhs = self._coerce(other)
        products = (
            self.lower * rhs.lower,
            self.lower * rhs.upper,
            self.upper * rhs.lower,
            self.upper * rhs.upper,
        )
        return RationalInterval(min(products), max(products))

    __rmul__ = __mul__

    def reciprocal(self) -> RationalInterval:
        if self.lower <= 0 <= self.upper:
            raise ZeroDivisionError("interval reciprocal crosses zero")
        values = (Fraction(1, 1) / self.lower, Fraction(1, 1) / self.upper)
        return RationalInterval(min(values), max(values))

    def __truediv__(self, other: RationalInterval | Fraction | int) -> RationalInterval:
        return self * self._coerce(other).reciprocal()

    def square(self) -> RationalInterval:
        if self.lower <= 0 <= self.upper:
            return RationalInterval(Fraction(0), max(self.lower * self.lower, self.upper * self.upper))
        return self * self

    @property
    def excludes_zero(self) -> bool:
        return self.upper < 0 or self.lower > 0

    def jsonable(self) -> dict[str, Any]:
        return {
            "lower": fraction_item(self.lower),
            "upper": fraction_item(self.upper),
            "excludes_zero": self.excludes_zero,
        }


def exp_interval(value: Fraction, terms: int = 18) -> RationalInterval:
    """Enclose exp(value) using an exact Taylor remainder bound."""

    x = Fraction(value)
    if abs(x) > 1:
        raise ValueError("exp_interval is specialized to |x| <= 1")
    if x < 0:
        return exp_interval(-x, terms).reciprocal()
    total = sum((x**order / factorial(order) for order in range(terms + 1)), Fraction(0))
    next_term = x ** (terms + 1) / factorial(terms + 1)
    ratio = x / (terms + 2)
    remainder = next_term / (1 - ratio)
    return RationalInterval(total, total + remainder)


def sin_interval(value: Fraction, pairs: int = 8) -> RationalInterval:
    """Enclose sin(value) by consecutive exact alternating partial sums."""

    x = Fraction(value)
    if abs(x) > 1:
        raise ValueError("sin_interval is specialized to |x| <= 1")
    if x < 0:
        return -sin_interval(-x, pairs)
    first = sum(
        ((-1) ** order * x ** (2 * order + 1) / factorial(2 * order + 1) for order in range(2 * pairs + 1)),
        Fraction(0),
    )
    second = first - x ** (4 * pairs + 3) / factorial(4 * pairs + 3)
    return RationalInterval(min(first, second), max(first, second))


def cos_interval(value: Fraction, pairs: int = 8) -> RationalInterval:
    """Enclose cos(value) by consecutive exact alternating partial sums."""

    x = abs(Fraction(value))
    if x > 1:
        raise ValueError("cos_interval is specialized to |x| <= 1")
    first = sum(
        ((-1) ** order * x ** (2 * order) / factorial(2 * order) for order in range(2 * pairs + 1)),
        Fraction(0),
    )
    second = first - x ** (4 * pairs + 2) / factorial(4 * pairs + 2)
    return RationalInterval(min(first, second), max(first, second))


def strict_cross(left: tuple[int, int, int], right: tuple[int, int, int]) -> tuple[int, int, int]:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )

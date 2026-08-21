"""Deterministic outward binary64 intervals with no libm transcendental calls."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from fractions import Fraction
from math import factorial

import numpy as np


def _down(value: np.ndarray | np.float64 | float) -> np.ndarray:
    return np.nextafter(np.asarray(value, dtype=np.float64), -np.inf)


def _up(value: np.ndarray | np.float64 | float) -> np.ndarray:
    return np.nextafter(np.asarray(value, dtype=np.float64), np.inf)


def _ratio_bounds(numerator: int, denominator: int) -> tuple[float, float]:
    """Return adjacent binary64 bounds and verify them by integer cross-products."""

    if denominator <= 0:
        raise ValueError("exact-ratio denominator must be positive")
    nearest = float(numerator / denominator)
    if not np.isfinite(nearest):
        raise FloatingPointError("exact ratio is not finite in binary64")
    float_numerator, float_denominator = nearest.as_integer_ratio()
    comparison = float_numerator * denominator - numerator * float_denominator
    if comparison < 0:
        lower, upper = nearest, float(np.nextafter(nearest, np.inf))
    elif comparison > 0:
        lower, upper = float(np.nextafter(nearest, -np.inf)), nearest
    else:
        lower = upper = nearest
    lower_numerator, lower_denominator = lower.as_integer_ratio()
    upper_numerator, upper_denominator = upper.as_integer_ratio()
    if (
        lower_numerator * denominator > numerator * lower_denominator
        or upper_numerator * denominator < numerator * upper_denominator
    ):
        raise AssertionError("adjacent binary64 bounds do not enclose the exact ratio")
    return lower, upper


@dataclass(frozen=True)
class Float64Interval:
    """Closed outward interval backed only by finite binary64 arrays."""

    lower: np.ndarray
    upper: np.ndarray

    def __post_init__(self) -> None:
        lower = np.asarray(self.lower, dtype=np.float64)
        upper = np.asarray(self.upper, dtype=np.float64)
        if lower.shape != upper.shape or not np.all(np.isfinite(lower)) or not np.all(np.isfinite(upper)):
            raise FloatingPointError("binary64 interval bounds must be finite equal shapes")
        if np.any(lower > upper):
            raise ValueError("binary64 interval lower bound exceeds upper bound")
        object.__setattr__(self, "lower", lower)
        object.__setattr__(self, "upper", upper)

    @classmethod
    def exact_ratio(cls, numerator: int, denominator: int = 1) -> Float64Interval:
        lower, upper = _ratio_bounds(numerator, denominator)
        return cls(np.asarray(lower), np.asarray(upper))

    @classmethod
    def exact_fraction(cls, value: Fraction | int) -> Float64Interval:
        item = Fraction(value)
        return cls.exact_ratio(item.numerator, item.denominator)

    @classmethod
    def ratios(
        cls,
        numerators: list[int] | np.ndarray,
        denominators: list[int] | np.ndarray | int,
    ) -> Float64Interval:
        numerator_array = np.asarray(numerators, dtype=object).reshape(-1)
        denominator_array = np.broadcast_to(np.asarray(denominators, dtype=object), numerator_array.shape)
        lower = np.empty(len(numerator_array), dtype=np.float64)
        upper = np.empty(len(numerator_array), dtype=np.float64)
        for index, (numerator, denominator) in enumerate(
            zip(numerator_array, denominator_array, strict=True)
        ):
            lower[index], upper[index] = _ratio_bounds(int(numerator), int(denominator))
        return cls(lower, upper)

    def _coerce(self, other: Float64Interval | Fraction | int) -> Float64Interval:
        return other if isinstance(other, Float64Interval) else Float64Interval.exact_fraction(other)

    def __add__(self, other: Float64Interval | Fraction | int) -> Float64Interval:
        rhs = self._coerce(other)
        return Float64Interval(_down(self.lower + rhs.lower), _up(self.upper + rhs.upper))

    __radd__ = __add__

    def __neg__(self) -> Float64Interval:
        return Float64Interval(-self.upper, -self.lower)

    def __sub__(self, other: Float64Interval | Fraction | int) -> Float64Interval:
        return self + (-self._coerce(other))

    def __rsub__(self, other: Float64Interval | Fraction | int) -> Float64Interval:
        return self._coerce(other) - self

    def __mul__(self, other: Float64Interval | Fraction | int) -> Float64Interval:
        rhs = self._coerce(other)
        products = np.stack(
            (
                self.lower * rhs.lower,
                self.lower * rhs.upper,
                self.upper * rhs.lower,
                self.upper * rhs.upper,
            )
        )
        return Float64Interval(_down(np.min(products, axis=0)), _up(np.max(products, axis=0)))

    __rmul__ = __mul__

    def __truediv__(self, other: Float64Interval | Fraction | int) -> Float64Interval:
        rhs = self._coerce(other)
        if np.any((rhs.lower <= 0.0) & (rhs.upper >= 0.0)):
            raise ZeroDivisionError("binary64 interval denominator contains zero")
        quotients = np.stack(
            (
                self.lower / rhs.lower,
                self.lower / rhs.upper,
                self.upper / rhs.lower,
                self.upper / rhs.upper,
            )
        )
        return Float64Interval(_down(np.min(quotients, axis=0)), _up(np.max(quotients, axis=0)))

    def at(self, index: int) -> Float64Interval:
        return Float64Interval(np.asarray(self.lower[index]), np.asarray(self.upper[index]))

    def jsonable_scalar(self) -> dict[str, float]:
        if self.lower.shape != () or self.upper.shape != ():
            raise ValueError("only a scalar interval is JSON serializable")
        return {
            "lower": float(self.lower),
            "upper": float(self.upper),
            "width": float(self.upper - self.lower),
        }


def _horner(x: Float64Interval, coefficients: tuple[Fraction, ...]) -> Float64Interval:
    result = Float64Interval.exact_fraction(coefficients[-1])
    for coefficient in reversed(coefficients[:-1]):
        result = result * x + coefficient
    return result


def exp_interval_binary64(x: Float64Interval) -> Float64Interval:
    if np.any(x.lower < -81.0 / 400.0) or np.any(x.upper > 81.0 / 400.0):
        raise ValueError("exp interval leaves the reviewed polynomial domain")
    coefficients = tuple(Fraction(1, factorial(order)) for order in range(15))
    polynomial = _horner(x, coefficients)
    remainder = Fraction(5, 4) * Fraction(81, 400) ** 15 / factorial(15)
    return polynomial + Float64Interval(-_up(float(remainder)), _up(float(remainder)))


def sin_interval_binary64(x: Float64Interval) -> Float64Interval:
    if np.any(x.lower < -47.0 / 500.0) or np.any(x.upper > 47.0 / 500.0):
        raise ValueError("sin interval leaves the reviewed polynomial domain")
    squared = x * x
    coefficients = tuple(Fraction((-1) ** order, factorial(2 * order + 1)) for order in range(7))
    polynomial = x * _horner(squared, coefficients)
    remainder = Fraction(47, 500) ** 15 / factorial(15)
    return polynomial + Float64Interval(-_up(float(remainder)), _up(float(remainder)))


def cos_interval_binary64(x: Float64Interval) -> Float64Interval:
    if np.any(x.lower < -1101.0 / 4000.0) or np.any(x.upper > 1101.0 / 4000.0):
        raise ValueError("cos interval leaves the reviewed polynomial domain")
    squared = x * x
    coefficients = tuple(Fraction((-1) ** order, factorial(2 * order)) for order in range(8))
    polynomial = _horner(squared, coefficients)
    remainder = Fraction(1101, 4000) ** 16 / factorial(16)
    return polynomial + Float64Interval(-_up(float(remainder)), _up(float(remainder)))


def balanced_pairwise_sum(values: Float64Interval) -> Float64Interval:
    lower = values.lower.reshape(-1)
    upper = values.upper.reshape(-1)
    if len(lower) == 0 or len(lower) & (len(lower) - 1):
        raise ValueError("balanced reduction requires a nonempty power-of-two count")
    current = Float64Interval(lower, upper)
    while len(current.lower) > 1:
        current = Float64Interval(
            _down(current.lower[0::2] + current.lower[1::2]),
            _up(current.upper[0::2] + current.upper[1::2]),
        )
    return current.at(0)


def runtime_contract() -> dict[str, object]:
    subnormal = float(np.nextafter(np.float64(0.0), np.float64(1.0)))
    passed = (
        sys.float_info.radix == 2
        and sys.float_info.mant_dig == 53
        and sys.float_info.rounds == 1
        and subnormal > 0.0
        and subnormal * 1.0 == subnormal
    )
    return {
        "dtype": "IEEE_754_binary64",
        "rounding": "round_to_nearest_ties_to_even",
        "outward_step": "numpy.nextafter_after_every_arithmetic_operation",
        "balanced_pairwise_reduction": True,
        "libm_transcendentals_used": False,
        "fma_reassociation_or_fast_math_used": False,
        "subnormal_preservation_probe": subnormal,
        "ftz_or_daz_observed": not (subnormal > 0.0 and subnormal * 1.0 == subnormal),
        "passed": passed,
    }

"""Typed contracts shared by the analytic proof-program modules."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

import numpy as np

Array = np.ndarray
OneForm = Callable[[Array], Array]
StateMap = Callable[[Array], Array]


class AnalyticDisposition(str, Enum):
    """Allowed dispositions for this non-empirical program."""

    PASS_INTERNAL_ANALYTIC = "PASS_INTERNAL_ANALYTIC"
    FAIL_INTERNAL_ANALYTIC = "FAIL_INTERNAL_ANALYTIC"
    INDETERMINATE_INTERNAL_ANALYTIC = "INDETERMINATE_INTERNAL_ANALYTIC"


class CaseDisposition(str, Enum):
    """Expected status vocabulary for frozen examples and counterexamples."""

    COUNTEREXAMPLE = "COUNTEREXAMPLE"
    INELIGIBLE_TAUTOLOGY = "INELIGIBLE_TAUTOLOGY"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"
    PASS_LOCAL_INTERNAL = "PASS_LOCAL_INTERNAL"


@dataclass(frozen=True)
class ResponseCycle:
    """One update-then-sample response cycle on an explicitly closed path."""

    path: Array
    states: Array
    samples: Array
    total_response: float
    initialization: str
    rho: float


@dataclass(frozen=True)
class OrientationPair:
    """Positive/reverse cycles and their orientation decomposition."""

    positive: ResponseCycle
    reverse: ResponseCycle

    @property
    def anti(self) -> float:
        return 0.5 * (self.positive.total_response - self.reverse.total_response)

    @property
    def even(self) -> float:
        return 0.5 * (self.positive.total_response + self.reverse.total_response)


@dataclass(frozen=True)
class Gate:
    """One deterministic analytic acceptance gate."""

    name: str
    passed: bool
    observed: object
    requirement: str

    def as_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": "pass" if self.passed else "fail",
            "observed": self.observed,
            "requirement": self.requirement,
        }

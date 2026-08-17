"""Fail-closed gate and case classification for the identity audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contract import case_gate_ownership, expected_case_dispositions


@dataclass(frozen=True)
class Gate:
    """One directly evaluable analytic or implementation-binding gate."""

    name: str
    natural_passed: bool
    passed: bool
    requirement: str
    observed: Any

    def jsonable(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": "pass" if self.passed else "fail",
            "natural_status": "pass" if self.natural_passed else "fail",
            "requirement": self.requirement,
            "observed": self.observed,
        }


def registry_gate_names() -> tuple[str, ...]:
    """Return the exact owned gate registry and reject duplicate ownership."""

    flattened = [name for _, names in case_gate_ownership() for name in names]
    if len(flattened) != len(set(flattened)):
        raise RuntimeError("every live gate must have exactly one case owner")
    return tuple(flattened)


def gate_owner(gate_name: str) -> str:
    """Return the immutable canonical owner for one live gate."""

    owners = [case_id for case_id, names in case_gate_ownership() if gate_name in names]
    if len(owners) != 1:
        raise KeyError(f"gate must have exactly one canonical owner: {gate_name}")
    return owners[0]


def apply_fail_only_overrides(
    natural: Mapping[str, tuple[bool, str, Any]],
    overrides: Mapping[str, bool] | None = None,
) -> list[Gate]:
    """Apply overrides monotonically: True can never rescue a natural failure."""

    expected = set(registry_gate_names())
    if set(natural) != expected:
        raise RuntimeError(
            f"live gate registry mismatch: absent={sorted(expected-set(natural))}, "
            f"orphan={sorted(set(natural)-expected)}"
        )
    requested = dict(overrides or {})
    unknown = sorted(set(requested) - expected)
    if unknown:
        raise KeyError(f"unknown gate overrides: {unknown}")
    if any(not isinstance(value, bool) for value in requested.values()):
        raise TypeError("gate override values must be booleans")
    gates = []
    for name in registry_gate_names():
        natural_passed, requirement, observed = natural[name]
        allowed = requested.get(name, True)
        gates.append(
            Gate(
                name=name,
                natural_passed=bool(natural_passed),
                passed=bool(natural_passed) and allowed,
                requirement=requirement,
                observed=observed,
            )
        )
    return gates


def case_dispositions(gates: list[Gate]) -> dict[str, str]:
    """Derive every case disposition from its owned gates."""

    names = tuple(gate.name for gate in gates)
    if names != registry_gate_names() or len(names) != len(set(names)):
        raise RuntimeError("case classification requires the ordered unique canonical gate registry")
    statuses = {gate.name: gate.passed for gate in gates}
    result = {}
    expected = expected_case_dispositions()
    for case_id, owned_names in case_gate_ownership():
        failed = [name for name in owned_names if not statuses[name]]
        result[case_id] = expected[case_id] if not failed else f"FAIL_INTERNAL_ANALYTIC:{','.join(failed)}"
    return result

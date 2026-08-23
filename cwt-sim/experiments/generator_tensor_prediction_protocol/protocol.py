"""Typed pre-response state machine; it contains no unlock transition."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from fractions import Fraction

from .contract import (
    A_CENTERS,
    EXPOSURE_REGISTRY,
    HELDOUT_AREA_VECTOR,
    HELDOUT_CENTER,
    RESERVATION_STATUS,
    V_CENTERS,
    Point,
    exposure_registry_issues,
    exposure_registry_sha256,
)


class ProtocolState(str, Enum):
    INIT = "INIT"
    EXPOSURE_FROZEN = "EXPOSURE_FROZEN"
    CRITERION_FROZEN = "CRITERION_FROZEN"
    SOURCE_REVIEW_READY = "SOURCE_REVIEW_READY"
    POISONED = "POISONED"


@dataclass(frozen=True)
class FalsificationCriterion:
    criterion_id: str = "CLOSED_CONNECTION3_GLOBAL_COEFFICIENT_FALSIFICATION_V1"
    predictor_family: str = "sigma*[k0*du^dv+k1*du^dp+k2*dv^dp]"
    coefficient_count: int = 3
    calibration_centers: tuple[Point, ...] = A_CENTERS
    confirmation_centers: tuple[Point, Point] = V_CENTERS
    heldout_center: Point = HELDOUT_CENTER
    heldout_area_vector: tuple[int, int, int] = HELDOUT_AREA_VECTOR
    exact_calibration_consistency_required: bool = True
    both_whole_center_confirmations_required: bool = True
    heldout_oblique_prediction_required: bool = True
    pointwise_coefficient_fit_forbidden: bool = True
    response_accessed: bool = False


REVIEWED_CRITERION_SHA256 = "ab5cc7a9ec39d33a096643a03b65aa5654200c1c00907bd76a8005490f37a6e7"


def _strict_equal(left: object, right: object) -> bool:
    if type(left) is not type(right):
        return False
    if type(left) in {tuple, list}:
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            _strict_equal(a, b) for a, b in zip(left, right, strict=True)  # type: ignore[arg-type]
        )
    if type(left) is dict:
        return tuple(left) == tuple(right) and all(  # type: ignore[arg-type]
            _strict_equal(left[key], right[key]) for key in left  # type: ignore[index,union-attr]
        )
    return bool(left == right)


def criterion_issues(criterion: FalsificationCriterion) -> tuple[str, ...]:
    expected = FalsificationCriterion()
    if type(criterion) is not FalsificationCriterion:
        return ("criterion_type",)
    issues = []
    observed_record = asdict(criterion)
    for name, expected_value in asdict(expected).items():
        if not _strict_equal(observed_record[name], expected_value):
            issues.append(name)
    return tuple(issues)


def _jsonable(value: object) -> object:
    if type(value) is Fraction:
        return {
            "numerator": value.numerator,
            "denominator": value.denominator,
        }
    if type(value) in {str, int, bool} or value is None:
        return value
    if type(value) in {tuple, list}:
        return [_jsonable(item) for item in value]  # type: ignore[arg-type]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError("noncanonical criterion key")
        return {key: _jsonable(item) for key, item in value.items()}  # type: ignore[union-attr]
    raise TypeError(f"noncanonical criterion value: {type(value).__name__}")


def criterion_sha256(criterion: FalsificationCriterion) -> str:
    if type(criterion) is not FalsificationCriterion:
        raise TypeError("criterion must use the exact reviewed dataclass")
    issues = criterion_issues(criterion)
    if issues:
        raise ValueError(f"criterion schema refused: {issues}")
    payload = json.dumps(
        _jsonable(asdict(criterion)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


class ProtocolSession:
    def __init__(self) -> None:
        self._state = ProtocolState.INIT
        self._events = [ProtocolState.INIT.value]
        self._exposure_registry_sha256: str | None = None
        self._criterion_sha256: str | None = None

    def _advance(self, expected: ProtocolState, target: ProtocolState) -> None:
        if self._state is not expected:
            self._state = ProtocolState.POISONED
            self._events.append(ProtocolState.POISONED.value)
            raise RuntimeError("pre-response protocol transition order violated")
        self._state = target
        self._events.append(target.value)

    def freeze_exposure_registry(self, registry: object = EXPOSURE_REGISTRY) -> None:
        issues = exposure_registry_issues(registry)
        if issues:
            self._state = ProtocolState.POISONED
            self._events.append(ProtocolState.POISONED.value)
            raise ValueError(f"exposure registry refused: {issues}")
        self._advance(ProtocolState.INIT, ProtocolState.EXPOSURE_FROZEN)
        self._exposure_registry_sha256 = exposure_registry_sha256(registry)

    def freeze_criterion(self, criterion: FalsificationCriterion) -> None:
        if type(criterion) is not FalsificationCriterion:
            self._state = ProtocolState.POISONED
            self._events.append(ProtocolState.POISONED.value)
            raise TypeError("criterion type refused")
        issues = criterion_issues(criterion)
        if issues:
            self._state = ProtocolState.POISONED
            self._events.append(ProtocolState.POISONED.value)
            raise ValueError(f"criterion schema refused: {issues}")
        digest = criterion_sha256(criterion)
        if digest != REVIEWED_CRITERION_SHA256:
            self._state = ProtocolState.POISONED
            self._events.append(ProtocolState.POISONED.value)
            raise ValueError("criterion reviewed digest refused")
        self._advance(ProtocolState.EXPOSURE_FROZEN, ProtocolState.CRITERION_FROZEN)
        self._criterion_sha256 = digest

    def mark_source_review_ready(self) -> None:
        self._advance(
            ProtocolState.CRITERION_FROZEN,
            ProtocolState.SOURCE_REVIEW_READY,
        )

    def record(self) -> dict[str, object]:
        return {
            "authority": "typed_pre_response_state_machine_without_unlock_transition",
            "state": self._state.value,
            "event_log": tuple(self._events),
            "exposure_registry_sha256": self._exposure_registry_sha256,
            "criterion_sha256": self._criterion_sha256,
            "reservation_status": RESERVATION_STATUS,
            "source_lock_present": False,
            "cryptographically_proven_unopened": False,
            "response_accessed": False,
            "response_unlock_command_exists": False,
        }


def canonical_protocol_record() -> dict[str, object]:
    session = ProtocolSession()
    session.freeze_exposure_registry()
    session.freeze_criterion(FalsificationCriterion())
    session.mark_source_review_ready()
    return session.record()

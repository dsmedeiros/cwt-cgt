"""Deterministic prediction-lock and oracle-access state machine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, TypeVar

from .contract import MODEL_CONTRACT, ConstitutiveMap3DContract

T = TypeVar("T")


def _canonical_bytes(payload: Any) -> bytes:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(payload: Any) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


class PipelineState(str, Enum):
    INIT = "INIT"
    PREDICTION_LOCKED = "PREDICTION_LOCKED"
    ORACLE_RUN = "ORACLE_RUN"
    VERIFIED = "VERIFIED"
    POISONED = "POISONED"


class PipelineViolation(RuntimeError):
    """Raised when staged access is reordered, replayed, or rebound."""


@dataclass(frozen=True)
class PredictionAccess:
    """One-use capability for predictor/factorization code in the INIT stage."""

    _session: PipelineSession
    _epoch: int

    def require_current(self) -> None:
        self._session._require_prediction_access(self._epoch)


@dataclass(frozen=True)
class PredictionLock:
    """Immutable binding of one prediction payload to the reviewed contract."""

    schema_version: int
    experiment_id: str
    contract_sha256: str
    prediction_sha256: str
    lock_sha256: str

    def unsigned_record(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "experiment_id": self.experiment_id,
            "contract_sha256": self.contract_sha256,
            "prediction_sha256": self.prediction_sha256,
        }

    def jsonable(self) -> dict[str, object]:
        return {**self.unsigned_record(), "lock_sha256": self.lock_sha256}


@dataclass(frozen=True)
class OracleAccess:
    """One-use capability bound to the current session prediction lock."""

    _session: PipelineSession
    _lock: PredictionLock

    def require_current(self) -> PredictionLock:
        return self._session._require_oracle_access(self._lock)


def create_prediction_lock(
    prediction: Any,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> PredictionLock:
    unsigned = {
        "schema_version": 1,
        "experiment_id": contract.experiment_id,
        "contract_sha256": _sha256(contract.jsonable()),
        "prediction_sha256": _sha256(prediction),
    }
    return PredictionLock(**unsigned, lock_sha256=_sha256(unsigned))


def validate_prediction_lock(
    lock: PredictionLock,
    contract: ConstitutiveMap3DContract = MODEL_CONTRACT,
) -> bool:
    if not isinstance(lock, PredictionLock):
        return False
    return (
        lock.schema_version == 1
        and lock.experiment_id == contract.experiment_id
        and lock.contract_sha256 == _sha256(contract.jsonable())
        and lock.lock_sha256 == _sha256(lock.unsigned_record())
    )


class PipelineSession:
    """One-use staged session; every violation irreversibly poisons it."""

    def __init__(self, contract: ConstitutiveMap3DContract = MODEL_CONTRACT) -> None:
        self.contract = contract
        self.state = PipelineState.INIT
        self._prediction_built = False
        self._prediction_access_open = False
        self._prediction_epoch = 0
        self._active_lock: PredictionLock | None = None
        self._event_log: list[str] = [PipelineState.INIT.value]

    @property
    def event_log(self) -> tuple[str, ...]:
        return tuple(self._event_log)

    @property
    def active_lock(self) -> PredictionLock | None:
        return self._active_lock

    def _poison(self, reason: str) -> None:
        if self.state is not PipelineState.POISONED:
            self.state = PipelineState.POISONED
            self._event_log.append(f"POISONED:{reason}")
        raise PipelineViolation(reason)

    def _require_prediction_access(self, epoch: int) -> None:
        if (
            self.state is not PipelineState.INIT
            or not self._prediction_access_open
            or epoch != self._prediction_epoch
        ):
            self._poison("predictor/factorization access is outside its one INIT capability")

    def _require_oracle_access(self, lock: PredictionLock) -> PredictionLock:
        if (
            self.state is not PipelineState.PREDICTION_LOCKED
            or self._active_lock is None
            or lock != self._active_lock
            or not validate_prediction_lock(lock, self.contract)
        ):
            self._poison("oracle capability is stale, replayed, or bound to the wrong lock")
        return lock

    def build_prediction(self, builder: Callable[[PredictionAccess], T]) -> T:
        if self.state is not PipelineState.INIT or self._prediction_built:
            self._poison("prediction access is permitted exactly once in INIT")
        self._prediction_epoch += 1
        access = PredictionAccess(self, self._prediction_epoch)
        self._prediction_access_open = True
        try:
            prediction = builder(access)
        except Exception as exc:
            self._prediction_access_open = False
            try:
                self._poison(f"prediction builder failed closed: {type(exc).__name__}")
            except PipelineViolation as violation:
                raise violation from exc
        self._prediction_access_open = False
        self._prediction_built = True
        return prediction

    def lock_prediction(self, prediction: Any) -> PredictionLock:
        if self.state is not PipelineState.INIT or not self._prediction_built:
            self._poison("prediction must be built before its one lock transition")
        lock = create_prediction_lock(prediction, self.contract)
        self._active_lock = lock
        self.state = PipelineState.PREDICTION_LOCKED
        self._event_log.append(PipelineState.PREDICTION_LOCKED.value)
        return lock

    def run_oracle(self, lock: PredictionLock, runner: Callable[[OracleAccess], T]) -> T:
        if self.state is not PipelineState.PREDICTION_LOCKED:
            self._poison("oracle access requires the PREDICTION_LOCKED state")
        if (
            self._active_lock is None
            or lock != self._active_lock
            or not validate_prediction_lock(lock, self.contract)
        ):
            self._poison("oracle received a stale, replayed, or foreign prediction lock")
        access = OracleAccess(self, lock)
        try:
            result = runner(access)
        except Exception as exc:
            try:
                self._poison(f"oracle runner failed closed: {type(exc).__name__}")
            except PipelineViolation as violation:
                raise violation from exc
        self.state = PipelineState.ORACLE_RUN
        self._event_log.append(PipelineState.ORACLE_RUN.value)
        return result

    def verify(self, lock: PredictionLock) -> tuple[str, ...]:
        if self.state is not PipelineState.ORACLE_RUN:
            self._poison("verification requires exactly one completed oracle run")
        if (
            self._active_lock is None
            or lock != self._active_lock
            or not validate_prediction_lock(lock, self.contract)
        ):
            self._poison("verification received the wrong prediction lock")
        self.state = PipelineState.VERIFIED
        self._event_log.append(PipelineState.VERIFIED.value)
        return self.event_log

    def require_verified(self) -> None:
        if self.state is not PipelineState.VERIFIED or self.event_log != (
            "INIT",
            "PREDICTION_LOCKED",
            "ORACLE_RUN",
            "VERIFIED",
        ):
            self._poison("final pipeline state or event log is not canonical")

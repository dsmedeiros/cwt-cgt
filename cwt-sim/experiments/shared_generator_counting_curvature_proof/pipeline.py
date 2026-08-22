"""Restricted prediction-lock/oracle capability state machine."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from typing import Any, Mapping


class PipelineState(str, Enum):
    INIT = "INIT"
    PREDICTION_LOCKED = "PREDICTION_LOCKED"
    ORACLE_RUN = "ORACLE_RUN"
    VERIFIED = "VERIFIED"
    POISONED = "POISONED"


REVIEWED_CRITERION_ID = "T0_T1_exact_B_F_before_oracle_v1"
REVIEWED_COMPARISON_RULE = "exact_componentwise_equality_and_nonzero_curvature"
REVIEWED_EXPERIMENT_ID = "shared_generator_counting_curvature_proof"
REVIEWED_CRITERION_SHA256 = "74ac96c99bd02a47074c1acc3c5d8b1abcb14b2cd098edc377841c4862bd0ed9"
REVIEWED_PRIMITIVE_CONTRACT_SHA256 = "5633805f1bbdf3f8335222ca7846e4fce5583c88826a9b57ca0833c7ec9c4e0b"


def _canonical_bytes(value: Any) -> bytes:
    def convert(item: Any) -> Any:
        if isinstance(item, Fraction):
            return {"fraction": f"{item.numerator}/{item.denominator}"}
        if isinstance(item, Mapping):
            return {str(key): convert(mapped) for key, mapped in item.items()}
        if isinstance(item, (tuple, list)):
            return [convert(mapped) for mapped in item]
        return item

    return json.dumps(convert(value), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode(
        "utf-8"
    )


@dataclass(frozen=True)
class FalsificationCriterion:
    """Exact predictions frozen before the response oracle can run."""

    criterion_id: str
    t0_B: tuple[Fraction, Fraction, Fraction]
    t0_F: tuple[Fraction, Fraction, Fraction]
    t1_B: tuple[Fraction, Fraction, Fraction]
    t1_F: tuple[Fraction, Fraction, Fraction]
    comparison_rule: str = REVIEWED_COMPARISON_RULE
    same_curvature_or_zero_preserving_homogeneous_map_inference_requested: bool = False

    def record(self) -> dict[str, object]:
        return {
            "criterion_id": self.criterion_id,
            "T0": {"B": self.t0_B, "F": self.t0_F},
            "T1": {"B": self.t1_B, "F": self.t1_F},
            "comparison_rule": self.comparison_rule,
            "same_curvature_or_zero_preserving_homogeneous_map_inference_requested": (
                self.same_curvature_or_zero_preserving_homogeneous_map_inference_requested
            ),
        }

    def reviewed_schema_issues(self) -> tuple[str, ...]:
        issues: list[str] = []
        if type(self.criterion_id) is not str or self.criterion_id != REVIEWED_CRITERION_ID:
            issues.append("criterion_id_not_reviewed")
        if type(self.comparison_rule) is not str or self.comparison_rule != REVIEWED_COMPARISON_RULE:
            issues.append("comparison_rule_not_reviewed")
        if type(self.same_curvature_or_zero_preserving_homogeneous_map_inference_requested) is not bool:
            issues.append("positive_inference_flag_not_exact_bool")
        elif self.same_curvature_or_zero_preserving_homogeneous_map_inference_requested is True:
            issues.append("positive_inference_requested")
        for name, values in (
            ("t0_B", self.t0_B),
            ("t0_F", self.t0_F),
            ("t1_B", self.t1_B),
            ("t1_F", self.t1_F),
        ):
            if (
                type(values) is not tuple
                or len(values) != 3
                or any(type(value) is not Fraction for value in values)
            ):
                issues.append(f"{name}_not_exact_fraction_triple")
        if hashlib.sha256(_canonical_bytes(self.record())).hexdigest() != REVIEWED_CRITERION_SHA256:
            issues.append("criterion_payload_not_reviewed")
        return tuple(issues)

    def accepts(self, oracle_result: Mapping[str, Any]) -> bool:
        if type(oracle_result) is not dict:
            return False
        for case, expected_B, expected_F in (
            ("T0", self.t0_B, self.t0_F),
            ("T1", self.t1_B, self.t1_F),
        ):
            result = oracle_result.get(case)
            if type(result) is not dict or set(result) != {"B", "F"}:
                return False
            for field, expected in (("B", expected_B), ("F", expected_F)):
                actual = result[field]
                if (
                    type(actual) is not tuple
                    or len(actual) != 3
                    or any(type(value) is not Fraction for value in actual)
                    or any(
                        value.numerator != target.numerator or value.denominator != target.denominator
                        for value, target in zip(actual, expected, strict=True)
                    )
                ):
                    return False
        return all(value != 0 for value in self.t0_F + self.t1_F)


@dataclass(frozen=True)
class PredictionLock:
    experiment_id: str
    criterion_sha256: str
    primitive_contract_sha256: str
    positive_map_inference_requested: bool = False

    @classmethod
    def create(
        cls,
        experiment_id: str,
        criterion: FalsificationCriterion,
        primitive_contract_sha256: str,
    ) -> PredictionLock:
        if criterion.reviewed_schema_issues():
            raise ValueError("unreviewed falsification criterion")
        if experiment_id != REVIEWED_EXPERIMENT_ID:
            raise ValueError("unreviewed experiment id")
        if primitive_contract_sha256 != REVIEWED_PRIMITIVE_CONTRACT_SHA256:
            raise ValueError("unreviewed primitive contract")
        return cls(
            experiment_id=experiment_id,
            criterion_sha256=hashlib.sha256(_canonical_bytes(criterion.record())).hexdigest(),
            primitive_contract_sha256=primitive_contract_sha256,
            positive_map_inference_requested=(
                criterion.same_curvature_or_zero_preserving_homogeneous_map_inference_requested
            ),
        )

    def authentic(
        self,
        criterion: FalsificationCriterion,
        primitive_contract_sha256: str,
    ) -> bool:
        return (
            self.experiment_id == REVIEWED_EXPERIMENT_ID
            and self.criterion_sha256 == REVIEWED_CRITERION_SHA256
            and self.criterion_sha256 == hashlib.sha256(_canonical_bytes(criterion.record())).hexdigest()
            and self.primitive_contract_sha256
            == primitive_contract_sha256
            == REVIEWED_PRIMITIVE_CONTRACT_SHA256
            and self.positive_map_inference_requested is False
        )


@dataclass(frozen=True)
class OracleCapability:
    """The only value provided to the response oracle."""

    experiment_id: str
    criterion_sha256: str
    primitive_contract_sha256: str
    capability: str
    payload_sha256: str

    @classmethod
    def issue(cls, lock: PredictionLock) -> OracleCapability:
        if (
            lock.experiment_id != REVIEWED_EXPERIMENT_ID
            or lock.criterion_sha256 != REVIEWED_CRITERION_SHA256
            or lock.primitive_contract_sha256 != REVIEWED_PRIMITIVE_CONTRACT_SHA256
            or lock.positive_map_inference_requested is not False
        ):
            raise ValueError("unreviewed prediction lock")
        capability = "frozen_generator_primitives_only"
        payload = {
            "experiment_id": lock.experiment_id,
            "criterion_sha256": lock.criterion_sha256,
            "primitive_contract_sha256": lock.primitive_contract_sha256,
            "capability": capability,
        }
        return cls(
            experiment_id=lock.experiment_id,
            criterion_sha256=lock.criterion_sha256,
            primitive_contract_sha256=lock.primitive_contract_sha256,
            capability=capability,
            payload_sha256=hashlib.sha256(_canonical_bytes(payload)).hexdigest(),
        )

    def payload_record(self) -> dict[str, str]:
        return {
            "experiment_id": self.experiment_id,
            "criterion_sha256": self.criterion_sha256,
            "primitive_contract_sha256": self.primitive_contract_sha256,
            "capability": self.capability,
        }

    def authentic(self, lock: PredictionLock | None = None) -> bool:
        payload_matches = (
            type(self.experiment_id) is str
            and self.experiment_id == REVIEWED_EXPERIMENT_ID
            and type(self.criterion_sha256) is str
            and self.criterion_sha256 == REVIEWED_CRITERION_SHA256
            and type(self.primitive_contract_sha256) is str
            and self.primitive_contract_sha256 == REVIEWED_PRIMITIVE_CONTRACT_SHA256
            and type(self.capability) is str
            and self.capability == "frozen_generator_primitives_only"
            and type(self.payload_sha256) is str
            and self.payload_sha256 == hashlib.sha256(_canonical_bytes(self.payload_record())).hexdigest()
        )
        return payload_matches and (
            lock is None
            or (
                self.experiment_id == lock.experiment_id
                and self.criterion_sha256 == lock.criterion_sha256
                and self.primitive_contract_sha256 == lock.primitive_contract_sha256
            )
        )


class PipelineSession:
    def __init__(self, experiment_id: str) -> None:
        self.experiment_id = experiment_id
        self.state = PipelineState.INIT
        self.events = ["INIT"]
        self._lock: PredictionLock | None = None
        self._criterion: FalsificationCriterion | None = None
        self._primitive_contract_sha256: str | None = None
        self._oracle_result: Mapping[str, Any] | None = None

    def lock_prediction(
        self,
        criterion: FalsificationCriterion,
        *,
        primitive_contract_sha256: str,
    ) -> PredictionLock:
        if self.state is not PipelineState.INIT:
            self._poison("prediction_lock_out_of_order")
        criterion_issues = criterion.reviewed_schema_issues()
        if criterion_issues:
            self._poison("unreviewed_falsification_criterion:" + ",".join(criterion_issues))
        if self.experiment_id != REVIEWED_EXPERIMENT_ID:
            self._poison("unreviewed_experiment_id")
        if primitive_contract_sha256 != REVIEWED_PRIMITIVE_CONTRACT_SHA256:
            self._poison("unreviewed_primitive_contract")
        lock = PredictionLock.create(
            self.experiment_id,
            criterion,
            primitive_contract_sha256,
        )
        self._lock = lock
        self._criterion = criterion
        self._primitive_contract_sha256 = primitive_contract_sha256
        self.state = PipelineState.PREDICTION_LOCKED
        self.events.append("PREDICTION_LOCKED")
        return lock

    def run_oracle(self, lock: PredictionLock, oracle) -> Mapping[str, Any]:
        if (
            self.state is not PipelineState.PREDICTION_LOCKED
            or self._lock is None
            or self._criterion is None
            or self._primitive_contract_sha256 is None
            or lock != self._lock
            or not lock.authentic(self._criterion, self._primitive_contract_sha256)
            or lock.experiment_id != self.experiment_id
        ):
            self._poison("oracle_without_current_authentic_lock")
        capability = OracleCapability.issue(lock)
        if not capability.authentic(lock):
            self._poison("oracle_capability_authentication_failed")
        result = oracle(capability)
        if type(result) is not dict:
            self._poison("oracle_result_is_not_an_exact_dict")
        if not self._criterion.accepts(result):
            self._poison("oracle_result_schema_or_values_invalid")
        self._oracle_result = dict(result)
        self.state = PipelineState.ORACLE_RUN
        self.events.append("ORACLE_RUN")
        return self._oracle_result

    def verify(self, lock: PredictionLock) -> tuple[str, ...]:
        if (
            self.state is not PipelineState.ORACLE_RUN
            or self._lock != lock
            or self._criterion is None
            or self._primitive_contract_sha256 is None
            or self._oracle_result is None
            or not lock.authentic(self._criterion, self._primitive_contract_sha256)
        ):
            self._poison("verification_without_current_authentic_lock")
        if not self._criterion.accepts(self._oracle_result):
            self._poison("oracle_falsified_locked_prediction")
        self.state = PipelineState.VERIFIED
        self.events.append("VERIFIED")
        return tuple(self.events)

    def predictor_access_after_oracle(self) -> None:
        if self.state in (PipelineState.ORACLE_RUN, PipelineState.VERIFIED):
            self._poison("predictor_access_after_oracle")

    def _poison(self, reason: str) -> None:
        self.state = PipelineState.POISONED
        self.events.append(f"POISONED:{reason}")
        raise RuntimeError(reason)

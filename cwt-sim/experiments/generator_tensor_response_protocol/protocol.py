"""One-way A-to-V-to-H protocol with terminal access semantics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

from .authority import (
    AuthorityVerificationError,
    _VerifiedAdapterSourceLock,
    _VerifiedPhaseAuthorization,
    phase_request_ids,
    verify_adapter_source_lock,
    verify_phase_authorization,
)
from .broker import (
    ExcessResponse,
    OneShotResponseBroker,
)
from .exact import strict_equal
from .fit import (
    FitRecord,
    PredictionCommit,
    commit_predictions,
    degeneracy_reason,
    fit_exact,
    fit_passes,
    prediction_record,
)
from .geometry_plan import GeometryPlan, geometry_plan, geometry_plan_valid


class ProtocolState(str, Enum):
    PREDICTOR_LOCKED = "PREDICTOR_LOCKED"
    ADAPTER_SOURCE_LOCKED = "ADAPTER_SOURCE_LOCKED"
    CAL_AUTHORIZED = "CAL_AUTHORIZED"
    CAL_ACCESSED = "CAL_ACCESSED"
    CAL_PASS = "CAL_PASS"
    CAL_FAIL = "CAL_FAIL"
    CAL_INDETERMINATE = "CAL_INDETERMINATE"
    DEGENERATE_NONINFORMATIVE_FIT = "DEGENERATE_NONINFORMATIVE_FIT"
    PREDICTIONS_PREPARED = "PREDICTIONS_PREPARED"
    PREDICTIONS_COMMITTED = "PREDICTIONS_COMMITTED"
    V_AUTHORIZED = "V_AUTHORIZED"
    V_ACCESSED = "V_ACCESSED"
    V_PASS = "V_PASS"
    V_FAIL = "V_FAIL"
    V_INDETERMINATE = "V_INDETERMINATE"
    H_AUTHORIZED = "H_AUTHORIZED"
    H_ACCESSED = "H_ACCESSED"
    H_PASS = "H_PASS"
    H_FAIL = "H_FAIL"
    H_INDETERMINATE = "H_INDETERMINATE"
    TERMINAL_INCIDENT = "TERMINAL_INCIDENT"


_SOURCE_TEST_TRANSITIONS = MappingProxyType(
    {
        (ProtocolState.PREDICTOR_LOCKED, "LOCK_VERIFIED"): ProtocolState.ADAPTER_SOURCE_LOCKED,
        (ProtocolState.ADAPTER_SOURCE_LOCKED, "CAL_AUTH_VERIFIED"): ProtocolState.CAL_AUTHORIZED,
        (ProtocolState.CAL_AUTHORIZED, "CAL_ACCESS_STARTED"): ProtocolState.CAL_ACCESSED,
        (ProtocolState.CAL_ACCESSED, "CAL_EXACT_PASS"): ProtocolState.CAL_PASS,
        (ProtocolState.CAL_PASS, "PREDICTIONS_PREPARED"): ProtocolState.PREDICTIONS_PREPARED,
        (
            ProtocolState.PREDICTIONS_PREPARED,
            "PREDICTIONS_DURABLY_COMMITTED",
        ): ProtocolState.PREDICTIONS_COMMITTED,
        (ProtocolState.PREDICTIONS_COMMITTED, "V_AUTH_VERIFIED"): ProtocolState.V_AUTHORIZED,
        (ProtocolState.V_AUTHORIZED, "V_ACCESS_STARTED"): ProtocolState.V_ACCESSED,
        (ProtocolState.V_ACCESSED, "V_ATOMIC_PASS"): ProtocolState.V_PASS,
        (ProtocolState.V_PASS, "H_AUTH_VERIFIED"): ProtocolState.H_AUTHORIZED,
        (ProtocolState.H_AUTHORIZED, "H_ACCESS_STARTED"): ProtocolState.H_ACCESSED,
        (ProtocolState.H_ACCESSED, "H_SCALAR_PASS"): ProtocolState.H_PASS,
    }
)


def nonauthoritative_source_test_trace(events: object) -> dict[str, object]:
    """Exercise the frozen transition graph without minting access authority."""

    if type(events) is not tuple or any(type(event) is not str for event in events):
        raise TypeError("source-test transition events refused")
    state = ProtocolState.PREDICTOR_LOCKED
    for event in events:
        wanted = _SOURCE_TEST_TRANSITIONS.get((state, event))
        if wanted is None:
            raise RuntimeError("source-test transition is out of order")
        state = wanted
    return {
        "authoritative": False,
        "response_accessed": False,
        "state": state.value,
        "events": events,
    }


def nonauthoritative_source_test_model(
    calibration_observations: object,
    confirmation_observations: object,
    heldout_scalar_observation: object,
) -> dict[str, object]:
    """Exercise exact fit/prediction comparisons without a broker or authority."""

    plan = geometry_plan()
    try:
        fit = fit_exact(plan, calibration_observations)
    except (TypeError, ValueError, RuntimeError):
        return {
            "authoritative": False,
            "response_accessed": False,
            "state": ProtocolState.CAL_INDETERMINATE.value,
        }
    if not fit_passes(plan, fit):
        state = ProtocolState.CAL_FAIL
    elif degeneracy_reason(plan, fit) is not None:
        state = ProtocolState.DEGENERATE_NONINFORMATIVE_FIT
    else:
        predictions = commit_predictions(plan, fit)
        if not strict_equal(confirmation_observations, predictions.confirmation_vectors):
            state = ProtocolState.V_FAIL
        elif not strict_equal(heldout_scalar_observation, predictions.heldout_scalar_projection):
            state = ProtocolState.H_FAIL
        else:
            state = ProtocolState.H_PASS
    return {
        "authoritative": False,
        "response_accessed": False,
        "state": state.value,
    }


@dataclass(frozen=True)
class IncidentEntry:
    sequence: int
    state: str
    code: str
    producer_call_count: int


class ProtocolSession:
    """One-way controller backed by external Git records and durable consumption markers."""

    __slots__ = (
        "__plan",
        "__state",
        "__source_lock",
        "__fit",
        "__predictions",
        "__calibration_responses",
        "__degeneracy",
        "_authorization",
        "_session_id",
        "_prior_authority_commit_oid",
        "_prior_record_sha256",
        "_incidents",
    )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("protocol session fields are read-only outside reviewed transitions")

    def __init__(self, plan: GeometryPlan) -> None:
        if not geometry_plan_valid(plan):
            raise TypeError("protocol requires the exact reviewed geometry plan")
        object.__setattr__(self, "_ProtocolSession__plan", plan)
        object.__setattr__(self, "_ProtocolSession__state", ProtocolState.PREDICTOR_LOCKED)
        object.__setattr__(self, "_ProtocolSession__source_lock", None)
        object.__setattr__(self, "_ProtocolSession__fit", None)
        object.__setattr__(self, "_ProtocolSession__predictions", None)
        object.__setattr__(self, "_ProtocolSession__calibration_responses", None)
        object.__setattr__(self, "_ProtocolSession__degeneracy", None)
        object.__setattr__(self, "_authorization", None)
        object.__setattr__(self, "_session_id", None)
        object.__setattr__(self, "_prior_authority_commit_oid", None)
        object.__setattr__(self, "_prior_record_sha256", None)
        object.__setattr__(self, "_incidents", ())

    @property
    def plan(self) -> GeometryPlan:
        return self.__plan

    @property
    def state(self) -> ProtocolState:
        return self.__state

    @property
    def source_lock(self) -> _VerifiedAdapterSourceLock | None:
        return self.__source_lock

    @property
    def fit(self) -> FitRecord | None:
        return self.__fit

    @property
    def predictions(self) -> PredictionCommit | None:
        return self.__predictions

    @property
    def calibration_responses(self) -> tuple[ExcessResponse, ...] | None:
        return self.__calibration_responses

    @property
    def degeneracy(self) -> str | None:
        return self.__degeneracy

    @property
    def incident_ledger(self) -> tuple[IncidentEntry, ...]:
        return self._incidents

    def _record(self, code: str, broker: OneShotResponseBroker | None = None) -> None:
        object.__setattr__(
            self,
            "_incidents",
            (
                *self._incidents,
                IncidentEntry(
                    sequence=len(self._incidents) + 1,
                    state=self.state.value,
                    code=code,
                    producer_call_count=0 if broker is None else broker.call_count,
                ),
            ),
        )

    def bind_adapter_source_lock(self, authority_commit_oid: object) -> None:
        if self.state is not ProtocolState.PREDICTOR_LOCKED:
            raise RuntimeError("adapter source lock may be bound exactly once")
        try:
            binding = verify_adapter_source_lock(
                authority_commit_oid,
                plan_sha256=self.plan.plan_sha256,
            )
        except AuthorityVerificationError:
            raise PermissionError("adapter source lock refused") from None
        object.__setattr__(self, "_ProtocolSession__source_lock", binding)
        object.__setattr__(self, "_prior_authority_commit_oid", binding.authority_commit_oid)
        object.__setattr__(self, "_prior_record_sha256", binding.raw_sha256)
        object.__setattr__(self, "_ProtocolSession__state", ProtocolState.ADAPTER_SOURCE_LOCKED)
        self._record("ADAPTER_SOURCE_LOCK_BOUND")

    def _authorize(
        self,
        authority_commit_oid: object,
        *,
        phase: str,
        sequence: int,
        expected_state: ProtocolState,
        durable_prior_state: str,
    ) -> None:
        if (
            self.state is not expected_state
            or self.source_lock is None
            or self._prior_authority_commit_oid is None
            or self._prior_record_sha256 is None
        ):
            raise RuntimeError(f"{phase} authorization is out of order")
        expected_prediction = (
            None if phase == "CAL" else self.predictions.prediction_sha256 if self.predictions else None
        )
        expected_prediction_record = None if self.predictions is None else prediction_record(self.predictions)
        try:
            authorization = verify_phase_authorization(
                authority_commit_oid,
                phase=phase,
                sequence=sequence,
                source_lock=self.source_lock,
                plan_sha256=self.plan.plan_sha256,
                prior_authority_commit_oid=self._prior_authority_commit_oid,
                prior_record_sha256=self._prior_record_sha256,
                prior_state=durable_prior_state,
                prediction_sha256=expected_prediction,
                prediction_record=expected_prediction_record,
                request_ids=phase_request_ids(phase),
                session_id=self._session_id,
            )
        except AuthorityVerificationError:
            raise PermissionError(f"{phase} authorization refused") from None
        if phase == "V":
            object.__setattr__(
                self,
                "_ProtocolSession__state",
                ProtocolState.PREDICTIONS_COMMITTED,
            )
            self._record("PREDICTIONS_DURABLY_COMMITTED")
        object.__setattr__(self, "_authorization", authorization)
        object.__setattr__(self, "_session_id", authorization.session_id)
        object.__setattr__(self, "_prior_authority_commit_oid", authorization.authority_commit_oid)
        object.__setattr__(self, "_prior_record_sha256", authorization.raw_sha256)
        object.__setattr__(
            self,
            "_ProtocolSession__state",
            {
                "CAL": ProtocolState.CAL_AUTHORIZED,
                "V": ProtocolState.V_AUTHORIZED,
                "H": ProtocolState.H_AUTHORIZED,
            }[phase],
        )
        self._record(f"{phase}_AUTHORIZED")

    def authorize_calibration(self, authority_commit_oid: object) -> None:
        self._authorize(
            authority_commit_oid,
            phase="CAL",
            sequence=1,
            expected_state=ProtocolState.ADAPTER_SOURCE_LOCKED,
            durable_prior_state=ProtocolState.ADAPTER_SOURCE_LOCKED.value,
        )

    def authorize_confirmation(self, authority_commit_oid: object) -> None:
        self._authorize(
            authority_commit_oid,
            phase="V",
            sequence=2,
            expected_state=ProtocolState.PREDICTIONS_PREPARED,
            durable_prior_state=ProtocolState.PREDICTIONS_COMMITTED.value,
        )

    def authorize_heldout(self, authority_commit_oid: object) -> None:
        self._authorize(
            authority_commit_oid,
            phase="H",
            sequence=3,
            expected_state=ProtocolState.V_PASS,
            durable_prior_state=ProtocolState.V_PASS.value,
        )

    def _broker_authorization(self, phase: str) -> _VerifiedPhaseAuthorization:
        del phase
        raise PermissionError("in-process broker authorization is nonauthoritative")

    def access_calibration(self, broker: OneShotResponseBroker) -> FitRecord | None:
        del broker
        raise PermissionError("calibration executes only in the fresh whole-phase child")

    def commit_predictions(self) -> PredictionCommit:
        if self.state is not ProtocolState.CAL_PASS or self.fit is None:
            raise RuntimeError("predictions require CAL_PASS")
        object.__setattr__(
            self,
            "_ProtocolSession__predictions",
            commit_predictions(self.plan, self.fit),
        )
        object.__setattr__(self, "_ProtocolSession__state", ProtocolState.PREDICTIONS_PREPARED)
        self._record("PREDICTIONS_PREPARED_FOR_EXTERNAL_COMMIT")
        return self.predictions

    def access_confirmation(self, broker: OneShotResponseBroker) -> bool:
        del broker
        raise PermissionError("confirmation executes only in the fresh whole-phase child")

    def access_heldout(self, broker: OneShotResponseBroker) -> bool:
        del broker
        raise PermissionError("heldout executes only in the fresh whole-phase child")

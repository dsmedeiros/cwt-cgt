"""Restricted criterion lock and oracle capability state machine."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum

from .contract import MODEL_CONTRACT, sha256_record


class PipelineState(str, Enum):
    INIT = "INIT"
    PREDICTION_LOCKED = "PREDICTION_LOCKED"
    ORACLE_RUN = "ORACLE_RUN"
    VERIFIED = "VERIFIED"
    POISONED = "POISONED"


@dataclass(frozen=True)
class FalsificationCriterion:
    criterion_id: str = "REFUTE_SCALAR_KAPPA_BY_EXACT_SIGN_NONCOLLINEARITY"
    comparison_rule: str = (
        "Omega_dt_and_F_dt_have_same_negative_sign_while_Omega_tb_positive_and_F_tb_negative"
    )
    same_curvature_or_scalar_map_only: bool = True
    general_linear_map_refutation_requested: bool = False
    affine_or_nonlinear_map_refutation_requested: bool = False
    heldout_claim_requested: bool = False


REVIEWED_CRITERION = FalsificationCriterion()
REVIEWED_EXPERIMENT_ID = "loop_flux_counting_curvature_proof"
REVIEWED_CONTRACT_SHA256 = "d5500b023825a84b75f1dedac2129f01e02542f131f3060d53f9ec5488e90db6"
REVIEWED_CRITERION_SHA256 = "e33c61c419d2118eaf2840407006f1277c94694ad22a182b079258966c2710c4"
REVIEWED_CAPABILITY_PAYLOAD_SHA256 = "ed951831cd21f6dc25576f66fde169c4c26ab6a836715f94751329a2d46830e9"


@dataclass(frozen=True)
class PredictionLock:
    experiment_id: str
    contract_sha256: str
    criterion_sha256: str
    payload_sha256: str


@dataclass(frozen=True)
class OracleCapability:
    experiment_id: str
    contract_sha256: str
    criterion_sha256: str
    payload_sha256: str

    def authentic(self) -> bool:
        if not all(
            type(value) is str
            for value in (
                self.experiment_id,
                self.contract_sha256,
                self.criterion_sha256,
                self.payload_sha256,
            )
        ):
            return False
        return (
            self.experiment_id == REVIEWED_EXPERIMENT_ID
            and self.contract_sha256 == REVIEWED_CONTRACT_SHA256
            and self.criterion_sha256 == REVIEWED_CRITERION_SHA256
            and self.payload_sha256 == REVIEWED_CAPABILITY_PAYLOAD_SHA256
        )


def _strict_oracle_record(record: object, capability: OracleCapability) -> bool:
    if type(record) is not dict:
        return False
    if tuple(record) != (
        "authority",
        "accepted_inputs",
        "capability_payload_sha256",
        "capability_payload_authenticated",
        "prediction_or_geometry_payload_received",
        "B",
        "F",
    ):
        return False
    if record["authority"] != "independent_exact_generator_Drazin_oracle":
        return False
    if record["accepted_inputs"] != "generator_primitives_plus_authenticated_criterion_digest":
        return False
    if record["capability_payload_sha256"] != capability.payload_sha256:
        return False
    if record["capability_payload_authenticated"] is not True:
        return False
    if record["prediction_or_geometry_payload_received"] is not False:
        return False
    from fractions import Fraction

    for key in ("B", "F"):
        value = record[key]
        if type(value) is not tuple or len(value) != 3:
            return False
        if not all(type(item) is Fraction for item in value):
            return False
    return True


class PipelineSession:
    def __init__(self) -> None:
        self.state = PipelineState.INIT
        self.events = [PipelineState.INIT.value]
        self.lock: PredictionLock | None = None
        self.oracle_record: dict[str, object] | None = None

    def _poison(self, message: str) -> None:
        self.state = PipelineState.POISONED
        self.events.append(PipelineState.POISONED.value)
        raise RuntimeError(message)

    def lock_prediction(self, criterion: FalsificationCriterion) -> PredictionLock:
        if self.state is not PipelineState.INIT:
            self._poison("criterion can only be locked from INIT")
        if type(criterion) is not FalsificationCriterion:
            self._poison("criterion has the wrong exact type")
        try:
            criterion_sha = sha256_record(asdict(criterion))
        except (TypeError, ValueError, OverflowError):
            self._poison("criterion is not canonical")
        if criterion_sha != REVIEWED_CRITERION_SHA256:
            self._poison("criterion differs from the reviewed scalar falsification rule")
        contract_sha = sha256_record(asdict(MODEL_CONTRACT))
        payload_sha = sha256_record(
            {
                "experiment_id": MODEL_CONTRACT.experiment_id,
                "contract_sha256": contract_sha,
                "criterion_sha256": criterion_sha,
            }
        )
        if (
            MODEL_CONTRACT.experiment_id != REVIEWED_EXPERIMENT_ID
            or contract_sha != REVIEWED_CONTRACT_SHA256
            or criterion_sha != REVIEWED_CRITERION_SHA256
            or payload_sha != REVIEWED_CAPABILITY_PAYLOAD_SHA256
        ):
            self._poison("criterion capability differs from reviewed cryptographic identity")
        self.lock = PredictionLock(
            experiment_id=MODEL_CONTRACT.experiment_id,
            contract_sha256=contract_sha,
            criterion_sha256=criterion_sha,
            payload_sha256=payload_sha,
        )
        self.state = PipelineState.PREDICTION_LOCKED
        self.events.append(PipelineState.PREDICTION_LOCKED.value)
        return self.lock

    def capability(self) -> OracleCapability:
        if self.state is not PipelineState.PREDICTION_LOCKED or self.lock is None:
            self._poison("oracle capability requested before criterion lock")
        return OracleCapability(**asdict(self.lock))

    def accept_oracle(self, capability: OracleCapability, record: object) -> None:
        if self.state is not PipelineState.PREDICTION_LOCKED or self.lock is None:
            self._poison("oracle result arrived out of order")
        if type(capability) is not OracleCapability or not capability.authentic():
            self._poison("oracle capability is not authentic")
        if asdict(capability) != asdict(self.lock):
            self._poison("oracle capability does not match the current lock")
        if not _strict_oracle_record(record, capability):
            self._poison("oracle result schema or types are invalid")
        self.oracle_record = record  # type: ignore[assignment]
        self.state = PipelineState.ORACLE_RUN
        self.events.append(PipelineState.ORACLE_RUN.value)

    def verify(self) -> None:
        if self.state is not PipelineState.ORACLE_RUN or self.oracle_record is None:
            self._poison("verification requires one authenticated oracle result")
        self.state = PipelineState.VERIFIED
        self.events.append(PipelineState.VERIFIED.value)

    def record(self) -> dict[str, object]:
        return {
            "state": self.state.value,
            "event_log": tuple(self.events),
            "event_log_exact": tuple(self.events) == ("INIT", "PREDICTION_LOCKED", "ORACLE_RUN", "VERIFIED"),
            "lock": asdict(self.lock) if self.lock is not None else None,
            "criterion": asdict(REVIEWED_CRITERION),
            "oracle": self.oracle_record,
            "general_map_or_heldout_requested": False,
        }

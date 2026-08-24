"""Count-blind geometry and call-plan lane; it has no response capability."""

from __future__ import annotations

from dataclasses import astuple, dataclass
from functools import lru_cache

from experiments.generator_tensor_prediction_protocol.connection_eligibility import connection_basis
from experiments.generator_tensor_prediction_protocol.contract import (
    A_CENTERS as PREDICTOR_A_CENTERS,
    HELDOUT_AREA_VECTOR as PREDICTOR_HELDOUT_AREA_VECTOR,
    HELDOUT_CENTER as PREDICTOR_HELDOUT_CENTER,
    V_CENTERS as PREDICTOR_V_CENTERS,
)

from .contract import (
    CALIBRATION_CENTERS,
    COMPONENT_ORDER,
    CONFIRMATION_CENTERS,
    CONTRACT_SHA256,
    GEOMETRY_PLAN_SHA256,
    HELDOUT_AREA_VECTOR,
    HELDOUT_CENTER,
    TARGET_EXPRESSION,
    calibration_call_plan,
    confirmation_call_plan,
    heldout_call_plan,
)
from .exact import Matrix, Vector, canonical_sha256, require_matrix, strict_equal

REVIEWED_CRITERION_SHA256 = "9d87d265cde1e921d89bc49367be4be709e1a281d1816568a426c34d8c89ff0a"
REVIEWED_GEOMETRY_PLAN_SHA256 = GEOMETRY_PLAN_SHA256
REVIEWED_GEOMETRY_RECORD_SHA256 = "313831860f2972d9fefda8466ba1e7bb856efe88d514e9ea07ec31ee0d3c21a2"


@dataclass(frozen=True)
class GeometryPlan:
    calibration_centers: tuple
    calibration_matrices: tuple[Matrix, ...]
    confirmation_centers: tuple
    confirmation_matrices: tuple[Matrix, Matrix]
    heldout_center: tuple
    heldout_matrix: Matrix
    heldout_area_vector: tuple[int, int, int]
    heldout_projection_row: Vector
    component_order: tuple[str, str, str]
    target_expression: str
    calibration_call_plan: tuple
    confirmation_call_plan: tuple
    heldout_call_plan: tuple
    criterion_sha256: str
    plan_sha256: str


def _basis_matrix(center: tuple) -> Matrix:
    basis = connection_basis(center)
    matrix = tuple(tuple(basis[column][row] for column in range(3)) for row in range(3))
    return require_matrix(matrix, rows=3, columns=3, label="count-blind basis matrix")


def _criterion_payload() -> dict[str, object]:
    return {
        "contract_sha256": CONTRACT_SHA256,
        "target_expression": TARGET_EXPRESSION,
        "component_order": COMPONENT_ORDER,
        "calibration_centers": CALIBRATION_CENTERS,
        "confirmation_centers": CONFIRMATION_CENTERS,
        "heldout_center": HELDOUT_CENTER,
        "heldout_area_vector": HELDOUT_AREA_VECTOR,
        "fit_rule": "k=(X^T X)^-1 X^T y",
        "rank_rule": "exact_rank_3",
        "residual_rule": "all_18_exactly_zero",
        "confirmation_rule": "both_complete_vectors_exact_before_H",
        "heldout_rule": "scalar_projection_only",
    }


@lru_cache(maxsize=1)
def _geometry_plan_fields() -> tuple[object, ...]:
    if not (
        strict_equal(PREDICTOR_A_CENTERS, CALIBRATION_CENTERS)
        and strict_equal(PREDICTOR_V_CENTERS, CONFIRMATION_CENTERS)
        and strict_equal(PREDICTOR_HELDOUT_CENTER, HELDOUT_CENTER)
        and strict_equal(PREDICTOR_HELDOUT_AREA_VECTOR, HELDOUT_AREA_VECTOR)
    ):
        raise RuntimeError("locked predictor geometry points differ")
    calibration_matrices = tuple(_basis_matrix(center) for center in CALIBRATION_CENTERS)
    confirmation_matrices = tuple(_basis_matrix(center) for center in CONFIRMATION_CENTERS)
    heldout_matrix = _basis_matrix(HELDOUT_CENTER)
    heldout_projection_row = tuple(
        sum(
            area * heldout_matrix[component][coefficient]
            for component, area in enumerate(HELDOUT_AREA_VECTOR)
        )
        for coefficient in range(3)
    )
    criterion_sha256 = canonical_sha256(_criterion_payload())
    payload = {
        **_criterion_payload(),
        "calibration_matrices": calibration_matrices,
        "confirmation_matrices": confirmation_matrices,
        "heldout_matrix": heldout_matrix,
        "heldout_projection_row": heldout_projection_row,
        "calibration_call_plan": calibration_call_plan(),
        "confirmation_call_plan": confirmation_call_plan(),
        "heldout_call_plan": heldout_call_plan(),
        "response_values_present": False,
    }
    plan_sha256 = canonical_sha256(payload)
    if criterion_sha256 != REVIEWED_CRITERION_SHA256:
        raise RuntimeError("reviewed criterion digest refused")
    if plan_sha256 != REVIEWED_GEOMETRY_PLAN_SHA256:
        raise RuntimeError("reviewed geometry-plan digest refused")
    plan = GeometryPlan(
        calibration_centers=CALIBRATION_CENTERS,
        calibration_matrices=calibration_matrices,
        confirmation_centers=CONFIRMATION_CENTERS,
        confirmation_matrices=confirmation_matrices,  # type: ignore[arg-type]
        heldout_center=HELDOUT_CENTER,
        heldout_matrix=heldout_matrix,
        heldout_area_vector=HELDOUT_AREA_VECTOR,
        heldout_projection_row=heldout_projection_row,
        component_order=COMPONENT_ORDER,
        target_expression=TARGET_EXPRESSION,
        calibration_call_plan=calibration_call_plan(),
        confirmation_call_plan=confirmation_call_plan(),
        heldout_call_plan=heldout_call_plan(),
        criterion_sha256=criterion_sha256,
        plan_sha256=plan_sha256,
    )
    return astuple(plan)


def geometry_plan() -> GeometryPlan:
    """Return a fresh authority object backed only by cached immutable tuple fields."""

    return GeometryPlan(*_geometry_plan_fields())


def geometry_plan_record() -> dict[str, object]:
    plan = geometry_plan()
    record = {
        "authority": "locked_count_blind_predictor_geometry_only",
        "calibration_centers": plan.calibration_centers,
        "calibration_basis_matrices": plan.calibration_matrices,
        "confirmation_centers": plan.confirmation_centers,
        "confirmation_basis_matrices": plan.confirmation_matrices,
        "heldout_center": plan.heldout_center,
        "heldout_area_vector": plan.heldout_area_vector,
        "heldout_basis_matrix": plan.heldout_matrix,
        "heldout_projection_row": plan.heldout_projection_row,
        "component_order": plan.component_order,
        "target_expression": plan.target_expression,
        "calibration_call_plan": plan.calibration_call_plan,
        "confirmation_call_plan": plan.confirmation_call_plan,
        "heldout_call_plan": plan.heldout_call_plan,
        "criterion_sha256": plan.criterion_sha256,
        "plan_sha256": plan.plan_sha256,
        "response_accessed": False,
        "producer_capability_received": False,
    }
    if canonical_sha256(record) != REVIEWED_GEOMETRY_RECORD_SHA256:
        raise RuntimeError("reviewed geometry-record digest refused")
    return record


def geometry_plan_valid(plan: object) -> bool:
    """Strictly bind every plan field; dataclass equality is not an authority."""

    if type(plan) is not GeometryPlan:
        return False
    expected = geometry_plan()
    if not strict_equal(astuple(plan), astuple(expected)):
        return False
    expected_record = {
        "authority": "locked_count_blind_predictor_geometry_only",
        "calibration_centers": expected.calibration_centers,
        "calibration_basis_matrices": expected.calibration_matrices,
        "confirmation_centers": expected.confirmation_centers,
        "confirmation_basis_matrices": expected.confirmation_matrices,
        "heldout_center": expected.heldout_center,
        "heldout_area_vector": expected.heldout_area_vector,
        "heldout_basis_matrix": expected.heldout_matrix,
        "heldout_projection_row": expected.heldout_projection_row,
        "component_order": expected.component_order,
        "target_expression": expected.target_expression,
        "calibration_call_plan": expected.calibration_call_plan,
        "confirmation_call_plan": expected.confirmation_call_plan,
        "heldout_call_plan": expected.heldout_call_plan,
        "criterion_sha256": expected.criterion_sha256,
        "plan_sha256": expected.plan_sha256,
        "response_accessed": False,
        "producer_capability_received": False,
    }
    return (
        type(plan.heldout_area_vector) is tuple
        and len(plan.heldout_area_vector) == 3
        and all(type(item) is int for item in plan.heldout_area_vector)
        and type(plan.component_order) is tuple
        and all(type(item) is str for item in plan.component_order)
        and type(plan.target_expression) is str
        and type(plan.criterion_sha256) is str
        and type(plan.plan_sha256) is str
        and len(plan.criterion_sha256) == 64
        and len(plan.plan_sha256) == 64
        and canonical_sha256(_criterion_payload()) == plan.criterion_sha256
        and plan.plan_sha256 == REVIEWED_GEOMETRY_PLAN_SHA256
        and canonical_sha256(expected_record) == REVIEWED_GEOMETRY_RECORD_SHA256
    )

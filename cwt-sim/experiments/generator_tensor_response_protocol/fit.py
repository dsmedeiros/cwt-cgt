"""Exact fit and prediction lane; this module has no producer capability."""

from __future__ import annotations

from dataclasses import astuple, dataclass
from fractions import Fraction

from .exact import (
    Matrix,
    Vector,
    canonical_sha256,
    determinant_three,
    matrix_multiply,
    matrix_vector,
    require_vector,
    solve_three,
    stack_rows,
    strict_equal,
    transpose,
)
from .geometry_plan import GeometryPlan, geometry_plan, geometry_plan_valid


@dataclass(frozen=True)
class FitRecord:
    plan_sha256: str
    observed_deltas: tuple[Vector, ...]
    design_matrix: Matrix
    target_vector: Vector
    coefficients: Vector
    gram_matrix: Matrix
    gram_inverse: Matrix
    normal_rhs: Vector
    gram_determinant: Fraction
    exact_rank: int
    residuals: Vector
    fit_sha256: str


@dataclass(frozen=True)
class PredictionCommit:
    fit: FitRecord
    coefficients: Vector
    confirmation_vectors: tuple[Vector, Vector]
    heldout_scalar_projection: Fraction
    plan_sha256: str
    fit_sha256: str
    prediction_sha256: str


def fit_exact(plan: GeometryPlan, observed_deltas: object) -> FitRecord:
    if not geometry_plan_valid(plan):
        raise TypeError("fit requires the exact geometry-plan type")
    if type(observed_deltas) is not tuple or len(observed_deltas) != 6:
        raise TypeError("calibration must contain six complete vectors")
    if len({id(vector) for vector in observed_deltas}) != 6:
        raise RuntimeError("calibration vectors alias")
    observed = tuple(
        require_vector(vector, length=3, label=f"calibration delta {index}")
        for index, vector in enumerate(observed_deltas)
    )
    design = stack_rows(plan.calibration_matrices)
    target = tuple(component for vector in observed for component in vector)
    if len(design) != 18 or len(target) != 18:
        raise RuntimeError("calibration design must contain exactly eighteen equations")
    design_t = transpose(design)
    gram = matrix_multiply(design_t, design)
    determinant = determinant_three(gram)
    if determinant == 0:
        raise ValueError("calibration design rank is not three")
    rhs = matrix_vector(design_t, target)
    coefficients = solve_three(gram, rhs)
    inverse_columns = tuple(
        solve_three(
            gram,
            tuple(Fraction(1) if row == column else Fraction(0) for row in range(3)),
        )
        for column in range(3)
    )
    gram_inverse = transpose(inverse_columns)
    fitted = matrix_vector(design, coefficients)
    residuals = tuple(predicted - actual for predicted, actual in zip(fitted, target, strict=True))
    record = {
        "fit_rule": "k=(X^T X)^-1 X^T y",
        "plan_sha256": plan.plan_sha256,
        "observed_deltas": observed,
        "design_matrix": design,
        "target_vector": target,
        "coefficients": coefficients,
        "gram_matrix": gram,
        "gram_inverse": gram_inverse,
        "normal_rhs": rhs,
        "gram_determinant": determinant,
        "exact_rank": 3,
        "residuals": residuals,
        "residual_count": len(residuals),
        "all_residuals_exactly_zero": all(value == 0 for value in residuals),
        "intercept": None,
        "normalization": None,
        "sign_flip": None,
        "weights": None,
        "regularization": None,
        "tolerance": None,
        "fallback": None,
    }
    return FitRecord(
        plan_sha256=plan.plan_sha256,
        observed_deltas=observed,
        design_matrix=design,
        target_vector=target,
        coefficients=coefficients,
        gram_matrix=gram,
        gram_inverse=gram_inverse,
        normal_rhs=rhs,
        gram_determinant=determinant,
        exact_rank=3,
        residuals=residuals,
        fit_sha256=canonical_sha256(record),
    )


def fit_passes(plan: GeometryPlan, record: object) -> bool:
    if not geometry_plan_valid(plan) or type(record) is not FitRecord:
        return False
    try:
        recomputed = fit_exact(plan, record.observed_deltas)
    except (TypeError, ValueError, RuntimeError):
        return False
    return (
        strict_fit_equal(record, recomputed)
        and record.exact_rank == 3
        and type(record.exact_rank) is int
        and type(record.gram_determinant) is Fraction
        and record.gram_determinant != 0
        and type(record.residuals) is tuple
        and len(record.residuals) == 18
        and all(type(value) is Fraction and value == 0 for value in record.residuals)
    )


def strict_fit_equal(left: FitRecord, right: FitRecord) -> bool:
    return (
        type(left) is FitRecord
        and type(right) is FitRecord
        and strict_equal(
            astuple(left),
            astuple(right),
        )
    )


def fit_record(plan: GeometryPlan, record: FitRecord) -> dict[str, object]:
    """Return the complete independently recomputed fit authority payload."""

    if not fit_passes(plan, record):
        raise RuntimeError("fit record is not an exact passing calibration")
    return {
        "fit_rule": "k=(X^T X)^-1 X^T y",
        "plan_sha256": record.plan_sha256,
        "observed_deltas": record.observed_deltas,
        "design_matrix": record.design_matrix,
        "target_vector": record.target_vector,
        "coefficients": record.coefficients,
        "gram_matrix": record.gram_matrix,
        "gram_inverse": record.gram_inverse,
        "normal_rhs": record.normal_rhs,
        "gram_determinant": record.gram_determinant,
        "exact_rank": record.exact_rank,
        "residuals": record.residuals,
        "residual_count": len(record.residuals),
        "all_residuals_exactly_zero": all(value == 0 for value in record.residuals),
        "intercept": None,
        "normalization": None,
        "sign_flip": None,
        "weights": None,
        "regularization": None,
        "tolerance": None,
        "fallback": None,
        "fit_sha256": record.fit_sha256,
    }


def degeneracy_reason(plan: GeometryPlan, record: FitRecord) -> str | None:
    if not geometry_plan_valid(plan) or type(record) is not FitRecord or not fit_passes(plan, record):
        raise RuntimeError("degeneracy check requires a passing exact fit")
    if all(value == 0 for value in record.coefficients):
        return "ZERO_COEFFICIENT_VECTOR"
    heldout_scalar = sum(
        coefficient * density
        for coefficient, density in zip(record.coefficients, plan.heldout_projection_row, strict=True)
    )
    if heldout_scalar == 0:
        return "ZERO_LOCKED_HELDOUT_SCALAR"
    return None


def predict_vector(matrix: Matrix, coefficients: Vector) -> Vector:
    coefficients = require_vector(coefficients, length=3, label="prediction coefficients")
    return tuple(item for item in matrix_vector(matrix, coefficients))


def commit_predictions(plan: GeometryPlan, fit: FitRecord) -> PredictionCommit:
    if not geometry_plan_valid(plan) or type(fit) is not FitRecord or not fit_passes(plan, fit):
        raise RuntimeError("predictions require an exact passing calibration fit")
    if degeneracy_reason(plan, fit) is not None:
        raise RuntimeError("degenerate noninformative fit cannot produce predictions")
    confirmation_vectors = tuple(
        predict_vector(matrix, fit.coefficients) for matrix in plan.confirmation_matrices
    )
    heldout_scalar = sum(
        coefficient * density
        for coefficient, density in zip(fit.coefficients, plan.heldout_projection_row, strict=True)
    )
    payload = {
        "plan_sha256": plan.plan_sha256,
        "fit_sha256": fit.fit_sha256,
        "fit_record": fit_record(plan, fit),
        "coefficients": fit.coefficients,
        "confirmation_vectors": confirmation_vectors,
        "heldout_scalar_projection": heldout_scalar,
        "confirmation_values_complete": True,
        "heldout_vector_committed_or_exposed": False,
    }
    prediction = PredictionCommit(
        fit=fit,
        coefficients=tuple(item for item in fit.coefficients),
        confirmation_vectors=tuple(tuple(item for item in vector) for vector in confirmation_vectors),  # type: ignore[arg-type]
        heldout_scalar_projection=heldout_scalar,
        plan_sha256=plan.plan_sha256,
        fit_sha256=fit.fit_sha256,
        prediction_sha256=canonical_sha256(payload),
    )
    prediction_record(prediction)
    return prediction


def prediction_record(prediction: PredictionCommit) -> dict[str, object]:
    if type(prediction) is not PredictionCommit:
        raise TypeError("prediction commit type refused")
    plan = geometry_plan()
    coefficients = require_vector(
        prediction.coefficients,
        length=3,
        label="prediction coefficients",
    )
    if (
        type(prediction.fit) is not FitRecord
        or not fit_passes(plan, prediction.fit)
        or prediction.fit.fit_sha256 != prediction.fit_sha256
        or not strict_equal(prediction.fit.coefficients, coefficients)
        or type(prediction.plan_sha256) is not str
        or prediction.plan_sha256 != plan.plan_sha256
        or type(prediction.fit_sha256) is not str
        or len(prediction.fit_sha256) != 64
        or any(character not in "0123456789abcdef" for character in prediction.fit_sha256)
        or type(prediction.prediction_sha256) is not str
        or len(prediction.prediction_sha256) != 64
        or any(character not in "0123456789abcdef" for character in prediction.prediction_sha256)
        or type(prediction.confirmation_vectors) is not tuple
        or len(prediction.confirmation_vectors) != 2
        or len({id(vector) for vector in prediction.confirmation_vectors}) != 2
        or any(vector is prediction.coefficients for vector in prediction.confirmation_vectors)
        or type(prediction.heldout_scalar_projection) is not Fraction
        or all(value == 0 for value in coefficients)
        or prediction.heldout_scalar_projection == 0
    ):
        raise TypeError("prediction commit schema refused")
    confirmation = tuple(
        require_vector(vector, length=3, label=f"prediction confirmation {index}")
        for index, vector in enumerate(prediction.confirmation_vectors)
    )
    expected_confirmation = tuple(
        predict_vector(matrix, coefficients) for matrix in plan.confirmation_matrices
    )
    expected_heldout = sum(
        coefficient * density
        for coefficient, density in zip(coefficients, plan.heldout_projection_row, strict=True)
    )
    if (
        not strict_equal(confirmation, expected_confirmation)
        or prediction.heldout_scalar_projection != expected_heldout
    ):
        raise RuntimeError("prediction values differ from the locked geometry plan")
    payload = {
        "plan_sha256": prediction.plan_sha256,
        "fit_sha256": prediction.fit_sha256,
        "fit_record": fit_record(plan, prediction.fit),
        "coefficients": prediction.coefficients,
        "confirmation_vectors": prediction.confirmation_vectors,
        "heldout_scalar_projection": prediction.heldout_scalar_projection,
        "confirmation_values_complete": True,
        "heldout_vector_committed_or_exposed": False,
    }
    if canonical_sha256(payload) != prediction.prediction_sha256:
        raise RuntimeError("prediction commit digest refused")
    return payload


def _json_fraction(value: object) -> Fraction:
    if type(value) is not dict or set(value) != {"denominator_hex", "numerator_hex"}:
        raise TypeError("canonical Fraction JSON refused")
    numerator_text = value["numerator_hex"]
    denominator_text = value["denominator_hex"]
    if type(numerator_text) is not str or type(denominator_text) is not str:
        raise TypeError("canonical Fraction JSON type refused")
    negative = numerator_text.startswith("-")
    numerator_digits = numerator_text[1:] if negative else numerator_text
    if (
        not numerator_digits
        or not denominator_text
        or any(character not in "0123456789abcdef" for character in numerator_digits)
        or any(character not in "0123456789abcdef" for character in denominator_text)
        or (len(numerator_digits) > 1 and numerator_digits.startswith("0"))
        or (len(denominator_text) > 1 and denominator_text.startswith("0"))
    ):
        raise TypeError("canonical Fraction JSON digits refused")
    numerator = int(numerator_digits, 16) * (-1 if negative else 1)
    denominator = int(denominator_text, 16)
    if denominator <= 0:
        raise TypeError("canonical Fraction JSON denominator refused")
    result = Fraction(numerator, denominator)
    if result.numerator != numerator or result.denominator != denominator:
        raise TypeError("canonical Fraction JSON was not reduced")
    return result


def _json_vector(value: object, *, length: int, label: str) -> Vector:
    if type(value) is not list or len(value) != length:
        raise TypeError(f"{label} JSON vector refused")
    return tuple(_json_fraction(item) for item in value)


def _json_matrix(value: object, *, rows: int, columns: int, label: str) -> Matrix:
    if type(value) is not list or len(value) != rows:
        raise TypeError(f"{label} JSON matrix refused")
    return tuple(_json_vector(row, length=columns, label=label) for row in value)


def validate_canonical_prediction_payload(payload: object, prediction_sha256: object) -> bool:
    """Reconstruct and validate a Git-carried prediction record from strict JSON types."""

    keys = {
        "plan_sha256",
        "fit_sha256",
        "fit_record",
        "coefficients",
        "confirmation_vectors",
        "heldout_scalar_projection",
        "confirmation_values_complete",
        "heldout_vector_committed_or_exposed",
    }
    fit_keys = {
        "fit_rule",
        "plan_sha256",
        "observed_deltas",
        "design_matrix",
        "target_vector",
        "coefficients",
        "gram_matrix",
        "gram_inverse",
        "normal_rhs",
        "gram_determinant",
        "exact_rank",
        "residuals",
        "residual_count",
        "all_residuals_exactly_zero",
        "intercept",
        "normalization",
        "sign_flip",
        "weights",
        "regularization",
        "tolerance",
        "fallback",
        "fit_sha256",
    }
    try:
        if (
            type(payload) is not dict
            or set(payload) != keys
            or type(prediction_sha256) is not str
            or len(prediction_sha256) != 64
            or any(character not in "0123456789abcdef" for character in prediction_sha256)
            or canonical_sha256(payload) != prediction_sha256
            or type(payload["fit_record"]) is not dict
            or set(payload["fit_record"]) != fit_keys
        ):
            return False
        raw_fit = payload["fit_record"]
        plan = geometry_plan()
        if (
            type(payload["plan_sha256"]) is not str
            or payload["plan_sha256"] != plan.plan_sha256
            or type(payload["fit_sha256"]) is not str
            or type(raw_fit["fit_sha256"]) is not str
            or payload["fit_sha256"] != raw_fit["fit_sha256"]
            or raw_fit["fit_rule"] != "k=(X^T X)^-1 X^T y"
            or type(raw_fit["fit_rule"]) is not str
            or raw_fit["plan_sha256"] != plan.plan_sha256
            or type(raw_fit["plan_sha256"]) is not str
            or type(raw_fit["exact_rank"]) is not int
            or raw_fit["exact_rank"] != 3
            or type(raw_fit["residual_count"]) is not int
            or raw_fit["residual_count"] != 18
            or raw_fit["all_residuals_exactly_zero"] is not True
            or type(raw_fit["all_residuals_exactly_zero"]) is not bool
            or any(
                raw_fit[name] is not None
                for name in (
                    "intercept",
                    "normalization",
                    "sign_flip",
                    "weights",
                    "regularization",
                    "tolerance",
                    "fallback",
                )
            )
            or payload["confirmation_values_complete"] is not True
            or type(payload["confirmation_values_complete"]) is not bool
            or payload["heldout_vector_committed_or_exposed"] is not False
            or type(payload["heldout_vector_committed_or_exposed"]) is not bool
        ):
            return False
        observed_raw = raw_fit["observed_deltas"]
        if type(observed_raw) is not list or len(observed_raw) != 6:
            return False
        observed = tuple(
            _json_vector(vector, length=3, label="canonical observed delta") for vector in observed_raw
        )
        fit = FitRecord(
            plan_sha256=raw_fit["plan_sha256"],
            observed_deltas=observed,
            design_matrix=_json_matrix(raw_fit["design_matrix"], rows=18, columns=3, label="design"),
            target_vector=_json_vector(raw_fit["target_vector"], length=18, label="target"),
            coefficients=_json_vector(raw_fit["coefficients"], length=3, label="fit coefficients"),
            gram_matrix=_json_matrix(raw_fit["gram_matrix"], rows=3, columns=3, label="Gram"),
            gram_inverse=_json_matrix(raw_fit["gram_inverse"], rows=3, columns=3, label="Gram inverse"),
            normal_rhs=_json_vector(raw_fit["normal_rhs"], length=3, label="normal RHS"),
            gram_determinant=_json_fraction(raw_fit["gram_determinant"]),
            exact_rank=raw_fit["exact_rank"],
            residuals=_json_vector(raw_fit["residuals"], length=18, label="residuals"),
            fit_sha256=raw_fit["fit_sha256"],
        )
        confirmations_raw = payload["confirmation_vectors"]
        if type(confirmations_raw) is not list or len(confirmations_raw) != 2:
            return False
        prediction = PredictionCommit(
            fit=fit,
            coefficients=_json_vector(payload["coefficients"], length=3, label="coefficients"),
            confirmation_vectors=tuple(
                _json_vector(vector, length=3, label="confirmation") for vector in confirmations_raw
            ),  # type: ignore[arg-type]
            heldout_scalar_projection=_json_fraction(payload["heldout_scalar_projection"]),
            plan_sha256=payload["plan_sha256"],
            fit_sha256=payload["fit_sha256"],
            prediction_sha256=prediction_sha256,
        )
        return canonical_sha256(prediction_record(prediction)) == prediction_sha256
    except (KeyError, TypeError, ValueError, RuntimeError, OverflowError):
        return False

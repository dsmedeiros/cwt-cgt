"""Fail-closed metadata validation for the active-loop design template.

This module is standard-library-only. It applies the recursively closed schema
and semantic G0-G12 gates without importing a numeric adapter, following a
substrate path, or evaluating an outcome. Its strongest state is metadata
verified pending a separately reviewed implementation.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .schema import POWER_GATES, PREIMPLEMENTATION_STATES, protocol_schema


class TemplateState(str, Enum):
    """The four preimplementation states allowed by the design contract."""

    BLOCKED_NO_SUBSTRATE = "BLOCKED_NO_SUBSTRATE"
    BLOCKED_INELIGIBLE_SOURCE = "BLOCKED_INELIGIBLE_SOURCE"
    BLOCKED_INCOMPLETE_METADATA = "BLOCKED_INCOMPLETE_METADATA"
    METADATA_VERIFIED_PENDING_IMPLEMENTATION = "METADATA_VERIFIED_PENDING_IMPLEMENTATION"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "path": self.path, "message": self.message}


@dataclass(frozen=True)
class ValidationReport:
    state: TemplateState
    issues: tuple[ValidationIssue, ...]

    @property
    def metadata_verified(self) -> bool:
        return self.state is TemplateState.METADATA_VERIFIED_PENDING_IMPLEMENTATION and not self.issues

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state.value,
            "metadata_verified": self.metadata_verified,
            "issue_count": len(self.issues),
            "issues": [issue.as_dict() for issue in self.issues],
            "outcome_execution_available": False,
            "maximum_reachable_state": (TemplateState.METADATA_VERIFIED_PENDING_IMPLEMENTATION.value),
        }


REQUIRED_TRUE_SOURCE_FIELDS = (
    "external_source",
    "immutable_primary_raw_measurements",
    "physical_measurement",
    "actually_executed_intervention",
    "randomized_orientation",
    "counterbalanced_orientation",
    "commanded_controls_recorded",
    "achieved_controls_recorded",
    "independent_raw_response_recorded",
    "reset_block_ids_recorded",
    "physical_timestamps_recorded",
    "measurement_units_recorded",
)
REQUIRED_FALSE_SOURCE_FIELDS = (
    "passive_only",
    "simulated",
    "derived_only",
    "natural_cycle_only",
    "model_generated",
)
REQUIRED_SOURCE_TEXT_FIELDS = (
    "immutable_revision",
    "license_identifier",
    "raw_manifest_sha256",
)
SOURCE_ELIGIBILITY_CODES = {
    "SOURCE_DERIVED_ONLY",
    "SOURCE_FIELD_REQUIRED_FALSE",
    "SOURCE_FIELD_REQUIRED_TRUE",
    "SOURCE_MANIFEST_COVERAGE",
    "SOURCE_MODEL_GENERATED",
    "SOURCE_NATURAL_CYCLE",
    "SOURCE_NOT_PHYSICAL",
    "SOURCE_PASSIVE",
    "SOURCE_RAW_HASHES_MISSING",
    "SOURCE_RAW_HASH_INVALID",
    "SOURCE_RAW_PATH_DUPLICATE",
    "SOURCE_RAW_PATH_INVALID",
    "SOURCE_RAW_PATH_PROXY",
    "SOURCE_SYNTHETIC",
    "SOURCE_UNVERSIONED",
}
SOURCE_SPECIFIC_NULL_FIELDS = (
    "calibration_power",
    "physical_response_sesoi",
    "beta_equivalence_margin",
    "beta_interval_definition",
    "response_lower_bound_definition",
    "perpendicular_tensor_margin",
    "perpendicular_ratio_definition",
    "comparator_loss_advantage_margin",
    "comparator_definition",
    "interaction_nondegeneracy_definition",
    "condition_number_threshold",
    "missingness_and_qc_rules",
)
RESPONSE_ALLOWED_FIELDS = (
    "pseudonymous_episode_id",
    "physical_timestamps",
    "calibrated_response",
    "predeclared_response_baseline",
    "response_sensor_qc",
)
RESPONSE_FORBIDDEN_FIELDS = {
    "achieved_control_path",
    "area",
    "area_vector",
    "coupling_label",
    "fitted_coefficient",
    "geometry_state",
    "omega",
    "orientation",
    "path_order",
    "phi",
    "planned_control_path",
}
INFERENCE_TIES_RULE = "count_permuted_T_greater_than_or_equal_to_observed_as_extreme"
INFERENCE_DUPLICATE_RULE = "deduplicate_assignments_and_include_observed_once"
INFERENCE_METHOD_RULE = "exact_if_group_size_at_most_999999_else_999999_seeded_draws"
INDEPENDENT_UNIT = "independently_randomized_washed_out_reset_block"
RANDOMIZATION_GROUP = "all_distinct_balanced_block_level_quartet_sign_code_assignments_within_frozen_strata"
WINDOW_ID_SEMANTICS = "pseudonymous_sha256_prefix_v1"
PSEUDONYM_RE = re.compile(r"ep_[0-9a-f]{16}\Z")
CONTROL_IDENTIFIER_RE = re.compile(r"(?=.{5,}\Z)[a-z][a-z0-9]*(?:_[a-z0-9]+)+\Z")
RAW_PATH_RE = re.compile(
    r"(?!/)(?![A-Za-z]:)(?!.*(?:^|/)\.\.(?:/|$))(?!.*//)" r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*\Z"
)
QUADRATURE_RULE = "timestamp_weighted_trapezoidal_Q_integral_v1"
PROXY_TOKENS = {
    "area",
    "ccw",
    "control",
    "coupling",
    "cw",
    "flux",
    "forward",
    "geometry",
    "minus",
    "omega",
    "orientation",
    "path",
    "phi",
    "plus",
    "reverse",
    "zero",
}
PROHIBITED_UNIT_KINDS = {
    "cycle",
    "loop",
    "rng_seed",
    "sample",
    "seed",
    "sensor",
    "tick",
    "timepoint",
    "window",
}
NONPHYSICAL_TIME_UNITS = {"cycle", "index", "iteration", "sample", "step", "tick", "ticks"}
PROXY_SUBSTRINGS = PROXY_TOKENS | {"treatment"}
NONPHYSICAL_SUBSTRINGS = {"cycle", "sample", "step", "tick"}
CONDITION_LABEL_TOKENS = {
    "ccw",
    "clockwise",
    "counterclockwise",
    "cw",
    "negative",
    "on",
    "positive",
    "zero",
}
COMPACT_CONDITION_ALIASES = CONDITION_LABEL_TOKENS - {"on"}
OUTCOME_FIT_PARTITION_MARKERS = {"confirmation", "heldout", "holdout"}
FORBIDDEN_GENERALIZATIONS = {
    "universal_CWT_or_CGT",
    "topology_or_topological_protection",
    "passive_ridge",
    "strict_locality",
    "population_generalization",
    "charge_without_calibrated_current_units",
}
FUTURE_CLAIM = (
    "Within the frozen named substrate, control region, branch, coupling, readout, "
    "physical-time regime, and loop family, the conjunctive active-loop result met "
    "the locked prediction and mechanism gates."
)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _nonempty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _compact_text(value: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(value).casefold())


def _contains_substring(value: Any, needles: set[str]) -> bool:
    compact = _compact_text(value)
    return any(needle in compact for needle in needles)


def _semantic_tokens(value: Any) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", str(value).casefold()))


def _control_aliases(payload: Mapping[str, Any]) -> set[str]:
    coordinates = _mapping(payload.get("coordinates"))
    identifiers = list(_sequence(coordinates.get("independently_actuable_controls"))) + list(
        _sequence(coordinates.get("right_handed_order"))
    )
    return {
        _compact_text(identifier)
        for identifier in identifiers
        if CONTROL_IDENTIFIER_RE.fullmatch(str(identifier)) is not None
    }


def _has_dynamic_or_condition_proxy(value: Any, payload: Mapping[str, Any]) -> bool:
    tokens = _semantic_tokens(value)
    compact = _compact_text(value)
    if "on" in tokens or any(alias in compact for alias in COMPACT_CONDITION_ALIASES):
        return True
    return any(alias in compact for alias in _control_aliases(payload))


def _has_outcome_fit_language(value: Any) -> bool:
    compact = _compact_text(value)
    return any(marker in compact for marker in OUTCOME_FIT_PARTITION_MARKERS)


def _issue(issues: list[ValidationIssue], code: str, path: str, message: str) -> None:
    issues.append(ValidationIssue(code=code, path=path, message=message))


def _json_identity(value: Any) -> str:
    return json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)


def _type_matches(value: Any, kind: str) -> bool:
    if kind == "null":
        return value is None
    if kind == "boolean":
        return isinstance(value, bool)
    if kind == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)
    if kind == "string":
        return isinstance(value, str)
    if kind == "array":
        return isinstance(value, list)
    if kind == "object":
        return isinstance(value, Mapping)
    return False


def _apply_schema(
    value: Any,
    schema: Mapping[str, Any],
    path: str,
    issues: list[ValidationIssue],
) -> None:
    """Apply the strict subset of JSON Schema used by schema.py."""

    if "const" in schema and value != schema["const"]:
        _issue(issues, "SCHEMA_CONST", path, f"must equal {schema['const']!r}")
    if "enum" in schema and value not in schema["enum"]:
        _issue(issues, "SCHEMA_ENUM", path, f"must be one of {schema['enum']!r}")

    declared = schema.get("type")
    if declared is not None:
        kinds = [declared] if isinstance(declared, str) else list(declared)
        if not any(_type_matches(value, kind) for kind in kinds):
            _issue(issues, "SCHEMA_TYPE", path, f"must have type in {kinds!r}")
            return
        if value is None:
            return

    if isinstance(value, Mapping):
        properties = _mapping(schema.get("properties"))
        required = set(_sequence(schema.get("required")))
        for key in sorted(required - set(value)):
            _issue(issues, "SCHEMA_REQUIRED", f"{path}.{key}", "required field is missing")
        additional = schema.get("additionalProperties", True)
        property_names = _mapping(schema.get("propertyNames"))
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else str(key)
            if property_names:
                _apply_schema(str(key), property_names, f"{path}{{key:{key}}}", issues)
            if key in properties:
                _apply_schema(child, _mapping(properties[key]), child_path, issues)
            elif additional is False:
                _issue(issues, "SCHEMA_UNKNOWN_FIELD", child_path, "unknown field is forbidden")
            elif isinstance(additional, Mapping):
                _apply_schema(child, additional, child_path, issues)
        if "minProperties" in schema and len(value) < schema["minProperties"]:
            _issue(issues, "SCHEMA_MIN_PROPERTIES", path, "mapping has too few entries")

    if isinstance(value, list):
        if "minItems" in schema and len(value) < schema["minItems"]:
            _issue(issues, "SCHEMA_MIN_ITEMS", path, "array has too few items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            _issue(issues, "SCHEMA_MAX_ITEMS", path, "array has too many items")
        if schema.get("uniqueItems"):
            identities = [_json_identity(item) for item in value]
            if len(identities) != len(set(identities)):
                _issue(issues, "SCHEMA_UNIQUE_ITEMS", path, "array items must be unique")
        item_schema = _mapping(schema.get("items"))
        for index, child in enumerate(value):
            _apply_schema(child, item_schema, f"{path}[{index}]", issues)

    if isinstance(value, str):
        if "minLength" in schema and len(value) < schema["minLength"]:
            _issue(issues, "SCHEMA_MIN_LENGTH", path, "string is empty")
        if "pattern" in schema and re.search(str(schema["pattern"]), value) is None:
            _issue(issues, "SCHEMA_PATTERN", path, "string does not match the required pattern")

    if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value):
        if "minimum" in schema and value < schema["minimum"]:
            _issue(issues, "SCHEMA_MINIMUM", path, f"must be >= {schema['minimum']}")
        if "maximum" in schema and value > schema["maximum"]:
            _issue(issues, "SCHEMA_MAXIMUM", path, f"must be <= {schema['maximum']}")
        if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
            _issue(
                issues,
                "SCHEMA_EXCLUSIVE_MINIMUM",
                path,
                f"must be > {schema['exclusiveMinimum']}",
            )


def _check_source(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> bool:
    substrate = _mapping(payload.get("substrate"))
    identifier_present = _nonempty_text(substrate.get("identifier"))
    qualification = _mapping(substrate.get("source_qualification"))
    for field in REQUIRED_TRUE_SOURCE_FIELDS:
        value = qualification.get(field)
        if value is not True:
            code = (
                "SOURCE_NOT_PHYSICAL"
                if field == "physical_measurement" and value is False
                else "SOURCE_FIELD_REQUIRED_TRUE"
            )
            _issue(issues, code, f"substrate.source_qualification.{field}", "must be true")
    for field in REQUIRED_FALSE_SOURCE_FIELDS:
        value = qualification.get(field)
        if value is not False:
            code = "SOURCE_FIELD_REQUIRED_FALSE"
            if value is True:
                code = {
                    "passive_only": "SOURCE_PASSIVE",
                    "simulated": "SOURCE_SYNTHETIC",
                    "derived_only": "SOURCE_DERIVED_ONLY",
                    "natural_cycle_only": "SOURCE_NATURAL_CYCLE",
                    "model_generated": "SOURCE_MODEL_GENERATED",
                }[field]
            _issue(issues, code, f"substrate.source_qualification.{field}", "must be false")
    for field in REQUIRED_SOURCE_TEXT_FIELDS:
        if not _nonempty_text(qualification.get(field)):
            code = "SOURCE_UNVERSIONED" if field == "immutable_revision" else "SOURCE_FIELD_REQUIRED_TRUE"
            _issue(issues, code, f"substrate.source_qualification.{field}", "must be immutable text")
    raw_hashes = qualification.get("raw_file_sha256")
    if not isinstance(raw_hashes, Mapping) or not raw_hashes:
        _issue(
            issues,
            "SOURCE_RAW_HASHES_MISSING",
            "substrate.source_qualification.raw_file_sha256",
            "must cover every immutable primary raw file",
        )
    elif any(
        not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None
        for value in raw_hashes.values()
    ):
        _issue(
            issues,
            "SOURCE_RAW_HASH_INVALID",
            "substrate.source_qualification.raw_file_sha256",
            "every raw file must have a lowercase hexadecimal SHA-256",
        )
    if isinstance(raw_hashes, Mapping):
        raw_paths = [str(path) for path in raw_hashes]
        invalid_paths = [path for path in raw_paths if RAW_PATH_RE.fullmatch(path) is None]
        if invalid_paths:
            _issue(
                issues,
                "SOURCE_RAW_PATH_INVALID",
                "substrate.source_qualification.raw_file_sha256",
                "raw paths must be nonempty canonical relative slash paths without traversal",
            )
        if len({path.casefold() for path in raw_paths}) != len(raw_paths):
            _issue(
                issues,
                "SOURCE_RAW_PATH_DUPLICATE",
                "substrate.source_qualification.raw_file_sha256",
                "raw paths must be unique under case folding",
            )
        if any(_has_dynamic_or_condition_proxy(path, payload) for path in raw_paths):
            _issue(
                issues,
                "SOURCE_RAW_PATH_PROXY",
                "substrate.source_qualification.raw_file_sha256",
                "raw paths must not reveal a control, orientation, or coupling condition",
            )
    if re.fullmatch(r"[0-9a-f]{64}", str(qualification.get("raw_manifest_sha256") or "")) is None:
        _issue(
            issues,
            "SOURCE_RAW_HASH_INVALID",
            "substrate.source_qualification.raw_manifest_sha256",
            "must be a lowercase hexadecimal SHA-256",
        )
    manifest_count = qualification.get("raw_manifest_file_count")
    if (
        not isinstance(manifest_count, int)
        or isinstance(manifest_count, bool)
        or not isinstance(raw_hashes, Mapping)
        or manifest_count != len(raw_hashes)
    ):
        _issue(
            issues,
            "SOURCE_MANIFEST_COVERAGE",
            "substrate.source_qualification.raw_manifest_file_count",
            "must equal the number of per-file SHA-256 entries",
        )
    return identifier_present


def _check_coordinates(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    coordinates = _mapping(payload.get("coordinates"))
    dimension = coordinates.get("dimension")
    if dimension != 3 or isinstance(dimension, bool):
        _issue(issues, "DIMENSION_NOT_PRIMARY_3", "coordinates.dimension", "must equal 3")
    controls = list(_sequence(coordinates.get("independently_actuable_controls")))
    order = list(_sequence(coordinates.get("right_handed_order")))
    if (
        len(controls) != 3
        or len({str(value).casefold() for value in controls}) != 3
        or any(CONTROL_IDENTIFIER_RE.fullmatch(str(value)) is None for value in controls)
    ):
        _issue(
            issues,
            "ACTUABLE_CONTROLS_INVALID",
            "coordinates.independently_actuable_controls",
            "must contain three unique canonical structured control identifiers",
        )
    if (
        len(order) != 3
        or any(CONTROL_IDENTIFIER_RE.fullmatch(str(value)) is None for value in order)
        or set(order) != set(controls)
    ):
        _issue(
            issues,
            "RIGHT_HANDED_ORDER_INVALID",
            "coordinates.right_handed_order",
            "must order the same three unique controls",
        )
    if coordinates.get("right_handed_orientation_verified") is not True:
        _issue(
            issues,
            "RIGHT_HANDED_ORDER_UNVERIFIED",
            "coordinates.right_handed_orientation_verified",
            "must be true",
        )
    units = list(_sequence(coordinates.get("units")))
    if len(units) != 3 or any(_contains_substring(unit, NONPHYSICAL_SUBSTRINGS) for unit in units):
        _issue(issues, "CONTROL_UNITS_INVALID", "coordinates.units", "must contain three physical units")
    scales = list(_sequence(coordinates.get("scales")))
    if len(scales) != 3 or any(
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or not math.isfinite(value)
        or value <= 0
        for value in scales
    ):
        _issue(
            issues,
            "CONTROL_SCALES_INVALID",
            "coordinates.scales",
            "must contain three finite positive scales",
        )
    references = list(_sequence(coordinates.get("reference")))
    if len(references) != 3 or any(
        not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value)
        for value in references
    ):
        _issue(
            issues,
            "CONTROL_REFERENCE_INVALID",
            "coordinates.reference",
            "must contain three finite references",
        )


def _check_response(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    firewall = _mapping(payload.get("response_firewall"))
    if tuple(_sequence(firewall.get("reducer_input_fields"))) != RESPONSE_ALLOWED_FIELDS:
        _issue(
            issues,
            "RESPONSE_FIREWALL_FIELD",
            "response_firewall.reducer_input_fields",
            "must equal the response-only schema",
        )
    forbidden = {str(value).casefold() for value in _sequence(firewall.get("forbidden_fields"))}
    if forbidden != RESPONSE_FORBIDDEN_FIELDS:
        _issue(
            issues,
            "RESPONSE_FIREWALL_INCOMPLETE",
            "response_firewall.forbidden_fields",
            "must equal the locked forbidden-field set",
        )
    for key in (
        "response_signal",
        "response_signal_units",
        "response_units",
        "integrated_units_derivation",
        "baseline_definition",
    ):
        if not _nonempty_text(firewall.get(key)):
            _issue(issues, "RESPONSE_DEFINITION_MISSING", f"response_firewall.{key}", "must be frozen")
    for key in (
        "response_signal",
        "response_signal_units",
        "response_units",
        "integrated_units_derivation",
        "baseline_definition",
    ):
        value = firewall.get(key)
        if _contains_substring(value, PROXY_SUBSTRINGS) or _has_dynamic_or_condition_proxy(value, payload):
            _issue(
                issues,
                "RESPONSE_PROXY_SEMANTICS",
                f"response_firewall.{key}",
                "must not reveal geometry, orientation, control, or treatment proxies",
            )
        if ("units" in key or key == "integrated_units_derivation") and _contains_substring(
            value, NONPHYSICAL_SUBSTRINGS
        ):
            _issue(
                issues,
                "RESPONSE_UNITS_NONPHYSICAL",
                f"response_firewall.{key}",
                "must use physical response or integrated-response units, never ticks/samples/cycles",
            )
    if not re.fullmatch(r"[0-9a-f]{64}", str(firewall.get("reducer_code_sha256") or "")):
        _issue(
            issues,
            "RESPONSE_REDUCER_HASH_INVALID",
            "response_firewall.reducer_code_sha256",
            "must be a SHA-256",
        )
    semantics = firewall.get("window_id_semantics")
    if semantics != WINDOW_ID_SEMANTICS:
        _issue(
            issues,
            "RESPONSE_PROXY_POLICY_INVALID",
            "response_firewall.window_id_semantics",
            f"must equal {WINDOW_ID_SEMANTICS}",
        )
    identifiers = _sequence(firewall.get("example_window_ids"))
    if not identifiers:
        _issue(
            issues,
            "RESPONSE_PROXY_IDS_MISSING",
            "response_firewall.example_window_ids",
            "must provide audited nonrevealing examples",
        )
    for identifier in identifiers:
        if (
            PSEUDONYM_RE.fullmatch(str(identifier)) is None
            or _contains_substring(identifier, PROXY_SUBSTRINGS)
            or _has_dynamic_or_condition_proxy(identifier, payload)
        ):
            _issue(
                issues,
                "RESPONSE_PROXY_ID",
                "response_firewall.example_window_ids",
                "identifier reveals a forbidden proxy",
            )
            break
    if firewall.get("geometry_mutation_response_bytes_identical") is not True:
        _issue(
            issues,
            "RESPONSE_FIREWALL_BIT_IDENTITY_UNPROVEN",
            "response_firewall.geometry_mutation_response_bytes_identical",
            "must be true",
        )


def _check_quartet_clock(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    quartet = _mapping(payload.get("quartet"))
    if quartet.get("coupling_levels") != ["on", "zero"] or quartet.get("orientations") != [
        "positive",
        "negative",
    ]:
        _issue(issues, "QUARTET_INCOMPLETE", "quartet", "must be exact on/zero by positive/negative")
    for field in ("exact_zero_coupling_mechanism",):
        if not _nonempty_text(quartet.get(field)):
            _issue(issues, "ZERO_COUPLING_MISSING", f"quartet.{field}", "must be frozen")
    for field in (
        "same_schedule_sensors_and_hysteresis_at_zero",
        "matched_achieved_shape_and_duration",
        "common_physical_clock_verified",
    ):
        if quartet.get(field) is not True:
            _issue(issues, "ORIENTATION_PAIR_INVALID", f"quartet.{field}", "must be true")
    if not re.fullmatch(r"[0-9a-f]{64}", str(quartet.get("assignment_table_sha256") or "")):
        _issue(
            issues, "QUARTET_ASSIGNMENT_HASH_INVALID", "quartet.assignment_table_sha256", "must be a SHA-256"
        )

    clock = _mapping(payload.get("physical_time_protocol"))
    duration = clock.get("duration_seconds")
    dt = clock.get("dt_seconds")
    if (
        not isinstance(duration, (int, float))
        or isinstance(duration, bool)
        or not math.isfinite(duration)
        or duration <= 0
    ):
        _issue(
            issues,
            "PHYSICAL_DURATION_INVALID",
            "physical_time_protocol.duration_seconds",
            "must be finite and positive",
        )
    if (
        not isinstance(dt, (int, float))
        or isinstance(dt, bool)
        or not math.isfinite(dt)
        or dt <= 0
        or (isinstance(duration, (int, float)) and dt >= duration)
    ):
        _issue(
            issues,
            "PHYSICAL_DT_INVALID",
            "physical_time_protocol.dt_seconds",
            "must be finite, positive, and less than duration",
        )
    for field in ("latency_bound_seconds", "jitter_bound_seconds"):
        value = clock.get(field)
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or not math.isfinite(value)
            or value < 0
            or (isinstance(duration, (int, float)) and value >= duration)
        ):
            _issue(
                issues,
                "CLOCK_BOUND_INVALID",
                f"physical_time_protocol.{field}",
                "must be finite, nonnegative, and less than duration",
            )
    closure = clock.get("achieved_path_closure_tolerance")
    if (
        not isinstance(closure, (int, float))
        or isinstance(closure, bool)
        or not math.isfinite(closure)
        or closure <= 0
    ):
        _issue(
            issues,
            "PATH_CLOSURE_TOLERANCE_INVALID",
            "physical_time_protocol.achieved_path_closure_tolerance",
            "must be finite and positive",
        )
    if clock.get("timestamp_units") != "seconds":
        _issue(
            issues,
            "PHYSICAL_TIME_UNITS_INVALID",
            "physical_time_protocol.timestamp_units",
            "must equal seconds",
        )
    for field in (
        "endpoint_rule",
        "achieved_path_source",
        "washout_or_periodic_initialization",
        "waveform_family",
    ):
        if not _nonempty_text(clock.get(field)):
            _issue(
                issues, "PHYSICAL_CLOCK_FIELD_MISSING", f"physical_time_protocol.{field}", "must be frozen"
            )
    if clock.get("quadrature_rule") != QUADRATURE_RULE:
        _issue(
            issues,
            "PHYSICAL_QUADRATURE_INVALID",
            "physical_time_protocol.quadrature_rule",
            f"must equal {QUADRATURE_RULE}",
        )
    dynamics = _mapping(clock.get("control_dynamics_map"))
    if (
        dynamics.get("kind") != "continuous_rate_map"
        or dynamics.get("formula") != "alpha(dt)=1-exp(-dt/tau)"
        or dynamics.get("fixed_alpha_across_dt_ladder") is not False
        or not isinstance(dynamics.get("tau_seconds"), (int, float))
        or isinstance(dynamics.get("tau_seconds"), bool)
        or not math.isfinite(dynamics.get("tau_seconds"))
        or dynamics.get("tau_seconds") <= 0
    ):
        _issue(
            issues,
            "PHYSICAL_RATE_MAP_INVALID",
            "physical_time_protocol.control_dynamics_map",
            "must freeze the continuous-rate alpha(dt) map and forbid fixed-alpha tick refinement",
        )
    heldout = _mapping(clock.get("heldout_level_index"))
    for ladder_name, index_name in (
        ("dt_ladder", "dt"),
        ("duration_ladder", "duration"),
        ("scale_ladder", "scale"),
    ):
        values = list(_sequence(clock.get(ladder_name)))
        valid = len(values) >= 5 and all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            and math.isfinite(value)
            and value > 0
            for value in values
        )
        if not valid or values != sorted(values) or len(values) != len(set(values)):
            _issue(
                issues,
                "LADDER_INVALID",
                f"physical_time_protocol.{ladder_name}",
                "must be a strictly increasing unique positive ladder with at least five levels",
            )
        index = heldout.get(index_name)
        if not isinstance(index, int) or isinstance(index, bool) or index < 0 or index >= len(values):
            _issue(
                issues,
                "HELDOUT_LEVEL_INVALID",
                f"physical_time_protocol.heldout_level_index.{index_name}",
                "must index the frozen ladder",
            )
    dt_ladder = list(_sequence(clock.get("dt_ladder")))
    duration_ladder = list(_sequence(clock.get("duration_ladder")))
    if isinstance(duration, (int, float)) and any(
        isinstance(value, (int, float)) and value >= duration for value in dt_ladder
    ):
        _issue(
            issues,
            "DT_LADDER_EXCEEDS_DURATION",
            "physical_time_protocol.dt_ladder",
            "every dt level must be shorter than the frozen duration",
        )
    if isinstance(dt, (int, float)) and any(
        isinstance(value, (int, float)) and value <= dt for value in duration_ladder
    ):
        _issue(
            issues,
            "DURATION_LADDER_BELOW_DT",
            "physical_time_protocol.duration_ladder",
            "every duration level must exceed the frozen dt",
        )


def _partition_records(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(_mapping(payload.get("cluster_split")).get("partitions"))


def _check_clusters(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    split = _mapping(payload.get("cluster_split"))
    unit = split.get("independent_unit_kind")
    if unit != INDEPENDENT_UNIT:
        _issue(
            issues,
            "PSEUDOREPLICATION_UNIT",
            "cluster_split.independent_unit_kind",
            f"must equal {INDEPENDENT_UNIT}",
        )
    minimum = split.get("minimum_independent_blocks")
    if not isinstance(minimum, int) or isinstance(minimum, bool) or minimum < 20:
        _issue(
            issues,
            "INDEPENDENT_BLOCK_MINIMUM_INVALID",
            "cluster_split.minimum_independent_blocks",
            "must be >=20",
        )
    for key in ("salt", "assignment_rule", "duplicate_detection_rule"):
        if not _nonempty_text(split.get(key)):
            _issue(issues, "SPLIT_RULE_MISSING", f"cluster_split.{key}", "must be frozen")
    partitions = _partition_records(payload)
    aggregate: dict[str, list[str]] = {key: [] for key in ("cluster_ids", "alias_ids", "content_sha256")}
    for name in ("calibration", "reduction_validation", "confirmation"):
        record = _mapping(partitions.get(name))
        arrays = {key: list(_sequence(record.get(key))) for key in aggregate}
        if (
            any(not values for values in arrays.values())
            or len({len(values) for values in arrays.values()}) != 1
        ):
            _issue(
                issues,
                "SPLIT_ARRAY_CLOSURE_INVALID",
                f"cluster_split.partitions.{name}",
                "cluster, alias, and content-hash arrays must be nonempty and equal length",
            )
        for key, values in arrays.items():
            aggregate[key].extend(str(value).casefold() for value in values)
    for key, values in aggregate.items():
        if len(values) != len(set(values)):
            _issue(
                issues,
                "CLUSTER_LEAKAGE",
                f"cluster_split.partitions.*.{key}",
                "duplicates or aliases cross partitions",
            )
    identity_values = aggregate["cluster_ids"] + aggregate["alias_ids"]
    if len(identity_values) != len(set(identity_values)):
        _issue(
            issues,
            "CLUSTER_ALIAS_COLLISION",
            "cluster_split.partitions",
            "cluster and alias identities must be globally disjoint",
        )
    confirmation_count = len(_sequence(_mapping(partitions.get("confirmation")).get("cluster_ids")))
    power = _mapping(_mapping(payload.get("source_specific_freeze_readiness")).get("calibration_power"))
    powered_n = power.get("powered_confirmation_n")
    required_n = max(
        20,
        minimum if isinstance(minimum, int) and not isinstance(minimum, bool) else 20,
        powered_n if isinstance(powered_n, int) and not isinstance(powered_n, bool) else 20,
    )
    if confirmation_count < required_n:
        _issue(
            issues,
            "CONFIRMATION_N_INSUFFICIENT",
            "cluster_split.partitions.confirmation.cluster_ids",
            f"requires at least {required_n} independent confirmation clusters",
        )


def _check_geometry(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    geometry = _mapping(payload.get("geometry_firewall"))
    for field in (
        "state_sensor",
        "state_map_revision",
        "projector_estimator",
        "wilson_estimator",
        "qgt_estimator",
        "gap_overlap_gauge_qc",
    ):
        if not _nonempty_text(geometry.get(field)):
            _issue(issues, "GEOMETRY_DEFINITION_MISSING", f"geometry_firewall.{field}", "must be frozen")
    if not re.fullmatch(r"[0-9a-f]{64}", str(geometry.get("estimator_code_sha256") or "")):
        _issue(
            issues, "GEOMETRY_HASH_INVALID", "geometry_firewall.estimator_code_sha256", "must be a SHA-256"
        )
    if geometry.get("response_signal_access") is not False:
        _issue(
            issues, "GEOMETRY_FIREWALL_BREACH", "geometry_firewall.response_signal_access", "must be false"
        )
    if geometry.get("state_sensor_distinct_from_response") is not True:
        _issue(
            issues,
            "SENSOR_SEPARATION_MISSING",
            "geometry_firewall.state_sensor_distinct_from_response",
            "must be true",
        )
    response_signal = _mapping(payload.get("response_firewall")).get("response_signal")
    if (
        _nonempty_text(response_signal)
        and str(response_signal).casefold() == str(geometry.get("state_sensor") or "").casefold()
    ):
        _issue(
            issues,
            "SENSOR_SEPARATION_MISSING",
            "geometry_firewall.state_sensor",
            "must differ from response signal",
        )

    predictor = _mapping(payload.get("predictor_geometry"))
    mode = predictor.get("mode")
    if mode not in {"common_on_geometry", "geometry_interaction"}:
        _issue(
            issues,
            "PREDICTOR_GEOMETRY_MODE_INVALID",
            "predictor_geometry.mode",
            "must freeze common/on or interaction geometry",
        )
    if predictor.get("finite_flux_estimator") not in {"integrated_curvature", "wilson_loop"}:
        _issue(
            issues,
            "FINITE_FLUX_ESTIMATOR_INVALID",
            "predictor_geometry.finite_flux_estimator",
            "must be integrated_curvature or wilson_loop",
        )
    if predictor.get("local_approximation_in_remainder") is not True:
        _issue(
            issues,
            "LOCAL_FLUX_REMAINDER_MISSING",
            "predictor_geometry.local_approximation_in_remainder",
            "must be true",
        )
    if mode == "common_on_geometry":
        for field in ("zero_state_equivalence", "zero_achieved_path_equivalence", "zero_omega_equivalence"):
            if predictor.get(field) is not True:
                _issue(
                    issues, "ZERO_GEOMETRY_EQUIVALENCE_MISSING", f"predictor_geometry.{field}", "must be true"
                )
        for field in ("state_equivalence_margin", "path_equivalence_margin", "omega_equivalence_margin"):
            value = predictor.get(field)
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value <= 0
            ):
                _issue(
                    issues,
                    "ZERO_GEOMETRY_MARGIN_INVALID",
                    f"predictor_geometry.{field}",
                    "must be finite and positive",
                )
        if (
            predictor.get("geometry_interaction_definition") is not None
            or predictor.get("geometry_interaction_code_sha256") is not None
        ):
            _issue(
                issues,
                "GEOMETRY_MODE_FIELDS_CONFLICT",
                "predictor_geometry",
                "common/on geometry must not also define an interaction predictor",
            )
    if mode == "geometry_interaction":
        definition = _mapping(predictor.get("geometry_interaction_definition"))
        if (
            definition.get("kind") != "state_only_condition_contrast_v1"
            or not _nonempty_text(definition.get("description"))
            or definition.get("response_inputs_allowed") is not False
            or definition.get("uses_confirmation_response") is not False
            or re.fullmatch(r"[0-9a-f]{64}", str(definition.get("definition_sha256") or "")) is None
            or _has_dynamic_or_condition_proxy(definition.get("description"), payload)
            or _has_outcome_fit_language(definition.get("description"))
        ):
            _issue(
                issues,
                "GEOMETRY_INTERACTION_MISSING",
                "predictor_geometry.geometry_interaction_definition",
                "must be a state-only hashed contrast with no response-derived provenance",
            )
        if not re.fullmatch(r"[0-9a-f]{64}", str(predictor.get("geometry_interaction_code_sha256") or "")):
            _issue(
                issues,
                "GEOMETRY_INTERACTION_HASH_INVALID",
                "predictor_geometry.geometry_interaction_code_sha256",
                "must be a SHA-256",
            )
        if any(
            predictor.get(field) is not None
            for field in (
                "zero_state_equivalence",
                "zero_achieved_path_equivalence",
                "zero_omega_equivalence",
                "state_equivalence_margin",
                "path_equivalence_margin",
                "omega_equivalence_margin",
            )
        ):
            _issue(
                issues,
                "GEOMETRY_MODE_FIELDS_CONFLICT",
                "predictor_geometry",
                "interaction geometry must not claim the common/on equivalence branch",
            )


def _check_tangent_prediction(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    tangent = _mapping(payload.get("tangent_remainder_validation"))
    for field in (
        "derivation_or_memory_kernel_limit",
        "reversal_test",
        "cyclic_start_test",
        "smooth_reparameterization_test",
        "concatenation_test",
        "matched_area_shape_test",
        "line_integral_comparison",
    ):
        if not _nonempty_text(tangent.get(field)):
            _issue(
                issues,
                "TANGENT_VALIDATION_MISSING",
                f"tangent_remainder_validation.{field}",
                "must be frozen",
            )
    remainder = _mapping(tangent.get("uniform_remainder_bound"))
    if not remainder:
        _issue(
            issues,
            "REMAINDER_BOUND_MISSING",
            "tangent_remainder_validation.uniform_remainder_bound",
            "must be a typed bound",
        )
    else:
        if remainder.get("probability_domain") == "high_probability" and not isinstance(
            remainder.get("probability_level"), (int, float)
        ):
            _issue(
                issues,
                "REMAINDER_PROBABILITY_INVALID",
                "tangent_remainder_validation.uniform_remainder_bound.probability_level",
                "is required for a stochastic bound",
            )
        if (
            remainder.get("probability_domain") == "deterministic"
            and remainder.get("probability_level") is not None
        ):
            _issue(
                issues,
                "REMAINDER_PROBABILITY_INVALID",
                "tangent_remainder_validation.uniform_remainder_bound.probability_level",
                "must be null for a deterministic bound",
            )

    prediction = _mapping(payload.get("prediction_model"))
    if (
        prediction.get("fit_partitions") != ["calibration"]
        or prediction.get("forbid_pointwise_heldout_f_response_over_omega") is not True
    ):
        _issue(
            issues,
            "HELDOUT_LOCAL_SELF_FIT",
            "prediction_model",
            "must fit calibration only and forbid pointwise held-out division",
        )
    for field in ("geometry_uncertainty_method", "calibration_uncertainty_method"):
        if not _nonempty_text(prediction.get(field)):
            _issue(issues, "PREDICTION_DESIGN_MISSING", f"prediction_model.{field}", "must be frozen")
    model_family = _mapping(prediction.get("calibration_model_family"))
    if (
        model_family.get("kind") not in {"constant_kappa_v1", "low_dimensional_kappa_v1"}
        or not _nonempty_text(model_family.get("description"))
        or model_family.get("fit_partitions") != ["calibration"]
        or model_family.get("uses_confirmation_response") is not False
        or model_family.get("uses_heldout_local_response_curvature_ratio") is not False
        or re.fullmatch(r"[0-9a-f]{64}", str(model_family.get("model_spec_sha256") or "")) is None
        or _has_dynamic_or_condition_proxy(model_family.get("description"), payload)
        or _has_outcome_fit_language(model_family.get("description"))
    ):
        _issue(
            issues,
            "PREDICTION_MODEL_PROVENANCE_INVALID",
            "prediction_model.calibration_model_family",
            "must be a hashed calibration-only model with no held-out response self-fit",
        )
    if prediction.get("rank_three_area_vector_design") is not True:
        _issue(
            issues,
            "PREDICTION_RANK_UNVERIFIED",
            "prediction_model.rank_three_area_vector_design",
            "must be true",
        )
    normals = list(_sequence(prediction.get("noncoplanar_normals")))
    normalized: list[list[float]] = []
    if len(normals) != 3 or any(len(_sequence(vector)) != 3 for vector in normals):
        _issue(
            issues,
            "PREDICTION_RANK_INVALID",
            "prediction_model.noncoplanar_normals",
            "must provide exactly three three-vectors",
        )
    else:
        try:
            rows = [[float(value) for value in vector] for vector in normals]
            for row in rows:
                norm = math.sqrt(sum(value * value for value in row))
                if not math.isfinite(norm) or norm <= 0:
                    raise ValueError("nonfinite or zero vector")
                normalized.append([value / norm for value in row])
        except (TypeError, ValueError):
            normalized = []
        if not normalized:
            _issue(
                issues,
                "PREDICTION_RANK_INVALID",
                "prediction_model.noncoplanar_normals",
                "must contain finite nonzero vectors",
            )
        else:
            a, b, c = normalized
            determinant = (
                a[0] * (b[1] * c[2] - b[2] * c[1])
                - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])
            )
            if not math.isfinite(determinant) or abs(determinant) <= 1e-12:
                _issue(
                    issues,
                    "PREDICTION_RANK_INVALID",
                    "prediction_model.noncoplanar_normals",
                    "normalized area-vector matrix must have full rank",
                )
            else:
                inverse = [
                    [
                        (b[1] * c[2] - b[2] * c[1]) / determinant,
                        (a[2] * c[1] - a[1] * c[2]) / determinant,
                        (a[1] * b[2] - a[2] * b[1]) / determinant,
                    ],
                    [
                        (b[2] * c[0] - b[0] * c[2]) / determinant,
                        (a[0] * c[2] - a[2] * c[0]) / determinant,
                        (a[2] * b[0] - a[0] * b[2]) / determinant,
                    ],
                    [
                        (b[0] * c[1] - b[1] * c[0]) / determinant,
                        (a[1] * c[0] - a[0] * c[1]) / determinant,
                        (a[0] * b[1] - a[1] * b[0]) / determinant,
                    ],
                ]
                frobenius_condition = math.sqrt(
                    sum(value * value for row in normalized for value in row)
                ) * math.sqrt(sum(value * value for row in inverse for value in row))
                declared = prediction.get("declared_frobenius_condition_number")
                threshold = _mapping(payload.get("source_specific_freeze_readiness")).get(
                    "condition_number_threshold"
                )
                if (
                    not isinstance(declared, (int, float))
                    or isinstance(declared, bool)
                    or not math.isclose(float(declared), frobenius_condition, rel_tol=1e-9, abs_tol=1e-12)
                ):
                    _issue(
                        issues,
                        "PREDICTION_CONDITION_MISMATCH",
                        "prediction_model.declared_frobenius_condition_number",
                        "must equal the reproducible normalized-row Frobenius condition number",
                    )
                if (
                    not isinstance(threshold, (int, float))
                    or isinstance(threshold, bool)
                    or not math.isfinite(threshold)
                    or frobenius_condition > threshold
                ):
                    _issue(
                        issues,
                        "PREDICTION_CONDITION_EXCEEDED",
                        "prediction_model.noncoplanar_normals",
                        "normalized-row Frobenius condition must not exceed the frozen threshold",
                    )
    oblique = list(_sequence(prediction.get("oblique_heldout_direction")))
    oblique_limit = prediction.get("heldout_oblique_max_abs_cosine")
    try:
        heldout = [float(value) for value in oblique]
        heldout_norm = math.sqrt(sum(value * value for value in heldout))
    except (TypeError, ValueError):
        heldout = []
        heldout_norm = 0.0
    if len(heldout) != 3 or not math.isfinite(heldout_norm) or heldout_norm <= 0:
        _issue(
            issues,
            "HELDOUT_DIRECTION_INVALID",
            "prediction_model.oblique_heldout_direction",
            "must be a nonzero three-vector",
        )
    elif normalized:
        unit_heldout = [value / heldout_norm for value in heldout]
        max_cosine = max(abs(sum(a * b for a, b in zip(row, unit_heldout))) for row in normalized)
        if (
            not isinstance(oblique_limit, (int, float))
            or isinstance(oblique_limit, bool)
            or not 0 < oblique_limit < 1
            or max_cosine > oblique_limit
        ):
            _issue(
                issues,
                "HELDOUT_DIRECTION_NOT_OBLIQUE",
                "prediction_model.oblique_heldout_direction",
                "must satisfy the frozen maximum absolute cosine against every primary normal",
            )
    if not re.fullmatch(r"[0-9a-f]{64}", str(prediction.get("prediction_hash_before_response_unlock") or "")):
        _issue(
            issues,
            "PREDICTION_HASH_INVALID",
            "prediction_model.prediction_hash_before_response_unlock",
            "must be a SHA-256",
        )


def _check_inference(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    inference = _mapping(payload.get("inference"))
    for field in (
        "strata_rule",
        "ties_rule",
        "duplicate_assignment_rule",
        "method_selection_rule",
    ):
        if not _nonempty_text(inference.get(field)):
            _issue(issues, "INFERENCE_DEFINITION_MISSING", f"inference.{field}", "must be frozen")
    unit = inference.get("randomization_unit")
    cluster_unit = _mapping(payload.get("cluster_split")).get("independent_unit_kind")
    if unit != INDEPENDENT_UNIT or unit != cluster_unit:
        _issue(
            issues,
            "RANDOMIZATION_UNIT_INVALID",
            "inference.randomization_unit",
            "must equal the independent block-level cluster unit",
        )
    if inference.get("randomization_group") != RANDOMIZATION_GROUP:
        _issue(
            issues,
            "RANDOMIZATION_GROUP_INVALID",
            "inference.randomization_group",
            f"must equal {RANDOMIZATION_GROUP}",
        )
    seed = inference.get("randomization_seed")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        _issue(
            issues,
            "RANDOMIZATION_SEED_INVALID",
            "inference.randomization_seed",
            "must be a frozen nonnegative integer",
        )
    locked_rules = {
        "ties_rule": INFERENCE_TIES_RULE,
        "duplicate_assignment_rule": INFERENCE_DUPLICATE_RULE,
        "method_selection_rule": INFERENCE_METHOD_RULE,
    }
    for field, expected in locked_rules.items():
        if inference.get(field) != expected:
            _issue(
                issues,
                "INFERENCE_RULE_INVALID",
                f"inference.{field}",
                f"must equal {expected!r}",
            )
    weights = _mapping(inference.get("primary_weights_rule"))
    if (
        not _nonempty_text(weights.get("formula"))
        or weights.get("provenance") != "calibration_design_only_v1"
        or weights.get("fit_partitions") != ["calibration"]
        or weights.get("uses_confirmation_response") is not False
        or weights.get("uses_heldout_response") is not False
        or re.fullmatch(r"[0-9a-f]{64}", str(weights.get("weights_sha256") or "")) is None
        or _contains_substring(weights.get("formula"), PROXY_SUBSTRINGS | {"confirmation", "heldout"})
        or _has_dynamic_or_condition_proxy(weights.get("formula"), payload)
        or _has_outcome_fit_language(weights.get("formula"))
    ):
        _issue(
            issues,
            "PRIMARY_WEIGHTS_INVALID",
            "inference.primary_weights_rule",
            "weights must be calibration/design-only, response-independent, and hash-frozen",
        )


def _check_readiness(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    readiness = _mapping(payload.get("source_specific_freeze_readiness"))
    for field in SOURCE_SPECIFIC_NULL_FIELDS:
        if readiness.get(field) is None:
            _issue(
                issues,
                "SOURCE_SPECIFIC_VALUE_UNFROZEN",
                f"source_specific_freeze_readiness.{field}",
                "must be a typed named definition",
            )
    power = _mapping(readiness.get("calibration_power"))
    if power:
        if power.get("required_minimum_power") != 0.9:
            _issue(
                issues,
                "POWER_THRESHOLD_INVALID",
                "source_specific_freeze_readiness.calibration_power.required_minimum_power",
                "must equal 0.90",
            )
        powered_n = power.get("powered_confirmation_n")
        if not isinstance(powered_n, int) or isinstance(powered_n, bool) or powered_n < 20:
            _issue(
                issues,
                "POWERED_N_INVALID",
                "source_specific_freeze_readiness.calibration_power.powered_confirmation_n",
                "must be >=20",
            )
        for field in ("method", "assumptions"):
            if not _nonempty_text(power.get(field)):
                _issue(
                    issues,
                    "POWER_DEFINITION_MISSING",
                    f"source_specific_freeze_readiness.calibration_power.{field}",
                    "must be frozen",
                )
        if (
            not isinstance(power.get("seed"), int)
            or isinstance(power.get("seed"), bool)
            or power.get("seed", -1) < 0
        ):
            _issue(
                issues,
                "POWER_DEFINITION_MISSING",
                "source_specific_freeze_readiness.calibration_power.seed",
                "must be nonnegative integer",
            )
        gates = _mapping(power.get("gates"))
        for gate in POWER_GATES:
            record = _mapping(gates.get(gate))
            if not record:
                _issue(
                    issues,
                    "POWER_GATE_MISSING",
                    f"source_specific_freeze_readiness.calibration_power.gates.{gate}",
                    "must be present",
                )
                continue
            gate_power = record.get("power")
            if (
                not isinstance(gate_power, (int, float))
                or isinstance(gate_power, bool)
                or not math.isfinite(gate_power)
                or gate_power < 0.9
            ):
                _issue(
                    issues,
                    "POWER_GATE_BELOW_090",
                    f"source_specific_freeze_readiness.calibration_power.gates.{gate}.power",
                    "must be >=0.90",
                )
            if record.get("independent_n") != powered_n:
                _issue(
                    issues,
                    "POWER_GATE_N_MISMATCH",
                    f"source_specific_freeze_readiness.calibration_power.gates.{gate}.independent_n",
                    "must equal powered_confirmation_n",
                )
            for field in ("method", "assumptions"):
                if not _nonempty_text(record.get(field)):
                    _issue(
                        issues,
                        "POWER_GATE_DEFINITION_MISSING",
                        f"source_specific_freeze_readiness.calibration_power.gates.{gate}.{field}",
                        "must be frozen per conjunctive gate",
                    )
            if not isinstance(record.get("seed"), int) or isinstance(record.get("seed"), bool):
                _issue(
                    issues,
                    "POWER_GATE_DEFINITION_MISSING",
                    f"source_specific_freeze_readiness.calibration_power.gates.{gate}.seed",
                    "must be a nonnegative integer",
                )
    beta_margin = readiness.get("beta_equivalence_margin")
    if (
        not isinstance(beta_margin, (int, float))
        or isinstance(beta_margin, bool)
        or not math.isfinite(beta_margin)
        or not 0 < beta_margin <= 1
    ):
        _issue(
            issues,
            "BETA_MARGIN_INVALID",
            "source_specific_freeze_readiness.beta_equivalence_margin",
            "must be in (0,1]",
        )
    condition = readiness.get("condition_number_threshold")
    if (
        not isinstance(condition, (int, float))
        or isinstance(condition, bool)
        or not math.isfinite(condition)
        or condition <= 1
    ):
        _issue(
            issues,
            "CONDITION_THRESHOLD_INVALID",
            "source_specific_freeze_readiness.condition_number_threshold",
            "must be finite and >1",
        )
    response_units = _mapping(payload.get("response_firewall")).get("response_units")
    sesoi = _mapping(readiness.get("physical_response_sesoi"))
    if sesoi and sesoi.get("units") != response_units:
        _issue(
            issues,
            "SESOI_UNITS_MISMATCH",
            "source_specific_freeze_readiness.physical_response_sesoi.units",
            "must equal Q response units",
        )
    remainder_units = _mapping(
        _mapping(payload.get("tangent_remainder_validation")).get("uniform_remainder_bound")
    ).get("response_units_after_dividing_by_s_squared")
    if remainder_units != response_units:
        _issue(
            issues,
            "REMAINDER_UNITS_MISMATCH",
            "tangent_remainder_validation.uniform_remainder_bound.response_units_after_dividing_by_s_squared",
            "must equal integrated Q response units because s is dimensionless",
        )
    interaction = _mapping(readiness.get("interaction_nondegeneracy_definition"))
    if interaction and interaction.get("units") != response_units:
        _issue(
            issues,
            "INTERACTION_UNITS_MISMATCH",
            "source_specific_freeze_readiness.interaction_nondegeneracy_definition.units",
            "must equal integrated Q response units",
        )
    comparator = _mapping(readiness.get("comparator_definition"))
    if comparator and comparator.get("loss_units") != "dimensionless_normalized_loss":
        _issue(
            issues,
            "COMPARATOR_LOSS_UNITS_INVALID",
            "source_specific_freeze_readiness.comparator_definition.loss_units",
            "must be the frozen dimensionless normalized loss",
        )
    clustered_fields = (
        ("beta_interval_definition", "cluster_unit"),
        ("response_lower_bound_definition", "cluster_aggregation"),
        ("comparator_definition", "aggregation_unit"),
    )
    for object_name, field in clustered_fields:
        if _mapping(readiness.get(object_name)).get(field) != INDEPENDENT_UNIT:
            _issue(
                issues,
                "INFERENCE_CLUSTER_UNIT_INVALID",
                f"source_specific_freeze_readiness.{object_name}.{field}",
                f"must equal {INDEPENDENT_UNIT}",
            )


def _check_controls_lock(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    controls = _mapping(payload.get("controls"))
    for field in (
        "retraced_zero_area_sham",
        "omega_orthogonal_nonzero_area_loop",
        "order_counterbalance",
        "gauge_invariance",
        "component_and_center_scramble",
        "response_sensor_reference_injection",
        "zero_geometry_comparator",
        "metric_only_comparator",
        "control_only_comparator",
    ):
        if not _nonempty_text(controls.get(field)):
            _issue(issues, "CONTROL_DEFINITION_MISSING", f"controls.{field}", "must be frozen")


def _check_claim(
    payload: Mapping[str, Any], issues: list[ValidationIssue], ready_without_claim: bool
) -> None:
    claim = _mapping(payload.get("claim_ceiling"))
    if (
        claim.get("template_is_evidence") is not False
        or claim.get("template_is_study_preregistration") is not False
    ):
        _issue(
            issues,
            "CLAIM_SCOPE_INVALID",
            "claim_ceiling",
            "template evidence/preregistration flags must be false",
        )
    if set(_sequence(claim.get("forbidden_generalizations"))) != FORBIDDEN_GENERALIZATIONS:
        _issue(
            issues,
            "CLAIM_FORBIDDEN_SET_INVALID",
            "claim_ceiling.forbidden_generalizations",
            "must equal the locked forbidden set",
        )
    allowed = claim.get("allowed_if_future_pass")
    if ready_without_claim:
        if allowed != FUTURE_CLAIM:
            _issue(
                issues,
                "FUTURE_CLAIM_NOT_FROZEN",
                "claim_ceiling.allowed_if_future_pass",
                "must equal the exact narrow claim",
            )
    elif allowed is not None:
        _issue(
            issues,
            "PREMATURE_FUTURE_CLAIM",
            "claim_ceiling.allowed_if_future_pass",
            "must remain null while blocked",
        )


def _check_forbidden_execution_aliases(payload: Mapping[str, Any], issues: list[ValidationIssue]) -> None:
    forbidden_key_suffixes = {
        "confirmationcommand",
        "confirmcommand",
        "dataadapter",
        "dataseturi",
        "numericresponsereducer",
        "outcomeadapter",
        "outcomeloader",
        "outcomepath",
        "outcomeuri",
        "rawdatapath",
        "resultpath",
        "resulturi",
    }

    def walk(value: Any, path: str, inside_hash_map: bool = False) -> None:
        if isinstance(value, Mapping):
            for key, child in value.items():
                child_path = f"{path}.{key}" if path else str(key)
                normalized = re.sub(r"[^a-z0-9]", "", str(key).casefold())
                if not inside_hash_map and any(
                    normalized.endswith(suffix) for suffix in forbidden_key_suffixes
                ):
                    _issue(
                        issues,
                        "OUTCOME_EXECUTION_FIELD_FORBIDDEN",
                        child_path,
                        "outcome/data execution aliases are forbidden",
                    )
                walk(child, child_path, inside_hash_map or key == "raw_file_sha256")
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]", inside_hash_map)

    walk(payload, "")


def validate_template(payload: Mapping[str, Any]) -> ValidationReport:
    """Apply schema and semantic gates without any substrate or outcome access."""

    issues: list[ValidationIssue] = []
    _apply_schema(payload, protocol_schema(), "$", issues)
    identifier_present = _check_source(payload, issues)
    _check_coordinates(payload, issues)
    _check_response(payload, issues)
    _check_quartet_clock(payload, issues)
    _check_clusters(payload, issues)
    _check_geometry(payload, issues)
    _check_tangent_prediction(payload, issues)
    _check_inference(payload, issues)
    _check_readiness(payload, issues)
    _check_controls_lock(payload, issues)
    _check_forbidden_execution_aliases(payload, issues)

    source_invalid = any(issue.code in SOURCE_ELIGIBILITY_CODES for issue in issues)
    ready_without_claim = identifier_present and not source_invalid and not issues
    _check_claim(payload, issues, ready_without_claim)

    if not identifier_present:
        state = TemplateState.BLOCKED_NO_SUBSTRATE
    elif source_invalid:
        state = TemplateState.BLOCKED_INELIGIBLE_SOURCE
    elif issues:
        state = TemplateState.BLOCKED_INCOMPLETE_METADATA
    else:
        state = TemplateState.METADATA_VERIFIED_PENDING_IMPLEMENTATION

    declared_states = {
        "template_state": payload.get("template_state"),
        "source_specific_freeze_readiness.current_status": _mapping(
            payload.get("source_specific_freeze_readiness")
        ).get("current_status"),
    }
    for path, declared in declared_states.items():
        if declared != state.value:
            _issue(issues, "DECLARED_STATE_MISMATCH", path, f"must equal substantive state {state.value}")
    if issues and state is TemplateState.METADATA_VERIFIED_PENDING_IMPLEMENTATION:
        state = TemplateState.BLOCKED_INCOMPLETE_METADATA
    return ValidationReport(state=state, issues=tuple(issues))


assert [state.value for state in TemplateState] == PREIMPLEMENTATION_STATES

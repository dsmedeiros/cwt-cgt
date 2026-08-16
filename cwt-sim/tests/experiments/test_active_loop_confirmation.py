from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest
from typer.main import get_command
from typer.testing import CliRunner

SIM_ROOT = Path(__file__).resolve().parents[2]
if str(SIM_ROOT) not in sys.path:
    sys.path.insert(0, str(SIM_ROOT))

from experiments.active_loop_confirmation.artifacts import (  # noqa: E402
    ARTIFACT_FILENAMES,
    DEFAULT_TEMPLATE_PATH,
    EXPERIMENT_DIR,
    SCHEMA_PATH,
    ArtifactVerificationError,
    canonical_source_text_bytes,
    load_template,
    sha256_file,
    verify_template_artifacts,
    write_template_artifacts,
)
from experiments.active_loop_confirmation.run import app  # noqa: E402
from experiments.active_loop_confirmation.schema import (  # noqa: E402
    CERTIFICATE_PROVENANCE,
    DEFINITION_PROVENANCE,
    ENDPOINT_FLAT_C3_REGULARITY,
    EQUILIBRIUM_INITIALIZATION,
    GENERIC_ASYMPTOTIC_REGIME,
    GENERIC_CONTINUOUS_AREA_RELATIVE_LIMIT,
    GENERIC_CONTINUOUS_BOUND,
    GENERIC_DISCRETE_AREA_RELATIVE_LIMIT,
    GENERIC_DISCRETE_BOUND,
    GENERIC_REGULARITY,
    GENERIC_TOTAL_BOUND,
    IMPROVED_ASYMPTOTIC_REGIME,
    IMPROVED_CONTINUOUS_AREA_RELATIVE_LIMIT,
    IMPROVED_CONTINUOUS_BOUND,
    IMPROVED_DISCRETE_AREA_RELATIVE_LIMIT,
    IMPROVED_DISCRETE_BOUND,
    IMPROVED_TOTAL_BOUND,
    MATCHED_CORRECTOR_INITIALIZATION,
    PERIODIC_C3_REGULARITY,
    PERIODIC_INITIALIZATION,
    POWER_GATES,
    REFERENCE_AUTHENTICATION_GATE_STATUS,
    TANGENT_DEFINITION_IDS,
    TANGENT_DEFINITION_PATHS,
    canonical_schema_bytes,
)
from experiments.active_loop_confirmation.template_model import (  # noqa: E402
    FUTURE_CLAIM,
    INFERENCE_DUPLICATE_RULE,
    INFERENCE_METHOD_RULE,
    INFERENCE_TIES_RULE,
    SOURCE_SPECIFIC_NULL_FIELDS,
    TemplateState,
    validate_template,
)


def _hash(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


def _definition(definition_id: str, artifact_path: str, stage: str = "theory_only") -> dict[str, Any]:
    return {
        "definition_id": definition_id,
        "artifact_path": artifact_path,
        "sha256": _hash(f"definition:{definition_id}:{artifact_path}"),
        "stage": stage,
        "provenance": DEFINITION_PROVENANCE,
        "locked_before_confirmation": True,
        "uses_any_confirmation_or_outcome": False,
    }


def _partition(prefix: str, count: int) -> dict[str, list[str]]:
    return {
        "cluster_ids": [f"{prefix}-cluster-{index:03d}" for index in range(count)],
        "alias_ids": [f"{prefix}-alias-{index:03d}" for index in range(count)],
        "content_sha256": [_hash(f"{prefix}-content-{index:03d}") for index in range(count)],
    }


def _complete_metadata_fixture() -> dict[str, Any]:
    """Return a structurally complete, non-evidentiary metadata fixture."""

    payload = copy.deepcopy(load_template())
    payload["template_state"] = "METADATA_VERIFIED_PENDING_IMPLEMENTATION"
    payload["substrate"] = {
        "identifier": "qualified-physical-fixture-metadata-only",
        "source_qualification": {
            "external_source": True,
            "immutable_primary_raw_measurements": True,
            "physical_measurement": True,
            "actually_executed_intervention": True,
            "randomized_orientation": True,
            "counterbalanced_orientation": True,
            "commanded_controls_recorded": True,
            "achieved_controls_recorded": True,
            "independent_raw_response_recorded": True,
            "reset_block_ids_recorded": True,
            "physical_timestamps_recorded": True,
            "measurement_units_recorded": True,
            "passive_only": False,
            "simulated": False,
            "derived_only": False,
            "natural_cycle_only": False,
            "model_generated": False,
            "immutable_revision": "fixture-revision-1",
            "license_identifier": "CC-BY-4.0",
            "raw_manifest_sha256": _hash("raw-manifest"),
            "raw_manifest_file_count": 2,
            "raw_file_sha256": {
                "raw/device-a.bin": _hash("device-a"),
                "raw/device-b.bin": _hash("device-b"),
            },
        },
    }
    payload["coordinates"].update(
        {
            "dimension": 3,
            "independently_actuable_controls": ["field_x", "field_y", "field_z"],
            "units": ["tesla", "tesla", "tesla"],
            "reference": [0.0, 0.0, 0.0],
            "scales": [1.0, 1.0, 1.0],
            "right_handed_order": ["field_x", "field_y", "field_z"],
            "right_handed_orientation_verified": True,
        }
    )
    payload["response_firewall"].update(
        {
            "forbidden_fields": sorted(
                {
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
            ),
            "response_signal": "calibrated_torque",
            "response_signal_units": "newton_metre",
            "response_units": "newton_metre_second",
            "integrated_units_derivation": (
                "newton_metre multiplied by physical seconds equals newton_metre_second"
            ),
            "baseline_definition": "pre-episode torque median from response-only window",
            "reducer_code_sha256": _hash("response-reducer"),
            "window_id_semantics": "pseudonymous_sha256_prefix_v1",
            "example_window_ids": ["ep_0000000000000001", "ep_0000000000000002"],
            "geometry_mutation_response_bytes_identical": True,
        }
    )
    payload["quartet"].update(
        {
            "exact_zero_coupling_mechanism": "open the readout coupling relay",
            "same_schedule_sensors_and_hysteresis_at_zero": True,
            "matched_achieved_shape_and_duration": True,
            "common_physical_clock_verified": True,
            "assignment_table_sha256": _hash("assignment-table"),
        }
    )
    payload["physical_time_protocol"].update(
        {
            "duration_seconds": 10.0,
            "dt_seconds": 0.01,
            "timestamp_units": "seconds",
            "latency_bound_seconds": 0.001,
            "jitter_bound_seconds": 0.001,
            "quadrature_rule": "timestamp_weighted_trapezoidal_Q_integral_v1",
            "endpoint_rule": "duplicate closing endpoint counted once",
            "achieved_path_source": "three-axis Hall-probe telemetry",
            "achieved_path_closure_tolerance": 0.01,
            "initialization_mode": EQUILIBRIUM_INITIALIZATION,
            "path_regularity_mode": GENERIC_REGULARITY,
            "control_dynamics_map": {
                "kind": "continuous_rate_map",
                "formula": "alpha(dt)=1-exp(-dt/tau)",
                "tau_seconds": 0.25,
                "fixed_alpha_across_dt_ladder": False,
            },
            "waveform_family": "frozen piecewise-C2 closed exact-reverse physical-time loops",
            "dt_ladder": [0.001, 0.002, 0.004, 0.008, 0.016],
            "duration_ladder": [1.0, 2.0, 4.0, 8.0, 16.0],
            "scale_ladder": [0.05, 0.1, 0.2, 0.3, 0.4],
            "heldout_level_index": {"dt": 4, "duration": 4, "scale": 4},
        }
    )
    payload["cluster_split"].update(
        {
            "independent_unit_kind": "independently_randomized_washed_out_reset_block",
            "minimum_independent_blocks": 20,
            "salt": "metadata-only-split-salt-v1",
            "assignment_rule": "hash whole physical reset blocks before outcomes",
            "duplicate_detection_rule": "reject identifier aliases and content duplicates",
            "partitions": {
                "calibration": _partition("cal", 5),
                "reduction_validation": _partition("val", 5),
                "confirmation": _partition("confirm", 40),
            },
        }
    )
    payload["geometry_firewall"].update(
        {
            "state_sensor": "independent_hall_state",
            "state_map_revision": "state-map-v1",
            "projector_estimator": "frozen rank-one projector estimator",
            "wilson_estimator": "frozen Wilson-overlap flux estimator",
            "qgt_estimator": "frozen projective derivative QGT estimator",
            "estimator_code_sha256": _hash("geometry-estimator"),
            "gap_overlap_gauge_qc": "predeclared gap, overlap, settling, and gauge gates",
            "state_sensor_distinct_from_response": True,
        }
    )
    payload["predictor_geometry"].update(
        {
            "mode": "common_on_geometry",
            "finite_flux_estimator": "wilson_loop",
            "local_approximation_in_remainder": True,
            "zero_state_equivalence": True,
            "zero_achieved_path_equivalence": True,
            "zero_omega_equivalence": True,
            "state_equivalence_margin": 0.01,
            "path_equivalence_margin": 0.01,
            "omega_equivalence_margin": 0.01,
            "geometry_interaction_definition": None,
            "geometry_interaction_code_sha256": None,
        }
    )
    payload["tangent_remainder_validation"].update(
        {
            "derivation_or_memory_kernel_limit": _definition(
                TANGENT_DEFINITION_IDS["derivation_or_memory_kernel_limit"],
                TANGENT_DEFINITION_PATHS["derivation_or_memory_kernel_limit"],
            ),
            "asymptotic_regime": {
                "selected_regime": GENERIC_ASYMPTOTIC_REGIME,
                "fixed_norm_definition": _definition(
                    TANGENT_DEFINITION_IDS["fixed_norm_definition"],
                    TANGENT_DEFINITION_PATHS["fixed_norm_definition"],
                ),
                "uniform_contraction_rho_upper": 0.8,
                "initialization_mode": EQUILIBRIUM_INITIALIZATION,
                "regularity_mode": GENERIC_REGULARITY,
                "discrete_remainder_bound": GENERIC_DISCRETE_BOUND,
                "continuous_remainder_bound": GENERIC_CONTINUOUS_BOUND,
                "discrete_area_relative_limit": GENERIC_DISCRETE_AREA_RELATIVE_LIMIT,
                "continuous_area_relative_limit": GENERIC_CONTINUOUS_AREA_RELATIVE_LIMIT,
                "generic_boundary_term_retained": True,
                "derivation_certificate": {
                    "kind": "generic_contraction_bound_v1",
                    "provenance": CERTIFICATE_PROVENANCE,
                    "derivation_sha256": _hash("generic-contraction-derivation"),
                    "cancellation_sha256": None,
                    "uses_confirmation_data": False,
                    "uses_outcome_response": False,
                    "locked_before_confirmation": True,
                },
            },
            "uniform_remainder_bound": {
                "form": GENERIC_TOTAL_BOUND,
                "selected_domain_definition": _definition(
                    TANGENT_DEFINITION_IDS["selected_domain_definition"],
                    TANGENT_DEFINITION_PATHS["selected_domain_definition"],
                    stage="calibration_only",
                ),
                "probability_domain": "deterministic",
                "probability_level": None,
                "p": 1.0,
                "integrated_response_units": "newton_metre_second",
                "constants": {
                    "C_N1": 1.0,
                    "C_N2": 1.0,
                    "C_T1": 1.0,
                    "C_T2": 0.0,
                    "C_dt": 1.0,
                    "C_phi": 1.0,
                },
            },
            "reversal_test": _definition(
                TANGENT_DEFINITION_IDS["reversal_test"],
                TANGENT_DEFINITION_PATHS["reversal_test"],
            ),
            "cyclic_start_test": _definition(
                TANGENT_DEFINITION_IDS["cyclic_start_test"],
                TANGENT_DEFINITION_PATHS["cyclic_start_test"],
            ),
            "smooth_reparameterization_test": _definition(
                TANGENT_DEFINITION_IDS["smooth_reparameterization_test"],
                TANGENT_DEFINITION_PATHS["smooth_reparameterization_test"],
            ),
            "concatenation_test": _definition(
                TANGENT_DEFINITION_IDS["concatenation_test"],
                TANGENT_DEFINITION_PATHS["concatenation_test"],
            ),
            "matched_area_shape_test": _definition(
                TANGENT_DEFINITION_IDS["matched_area_shape_test"],
                TANGENT_DEFINITION_PATHS["matched_area_shape_test"],
            ),
            "line_integral_comparison": _definition(
                TANGENT_DEFINITION_IDS["line_integral_comparison"],
                TANGENT_DEFINITION_PATHS["line_integral_comparison"],
            ),
            "reference_content_authentication": {
                "gate_status": REFERENCE_AUTHENTICATION_GATE_STATUS,
                "reference_root": None,
                "resolver_implemented": False,
                "containment_verified": False,
                "existence_verified": False,
                "regular_file_verified": False,
                "raw_sha256_matched": False,
                "included_in_immutable_closure": False,
                "reference_content_authenticated": False,
                "implementation_or_response_unlock_allowed": False,
            },
        }
    )
    payload["prediction_model"].update(
        {
            "calibration_model_family": {
                "kind": "constant_kappa_v1",
                "description": "constant coefficient using calibration clusters exclusively",
                "fit_partitions": ["calibration"],
                "uses_confirmation_response": False,
                "uses_heldout_local_response_curvature_ratio": False,
                "model_spec_sha256": _hash("calibration-model-spec"),
            },
            "rank_three_area_vector_design": True,
            "area_vector_normalization_rule": ("unit_Euclidean_norm_before_Frobenius_condition_v1"),
            "condition_number_method": ("Frobenius_norm_A_times_Frobenius_norm_A_inverse"),
            "declared_frobenius_condition_number": 3.0,
            "noncoplanar_normals": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
            "oblique_heldout_direction": [1.0, 1.0, 1.0],
            "heldout_oblique_max_abs_cosine": 0.75,
            "prediction_hash_before_response_unlock": _hash("prediction-table"),
            "geometry_uncertainty_method": "cluster bootstrap of pre-unlocked geometry",
            "calibration_uncertainty_method": "calibration-cluster bootstrap",
        }
    )
    payload["inference"].update(
        {
            "randomization_group": (
                "all_distinct_balanced_block_level_quartet_sign_code_assignments_" "within_frozen_strata"
            ),
            "strata_rule": "labels remain within pre-outcome physical reset strata",
            "ties_rule": INFERENCE_TIES_RULE,
            "duplicate_assignment_rule": INFERENCE_DUPLICATE_RULE,
            "method_selection_rule": INFERENCE_METHOD_RULE,
            "randomization_unit": "independently_randomized_washed_out_reset_block",
            "randomization_seed": 321,
            "primary_weights_rule": {
                "formula": "calibration-frozen inverse-variance weights constrained above a floor",
                "provenance": "calibration_design_only_v1",
                "fit_partitions": ["calibration"],
                "uses_confirmation_response": False,
                "uses_heldout_response": False,
                "weights_sha256": _hash("primary-weights"),
            },
        }
    )
    power_gates = {
        gate: {
            "power": 0.91,
            "effect": 0.2,
            "variance": 1.0,
            "independent_n": 40,
            "method": f"simulation power for {gate}",
            "assumptions": f"frozen cluster assumptions for {gate}",
            "seed": index + 1,
        }
        for index, gate in enumerate(POWER_GATES)
    }
    payload["source_specific_freeze_readiness"] = {
        "current_status": "METADATA_VERIFIED_PENDING_IMPLEMENTATION",
        "calibration_power": {
            "required_minimum_power": 0.9,
            "powered_confirmation_n": 40,
            "method": "joint calibration-cluster simulation",
            "assumptions": "frozen cluster dependence and attrition assumptions",
            "seed": 123,
            "gates": power_gates,
        },
        "physical_response_sesoi": {
            "target": "D_bl",
            "value": 0.1,
            "units": "newton_metre_second",
            "direction": "absolute_magnitude",
        },
        "beta_equivalence_margin": 0.2,
        "beta_interval_definition": {
            "confidence": 0.99,
            "method": "cluster bootstrap with nested calibration draws",
            "cluster_unit": "independently_randomized_washed_out_reset_block",
            "calibration_uncertainty": "nested calibration-model resampling",
            "geometry_uncertainty": "nested pre-unlocked geometry resampling",
            "denominator_rule": "sum w*mu^2 must exceed frozen positive floor",
            "near_zero_rule": "below denominator floor is INDETERMINATE",
            "finite_miss_rule": "FAIL",
            "undefined_rule": "INDETERMINATE",
        },
        "response_lower_bound_definition": {
            "target": "absolute D_bl aligned with mu_l",
            "confidence": 0.99,
            "method": "one-sided cluster bootstrap lower bound",
            "cluster_aggregation": "independently_randomized_washed_out_reset_block",
            "uncertainty_propagation": "nested calibration and geometry draws",
            "finite_miss_rule": "FAIL",
            "undefined_rule": "INDETERMINATE",
        },
        "perpendicular_tensor_margin": 0.2,
        "perpendicular_ratio_definition": {
            "numerator": "norm of f_R^D orthogonal to predicted omega",
            "denominator": "norm of projected f_R^D above frozen floor",
            "near_zero_rule": "denominator below floor is INDETERMINATE",
            "confidence_bound_method": "99% cluster bootstrap upper bound",
            "finite_miss_rule": "FAIL",
            "undefined_rule": "INDETERMINATE",
        },
        "comparator_loss_advantage_margin": 0.01,
        "comparator_definition": {
            "name": "locked antisymmetric lag comparator",
            "inputs": ["command_history", "predeclared_nuisance_covariates"],
            "loss": "held-out cluster weighted squared prediction loss",
            "loss_units": "dimensionless_normalized_loss",
            "aggregation_unit": "independently_randomized_washed_out_reset_block",
            "uncertainty_method": "paired cluster bootstrap",
            "finite_miss_rule": "FAIL",
            "undefined_rule": "INDETERMINATE",
        },
        "interaction_nondegeneracy_definition": {
            "target": "D_bl",
            "effect_threshold": 0.1,
            "units": "newton_metre_second",
            "confidence_bound_method": "99% one-sided cluster lower bound",
            "valid_zero_flux_orientation_effect": "FAIL",
            "finite_miss_rule": "FAIL",
            "undefined_rule": "INDETERMINATE",
        },
        "condition_number_threshold": 10.0,
        "missingness_and_qc_rules": "no outcome-aware exclusions; undefined required cell is INDETERMINATE",
    }
    payload["controls"] = {
        "retraced_zero_area_sham": "matched retraced zero-area schedule",
        "omega_orthogonal_nonzero_area_loop": "frozen nonzero-area orthogonal loop",
        "order_counterbalance": "balanced quartet order table",
        "gauge_invariance": "projector and Wilson gauge-invariance check",
        "component_and_center_scramble": "locked component and center scrambles",
        "response_sensor_reference_injection": "calibrated dynamic-range reference injection",
        "zero_geometry_comparator": "common/on geometry equivalence comparator",
        "metric_only_comparator": "locked metric-only comparator",
        "control_only_comparator": "locked achieved-control-only comparator",
    }
    payload["claim_ceiling"]["allowed_if_future_pass"] = FUTURE_CLAIM
    return payload


def _periodic_improved_fixture() -> dict[str, Any]:
    payload = _complete_metadata_fixture()
    regime = payload["tangent_remainder_validation"]["asymptotic_regime"]
    regime.update(
        {
            "selected_regime": IMPROVED_ASYMPTOTIC_REGIME,
            "initialization_mode": PERIODIC_INITIALIZATION,
            "regularity_mode": PERIODIC_C3_REGULARITY,
            "discrete_remainder_bound": IMPROVED_DISCRETE_BOUND,
            "continuous_remainder_bound": IMPROVED_CONTINUOUS_BOUND,
            "discrete_area_relative_limit": IMPROVED_DISCRETE_AREA_RELATIVE_LIMIT,
            "continuous_area_relative_limit": IMPROVED_CONTINUOUS_AREA_RELATIVE_LIMIT,
            "generic_boundary_term_retained": False,
            "derivation_certificate": {
                "kind": "periodic_summation_by_parts_v1",
                "provenance": CERTIFICATE_PROVENANCE,
                "derivation_sha256": _hash("periodic-derivation"),
                "cancellation_sha256": _hash("periodic-cancellation"),
                "uses_confirmation_data": False,
                "uses_outcome_response": False,
                "locked_before_confirmation": True,
            },
        }
    )
    payload["physical_time_protocol"]["initialization_mode"] = PERIODIC_INITIALIZATION
    payload["physical_time_protocol"]["path_regularity_mode"] = PERIODIC_C3_REGULARITY
    payload["tangent_remainder_validation"]["uniform_remainder_bound"]["form"] = IMPROVED_TOTAL_BOUND
    payload["tangent_remainder_validation"]["uniform_remainder_bound"]["constants"]["C_T2"] = 1.0
    return payload


TANGENT_REFERENCE_NAMES = tuple(TANGENT_DEFINITION_IDS)


def _tangent_definition_records(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    tangent = payload["tangent_remainder_validation"]
    records = {
        field: tangent[field]
        for field in (
            "derivation_or_memory_kernel_limit",
            "reversal_test",
            "cyclic_start_test",
            "smooth_reparameterization_test",
            "concatenation_test",
            "matched_area_shape_test",
            "line_integral_comparison",
        )
    }
    records["fixed_norm_definition"] = tangent["asymptotic_regime"]["fixed_norm_definition"]
    records["selected_domain_definition"] = tangent["uniform_remainder_bound"]["selected_domain_definition"]
    return records


def _codes(payload: dict[str, Any]) -> set[str]:
    return {issue.code for issue in validate_template(payload).issues}


def _set_declared_state(payload: dict[str, Any], state: TemplateState) -> None:
    payload["template_state"] = state.value
    payload["source_specific_freeze_readiness"]["current_status"] = state.value


def test_checked_template_is_blocked_and_complete_fixture_only_verifies_metadata() -> None:
    blocked = load_template()
    blocked_report = validate_template(blocked)
    complete = _complete_metadata_fixture()
    complete_report = validate_template(complete)

    assert blocked_report.state is TemplateState.BLOCKED_NO_SUBSTRATE
    assert blocked_report.metadata_verified is False
    assert complete_report.state is TemplateState.METADATA_VERIFIED_PENDING_IMPLEMENTATION
    assert complete_report.issues == ()
    assert complete_report.as_dict()["outcome_execution_available"] is False
    assert blocked["analysis_implementation_available"] is False
    readiness = blocked["source_specific_freeze_readiness"]
    assert all(readiness[field] is None for field in SOURCE_SPECIFIC_NULL_FIELDS)
    assert not (EXPERIMENT_DIR / "artifacts" / "results").exists()


def test_all_four_preimplementation_states_are_truthful() -> None:
    no_source = load_template()

    ineligible = _complete_metadata_fixture()
    ineligible["substrate"]["source_qualification"]["passive_only"] = True
    ineligible["claim_ceiling"]["allowed_if_future_pass"] = None
    _set_declared_state(ineligible, TemplateState.BLOCKED_INELIGIBLE_SOURCE)

    incomplete = _complete_metadata_fixture()
    incomplete["response_firewall"]["baseline_definition"] = None
    incomplete["claim_ceiling"]["allowed_if_future_pass"] = None
    _set_declared_state(incomplete, TemplateState.BLOCKED_INCOMPLETE_METADATA)

    complete = _complete_metadata_fixture()

    assert validate_template(no_source).state is TemplateState.BLOCKED_NO_SUBSTRATE
    assert validate_template(ineligible).state is TemplateState.BLOCKED_INELIGIBLE_SOURCE
    assert validate_template(incomplete).state is TemplateState.BLOCKED_INCOMPLETE_METADATA
    assert validate_template(complete).state is TemplateState.METADATA_VERIFIED_PENDING_IMPLEMENTATION


def test_declared_verified_cannot_override_substantive_state() -> None:
    payload = _complete_metadata_fixture()
    payload["substrate"]["source_qualification"]["simulated"] = True
    payload["claim_ceiling"]["allowed_if_future_pass"] = None

    report = validate_template(payload)

    assert report.state is TemplateState.BLOCKED_INELIGIBLE_SOURCE
    assert "DECLARED_STATE_MISMATCH" in {issue.code for issue in report.issues}


def test_declared_blocked_cannot_leave_verified_state_or_cli_success(tmp_path: Path) -> None:
    payload = _complete_metadata_fixture()
    _set_declared_state(payload, TemplateState.BLOCKED_INCOMPLETE_METADATA)

    report = validate_template(payload)
    template = tmp_path / "declared-blocked.json"
    template.write_text(json.dumps(payload), encoding="utf-8")
    result = CliRunner().invoke(app, ["validate-template", "--template", str(template)])

    assert report.state is TemplateState.BLOCKED_INCOMPLETE_METADATA
    assert report.metadata_verified is False
    assert "DECLARED_STATE_MISMATCH" in {issue.code for issue in report.issues}
    assert result.exit_code == 2


@pytest.mark.parametrize(
    ("field", "expected_code"),
    [
        ("passive_only", "SOURCE_PASSIVE"),
        ("simulated", "SOURCE_SYNTHETIC"),
        ("derived_only", "SOURCE_DERIVED_ONLY"),
        ("natural_cycle_only", "SOURCE_NATURAL_CYCLE"),
        ("model_generated", "SOURCE_MODEL_GENERATED"),
    ],
)
def test_named_passive_synthetic_derived_sources_are_ineligible(field: str, expected_code: str) -> None:
    payload = _complete_metadata_fixture()
    payload["substrate"]["source_qualification"][field] = True
    payload["claim_ceiling"]["allowed_if_future_pass"] = None
    _set_declared_state(payload, TemplateState.BLOCKED_INELIGIBLE_SOURCE)

    report = validate_template(payload)

    assert expected_code in {issue.code for issue in report.issues}
    assert report.state is TemplateState.BLOCKED_INELIGIBLE_SOURCE


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("bad_raw_hash", "SOURCE_RAW_HASH_INVALID"),
        ("duplicate_controls", "ACTUABLE_CONTROLS_INVALID"),
        ("short_control_ids", "ACTUABLE_CONTROLS_INVALID"),
        ("zero_scale", "CONTROL_SCALES_INVALID"),
        ("tick_control_unit", "CONTROL_UNITS_INVALID"),
        ("null_split_arrays", "SPLIT_ARRAY_CLOSURE_INVALID"),
        ("loop_cluster_unit", "PSEUDOREPLICATION_UNIT"),
        ("tick_randomization_unit", "RANDOMIZATION_UNIT_INVALID"),
        ("negative_duration", "PHYSICAL_DURATION_INVALID"),
        ("negative_latency", "CLOCK_BOUND_INVALID"),
        ("duplicate_ladder", "LADDER_INVALID"),
        ("manifest_coverage", "SOURCE_MANIFEST_COVERAGE"),
        ("nonfinite_margin", "SCHEMA_TYPE"),
        ("wrong_type", "SCHEMA_TYPE"),
        ("arbitrary_power_placeholder", "SCHEMA_REQUIRED"),
        ("loop_bundle_units", "PSEUDOREPLICATION_UNIT"),
        ("tick_response_units", "RESPONSE_UNITS_NONPHYSICAL"),
        ("tick_timestamp_units", "PHYSICAL_TIME_UNITS_INVALID"),
        ("geometry_response_name", "RESPONSE_PROXY_SEMANTICS"),
        ("revealing_glued_id", "RESPONSE_PROXY_ID"),
        ("treatment_baseline", "RESPONSE_PROXY_SEMANTICS"),
        ("tick_sum_quadrature", "PHYSICAL_QUADRATURE_INVALID"),
        ("fixed_alpha_tick_map", "PHYSICAL_RATE_MAP_INVALID"),
        ("confirmation_fitted_weights", "PRIMARY_WEIGHTS_INVALID"),
        ("tick_sensor_randomization", "RANDOMIZATION_GROUP_INVALID"),
    ],
)
def test_single_malicious_metadata_mutations_fail_closed(mutation: str, expected_code: str) -> None:
    payload = _complete_metadata_fixture()
    if mutation == "bad_raw_hash":
        payload["substrate"]["source_qualification"]["raw_file_sha256"]["raw/device-a.bin"] = "x"
    elif mutation == "duplicate_controls":
        payload["coordinates"]["independently_actuable_controls"] = ["x", "x", "z"]
    elif mutation == "short_control_ids":
        payload["coordinates"]["independently_actuable_controls"] = ["x", "y", "z"]
        payload["coordinates"]["right_handed_order"] = ["x", "y", "z"]
    elif mutation == "zero_scale":
        payload["coordinates"]["scales"][0] = 0.0
    elif mutation == "tick_control_unit":
        payload["coordinates"]["units"][2] = "tick"
    elif mutation == "null_split_arrays":
        payload["cluster_split"]["partitions"]["confirmation"]["cluster_ids"] = None
    elif mutation == "loop_cluster_unit":
        payload["cluster_split"]["independent_unit_kind"] = "loop"
        payload["inference"]["randomization_unit"] = "loop"
    elif mutation == "tick_randomization_unit":
        payload["inference"]["randomization_unit"] = "tick"
    elif mutation == "negative_duration":
        payload["physical_time_protocol"]["duration_seconds"] = -1.0
    elif mutation == "negative_latency":
        payload["physical_time_protocol"]["latency_bound_seconds"] = -1.0
    elif mutation == "duplicate_ladder":
        payload["physical_time_protocol"]["dt_ladder"] = [0.001] * 5
    elif mutation == "manifest_coverage":
        payload["substrate"]["source_qualification"]["raw_manifest_file_count"] = 3
    elif mutation == "nonfinite_margin":
        payload["source_specific_freeze_readiness"]["beta_equivalence_margin"] = float("nan")
    elif mutation == "wrong_type":
        payload["physical_time_protocol"]["dt_seconds"] = "one tick"
    elif mutation == "arbitrary_power_placeholder":
        payload["source_specific_freeze_readiness"]["calibration_power"] = {"assertion": "looks powered"}
    elif mutation == "loop_bundle_units":
        payload["cluster_split"]["independent_unit_kind"] = "loop_bundle"
        payload["inference"]["randomization_unit"] = "loop_bundle"
    elif mutation == "tick_response_units":
        payload["response_firewall"]["response_units"] = "ticks"
    elif mutation == "tick_timestamp_units":
        payload["physical_time_protocol"]["timestamp_units"] = "ticks"
    elif mutation == "geometry_response_name":
        payload["response_firewall"]["response_signal"] = "phi_geometry_response"
    elif mutation == "revealing_glued_id":
        payload["response_firewall"]["example_window_ids"] = ["ep001cw"]
    elif mutation == "treatment_baseline":
        payload["response_firewall"]["baseline_definition"] = "post-treatment phi-derived"
    elif mutation == "tick_sum_quadrature":
        payload["physical_time_protocol"]["quadrature_rule"] = "tick sum"
    elif mutation == "fixed_alpha_tick_map":
        payload["physical_time_protocol"]["control_dynamics_map"] = "fixed alpha while increasing ticks"
    elif mutation == "confirmation_fitted_weights":
        payload["inference"]["primary_weights_rule"]["formula"] = "estimated from confirmation responses"
        payload["inference"]["primary_weights_rule"]["uses_confirmation_response"] = True
    elif mutation == "tick_sensor_randomization":
        payload["inference"]["randomization_group"] = "permute tick and sensor labels"

    assert expected_code in _codes(payload)
    assert not validate_template(payload).metadata_verified


def test_recursive_schema_and_alias_firewall_reject_hidden_outcome_fields() -> None:
    payload = _complete_metadata_fixture()
    payload["response_firewall"]["hidden_outcome_uri"] = "file:///forbidden.csv"

    codes = _codes(payload)

    assert "SCHEMA_UNKNOWN_FIELD" in codes
    assert "OUTCOME_EXECUTION_FIELD_FORBIDDEN" in codes


def test_one_dimensional_sweep_and_two_dimensional_self_fit_are_rejected() -> None:
    payload = _complete_metadata_fixture()
    payload["coordinates"].update(
        {
            "dimension": 1,
            "independently_actuable_controls": ["potential"],
            "units": ["volt"],
            "reference": [0.0],
            "scales": [1.0],
            "right_handed_order": ["potential"],
        }
    )
    payload["prediction_model"]["dimension"] = 2
    payload["prediction_model"]["fit_partitions"] = ["calibration", "confirmation"]
    payload["prediction_model"]["forbid_pointwise_heldout_f_response_over_omega"] = False

    codes = _codes(payload)

    assert "DIMENSION_NOT_PRIMARY_3" in codes
    assert "HELDOUT_LOCAL_SELF_FIT" in codes
    assert "SCHEMA_CONST" in codes


def test_sign_factor_flux_and_interaction_conventions_are_locked() -> None:
    payload = _complete_metadata_fixture()
    protocol = (EXPERIMENT_DIR / "PROTOCOL_TEMPLATE.md").read_text(encoding="utf-8")

    assert payload["coordinates"]["connection_convention"] == "A_i=-i<psi|partial_i psi>"
    assert payload["coordinates"]["curvature_convention"] == "Omega_ij=+2 Im C_ij"
    assert payload["predictor_geometry"]["finite_flux_definition"].startswith("Phi(S)=integral_S Omega")
    assert "\\Phi(S)=\\int_S\\Omega" in protocol
    assert "local `O(s^3)`" in protocol
    assert "ordinary difference-in-differences contrast is **`2 D_bl`**" in protocol
    assert payload["tangent_remainder_validation"]["interaction_one_form"] == "B^D=B^on-B^0"
    assert payload["tangent_remainder_validation"]["interaction_curvature"] == "F_R^D=dB^D"


@pytest.mark.parametrize(
    ("field", "wrong_value"),
    [
        ("discrete_remainder_bound", IMPROVED_DISCRETE_BOUND),
        ("continuous_remainder_bound", IMPROVED_CONTINUOUS_BOUND),
        ("discrete_area_relative_limit", IMPROVED_DISCRETE_AREA_RELATIVE_LIMIT),
        ("continuous_area_relative_limit", IMPROVED_CONTINUOUS_AREA_RELATIVE_LIMIT),
    ],
)
def test_generic_reset_cannot_claim_improved_rate_or_limit(field: str, wrong_value: str) -> None:
    payload = _complete_metadata_fixture()
    payload["tangent_remainder_validation"]["asymptotic_regime"][field] = wrong_value

    assert "ASYMPTOTIC_BOUND_MISMATCH" in _codes(payload)


def test_generic_reset_cannot_claim_improved_total_remainder() -> None:
    payload = _complete_metadata_fixture()
    payload["tangent_remainder_validation"]["uniform_remainder_bound"]["form"] = IMPROVED_TOTAL_BOUND

    assert "TOTAL_REMAINDER_BOUND_MISMATCH" in _codes(payload)


def test_periodic_improved_regime_requires_every_stronger_assumption() -> None:
    payload = _periodic_improved_fixture()

    assert validate_template(payload).metadata_verified

    for field, value in (
        ("initialization_mode", EQUILIBRIUM_INITIALIZATION),
        ("regularity_mode", GENERIC_REGULARITY),
    ):
        mutation = copy.deepcopy(payload)
        mutation["tangent_remainder_validation"]["asymptotic_regime"][field] = value
        assert "IMPROVED_REGIME_UNJUSTIFIED" in _codes(mutation)

    mutation = copy.deepcopy(payload)
    mutation["tangent_remainder_validation"]["asymptotic_regime"]["derivation_certificate"][
        "cancellation_sha256"
    ] = None
    assert "IMPROVED_REGIME_UNJUSTIFIED" in _codes(mutation)


def test_c2_periodic_claim_is_not_an_accepted_c3_assumption() -> None:
    payload = _complete_metadata_fixture()
    regime = payload["tangent_remainder_validation"]["asymptotic_regime"]
    regime["regularity_mode"] = "periodic_c2_endpoint_consistent_full_period"

    codes = _codes(payload)
    assert "SCHEMA_ENUM" in codes


def test_improved_regime_cannot_coexist_with_equilibrium_reset_or_clock_mismatch() -> None:
    payload = _periodic_improved_fixture()
    payload["physical_time_protocol"]["initialization_mode"] = EQUILIBRIUM_INITIALIZATION
    codes = _codes(payload)
    assert "ASYMPTOTIC_CLOCK_MISMATCH" in codes


def test_reviewed_improved_regime_composite_exploit_fails_closed() -> None:
    payload = _periodic_improved_fixture()
    payload["physical_time_protocol"]["initialization_mode"] = EQUILIBRIUM_INITIALIZATION
    payload["physical_time_protocol"]["path_regularity_mode"] = GENERIC_REGULARITY
    regime = payload["tangent_remainder_validation"]["asymptotic_regime"]
    regime["initialization_rule"] = "equilibrium reset chosen to minimize heldout response"
    payload["tangent_remainder_validation"]["derivation_or_memory_kernel_limit"][
        "description"
    ] = "fit directly to heldout confirmation response"
    payload["tangent_remainder_validation"]["uniform_remainder_bound"][
        "selected_domain"
    ] = "fit directly to heldout confirmation response"
    constants = payload["tangent_remainder_validation"]["uniform_remainder_bound"]["constants"]
    for field in constants:
        constants[field] = 0.0

    report = validate_template(payload)
    codes = {issue.code for issue in report.issues}
    assert not report.metadata_verified
    assert "SCHEMA_UNKNOWN_FIELD" in codes
    assert "ASYMPTOTIC_CLOCK_MISMATCH" in codes
    assert "REMAINDER_CONSTANT_INVALID" in codes
    assert "LOCAL_FLUX_CONSTANT_INVALID" in codes

    payload = _periodic_improved_fixture()
    payload["tangent_remainder_validation"]["asymptotic_regime"][
        "initialization_mode"
    ] = EQUILIBRIUM_INITIALIZATION
    codes = _codes(payload)
    assert "IMPROVED_REGIME_UNJUSTIFIED" in codes
    assert "ASYMPTOTIC_CLOCK_MISMATCH" in codes


def test_matched_corrector_improved_contract_is_structured_and_valid() -> None:
    payload = _periodic_improved_fixture()
    payload["physical_time_protocol"]["initialization_mode"] = MATCHED_CORRECTOR_INITIALIZATION
    payload["physical_time_protocol"]["path_regularity_mode"] = ENDPOINT_FLAT_C3_REGULARITY
    regime = payload["tangent_remainder_validation"]["asymptotic_regime"]
    regime["initialization_mode"] = MATCHED_CORRECTOR_INITIALIZATION
    regime["regularity_mode"] = ENDPOINT_FLAT_C3_REGULARITY
    regime["derivation_certificate"]["kind"] = "endpoint_flat_matched_corrector_v1"

    assert validate_template(payload).metadata_verified


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("derivation_sha256", "not-a-hash"),
        ("cancellation_sha256", None),
        ("uses_confirmation_data", True),
        ("uses_outcome_response", True),
        ("locked_before_confirmation", False),
    ],
)
def test_improved_certificate_fails_closed(field: str, value: Any) -> None:
    payload = _periodic_improved_fixture()
    payload["tangent_remainder_validation"]["asymptotic_regime"]["derivation_certificate"][field] = value

    codes = _codes(payload)
    assert {"ASYMPTOTIC_CERTIFICATE_INVALID", "IMPROVED_REGIME_UNJUSTIFIED"}.intersection(codes)


@pytest.mark.parametrize("record_name", TANGENT_REFERENCE_NAMES)
@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("definition_id", "heldout_response_definition_v1"),
        ("artifact_path", "../escape.json"),
        ("sha256", "not-a-sha256"),
        ("stage", "confirmation_only"),
        ("provenance", "unreviewed_inline_text_v1"),
        ("locked_before_confirmation", False),
        ("uses_any_confirmation_or_outcome", True),
    ],
)
def test_every_tangent_reference_record_field_fails_closed(
    record_name: str, field: str, invalid_value: Any
) -> None:
    payload = _complete_metadata_fixture()
    _tangent_definition_records(payload)[record_name][field] = invalid_value

    assert not validate_template(payload).metadata_verified
    assert "TANGENT_REFERENCE_INVALID" in _codes(payload)


@pytest.mark.parametrize(
    "phrase",
    [
        "fit to test-set response",
        "tuned against evaluation-set readout",
        "selected using blinded test target",
        "derived from reserved partition measurements",
        "optimized on unseen evaluation labels",
    ],
)
@pytest.mark.parametrize("record_name", TANGENT_REFERENCE_NAMES)
def test_inline_bypass_phrases_are_forbidden_unknown_fields(phrase: str, record_name: str) -> None:
    payload = _complete_metadata_fixture()
    _tangent_definition_records(payload)[record_name]["description"] = phrase

    report = validate_template(payload)
    assert not report.metadata_verified
    assert "SCHEMA_UNKNOWN_FIELD" in {issue.code for issue in report.issues}


@pytest.mark.parametrize("record_name", TANGENT_REFERENCE_NAMES)
@pytest.mark.parametrize(
    "alias",
    [
        "test-set",
        "test_set",
        "TestSet",
        "evaluation-set",
        "evaluation_set",
        "EvaluationSet",
        "reserved-partition",
        "ReservedPartition",
        "unseen-labels",
        "UnseenLabels",
        "confirmation-response",
        "ConfirmationResponse",
        "held-out",
        "held_out",
        "HeldOut",
        "holdout",
        "response",
        "orientation",
        "cw",
        "ccw",
        "field_x",
    ],
)
@pytest.mark.parametrize("field", ["definition_id", "artifact_path"])
def test_partition_proxy_aliases_are_forbidden_in_reference_ids_and_paths(
    record_name: str, alias: str, field: str
) -> None:
    payload = _complete_metadata_fixture()
    record = _tangent_definition_records(payload)[record_name]
    record[field] = alias if field == "definition_id" else f"definitions/{alias}.json"

    codes = _codes(payload)
    assert "TANGENT_REFERENCE_INVALID" in codes
    assert "TANGENT_REFERENCE_PROXY" in codes


@pytest.mark.parametrize("record_name", TANGENT_REFERENCE_NAMES)
@pytest.mark.parametrize(
    "alternate_path",
    [
        "definitions/evaluationresponses.json",
        "definitions/testcohort.json",
        "definitions/confirmatoryresults.json",
        "definitions/unblindedoutcomes.json",
        "definitions/responsefitted.json",
        "definitions/orientations.json",
        "definitions/controlsignals.json",
        "definitions/geometries.json",
        "definitions/omegas.json",
        "definitions/couplings.json",
        "definitions/fluxes.json",
        "definitions/readouts.json",
        "definitions/targets.json",
        "definitions/labels.json",
    ],
)
def test_only_exact_neutral_path_is_accepted_for_each_definition(
    record_name: str, alternate_path: str
) -> None:
    payload = _complete_metadata_fixture()
    _tangent_definition_records(payload)[record_name]["artifact_path"] = alternate_path

    assert not validate_template(payload).metadata_verified
    assert "TANGENT_REFERENCE_INVALID" in _codes(payload)


@pytest.mark.parametrize(
    "artifact_path",
    [
        "/absolute.json",
        "C:/absolute.json",
        "../escape.json",
        "definitions/./record.json",
        "definitions\\record.json",
        "definitions//record.json",
    ],
)
def test_tangent_reference_paths_are_canonical_relative_paths(artifact_path: str) -> None:
    payload = _complete_metadata_fixture()
    payload["tangent_remainder_validation"]["reversal_test"]["artifact_path"] = artifact_path

    assert "TANGENT_REFERENCE_INVALID" in _codes(payload)


def test_tangent_reference_paths_must_be_unique() -> None:
    payload = _complete_metadata_fixture()
    records = _tangent_definition_records(payload)
    records["reversal_test"]["artifact_path"] = records["cyclic_start_test"]["artifact_path"]

    assert "TANGENT_REFERENCE_PATH_DUPLICATE" in _codes(payload)


def test_nonexistent_definition_paths_validate_only_as_closed_declarations() -> None:
    payload = _complete_metadata_fixture()
    report = validate_template(payload)
    authentication = payload["tangent_remainder_validation"]["reference_content_authentication"]

    assert report.metadata_verified
    assert all(not (EXPERIMENT_DIR / path).exists() for path in TANGENT_DEFINITION_PATHS.values())
    assert authentication == {
        "gate_status": REFERENCE_AUTHENTICATION_GATE_STATUS,
        "reference_root": None,
        "resolver_implemented": False,
        "containment_verified": False,
        "existence_verified": False,
        "regular_file_verified": False,
        "raw_sha256_matched": False,
        "included_in_immutable_closure": False,
        "reference_content_authenticated": False,
        "implementation_or_response_unlock_allowed": False,
    }


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("gate_status", "COMPLETE"),
        ("reference_root", "definitions"),
        ("resolver_implemented", True),
        ("containment_verified", True),
        ("existence_verified", True),
        ("regular_file_verified", True),
        ("raw_sha256_matched", True),
        ("included_in_immutable_closure", True),
        ("reference_content_authenticated", True),
        ("implementation_or_response_unlock_allowed", True),
    ],
)
def test_unimplemented_reference_content_gate_cannot_be_self_asserted(field: str, invalid_value: Any) -> None:
    payload = _complete_metadata_fixture()
    payload["tangent_remainder_validation"]["reference_content_authentication"][field] = invalid_value

    report = validate_template(payload)
    assert not report.metadata_verified
    assert "REFERENCE_CONTENT_AUTHENTICATION_CLAIM_INVALID" in {issue.code for issue in report.issues}


@pytest.mark.parametrize("constant", ["C_N1", "C_N2", "C_T1", "C_dt", "C_phi"])
def test_generic_regime_requires_every_used_bound_constant_positive(constant: str) -> None:
    payload = _complete_metadata_fixture()
    payload["tangent_remainder_validation"]["uniform_remainder_bound"]["constants"][constant] = 0.0

    expected = "LOCAL_FLUX_CONSTANT_INVALID" if constant == "C_phi" else "REMAINDER_CONSTANT_INVALID"
    assert expected in _codes(payload)


def test_generic_unused_ct2_must_be_zero() -> None:
    payload = _complete_metadata_fixture()
    payload["tangent_remainder_validation"]["uniform_remainder_bound"]["constants"]["C_T2"] = 1.0

    assert "UNUSED_REMAINDER_CONSTANT_NONZERO" in _codes(payload)


def test_exact_integrated_flux_permits_zero_local_approximation_constant() -> None:
    payload = _complete_metadata_fixture()
    payload["predictor_geometry"]["local_approximation_in_remainder"] = False
    payload["tangent_remainder_validation"]["uniform_remainder_bound"]["constants"]["C_phi"] = 0.0

    assert validate_template(payload).metadata_verified


@pytest.mark.parametrize("constant", ["C_N1", "C_N2", "C_T1", "C_T2", "C_dt", "C_phi"])
def test_improved_regime_requires_every_bound_constant_positive(constant: str) -> None:
    payload = _periodic_improved_fixture()
    payload["tangent_remainder_validation"]["uniform_remainder_bound"]["constants"][constant] = 0.0

    expected = "LOCAL_FLUX_CONSTANT_INVALID" if constant == "C_phi" else "REMAINDER_CONSTANT_INVALID"
    assert expected in _codes(payload)


def test_response_firewall_rejects_path_fields_and_revealing_proxy_ids() -> None:
    payload = _complete_metadata_fixture()
    payload["response_firewall"]["reducer_input_fields"].append("orientation")
    payload["response_firewall"]["example_window_ids"] = ["device07_cw_on_phi"]

    codes = _codes(payload)

    assert "RESPONSE_FIREWALL_FIELD" in codes
    assert "RESPONSE_PROXY_ID" in codes


@pytest.mark.parametrize(
    ("mutation", "expected_code"),
    [
        ("signal_control", "RESPONSE_PROXY_SEMANTICS"),
        ("baseline_control", "RESPONSE_PROXY_SEMANTICS"),
        ("signal_clockwise", "RESPONSE_PROXY_SEMANTICS"),
        ("signal_counterclockwise", "RESPONSE_PROXY_SEMANTICS"),
        ("signal_positive", "RESPONSE_PROXY_SEMANTICS"),
        ("signal_negative", "RESPONSE_PROXY_SEMANTICS"),
        ("signal_on", "RESPONSE_PROXY_SEMANTICS"),
        ("baseline_on", "RESPONSE_PROXY_SEMANTICS"),
        ("heldout_response_weights", "PRIMARY_WEIGHTS_INVALID"),
        ("heldout_local_ratio_model", "PREDICTION_MODEL_PROVENANCE_INVALID"),
        ("confirmation_response_model", "PREDICTION_MODEL_PROVENANCE_INVALID"),
        ("response_derived_geometry", "GEOMETRY_INTERACTION_MISSING"),
        ("raw_condition_path", "SOURCE_RAW_PATH_PROXY"),
    ],
)
def test_dynamic_control_condition_and_outcome_fit_proxies_fail_closed(
    mutation: str, expected_code: str
) -> None:
    payload = _complete_metadata_fixture()
    firewall = payload["response_firewall"]
    if mutation == "signal_control":
        firewall["response_signal"] = "field_x"
    elif mutation == "baseline_control":
        firewall["baseline_definition"] = "pre-episode field_x median"
    elif mutation.startswith("signal_"):
        label = mutation.removeprefix("signal_")
        firewall["response_signal"] = f"{label}_torque"
    elif mutation == "baseline_on":
        firewall["baseline_definition"] = "pre-episode on relay median"
    elif mutation == "heldout_response_weights":
        payload["inference"]["primary_weights_rule"][
            "formula"
        ] = "nonnegative weights estimated from heldout responses"
    elif mutation == "heldout_local_ratio_model":
        payload["prediction_model"]["calibration_model_family"][
            "description"
        ] = "pointwise heldout F_R divided by heldout curvature"
    elif mutation == "confirmation_response_model":
        payload["prediction_model"]["calibration_model_family"][
            "description"
        ] = "fit from confirmation response values"
    elif mutation == "response_derived_geometry":
        predictor = payload["predictor_geometry"]
        predictor.update(
            {
                "mode": "geometry_interaction",
                "zero_state_equivalence": None,
                "zero_achieved_path_equivalence": None,
                "zero_omega_equivalence": None,
                "state_equivalence_margin": None,
                "path_equivalence_margin": None,
                "omega_equivalence_margin": None,
                "geometry_interaction_definition": {
                    "kind": "state_only_condition_contrast_v1",
                    "description": "computed from confirmation response",
                    "response_inputs_allowed": False,
                    "uses_confirmation_response": False,
                    "definition_sha256": _hash("bad-geometry-interaction-definition"),
                },
                "geometry_interaction_code_sha256": _hash("geometry-interaction"),
            }
        )
    else:
        raw = payload["substrate"]["source_qualification"]["raw_file_sha256"]
        raw["raw/cw-response.bin"] = raw.pop("raw/device-a.bin")

    assert expected_code in _codes(payload)
    assert not validate_template(payload).metadata_verified


@pytest.mark.parametrize(
    "variant",
    [
        "held-out",
        "held_out",
        "held out",
        "heldout",
        "hold-out",
        "hold_out",
        "hold out",
        "holdout",
    ],
)
@pytest.mark.parametrize(
    ("target", "expected_code"),
    [
        ("model", "PREDICTION_MODEL_PROVENANCE_INVALID"),
        ("weights", "PRIMARY_WEIGHTS_INVALID"),
        ("geometry", "GEOMETRY_INTERACTION_MISSING"),
    ],
)
def test_all_heldout_spellings_are_blocked_across_prediction_provenance(
    variant: str, target: str, expected_code: str
) -> None:
    payload = _complete_metadata_fixture()
    if target == "model":
        payload["prediction_model"]["calibration_model_family"][
            "description"
        ] = f"pointwise {variant} F_R divided by {variant} curvature"
    elif target == "weights":
        payload["inference"]["primary_weights_rule"][
            "formula"
        ] = f"nonnegative weights estimated from {variant} responses"
    else:
        predictor = payload["predictor_geometry"]
        predictor.update(
            {
                "mode": "geometry_interaction",
                "zero_state_equivalence": None,
                "zero_achieved_path_equivalence": None,
                "zero_omega_equivalence": None,
                "state_equivalence_margin": None,
                "path_equivalence_margin": None,
                "omega_equivalence_margin": None,
                "geometry_interaction_definition": {
                    "kind": "state_only_condition_contrast_v1",
                    "description": f"computed from {variant} response",
                    "response_inputs_allowed": False,
                    "uses_confirmation_response": False,
                    "definition_sha256": _hash(f"bad-geometry-{variant}"),
                },
                "geometry_interaction_code_sha256": _hash("geometry-interaction"),
            }
        )

    assert expected_code in _codes(payload)
    assert not validate_template(payload).metadata_verified


def test_compact_outcome_fit_cross_product_fails_closed() -> None:
    partitions = (
        "heldout",
        "holdout",
        "held_out",
        "hold_out",
        "held-out",
        "hold-out",
        "HeldOut",
        "confirmation",
        "Confirmation",
    )
    targets = ("response", "Response", "outcome", "curvature", "pointwise")
    separators = ("", "_", "-", " ")
    expected = {
        "model": "PREDICTION_MODEL_PROVENANCE_INVALID",
        "weights": "PRIMARY_WEIGHTS_INVALID",
        "geometry": "GEOMETRY_INTERACTION_MISSING",
    }

    for target_kind, expected_code in expected.items():
        for partition in partitions:
            for outcome_target in targets:
                for separator in separators:
                    phrase = f"{partition}{separator}{outcome_target}"
                    payload = _complete_metadata_fixture()
                    if target_kind == "model":
                        payload["prediction_model"]["calibration_model_family"]["description"] = phrase
                    elif target_kind == "weights":
                        payload["inference"]["primary_weights_rule"]["formula"] = phrase
                    else:
                        predictor = payload["predictor_geometry"]
                        predictor.update(
                            {
                                "mode": "geometry_interaction",
                                "zero_state_equivalence": None,
                                "zero_achieved_path_equivalence": None,
                                "zero_omega_equivalence": None,
                                "state_equivalence_margin": None,
                                "path_equivalence_margin": None,
                                "omega_equivalence_margin": None,
                                "geometry_interaction_definition": {
                                    "kind": "state_only_condition_contrast_v1",
                                    "description": phrase,
                                    "response_inputs_allowed": False,
                                    "uses_confirmation_response": False,
                                    "definition_sha256": _hash(f"bad-{phrase}"),
                                },
                                "geometry_interaction_code_sha256": _hash("geometry-interaction"),
                            }
                        )
                    assert expected_code in _codes(payload), (
                        target_kind,
                        partition,
                        outcome_target,
                        separator,
                    )


@pytest.mark.parametrize(
    "description",
    ["held-out local F_R divided by Omega", "holdoutOmega", "HeldOut-F_R pointwise"],
)
def test_local_fr_omega_self_fit_language_is_blocked(description: str) -> None:
    payload = _complete_metadata_fixture()
    payload["prediction_model"]["calibration_model_family"]["description"] = description

    assert "PREDICTION_MODEL_PROVENANCE_INVALID" in _codes(payload)


@pytest.mark.parametrize(
    "description",
    ["heldoutFR", "heldoutF_R", "holdoutfr", "confirmationFR", "heldoutΩ", "holdoutΩ"],
)
def test_compact_fr_and_unicode_omega_variants_block_in_all_provenance_text(
    description: str,
) -> None:
    for target, expected_code in (
        ("model", "PREDICTION_MODEL_PROVENANCE_INVALID"),
        ("weights", "PRIMARY_WEIGHTS_INVALID"),
        ("geometry", "GEOMETRY_INTERACTION_MISSING"),
    ):
        payload = _complete_metadata_fixture()
        if target == "model":
            payload["prediction_model"]["calibration_model_family"]["description"] = description
        elif target == "weights":
            payload["inference"]["primary_weights_rule"]["formula"] = description
        else:
            predictor = payload["predictor_geometry"]
            predictor.update(
                {
                    "mode": "geometry_interaction",
                    "zero_state_equivalence": None,
                    "zero_achieved_path_equivalence": None,
                    "zero_omega_equivalence": None,
                    "state_equivalence_margin": None,
                    "path_equivalence_margin": None,
                    "omega_equivalence_margin": None,
                    "geometry_interaction_definition": {
                        "kind": "state_only_condition_contrast_v1",
                        "description": description,
                        "response_inputs_allowed": False,
                        "uses_confirmation_response": False,
                        "definition_sha256": _hash(f"bad-unicode-{description}"),
                    },
                    "geometry_interaction_code_sha256": _hash("geometry-interaction"),
                }
            )
        assert expected_code in _codes(payload), (target, description)


def test_benign_calibration_only_provenance_descriptions_verify() -> None:
    payload = _complete_metadata_fixture()
    payload["prediction_model"]["calibration_model_family"][
        "description"
    ] = "constant coefficient using calibration clusters exclusively"
    payload["inference"]["primary_weights_rule"][
        "formula"
    ] = "calibration-frozen inverse-variance weights constrained above a floor"

    assert validate_template(payload).metadata_verified


@pytest.mark.parametrize(
    "alias",
    [
        "cwresponse",
        "ccwresponse",
        "clockwise_response",
        "counterclockwise-response",
        "PositiveResponse",
        "negative_response",
        "zero-response",
    ],
)
def test_compact_condition_aliases_are_blocked_in_raw_paths_and_ids(alias: str) -> None:
    raw_payload = _complete_metadata_fixture()
    raw = raw_payload["substrate"]["source_qualification"]["raw_file_sha256"]
    raw[f"raw/{alias}.bin"] = raw.pop("raw/device-a.bin")
    id_payload = _complete_metadata_fixture()
    id_payload["response_firewall"]["example_window_ids"] = [f"ep_{alias}"]

    assert "SOURCE_RAW_PATH_PROXY" in _codes(raw_payload)
    assert "RESPONSE_PROXY_ID" in _codes(id_payload)


def test_missing_command_achievement_clock_or_zero_coupling_is_blocking() -> None:
    payload = _complete_metadata_fixture()
    payload["substrate"]["source_qualification"]["achieved_controls_recorded"] = False
    payload["quartet"]["common_physical_clock_verified"] = False
    payload["quartet"]["exact_zero_coupling_mechanism"] = None
    payload["physical_time_protocol"]["achieved_path_source"] = None

    codes = _codes(payload)

    assert "SOURCE_FIELD_REQUIRED_TRUE" in codes
    assert "ORIENTATION_PAIR_INVALID" in codes
    assert "ZERO_COUPLING_MISSING" in codes
    assert "PHYSICAL_CLOCK_FIELD_MISSING" in codes


def test_unmatched_clockwise_counterclockwise_pair_is_rejected() -> None:
    payload = _complete_metadata_fixture()
    payload["quartet"]["matched_achieved_shape_and_duration"] = False

    assert "ORIENTATION_PAIR_INVALID" in _codes(payload)


def test_cluster_alias_content_leakage_and_small_n_are_rejected() -> None:
    payload = _complete_metadata_fixture()
    confirmation = payload["cluster_split"]["partitions"]["confirmation"]
    confirmation["cluster_ids"] = confirmation["cluster_ids"][:19]
    confirmation["alias_ids"] = confirmation["alias_ids"][:19]
    confirmation["content_sha256"] = confirmation["content_sha256"][:19]
    confirmation["alias_ids"][0] = payload["cluster_split"]["partitions"]["calibration"]["cluster_ids"][0]
    confirmation["content_sha256"][0] = payload["cluster_split"]["partitions"]["calibration"][
        "content_sha256"
    ][0]

    codes = _codes(payload)

    assert "CLUSTER_ALIAS_COLLISION" in codes
    assert "CLUSTER_LEAKAGE" in codes
    assert "CONFIRMATION_N_INSUFFICIENT" in codes


def test_cycles_on_two_devices_are_not_twenty_independent_units() -> None:
    payload = _complete_metadata_fixture()
    payload["cluster_split"]["independent_unit_kind"] = "cycle"
    payload["inference"]["randomization_unit"] = "cycle"
    confirmation = payload["cluster_split"]["partitions"]["confirmation"]
    for field in ("cluster_ids", "alias_ids", "content_sha256"):
        confirmation[field] = confirmation[field][:2]

    codes = _codes(payload)

    assert "PSEUDOREPLICATION_UNIT" in codes
    assert "CONFIRMATION_N_INSUFFICIENT" in codes


def test_confirmation_n_at_powered_40_is_accepted_but_39_is_blocked() -> None:
    accepted = _complete_metadata_fixture()
    rejected = _complete_metadata_fixture()
    confirmation = rejected["cluster_split"]["partitions"]["confirmation"]
    for field in ("cluster_ids", "alias_ids", "content_sha256"):
        confirmation[field] = confirmation[field][:-1]

    assert validate_template(accepted).metadata_verified
    assert "CONFIRMATION_N_INSUFFICIENT" in _codes(rejected)


def test_power_must_cover_every_conjunctive_gate_at_point_90() -> None:
    low = _complete_metadata_fixture()
    low["source_specific_freeze_readiness"]["calibration_power"]["gates"]["randomization"]["power"] = 0.89
    missing = _complete_metadata_fixture()
    del missing["source_specific_freeze_readiness"]["calibration_power"]["gates"]["controls"]

    assert "POWER_GATE_BELOW_090" in _codes(low)
    assert "POWER_GATE_MISSING" in _codes(missing)
    assert validate_template(_complete_metadata_fixture()).metadata_verified


def test_empty_typed_readiness_placeholder_does_not_verify() -> None:
    payload = _complete_metadata_fixture()
    payload["source_specific_freeze_readiness"]["comparator_definition"] = {
        "name": "",
        "inputs": [],
        "loss": "",
        "aggregation_unit": "",
        "uncertainty_method": "",
        "finite_miss_rule": "FAIL",
        "undefined_rule": "INDETERMINATE",
    }

    codes = _codes(payload)

    assert "SCHEMA_MIN_LENGTH" in codes
    assert "SCHEMA_MIN_ITEMS" in codes
    assert not validate_template(payload).metadata_verified


def test_geometry_predictor_modes_are_mutually_exclusive_and_complete() -> None:
    common_missing = _complete_metadata_fixture()
    common_missing["predictor_geometry"]["zero_omega_equivalence"] = False

    interaction = _complete_metadata_fixture()
    predictor = interaction["predictor_geometry"]
    predictor.update(
        {
            "mode": "geometry_interaction",
            "zero_state_equivalence": None,
            "zero_achieved_path_equivalence": None,
            "zero_omega_equivalence": None,
            "state_equivalence_margin": None,
            "path_equivalence_margin": None,
            "omega_equivalence_margin": None,
            "geometry_interaction_definition": {
                "kind": "state_only_condition_contrast_v1",
                "description": "predeclared projector contrast between two blinded conditions",
                "response_inputs_allowed": False,
                "uses_confirmation_response": False,
                "definition_sha256": _hash("geometry-interaction-definition"),
            },
            "geometry_interaction_code_sha256": _hash("geometry-interaction"),
        }
    )

    assert "ZERO_GEOMETRY_EQUIVALENCE_MISSING" in _codes(common_missing)
    assert validate_template(interaction).metadata_verified


def test_inference_defines_exact_and_sampled_branches_without_extension() -> None:
    payload = _complete_metadata_fixture()
    assert validate_template(payload).metadata_verified

    payload["inference"]["exact_enumeration"]["p_value"] = "(1+K)/(|G|+1)"
    payload["inference"]["sampled_monte_carlo"]["draws"] = 99999
    payload["inference"]["method_selection_rule"] = "choose after result"

    codes = _codes(payload)

    assert "SCHEMA_CONST" in codes
    assert "INFERENCE_RULE_INVALID" in codes


def test_sharp_null_and_sampled_assignment_rule_are_exactly_locked() -> None:
    payload = _complete_metadata_fixture()
    payload["inference"]["null_hypothesis"] = "H0: E[T]<=0 under exchangeability"
    payload["inference"]["sampled_monte_carlo"][
        "assignment_draw_rule"
    ] = "sample distinct assignments without replacement"

    assert "SCHEMA_CONST" in _codes(payload)


def test_normalized_condition_and_oblique_heldout_direction_are_enforced() -> None:
    ill_conditioned = _complete_metadata_fixture()
    ill_conditioned["prediction_model"]["noncoplanar_normals"] = [
        [1.0, 0.0, 0.0],
        [1.0, 1e-5, 0.0],
        [1.0, 0.0, 1e-5],
    ]
    axis_repeat = _complete_metadata_fixture()
    axis_repeat["prediction_model"]["oblique_heldout_direction"] = [1.0, 0.0, 0.0]

    ill_codes = _codes(ill_conditioned)
    assert "PREDICTION_CONDITION_MISMATCH" in ill_codes
    assert "PREDICTION_CONDITION_EXCEEDED" in ill_codes
    assert "HELDOUT_DIRECTION_NOT_OBLIQUE" in _codes(axis_repeat)


@pytest.mark.parametrize("raw_path", ["", "/absolute.bin", "../escape.bin", "raw\\bad.bin"])
def test_raw_paths_are_nonempty_canonical_relative_slash_paths(raw_path: str) -> None:
    payload = _complete_metadata_fixture()
    raw = payload["substrate"]["source_qualification"]["raw_file_sha256"]
    value = raw.pop("raw/device-a.bin")
    raw[raw_path] = value

    assert "SOURCE_RAW_PATH_INVALID" in _codes(payload)


def test_raw_paths_are_casefold_unique() -> None:
    payload = _complete_metadata_fixture()
    raw = payload["substrate"]["source_qualification"]["raw_file_sha256"]
    raw["RAW/DEVICE-A.BIN"] = _hash("duplicate-case-path")
    payload["substrate"]["source_qualification"]["raw_manifest_file_count"] = 3

    assert "SOURCE_RAW_PATH_DUPLICATE" in _codes(payload)


@pytest.mark.parametrize(
    ("target", "expected_code"),
    [
        ("remainder", "REMAINDER_UNITS_MISMATCH"),
        ("interaction", "INTERACTION_UNITS_MISMATCH"),
        ("comparator", "COMPARATOR_LOSS_UNITS_INVALID"),
    ],
)
def test_all_integrated_response_and_loss_units_are_bound(target: str, expected_code: str) -> None:
    payload = _complete_metadata_fixture()
    readiness = payload["source_specific_freeze_readiness"]
    if target == "remainder":
        payload["tangent_remainder_validation"]["uniform_remainder_bound"][
            "integrated_response_units"
        ] = "metres"
    elif target == "interaction":
        readiness["interaction_nondegeneracy_definition"]["units"] = "metres"
    else:
        readiness["comparator_definition"]["loss_units"] = "metres"

    assert expected_code in _codes(payload)


def test_claim_and_template_kind_cannot_be_mutated_into_evidence() -> None:
    payload = _complete_metadata_fixture()
    payload["template_kind"] = "empirical_result"
    payload["claim_ceiling"]["template_is_evidence"] = True
    payload["claim_ceiling"]["allowed_if_future_pass"] = "universal CWT proof"
    payload["claim_ceiling"]["forbidden_generalizations"] = []
    payload["claim_ceiling"]["universal_claim"] = True

    codes = _codes(payload)

    assert "SCHEMA_CONST" in codes
    assert "SCHEMA_UNKNOWN_FIELD" in codes
    assert "CLAIM_SCOPE_INVALID" in codes
    assert "CLAIM_FORBIDDEN_SET_INVALID" in codes
    assert "PREMATURE_FUTURE_CLAIM" in codes


def test_cli_has_no_confirmation_outcome_or_result_command() -> None:
    runner = CliRunner()
    help_result = runner.invoke(app, ["--help"])
    status_result = runner.invoke(app, ["status"])
    command_names = set(get_command(app).commands)

    assert help_result.exit_code == 0
    assert {"status", "validate-template", "freeze-template", "verify-template"} <= command_names
    assert all("confirm" not in name for name in command_names)
    assert all("result" not in name for name in command_names)
    assert status_result.exit_code == 2
    assert "BLOCKED_NO_SUBSTRATE" in status_result.stdout


def test_artifact_freeze_is_exact_lf_and_tamper_evident(tmp_path: Path) -> None:
    output = tmp_path / "template"
    first = write_template_artifacts(output_dir=output)
    first_hashes = {name: sha256_file(path) for name, path in first.items()}
    second = write_template_artifacts(output_dir=output)
    second_hashes = {name: sha256_file(path) for name, path in second.items()}

    assert first_hashes == second_hashes
    assert {path.name for path in second.values()} == set(ARTIFACT_FILENAMES)
    assert all(b"\r" not in path.read_bytes() for path in second.values())
    assert verify_template_artifacts(output_dir=output)["status"] == (
        "TEMPLATE_VERIFIED_BLOCKED_NO_SUBSTRATE"
    )

    (output / "REPORT.md").write_bytes((output / "REPORT.md").read_bytes() + b"tamper\n")
    with pytest.raises(ArtifactVerificationError, match="differ.*generator"):
        verify_template_artifacts(output_dir=output)


def test_artifact_verifier_rejects_nested_hidden_outcome_file(tmp_path: Path) -> None:
    output = tmp_path / "template"
    write_template_artifacts(output_dir=output)
    hidden = output / "hidden"
    hidden.mkdir()
    (hidden / "outcome.json").write_text("{}\n", encoding="utf-8", newline="\n")

    with pytest.raises(ArtifactVerificationError, match="unexpected template artifact inventory"):
        verify_template_artifacts(output_dir=output)


def test_source_text_hash_domain_is_lf_crlf_portable_and_fails_closed() -> None:
    lf = b"alpha\nbeta\n"
    crlf = b"alpha\r\nbeta\r\n"

    assert canonical_source_text_bytes(lf) == canonical_source_text_bytes(crlf) == lf
    with pytest.raises(ValueError, match="carriage"):
        canonical_source_text_bytes(b"alpha\rbeta\n")
    with pytest.raises(ValueError, match="BOM"):
        canonical_source_text_bytes(b"\xef\xbb\xbfalpha\n")
    with pytest.raises(UnicodeDecodeError):
        canonical_source_text_bytes(b"\xff\xfe")
    assert (
        hashlib.sha256(canonical_source_text_bytes(lf)).digest()
        != hashlib.sha256(canonical_source_text_bytes(b"alpha\ngamma\n")).digest()
    )


def test_checked_schema_is_generated_recursively_closed_lf_json() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert SCHEMA_PATH.read_bytes() == canonical_schema_bytes()
    assert schema["additionalProperties"] is False
    assert schema["properties"]["substrate"]["additionalProperties"] is False
    assert b"\r" not in DEFAULT_TEMPLATE_PATH.read_bytes()
    assert b"\r" not in SCHEMA_PATH.read_bytes()


def test_substrate_screen_discloses_structural_inspection_without_outcome_analysis() -> None:
    screen = (EXPERIMENT_DIR / "SUBSTRATE_SCREEN.md").read_text(encoding="utf-8")
    normalized_screen = " ".join(screen.replace(">", "").split())

    assert "no reviewed public source clears G0-G12" in screen
    assert "Small official" in screen
    assert "no candidate outcome analysis was conducted" in normalized_screen
    assert "no candidate data were retained" in normalized_screen
    assert "BLOCKED_NO_SUBSTRATE" in screen
    assert "zenodo.org/records/15857197" in screen
    assert "zenodo.15299253" in screen
    assert "12 calibration reset blocks" in screen
    assert "40-48" in screen


def test_python_package_has_no_numeric_or_oedi_data_adapter_import() -> None:
    prohibited_import_roots = {"numpy", "pandas", "scipy", "xarray"}
    for path in sorted(EXPERIMENT_DIR.glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert imported.isdisjoint(prohibited_import_roots)
        assert "oedi" not in source.casefold()


def test_state_model_can_never_emit_study_pass_or_fail() -> None:
    values = {state.value for state in TemplateState}

    assert "PASS" not in values
    assert "FAIL" not in values
    assert (
        validate_template(_complete_metadata_fixture()).as_dict()["maximum_reachable_state"]
        == "METADATA_VERIFIED_PENDING_IMPLEMENTATION"
    )

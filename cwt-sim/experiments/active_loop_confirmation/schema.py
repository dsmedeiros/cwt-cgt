"""Canonical strict schema for the metadata-only active-loop template."""

from __future__ import annotations

import json
from typing import Any

SHA256_PATTERN = "^[0-9a-f]{64}$"
RAW_PATH_PATTERN = (
    r"^(?!/)(?![A-Za-z]:)(?!.*(?:^|/)\.\.(?:/|$))(?!.*//)" r"[A-Za-z0-9._-]+(?:/[A-Za-z0-9._-]+)*$"
)
PSEUDONYM_PATTERN = "^ep_[0-9a-f]{16}$"
PREIMPLEMENTATION_STATES = [
    "BLOCKED_NO_SUBSTRATE",
    "BLOCKED_INELIGIBLE_SOURCE",
    "BLOCKED_INCOMPLETE_METADATA",
    "METADATA_VERIFIED_PENDING_IMPLEMENTATION",
]
POWER_GATES = [
    "firewall_and_validity",
    "randomization",
    "beta_equivalence",
    "response_sesoi",
    "perpendicular_tensor",
    "comparator_loss",
    "on_zero_interaction",
    "tangent_remainder",
    "controls",
]


def _object(properties: dict[str, Any], *, additional: bool | dict[str, Any] = False) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": additional,
        "properties": properties,
        "required": list(properties),
    }


def _nullable(kind: str, **constraints: Any) -> dict[str, Any]:
    return {"type": ["null", kind], **constraints}


def _nullable_object(schema: dict[str, Any]) -> dict[str, Any]:
    """Return an object schema that also accepts the blocked-template null."""

    result = dict(schema)
    result["type"] = ["null", "object"]
    return result


def _nullable_array(
    item_schema: dict[str, Any],
    *,
    min_items: int | None = None,
    max_items: int | None = None,
    unique: bool = False,
) -> dict[str, Any]:
    schema: dict[str, Any] = {"type": ["null", "array"], "items": item_schema}
    if min_items is not None:
        schema["minItems"] = min_items
    if max_items is not None:
        schema["maxItems"] = max_items
    if unique:
        schema["uniqueItems"] = True
    return schema


def _power_gate_schema() -> dict[str, Any]:
    return _object(
        {
            "power": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "effect": {"type": "number", "exclusiveMinimum": 0.0},
            "variance": {"type": "number", "exclusiveMinimum": 0.0},
            "independent_n": {"type": "integer", "minimum": 1},
            "method": {"type": "string", "minLength": 1},
            "assumptions": {"type": "string", "minLength": 1},
            "seed": {"type": "integer", "minimum": 0},
        }
    )


def protocol_schema() -> dict[str, Any]:
    """Return the complete recursively closed JSON-schema document."""

    nullable_text = _nullable("string", minLength=1)
    nullable_bool = _nullable("boolean")
    nullable_positive = _nullable("number", exclusiveMinimum=0.0)
    nullable_hash = _nullable("string", pattern=SHA256_PATTERN)
    nullable_text_array = _nullable_array({"type": "string", "minLength": 1}, unique=True)
    nullable_hash_array = _nullable_array({"type": "string", "pattern": SHA256_PATTERN}, unique=True)
    nullable_positive_array = _nullable_array(
        {"type": "number", "exclusiveMinimum": 0.0}, min_items=5, unique=True
    )

    source_qualification = _object(
        {
            "external_source": nullable_bool,
            "immutable_primary_raw_measurements": nullable_bool,
            "physical_measurement": nullable_bool,
            "actually_executed_intervention": nullable_bool,
            "randomized_orientation": nullable_bool,
            "counterbalanced_orientation": nullable_bool,
            "commanded_controls_recorded": nullable_bool,
            "achieved_controls_recorded": nullable_bool,
            "independent_raw_response_recorded": nullable_bool,
            "reset_block_ids_recorded": nullable_bool,
            "physical_timestamps_recorded": nullable_bool,
            "measurement_units_recorded": nullable_bool,
            "passive_only": nullable_bool,
            "simulated": nullable_bool,
            "derived_only": nullable_bool,
            "natural_cycle_only": nullable_bool,
            "model_generated": nullable_bool,
            "immutable_revision": nullable_text,
            "license_identifier": nullable_text,
            "raw_manifest_sha256": nullable_hash,
            "raw_manifest_file_count": _nullable("integer", minimum=1),
            "raw_file_sha256": {
                "type": ["null", "object"],
                "minProperties": 1,
                "additionalProperties": {"type": "string", "pattern": SHA256_PATTERN},
                "propertyNames": {
                    "type": "string",
                    "minLength": 1,
                    "pattern": RAW_PATH_PATTERN,
                },
                "properties": {},
            },
        }
    )
    partition = _object(
        {
            "cluster_ids": nullable_text_array,
            "alias_ids": nullable_text_array,
            "content_sha256": nullable_hash_array,
        }
    )
    remainder = _object(
        {
            "form": {"const": "|r|/s^2 <= C_s*s + C_T*tau/T + C_dt*(dt/tau)^p + C_phi*s"},
            "selected_domain": {"type": "string", "minLength": 1},
            "probability_domain": {"enum": ["deterministic", "high_probability"]},
            "probability_level": _nullable("number", exclusiveMinimum=0.0, maximum=1.0),
            "p": {"type": "number", "exclusiveMinimum": 0.0},
            "response_units_after_dividing_by_s_squared": {"type": "string", "minLength": 1},
            "constants": _object(
                {
                    "C_s": {"type": "number", "minimum": 0.0},
                    "C_T": {"type": "number", "minimum": 0.0},
                    "C_dt": {"type": "number", "minimum": 0.0},
                    "C_phi": {"type": "number", "minimum": 0.0},
                }
            ),
        }
    )
    calibration_power = _object(
        {
            "required_minimum_power": {"const": 0.9},
            "powered_confirmation_n": {"type": "integer", "minimum": 20},
            "method": {"type": "string", "minLength": 1},
            "assumptions": {"type": "string", "minLength": 1},
            "seed": {"type": "integer", "minimum": 0},
            "gates": _object({gate: _power_gate_schema() for gate in POWER_GATES}),
        }
    )

    properties: dict[str, Any] = {
        "schema_version": {"const": 2},
        "template_id": {"const": "active-loop-confirmation-v2"},
        "template_kind": {"const": "metadata_only_design_template"},
        "template_state": {"enum": PREIMPLEMENTATION_STATES},
        "analysis_implementation_available": {"const": False},
        "substrate": _object(
            {
                "identifier": nullable_text,
                "source_qualification": source_qualification,
            }
        ),
        "coordinates": _object(
            {
                "dimension": _nullable("integer", minimum=3, maximum=3),
                "independently_actuable_controls": _nullable_array(
                    {"type": "string", "minLength": 1}, min_items=3, max_items=3, unique=True
                ),
                "units": _nullable_array({"type": "string", "minLength": 1}, min_items=3, max_items=3),
                "reference": _nullable_array({"type": "number"}, min_items=3, max_items=3),
                "scales": _nullable_array(
                    {"type": "number", "exclusiveMinimum": 0.0}, min_items=3, max_items=3
                ),
                "right_handed_order": _nullable_array(
                    {"type": "string", "minLength": 1}, min_items=3, max_items=3, unique=True
                ),
                "right_handed_orientation_verified": nullable_bool,
                "normalized_coordinate_rule": {"const": "x^i=(lambda^i-lambda_ref^i)/L_i"},
                "connection_convention": {"const": "A_i=-i<psi|partial_i psi>"},
                "curvature_convention": {"const": "Omega_ij=+2 Im C_ij"},
            }
        ),
        "response_firewall": _object(
            {
                "reducer_input_fields": {
                    "const": [
                        "pseudonymous_episode_id",
                        "physical_timestamps",
                        "calibrated_response",
                        "predeclared_response_baseline",
                        "response_sensor_qc",
                    ]
                },
                "forbidden_fields": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
                "response_signal": nullable_text,
                "response_signal_units": nullable_text,
                "response_units": nullable_text,
                "integrated_units_derivation": nullable_text,
                "baseline_definition": nullable_text,
                "reducer_code_sha256": nullable_hash,
                "window_id_semantics": {"enum": [None, "pseudonymous_sha256_prefix_v1"]},
                "example_window_ids": _nullable_array(
                    {"type": "string", "pattern": PSEUDONYM_PATTERN}, unique=True
                ),
                "geometry_mutation_response_bytes_identical": nullable_bool,
                "quadrature_semantics": {"const": "Q=integral[Y(t)-b(t)]dt with physical timestamps"},
            }
        ),
        "quartet": _object(
            {
                "coupling_levels": {"const": ["on", "zero"]},
                "orientations": {"const": ["positive", "negative"]},
                "negative_path_rule": {"const": "gamma_minus(t)=gamma_plus(T-t)"},
                "exact_zero_coupling_mechanism": nullable_text,
                "same_schedule_sensors_and_hysteresis_at_zero": nullable_bool,
                "matched_achieved_shape_and_duration": nullable_bool,
                "common_physical_clock_verified": nullable_bool,
                "assignment_table_sha256": nullable_hash,
            }
        ),
        "physical_time_protocol": _object(
            {
                "duration_seconds": nullable_positive,
                "dt_seconds": nullable_positive,
                "timestamp_units": {"enum": [None, "seconds"]},
                "latency_bound_seconds": _nullable("number", minimum=0.0),
                "jitter_bound_seconds": _nullable("number", minimum=0.0),
                "quadrature_rule": {"enum": [None, "timestamp_weighted_trapezoidal_Q_integral_v1"]},
                "endpoint_rule": nullable_text,
                "achieved_path_source": nullable_text,
                "achieved_path_closure_tolerance": nullable_positive,
                "washout_or_periodic_initialization": nullable_text,
                "control_dynamics_map": _nullable_object(
                    _object(
                        {
                            "kind": {"const": "continuous_rate_map"},
                            "formula": {"const": "alpha(dt)=1-exp(-dt/tau)"},
                            "tau_seconds": {
                                "type": "number",
                                "exclusiveMinimum": 0.0,
                            },
                            "fixed_alpha_across_dt_ladder": {"const": False},
                        }
                    )
                ),
                "waveform_family": nullable_text,
                "dt_ladder": nullable_positive_array,
                "duration_ladder": nullable_positive_array,
                "scale_ladder": nullable_positive_array,
                "heldout_level_index": _object(
                    {
                        "dt": _nullable("integer", minimum=0),
                        "duration": _nullable("integer", minimum=0),
                        "scale": _nullable("integer", minimum=0),
                    }
                ),
            }
        ),
        "cluster_split": _object(
            {
                "independent_unit_kind": {
                    "enum": [
                        None,
                        "independently_randomized_washed_out_reset_block",
                    ]
                },
                "minimum_independent_blocks": {"type": "integer", "minimum": 20},
                "salt": nullable_text,
                "assignment_rule": nullable_text,
                "duplicate_detection_rule": nullable_text,
                "partitions": _object(
                    {
                        "calibration": partition,
                        "reduction_validation": partition,
                        "confirmation": partition,
                    }
                ),
            }
        ),
        "geometry_firewall": _object(
            {
                "state_sensor": nullable_text,
                "state_map_revision": nullable_text,
                "projector_estimator": nullable_text,
                "wilson_estimator": nullable_text,
                "qgt_estimator": nullable_text,
                "estimator_code_sha256": nullable_hash,
                "gap_overlap_gauge_qc": nullable_text,
                "response_signal_access": {"const": False},
                "state_sensor_distinct_from_response": nullable_bool,
            }
        ),
        "predictor_geometry": _object(
            {
                "mode": _nullable("string"),
                "finite_flux_definition": {
                    "const": "Phi(S)=integral_S Omega using frozen integrated-curvature or Wilson estimator"
                },
                "finite_flux_estimator": nullable_text,
                "local_vector_area_approximation": {
                    "const": "Phi=omega(c).a+O(s^3) for the frozen shrinking-loop family"
                },
                "local_approximation_in_remainder": nullable_bool,
                "zero_state_equivalence": nullable_bool,
                "zero_achieved_path_equivalence": nullable_bool,
                "zero_omega_equivalence": nullable_bool,
                "state_equivalence_margin": nullable_positive,
                "path_equivalence_margin": nullable_positive,
                "omega_equivalence_margin": nullable_positive,
                "geometry_interaction_definition": _nullable_object(
                    _object(
                        {
                            "kind": {"const": "state_only_condition_contrast_v1"},
                            "description": {"type": "string", "minLength": 1},
                            "response_inputs_allowed": {"const": False},
                            "uses_confirmation_response": {"const": False},
                            "definition_sha256": {
                                "type": "string",
                                "pattern": SHA256_PATTERN,
                            },
                        }
                    )
                ),
                "geometry_interaction_code_sha256": nullable_hash,
            }
        ),
        "tangent_remainder_validation": _object(
            {
                "interaction_one_form": {"const": "B^D=B^on-B^0"},
                "interaction_curvature": {"const": "F_R^D=dB^D"},
                "compare_interaction_not_on_only": {"const": True},
                "derivation_or_memory_kernel_limit": nullable_text,
                "uniform_remainder_bound": _nullable_object(remainder),
                "minimum_fit_levels_per_ladder": {"const": 4},
                "heldout_ladder_level_required": {"const": True},
                "reversal_test": nullable_text,
                "cyclic_start_test": nullable_text,
                "smooth_reparameterization_test": nullable_text,
                "concatenation_test": nullable_text,
                "matched_area_shape_test": nullable_text,
                "line_integral_comparison": nullable_text,
            }
        ),
        "prediction_model": _object(
            {
                "dimension": {"const": 3},
                "fit_partitions": {"const": ["calibration"]},
                "forbid_pointwise_heldout_f_response_over_omega": {"const": True},
                "calibration_model_family": _nullable_object(
                    _object(
                        {
                            "kind": {
                                "enum": [
                                    "constant_kappa_v1",
                                    "low_dimensional_kappa_v1",
                                ]
                            },
                            "description": {"type": "string", "minLength": 1},
                            "fit_partitions": {"const": ["calibration"]},
                            "uses_confirmation_response": {"const": False},
                            "uses_heldout_local_response_curvature_ratio": {"const": False},
                            "model_spec_sha256": {
                                "type": "string",
                                "pattern": SHA256_PATTERN,
                            },
                        }
                    )
                ),
                "rank_three_area_vector_design": nullable_bool,
                "area_vector_normalization_rule": {
                    "const": "unit_Euclidean_norm_before_Frobenius_condition_v1"
                },
                "condition_number_method": {"const": "Frobenius_norm_A_times_Frobenius_norm_A_inverse"},
                "declared_frobenius_condition_number": nullable_positive,
                "noncoplanar_normals": _nullable_array(
                    {
                        "type": "array",
                        "items": {"type": "number"},
                        "minItems": 3,
                        "maxItems": 3,
                    },
                    min_items=3,
                    max_items=3,
                ),
                "oblique_heldout_direction": _nullable_array({"type": "number"}, min_items=3, max_items=3),
                "heldout_oblique_max_abs_cosine": _nullable(
                    "number", exclusiveMinimum=0.0, maximum=0.999999999999
                ),
                "prediction_hash_before_response_unlock": nullable_hash,
                "geometry_uncertainty_method": nullable_text,
                "calibration_uncertainty_method": nullable_text,
            }
        ),
        "inference": _object(
            {
                "primary_statistic": {"const": "T:=S=sum_bl w_l*mu_l*D_bl"},
                "null_hypothesis": {
                    "const": "H0: outcomes are invariant under every admissible assignment in G"
                },
                "alternative_hypothesis": {"const": "H1: T>0 in the frozen CGT-predicted direction"},
                "randomization_group": {
                    "enum": [
                        None,
                        (
                            "all_distinct_balanced_block_level_quartet_sign_code_"
                            "assignments_within_frozen_strata"
                        ),
                    ]
                },
                "strata_rule": nullable_text,
                "ties_rule": {
                    "enum": [
                        None,
                        "count_permuted_T_greater_than_or_equal_to_observed_as_extreme",
                    ]
                },
                "duplicate_assignment_rule": {
                    "enum": [None, "deduplicate_assignments_and_include_observed_once"]
                },
                "method_selection_rule": {
                    "enum": [
                        None,
                        "exact_if_group_size_at_most_999999_else_999999_seeded_draws",
                    ]
                },
                "exact_enumeration": _object(
                    {
                        "p_value": {"const": "K/|G|"},
                        "includes_observed_assignment_once": {"const": True},
                        "monte_carlo_interval": {"const": False},
                        "decision_rule": {"const": "p<0.01 PASS; p>=0.01 FAIL"},
                    }
                ),
                "sampled_monte_carlo": _object(
                    {
                        "draws": {"const": 999999},
                        "assignment_draw_rule": {
                            "const": ("independent_uniform_with_replacement_from_G_using_frozen_seed")
                        },
                        "p_value": {"const": "(1+K)/(M+1)"},
                        "tail_probability_interval": {
                            "const": "99% Clopper-Pearson interval for q=P(T_perm>=T_observed)"
                        },
                        "decision_rule": {
                            "const": ("CP99 upper<0.01 PASS; lower>0.01 FAIL; " "straddle INDETERMINATE")
                        },
                        "ad_hoc_extension_allowed": {"const": False},
                    }
                ),
                "primary_alpha": {"const": 0.01},
                "confidence_level": {"const": 0.99},
                "randomization_unit": {
                    "enum": [
                        None,
                        "independently_randomized_washed_out_reset_block",
                    ]
                },
                "randomization_seed": _nullable("integer", minimum=0),
                "primary_weights_rule": _nullable_object(
                    _object(
                        {
                            "formula": {"type": "string", "minLength": 1},
                            "provenance": {"const": "calibration_design_only_v1"},
                            "fit_partitions": {"const": ["calibration"]},
                            "uses_confirmation_response": {"const": False},
                            "uses_heldout_response": {"const": False},
                            "weights_sha256": {
                                "type": "string",
                                "pattern": SHA256_PATTERN,
                            },
                        }
                    )
                ),
                "all_primary_gates_conjunctive": {"const": True},
                "fixed_sample_no_interim": {"const": True},
                "secondary_holm_alpha": {"const": 0.05},
            }
        ),
        "source_specific_freeze_readiness": _object(
            {
                "current_status": {"enum": PREIMPLEMENTATION_STATES},
                "calibration_power": _nullable_object(calibration_power),
                "physical_response_sesoi": _nullable_object(
                    _object(
                        {
                            "target": {"const": "D_bl"},
                            "value": {"type": "number", "exclusiveMinimum": 0.0},
                            "units": {"type": "string", "minLength": 1},
                            "direction": {"enum": ["absolute_magnitude", "predicted_signed"]},
                        }
                    )
                ),
                "beta_equivalence_margin": nullable_positive,
                "beta_interval_definition": _nullable_object(
                    _object(
                        {
                            "confidence": {"const": 0.99},
                            "method": {"type": "string", "minLength": 1},
                            "cluster_unit": {"type": "string", "minLength": 1},
                            "calibration_uncertainty": {"type": "string", "minLength": 1},
                            "geometry_uncertainty": {"type": "string", "minLength": 1},
                            "denominator_rule": {"type": "string", "minLength": 1},
                            "near_zero_rule": {"type": "string", "minLength": 1},
                            "finite_miss_rule": {"const": "FAIL"},
                            "undefined_rule": {"const": "INDETERMINATE"},
                        }
                    )
                ),
                "response_lower_bound_definition": _nullable_object(
                    _object(
                        {
                            "target": {"const": "absolute D_bl aligned with mu_l"},
                            "confidence": {"const": 0.99},
                            "method": {"type": "string", "minLength": 1},
                            "cluster_aggregation": {"type": "string", "minLength": 1},
                            "uncertainty_propagation": {"type": "string", "minLength": 1},
                            "finite_miss_rule": {"const": "FAIL"},
                            "undefined_rule": {"const": "INDETERMINATE"},
                        }
                    )
                ),
                "perpendicular_tensor_margin": nullable_positive,
                "perpendicular_ratio_definition": _nullable_object(
                    _object(
                        {
                            "numerator": {"type": "string", "minLength": 1},
                            "denominator": {"type": "string", "minLength": 1},
                            "near_zero_rule": {"type": "string", "minLength": 1},
                            "confidence_bound_method": {"type": "string", "minLength": 1},
                            "finite_miss_rule": {"const": "FAIL"},
                            "undefined_rule": {"const": "INDETERMINATE"},
                        }
                    )
                ),
                "comparator_loss_advantage_margin": nullable_positive,
                "comparator_definition": _nullable_object(
                    _object(
                        {
                            "name": {"type": "string", "minLength": 1},
                            "inputs": {"type": "array", "items": {"type": "string"}, "minItems": 1},
                            "loss": {"type": "string", "minLength": 1},
                            "loss_units": {"const": "dimensionless_normalized_loss"},
                            "aggregation_unit": {"type": "string", "minLength": 1},
                            "uncertainty_method": {"type": "string", "minLength": 1},
                            "finite_miss_rule": {"const": "FAIL"},
                            "undefined_rule": {"const": "INDETERMINATE"},
                        }
                    )
                ),
                "interaction_nondegeneracy_definition": _nullable_object(
                    _object(
                        {
                            "target": {"const": "D_bl"},
                            "effect_threshold": {"type": "number", "exclusiveMinimum": 0.0},
                            "units": {"type": "string", "minLength": 1},
                            "confidence_bound_method": {"type": "string", "minLength": 1},
                            "valid_zero_flux_orientation_effect": {"const": "FAIL"},
                            "finite_miss_rule": {"const": "FAIL"},
                            "undefined_rule": {"const": "INDETERMINATE"},
                        }
                    )
                ),
                "condition_number_threshold": nullable_positive,
                "missingness_and_qc_rules": nullable_text,
            }
        ),
        "controls": _object(
            {
                "retraced_zero_area_sham": nullable_text,
                "omega_orthogonal_nonzero_area_loop": nullable_text,
                "order_counterbalance": nullable_text,
                "gauge_invariance": nullable_text,
                "component_and_center_scramble": nullable_text,
                "response_sensor_reference_injection": nullable_text,
                "zero_geometry_comparator": nullable_text,
                "metric_only_comparator": nullable_text,
                "control_only_comparator": nullable_text,
            }
        ),
        "stopping_and_recovery": _object(
            {
                "authorized_confirmation_executions": {"const": 1},
                "default_retry_allowed": {"const": False},
                "incident_ledger_required": {"const": True},
                "independent_reauthorization_required": {"const": True},
                "identical_digest_required": {"const": True},
                "no_outcome_observed_required": {"const": True},
                "no_live_process_or_artifact_required": {"const": True},
            }
        ),
        "lock_and_authorization": _object(
            {
                "acyclic_byte_hash_closure_required": {"const": True},
                "raw_lineage_units_and_diagrams_required": {"const": True},
                "split_waveform_randomization_table_required": {"const": True},
                "commanded_and_achieved_paths_required": {"const": True},
                "qc_code_container_dependencies_seeds_predictions_required": {"const": True},
                "clean_index_archive_cross_platform_verification_required": {"const": True},
                "independent_preflight_review_required": {"const": True},
            }
        ),
        "claim_ceiling": _object(
            {
                "allowed_if_future_pass": nullable_text,
                "forbidden_generalizations": {
                    "type": "array",
                    "items": {"type": "string", "minLength": 1},
                    "uniqueItems": True,
                },
                "template_is_evidence": {"const": False},
                "template_is_study_preregistration": {"const": False},
            }
        ),
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": "https://cwt-cgt.invalid/schemas/active-loop-confirmation-v2.json",
        "title": "Active-loop confirmation metadata-only design template",
        "description": (
            "Recursively closed metadata schema. Null substrate fields preserve the checked-in "
            "BLOCKED_NO_SUBSTRATE state; semantic gates are applied by template_model.py."
        ),
        **_object(properties),
    }


def canonical_schema_bytes() -> bytes:
    """Return strict deterministic LF JSON for the checked schema file."""

    return (json.dumps(protocol_schema(), allow_nan=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

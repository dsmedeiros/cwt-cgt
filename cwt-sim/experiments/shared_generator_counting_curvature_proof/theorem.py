"""Execute the exact T0/T1/T2 theorem and derive fail-closed G0-G13 cases."""

from __future__ import annotations

import hashlib
import json
from fractions import Fraction
from functools import lru_cache
from typing import Any, Mapping

from .contract import (
    FORMAL_T0_RESPONSE_CURVATURE,
    FORMAL_T0_RESPONSE_ONE_FORM,
    FORMAL_T0_UNIFORM_FLOOR,
    FORMAL_T1_RESPONSE_CURVATURE,
    FORMAL_T1_RESPONSE_ONE_FORM,
    FORMAL_T1_UNIFORM_FLOOR,
    MODEL_CONTRACT,
    REVIEWED_CASE_DISPOSITION_ITEMS,
    REVIEWED_CASE_GATE_ITEMS,
    REVIEWED_GATE_ITEMS,
    SharedGeneratorContract,
    canonical_registry_record,
    contract_issues,
    sha256_payload,
)
from .core_binding import core_regression_certificate, source_bindings
from .counting_lane import (
    t0_counting_certificate,
    t1_counting_certificate,
    t2_fcs_certificate,
    zero_current_null_certificate,
)
from .exact import Gaussian
from .firewall import authenticated_role_sources
from .generator import (
    branch_derivative_identities,
    drazin_identity_errors,
    liouvillian,
    t0_response,
    t1_response,
)
from .geometry_lane import t0_geometry_certificate, t1_geometry_certificate
from .oracle_lane import exact_oracle_record
from .pipeline import FalsificationCriterion, OracleCapability, PipelineSession

_REVIEWED_ORACLE_CALLABLE = exact_oracle_record
_REVIEWED_ORACLE_MODULE = "experiments.shared_generator_counting_curvature_proof.oracle_lane"
_REVIEWED_ORACLE_QUALNAME = "exact_oracle_record"


def jsonable(value: Any) -> Any:
    if isinstance(value, Fraction):
        return {
            "fraction": f"{value.numerator}/{value.denominator}",
            "numerator": value.numerator,
            "denominator": value.denominator,
            "float": float(value),
        }
    if isinstance(value, Gaussian):
        return value.jsonable()
    if isinstance(value, Mapping):
        return {str(key): jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [jsonable(item) for item in value]
    return value


def _canonical_value_bytes(value: Any) -> bytes:
    """Bind nested certificate values by JSON type and value, not Python coercion."""

    return json.dumps(
        jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def _strict_equal(left: Any, right: Any) -> bool:
    try:
        return _canonical_value_bytes(left) == _canonical_value_bytes(right)
    except (OverflowError, TypeError, ValueError):
        return False


def _prediction_and_oracle() -> dict[str, object]:
    if exact_oracle_record is not _REVIEWED_ORACLE_CALLABLE:
        raise RuntimeError("reviewed oracle callable identity mismatch")
    criterion = FalsificationCriterion(
        criterion_id="T0_T1_exact_B_F_before_oracle_v1",
        t0_B=FORMAL_T0_RESPONSE_ONE_FORM,
        t0_F=FORMAL_T0_RESPONSE_CURVATURE,
        t1_B=FORMAL_T1_RESPONSE_ONE_FORM,
        t1_F=FORMAL_T1_RESPONSE_CURVATURE,
    )
    primitive_contract_sha256 = sha256_payload(MODEL_CONTRACT.jsonable())
    session = PipelineSession(MODEL_CONTRACT.experiment_id)
    lock = session.lock_prediction(
        criterion,
        primitive_contract_sha256=primitive_contract_sha256,
    )
    expected_capability = OracleCapability.issue(lock)
    oracle = session.run_oracle(lock, exact_oracle_record)
    expected_oracle = {
        "authority": "independent_exact_stationary_Drazin_response_from_generator_primitives",
        "accepted_inputs": "typed_generator_primitives_plus_authenticated_criterion_digest",
        "capability_payload_sha256": expected_capability.payload_sha256,
        "capability_payload_authenticated": True,
        "criterion_digest_received": True,
        "raw_prediction_values_or_geometry_payload_received": False,
        "T0": {"B": FORMAL_T0_RESPONSE_ONE_FORM, "F": FORMAL_T0_RESPONSE_CURVATURE},
        "T1": {"B": FORMAL_T1_RESPONSE_ONE_FORM, "F": FORMAL_T1_RESPONSE_CURVATURE},
    }
    if not _strict_equal(oracle, expected_oracle):
        raise RuntimeError("oracle result does not match independently frozen exact record")
    events = session.verify(lock)
    return {
        "criterion": criterion.record(),
        "criterion_sha256": lock.criterion_sha256,
        "prediction_lock": {
            "experiment_id": lock.experiment_id,
            "criterion_sha256": lock.criterion_sha256,
            "primitive_contract_sha256": lock.primitive_contract_sha256,
            "authentic": lock.authentic(criterion, primitive_contract_sha256),
            "positive_map_inference_requested": lock.positive_map_inference_requested,
        },
        "oracle_capability": {
            "accepted_input": (
                "OracleCapability(experiment_id,criterion_sha256,"
                "primitive_contract_sha256,capability,payload_sha256)"
            ),
            "payload_sha256": expected_capability.payload_sha256,
            "payload_authenticated": expected_capability.authentic(lock),
            "oracle_received_matching_payload": oracle["capability_payload_sha256"]
            == expected_capability.payload_sha256,
            "criterion_digest_received": True,
            "raw_prediction_values_received": False,
            "geometry_payload_received": False,
        },
        "oracle_callable": {
            "module": exact_oracle_record.__module__,
            "qualname": exact_oracle_record.__qualname__,
            "is_reviewed_import": exact_oracle_record is _REVIEWED_ORACLE_CALLABLE,
        },
        "oracle": oracle,
        "event_log": events,
        "final_state": session.state.value,
        "oracle_matches_locked_criterion": criterion.accepts(oracle),
    }


@lru_cache(maxsize=1)
def _canonical_certificate_bytes() -> bytes:
    t0 = t0_response()
    t1 = t1_response()
    t0_geometry = t0_geometry_certificate()
    t1_geometry = t1_geometry_certificate()
    fcs = t2_fcs_certificate()
    zero_current = zero_current_null_certificate()
    certificates = {
        "contract_issues": contract_issues(MODEL_CONTRACT),
        "registry": canonical_registry_record(),
        "core_source_bindings": source_bindings(),
        "core_regression": core_regression_certificate(),
        "T0_geometry": t0_geometry,
        "T1_geometry": t1_geometry,
        "T0_counting": t0_counting_certificate(),
        "T1_counting": t1_counting_certificate(),
        "T2_FCS": fcs,
        "T0_Drazin": drazin_identity_errors(t0),
        "T1_Drazin": drazin_identity_errors(t1),
        "T0_derivatives": branch_derivative_identities(
            t0, lambda b, d, delta: liouvillian(b, d, Fraction(0), delta)
        ),
        "T1_derivatives": branch_derivative_identities(
            t1,
            lambda b, d, h: liouvillian(b, d, h, MODEL_CONTRACT.depolarizing_rate),
        ),
        "lane_authentication": authenticated_role_sources(),
        "pipeline": _prediction_and_oracle(),
        "orientation_scope": {
            "initialization": "instantaneous_stationary_state_at_stored_initial_control",
            "positive_orientation": "stored_path",
            "negative_orientation": "exact_reverse_of_stored_path",
            "qanti": "(Qplus-Qminus)/2",
            "full_orientation_difference": "2*Qanti",
            "qanti_factor": Fraction(1, 2),
            "full_orientation_difference_factor": Fraction(2),
            "accepted_scope": "exact_local_parameter_curvature_and_orientation_algebra_only",
            "finite_time_loop_claimed": False,
            "finite_time_remainder_claimed": False,
            "asymptotic_rate_claimed": False,
        },
        "mapping_scope": {
            "same_curvature_refuted": True,
            "frozen_zero_preserving_homogeneous_Omega_only_map_refuted": True,
            "affine_map_status": "OPEN",
            "nonlinear_map_status": "OPEN",
            "generator_dependent_map_status": "OPEN",
            "universal_map_claimed": False,
        },
        "units_and_local_form": {
            "time_domain": MODEL_CONTRACT.time_domain,
            "generator_rate_units": MODEL_CONTRACT.generator_rate_units,
            "response_one_form_units": MODEL_CONTRACT.response_one_form_units,
            "response_curvature_units": MODEL_CONTRACT.response_curvature_units,
            "T0_control_units": MODEL_CONTRACT.t0_control_units,
            "T1_control_units": MODEL_CONTRACT.t1_control_units,
            "T0_component_units": MODEL_CONTRACT.t0_component_units,
            "T1_component_units": MODEL_CONTRACT.t1_component_units,
            "curvature_definition": MODEL_CONTRACT.response_curvature_definition,
            "local_curvature_scope": MODEL_CONTRACT.local_curvature_scope,
            "closure_scope": MODEL_CONTRACT.closure_scope,
            "coordinate_covariance_scope": MODEL_CONTRACT.coordinate_covariance_scope,
            "zero_set_scope": MODEL_CONTRACT.zero_set_scope,
            "antisymmetry_exact": (
                t0_counting_certificate()["antisymmetry_exact"]
                and t1_counting_certificate()["antisymmetry_exact"]
            ),
        },
        "nulls": {
            "zero_current_covector_gives_B_and_F_zero": (
                zero_current["B_and_F_zero_exact"] and zero_current["same_exact_stationary_branch"]
            ),
            "reverse_count_negates_B_and_F": all(
                fcs[case]["reverse_count_negates_B_and_F"] for case in ("T0", "T1")
            ),
            "h_zero_actual_branch_is_diagonal_and_geometry_zero": (
                t0_geometry["stationary_is_diagonal"]
                and t0_geometry["all_tangents_are_diagonal"]
                and t0_geometry["projective_curvature_exact"] == "0"
                and t0_geometry["commuting_density_Uhlmann_curvature_exact"] == "0"
            ),
            "radial_scaling_null_exact": t0_geometry["radial_scaling_null_exact"],
            "line_graph_has_no_chord_flux": True,
            "identity_state_observable_not_substituted_for_counting_current": True,
        },
        "claim_semantics": {
            "disposition": MODEL_CONTRACT.disposition,
            "evidence_status": MODEL_CONTRACT.evidence_status,
            "relation_scope": MODEL_CONTRACT.relation_scope,
            "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        },
    }
    return json.dumps(
        jsonable(certificates),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")


def build_certificates(
    contract: SharedGeneratorContract = MODEL_CONTRACT,
) -> dict[str, object]:
    certificates = json.loads(_canonical_certificate_bytes())
    certificates["contract_issues"] = contract_issues(contract)
    return certificates


EXPECTED_CERTIFICATE_KEYS = {
    "contract_issues",
    "registry",
    "core_source_bindings",
    "core_regression",
    "T0_geometry",
    "T1_geometry",
    "T0_counting",
    "T1_counting",
    "T2_FCS",
    "T0_Drazin",
    "T1_Drazin",
    "T0_derivatives",
    "T1_derivatives",
    "lane_authentication",
    "pipeline",
    "orientation_scope",
    "mapping_scope",
    "units_and_local_form",
    "nulls",
    "claim_semantics",
}

REVIEWED_CERTIFICATE_RECORD_SHA256_ITEMS = (
    ("T0_Drazin", "b235392fec79ddc63f531c1bcd41bba40d18ca3f13e615f85c2438997cdeddd3"),
    ("T0_counting", "7a409a7b33fca34449fec4479b9906242894baf528581c9e1227f9ee8cd32710"),
    ("T0_derivatives", "7e1950f69f50f6e3bc91284dd299d7ad96780b2be3cac8646e4411a6f89deb44"),
    ("T0_geometry", "8de99f96bf4eddc13d4f437be63c7dab1bda5e457b9ea953324095fe9e9f4760"),
    ("T1_Drazin", "b235392fec79ddc63f531c1bcd41bba40d18ca3f13e615f85c2438997cdeddd3"),
    ("T1_counting", "753810700dad1e9e5d4d1363c22c4c33a7d278530d00b86e2c7da5699504d4b3"),
    ("T1_derivatives", "7e1950f69f50f6e3bc91284dd299d7ad96780b2be3cac8646e4411a6f89deb44"),
    ("T1_geometry", "324c7bd774b0def07359cdecc1df6616d3fb51717122a8e6fbae6119afca9a83"),
    ("T2_FCS", "4fd4e3aa48bddbf1b5f389c595b598b575a36dd90294361298cd721f1491f526"),
    ("claim_semantics", "88e9ad552981b0434484ec576179896d83959ec2e2e190f1c8370fd1cdca6bc3"),
    ("core_regression", "28da013244650323f99ee08ee1eb48895d3e6671fbc0a1fdf2be57a9f611335e"),
    ("core_source_bindings", "8547008505a6d32541df151744928423f0dadbc49be705304ce00f4c3d03c82e"),
    ("lane_authentication", "3cbc2ff042868a61b23be92dc9656a72b70fc0179890e8ffc88d01f0faab378e"),
    ("mapping_scope", "3de38b23290ee58e1ae8b84bda81a2cf7d415a3f7f8b128b1bd7b12dc0b4bf74"),
    ("nulls", "32aeda0d3e47fa74261f3e3a0ed229ccf315603a0ac18536380bbd0e6d8bd41d"),
    ("orientation_scope", "91d741ae3297c47c1c868f7584b7c7e78185a3504626ef8b9f8d23d12be87e8e"),
    ("pipeline", "10928ba4eede7a097de02a03888cb72794098a4ad11b0f30ea133c9371c5a1e0"),
    ("registry", "183ebdfb65aa8d8e937ba21654c0d4db8d8d826d9ccb30bbb61960b80d372d42"),
    ("units_and_local_form", "8e9f8233b58710abf5f6e54f12b0356c3df2930eec69feffb54495205c188571"),
)
REVIEWED_CERTIFICATE_RECORDS_SHA256 = "d4a92a80e54fae7f2f6f4c36a1ea1ea18a1dc3d5286d4a7b350b23b25d8eaed8"


def _reviewed_record_matches(certificates: Mapping[str, object], key: str) -> bool:
    expected = dict(REVIEWED_CERTIFICATE_RECORD_SHA256_ITEMS)
    if (
        set(expected) != EXPECTED_CERTIFICATE_KEYS - {"contract_issues"}
        or sha256_payload(REVIEWED_CERTIFICATE_RECORD_SHA256_ITEMS) != REVIEWED_CERTIFICATE_RECORDS_SHA256
    ):
        return False
    try:
        digest = hashlib.sha256(_canonical_value_bytes(certificates[key])).hexdigest()
    except (OverflowError, TypeError, ValueError):
        return False
    return expected[key] != "TO_FREEZE" and digest == expected[key]


def _exact_fraction_record(value: object) -> Fraction | None:
    if type(value) is not dict or set(value) != {"fraction", "numerator", "denominator", "float"}:
        return None
    numerator = value["numerator"]
    denominator = value["denominator"]
    if type(numerator) is not int or type(denominator) is not int or denominator == 0:
        return None
    fraction = Fraction(numerator, denominator)
    if type(value["fraction"]) is not str or value["fraction"] != (
        f"{fraction.numerator}/{fraction.denominator}"
    ):
        return None
    if type(value["float"]) is not float or value["float"] != float(fraction):
        return None
    return fraction


def _certificate_schema_issues(certificates: Mapping[str, object]) -> list[str]:
    issues: list[str] = []
    if set(certificates) != EXPECTED_CERTIFICATE_KEYS:
        issues.append("CERTIFICATE_TOP_LEVEL_SCHEMA_MISMATCH")
    mapping_keys = EXPECTED_CERTIFICATE_KEYS - {"contract_issues"}
    for key in sorted(mapping_keys):
        if not isinstance(certificates.get(key), Mapping):
            issues.append(f"CERTIFICATE_RECORD_INVALID:{key}")
    if not isinstance(certificates.get("contract_issues"), list):
        issues.append("CERTIFICATE_RECORD_INVALID:contract_issues")
    return issues


def natural_gate_results(
    certificates: Mapping[str, object],
) -> dict[str, tuple[bool, str, object]]:
    schema_issues = _certificate_schema_issues(certificates)
    if schema_issues:
        return {
            gate_id: (False, requirement, {"schema_issues": schema_issues})
            for gate_id, requirement in REVIEWED_GATE_ITEMS
        }
    canonical = json.loads(_canonical_certificate_bytes())

    t0g = certificates["T0_geometry"]
    t1g = certificates["T1_geometry"]
    t0c = certificates["T0_counting"]
    t1c = certificates["T1_counting"]
    fcs = certificates["T2_FCS"]
    pipeline = certificates["pipeline"]
    lanes = certificates["lane_authentication"]
    t0d = certificates["T0_Drazin"]
    t1d = certificates["T1_Drazin"]
    t0x = certificates["T0_derivatives"]
    t1x = certificates["T1_derivatives"]
    orientation = certificates["orientation_scope"]
    mapping_scope = certificates["mapping_scope"]
    units = certificates["units_and_local_form"]
    nulls = certificates["nulls"]
    claims = certificates["claim_semantics"]
    canonical_t0g = jsonable(t0_geometry_certificate())
    canonical_t1g = jsonable(t1_geometry_certificate())
    canonical_t0c = jsonable(t0_counting_certificate())
    canonical_t1c = jsonable(t1_counting_certificate())
    canonical_fcs = jsonable(t2_fcs_certificate())
    frozen_oracle_outputs = {
        "T0": {
            "B": jsonable(FORMAL_T0_RESPONSE_ONE_FORM),
            "F": jsonable(FORMAL_T0_RESPONSE_CURVATURE),
        },
        "T1": {
            "B": jsonable(FORMAL_T1_RESPONSE_ONE_FORM),
            "F": jsonable(FORMAL_T1_RESPONSE_CURVATURE),
        },
    }

    floor_terms = [
        jsonable(Fraction(147, 1000)),
        jsonable(Fraction(784, 1000)),
        jsonable(Fraction(3)),
    ]
    values = (
        _strict_equal(certificates["contract_issues"], canonical["contract_issues"])
        and not certificates["contract_issues"],
        _reviewed_record_matches(certificates, "core_source_bindings")
        and _reviewed_record_matches(certificates, "core_regression")
        and t0c["authority"] == t1c["authority"] == fcs["authority"]
        and _strict_equal(certificates["core_source_bindings"], canonical["core_source_bindings"])
        and _strict_equal(certificates["core_regression"], canonical["core_regression"])
        and certificates["core_regression"]["used_by_theorem_pass"] is False,
        _reviewed_record_matches(certificates, "T0_geometry")
        and _reviewed_record_matches(certificates, "T1_geometry")
        and _strict_equal(t0g, canonical_t0g)
        and _strict_equal(t1g, canonical_t1g)
        and t0g["uniform_full_rank_floor"] == jsonable(FORMAL_T0_UNIFORM_FLOOR)
        and t1g["uniform_full_rank_floor"] == jsonable(FORMAL_T1_UNIFORM_FLOOR)
        and t0g["delta_box_unique_full_rank_branch"]
        and t1g["h_box_certified_without_shrink"]
        and t0g["center_trace_norm_contraction_rate"] == jsonable(Fraction(1, 25))
        and t1g["center_trace_norm_contraction_rate"] == jsonable(Fraction(1, 25))
        and t0g["center_Drazin_trace_norm_bound"] == jsonable(Fraction(25))
        and t1g["center_Drazin_trace_norm_bound"] == jsonable(Fraction(25))
        and t0g["delta_box_uniform_trace_norm_contraction_rate"] == jsonable(Fraction(1, 50))
        and t0g["delta_box_uniform_Drazin_trace_norm_bound"] == jsonable(Fraction(50))
        and t1g["h_box_uniform_trace_norm_contraction_rate"] == jsonable(Fraction(1, 25))
        and t1g["h_box_uniform_Drazin_trace_norm_bound"] == jsonable(Fraction(25))
        and t0g["uniform_floor_certificate"]["no_depolarizing_reset_probability_lower"]
        == jsonable(Fraction(1997, 2000))
        and t1g["uniform_floor_certificate"]["no_depolarizing_reset_probability_lower"]
        == jsonable(Fraction(999, 1000))
        and t0g["uniform_floor_certificate"]["nonnegative_L0_rates_imply_CPTP_semigroup"]
        and t1g["uniform_floor_certificate"]["nonnegative_L0_rates_imply_CPTP_semigroup"]
        and t0g["uniform_floor_certificate"]["identity_generator_norm_terms"] == floor_terms
        and t1g["uniform_floor_certificate"]["identity_generator_norm_terms"] == floor_terms
        and t0g["uniform_floor_certificate"]["identity_generator_norm_total"]
        == jsonable(Fraction(3931, 1000))
        and t1g["uniform_floor_certificate"]["identity_generator_norm_total"]
        == jsonable(Fraction(3931, 1000))
        and t0g["uniform_floor_certificate"]["identity_generator_norm_domain"]
        == "superoperator_norm_induced_by_matrix_spectral_operator_norm"
        and t1g["uniform_floor_certificate"]["identity_generator_norm_domain"]
        == "superoperator_norm_induced_by_matrix_spectral_operator_norm"
        and t0g["uniform_floor_certificate"]["semigroup_series_parameter"] == jsonable(Fraction(3931, 40000))
        and t1g["uniform_floor_certificate"]["semigroup_series_parameter"] == jsonable(Fraction(3931, 40000))
        and t0g["uniform_floor_certificate"]["semigroup_series_parameter_in_unit_interval"] is True
        and t1g["uniform_floor_certificate"]["semigroup_series_parameter_in_unit_interval"] is True
        and t0g["uniform_floor_certificate"]["exponential_series_majorant"] == jsonable(Fraction(3931, 36069))
        and t1g["uniform_floor_certificate"]["exponential_series_majorant"] == jsonable(Fraction(3931, 36069))
        and t0g["uniform_floor_certificate"]["semigroup_difference_spectral_norm_bound"]
        == jsonable(Fraction(3931, 180345))
        and t1g["uniform_floor_certificate"]["semigroup_difference_spectral_norm_bound"]
        == jsonable(Fraction(3931, 180345))
        and t0g["uniform_floor_certificate"]["continuity_pointwise_floor"]
        == jsonable(Fraction(32138, 180345))
        and t1g["uniform_floor_certificate"]["continuity_pointwise_floor"]
        == jsonable(Fraction(32138, 180345))
        and t0g["uniform_floor_certificate"]["time_cutoff"] == jsonable(Fraction(1, 40))
        and t1g["uniform_floor_certificate"]["time_cutoff"] == jsonable(Fraction(1, 40))
        and t0g["uniform_floor_certificate"]["all_inequalities_strictly_positive"] is True
        and t1g["uniform_floor_certificate"]["all_inequalities_strictly_positive"] is True,
        _reviewed_record_matches(certificates, "T0_Drazin")
        and _reviewed_record_matches(certificates, "T1_Drazin")
        and _reviewed_record_matches(certificates, "T0_derivatives")
        and _reviewed_record_matches(certificates, "T1_derivatives")
        and _strict_equal(t0d, canonical["T0_Drazin"])
        and _strict_equal(t1d, canonical["T1_Drazin"])
        and _strict_equal(t0x, canonical["T0_derivatives"])
        and _strict_equal(t1x, canonical["T1_derivatives"])
        and all(t0d.values())
        and all(t1d.values())
        and all(t0x.values())
        and all(t1x.values()),
        _reviewed_record_matches(certificates, "T0_geometry")
        and _reviewed_record_matches(certificates, "T1_geometry")
        and _strict_equal(t0g, canonical_t0g)
        and _strict_equal(t1g, canonical_t1g)
        and t0g["authority"] == t1g["authority"] == "actual_exact_stationary_branch_only"
        and t0g["metric_rank"] == 2
        and t0g["projective_curvature_exact"] == "0"
        and t1g["SLD_metric_rank"] == 3
        and (_exact_fraction_record(t1g["tangent_Gram_determinant"]) or Fraction(-1)) > 0
        and (_exact_fraction_record(t1g["SLD_metric_determinant"]) or Fraction(-1)) > 0
        and t1g["mean_Uhlmann_curvature_zero_exact"]
        and t0g["input_capability_type"] == "StationaryTangentRecord"
        and t1g["input_capability_type"] == "StationaryTangentRecord"
        and t0g["input_capability_excludes_current_B_and_F"]
        and t1g["input_capability_excludes_current_B_and_F"]
        and t0g["no_auxiliary_branch"]
        and t1g["no_auxiliary_branch"],
        _reviewed_record_matches(certificates, "T2_FCS")
        and _strict_equal(fcs, canonical_fcs)
        and all(
            fcs[case][key]
            for case in ("T0", "T1")
            for key in (
                "Wq_at_q0_equals_W",
                "first_q_jet_has_only_forward_and_reverse_counted_gains",
                "first_q_jet_losses_unchanged",
                "trace_W_at_q0_zero",
                "J_equals_partial_q_Wq_at_q0",
                "left_q_eigenvector_equation_exact",
                "right_q_eigenvector_equation_exact",
            )
        ),
        _reviewed_record_matches(certificates, "T0_counting")
        and _reviewed_record_matches(certificates, "T1_counting")
        and _reviewed_record_matches(certificates, "T2_FCS")
        and _strict_equal(t0c, canonical_t0c)
        and _strict_equal(t1c, canonical_t1c)
        and _strict_equal(fcs, canonical_fcs)
        and t0c["center"] == jsonable(MODEL_CONTRACT.t0_center)
        and t1c["center"] == jsonable(MODEL_CONTRACT.t1_center)
        and t0c["response_one_form"] == jsonable(FORMAL_T0_RESPONSE_ONE_FORM)
        and t0c["response_curvature"] == jsonable(FORMAL_T0_RESPONSE_CURVATURE)
        and t1c["response_one_form"] == jsonable(FORMAL_T1_RESPONSE_ONE_FORM)
        and t1c["response_curvature"] == jsonable(FORMAL_T1_RESPONSE_CURVATURE)
        and all(
            fcs[case]["B_equals_minus_partial_q_A"]
            and fcs[case]["F_equals_minus_partial_q_dA"]
            and fcs[case]["F_from_independent_normal_connection_curl"] == fcs[case]["F_value"]
            for case in ("T0", "T1")
        ),
        _reviewed_record_matches(certificates, "mapping_scope")
        and _strict_equal(mapping_scope, canonical["mapping_scope"])
        and mapping_scope["same_curvature_refuted"] is True
        and mapping_scope["frozen_zero_preserving_homogeneous_Omega_only_map_refuted"] is True
        and mapping_scope["affine_map_status"] == "OPEN"
        and mapping_scope["nonlinear_map_status"] == "OPEN"
        and mapping_scope["generator_dependent_map_status"] == "OPEN"
        and mapping_scope["universal_map_claimed"] is False
        and t1g["mean_Uhlmann_curvature_zero_exact"]
        and t1c["all_curvature_components_nonzero"]
        and not MODEL_CONTRACT.positive_map_claim_allowed,
        _reviewed_record_matches(certificates, "lane_authentication")
        and _reviewed_record_matches(certificates, "pipeline")
        and _strict_equal(lanes, canonical["lane_authentication"])
        and all(item["authenticated"] and item["firewall_issues"] == [] for item in lanes.values())
        and t0g["input_capability_excludes_current_B_and_F"]
        and t1g["input_capability_excludes_current_B_and_F"]
        and pipeline["oracle_capability"]["criterion_digest_received"] is True
        and pipeline["oracle_capability"]["raw_prediction_values_received"] is False
        and pipeline["oracle_capability"]["geometry_payload_received"] is False
        and _strict_equal(
            pipeline["oracle_callable"],
            {
                "module": _REVIEWED_ORACLE_MODULE,
                "qualname": _REVIEWED_ORACLE_QUALNAME,
                "is_reviewed_import": True,
            },
        )
        and _strict_equal(pipeline["oracle"]["T0"], frozen_oracle_outputs["T0"])
        and _strict_equal(pipeline["oracle"]["T1"], frozen_oracle_outputs["T1"])
        and pipeline["oracle_capability"]["payload_authenticated"]
        and pipeline["oracle_capability"]["oracle_received_matching_payload"]
        and pipeline["oracle"]["capability_payload_authenticated"]
        and pipeline["oracle"]["criterion_digest_received"] is True
        and pipeline["oracle"]["raw_prediction_values_or_geometry_payload_received"] is False,
        _reviewed_record_matches(certificates, "pipeline")
        and _strict_equal(pipeline, canonical["pipeline"])
        and _strict_equal(pipeline["oracle"]["T0"], frozen_oracle_outputs["T0"])
        and _strict_equal(pipeline["oracle"]["T1"], frozen_oracle_outputs["T1"])
        and pipeline["final_state"] == "VERIFIED"
        and pipeline["event_log"] == ["INIT", "PREDICTION_LOCKED", "ORACLE_RUN", "VERIFIED"]
        and pipeline["prediction_lock"]["authentic"]
        and not pipeline["prediction_lock"]["positive_map_inference_requested"]
        and pipeline["oracle_matches_locked_criterion"]
        and not pipeline["criterion"][
            "same_curvature_or_zero_preserving_homogeneous_map_inference_requested"
        ],
        _reviewed_record_matches(certificates, "units_and_local_form")
        and _strict_equal(units, canonical["units_and_local_form"])
        and units["time_domain"] == MODEL_CONTRACT.time_domain
        and units["generator_rate_units"] == MODEL_CONTRACT.generator_rate_units
        and units["response_one_form_units"] == MODEL_CONTRACT.response_one_form_units
        and units["response_curvature_units"] == MODEL_CONTRACT.response_curvature_units
        and units["T0_control_units"] == jsonable(MODEL_CONTRACT.t0_control_units)
        and units["T1_control_units"] == jsonable(MODEL_CONTRACT.t1_control_units)
        and units["T0_component_units"] == jsonable(MODEL_CONTRACT.t0_component_units)
        and units["T1_component_units"] == jsonable(MODEL_CONTRACT.t1_component_units)
        and units["curvature_definition"] == MODEL_CONTRACT.response_curvature_definition
        and units["local_curvature_scope"] == MODEL_CONTRACT.local_curvature_scope
        and units["closure_scope"] == MODEL_CONTRACT.closure_scope
        and units["coordinate_covariance_scope"] == MODEL_CONTRACT.coordinate_covariance_scope
        and units["zero_set_scope"] == MODEL_CONTRACT.zero_set_scope
        and units["antisymmetry_exact"],
        _reviewed_record_matches(certificates, "nulls")
        and _reviewed_record_matches(certificates, "T2_FCS")
        and _strict_equal(nulls, canonical["nulls"])
        and all(nulls.values())
        and _strict_equal(fcs, canonical_fcs)
        and all(
            fcs[case]["reverse_count_B_recomputed_independently"]
            and fcs[case]["reverse_count_F_recomputed_independently"]
            and fcs[case]["reverse_count_B"]
            == [
                jsonable(-value)
                for value in (FORMAL_T0_RESPONSE_ONE_FORM if case == "T0" else FORMAL_T1_RESPONSE_ONE_FORM)
            ]
            and fcs[case]["reverse_count_F"]
            == [
                jsonable(-value)
                for value in (FORMAL_T0_RESPONSE_CURVATURE if case == "T0" else FORMAL_T1_RESPONSE_CURVATURE)
            ]
            for case in ("T0", "T1")
        ),
        _reviewed_record_matches(certificates, "orientation_scope")
        and _strict_equal(orientation, canonical["orientation_scope"])
        and orientation["negative_orientation"] == "exact_reverse_of_stored_path"
        and orientation["qanti"] == "(Qplus-Qminus)/2"
        and orientation["full_orientation_difference"] == "2*Qanti"
        and orientation["qanti_factor"] == jsonable(Fraction(1, 2))
        and orientation["full_orientation_difference_factor"] == jsonable(Fraction(2))
        and orientation["accepted_scope"] == "exact_local_parameter_curvature_and_orientation_algebra_only"
        and orientation["finite_time_loop_claimed"] is False
        and orientation["finite_time_remainder_claimed"] is False
        and orientation["asymptotic_rate_claimed"] is False,
        _reviewed_record_matches(certificates, "registry")
        and _reviewed_record_matches(certificates, "claim_semantics")
        and _strict_equal(certificates["registry"], canonical["registry"])
        and _strict_equal(canonical["registry"], canonical_registry_record())
        and _strict_equal(claims, canonical["claim_semantics"])
        and _strict_equal(
            claims,
            {
                "disposition": MODEL_CONTRACT.disposition,
                "evidence_status": MODEL_CONTRACT.evidence_status,
                "relation_scope": MODEL_CONTRACT.relation_scope,
                "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
            },
        )
        and not MODEL_CONTRACT.empirical_claim_allowed,
    )
    evidence = (
        {"contract_issues": certificates["contract_issues"]},
        {"core_source_bindings": certificates["core_source_bindings"]},
        {
            "T0_uniform_floor": t0g["uniform_floor_certificate"],
            "T1_uniform_floor": t1g["uniform_floor_certificate"],
        },
        {"T0": t0d, "T1": t1d},
        {"T0": t0g, "T1": t1g},
        {"T0": fcs["T0"], "T1": fcs["T1"]},
        {"T0": t0c, "T1": t1c},
        mapping_scope,
        {"lanes": lanes, "typed_capabilities": pipeline["oracle_capability"]},
        pipeline,
        units,
        nulls,
        orientation,
        {"registry": certificates["registry"], "claims": claims},
    )
    requirements = dict(REVIEWED_GATE_ITEMS)
    return {
        gate_id: (bool(value), requirements[gate_id], item)
        for (gate_id, _name), value, item in zip(REVIEWED_GATE_ITEMS, values, evidence, strict=True)
    }


def _execute_from_certificates(
    certificates: Mapping[str, object],
    *,
    gate_overrides: Mapping[str, bool] | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    certs = dict(certificates)
    natural = natural_gate_results(certs)
    overrides = dict(gate_overrides or {})
    unknown = sorted(set(overrides) - set(natural))
    if unknown or any(not isinstance(value, bool) for value in overrides.values()):
        raise ValueError(f"invalid gate override record: unknown={unknown}")
    records: list[dict[str, object]] = []
    failed: list[str] = []
    for gate_id, _name in REVIEWED_GATE_ITEMS:
        natural_value, requirement, evidence = natural[gate_id]
        final_value = natural_value and overrides.get(gate_id, True)
        if not final_value:
            failed.append(gate_id)
        records.append(
            {
                "record_type": "gate",
                "gate_id": gate_id,
                "name": dict(REVIEWED_GATE_ITEMS)[gate_id],
                "requirement": requirement,
                "natural_status": "pass" if natural_value else "fail",
                "status": "pass" if final_value else "fail",
                "evidence": evidence,
            }
        )
    expected_dispositions = dict(REVIEWED_CASE_DISPOSITION_ITEMS)
    case_dispositions: dict[str, str] = {}
    for case_id, gates in REVIEWED_CASE_GATE_ITEMS:
        case_failed = [gate for gate in gates if gate in failed]
        case_dispositions[case_id] = (
            expected_dispositions[case_id]
            if not case_failed
            else f"FAIL_INTERNAL_ANALYTIC:{','.join(case_failed)}"
        )
    passed = not failed
    summary = {
        "experiment_id": MODEL_CONTRACT.experiment_id,
        "disposition": MODEL_CONTRACT.disposition if passed else "FAIL_INTERNAL_ANALYTIC",
        "formal_disposition": MODEL_CONTRACT.disposition if passed else "FAIL_INTERNAL_ANALYTIC",
        "evidence_status": MODEL_CONTRACT.evidence_status,
        "relation_scope": MODEL_CONTRACT.relation_scope,
        "claim_ceiling": MODEL_CONTRACT.claim_ceiling,
        "case_dispositions": case_dispositions,
        "failed_gates": failed,
        "gate_count": len(records),
        "registry": canonical_registry_record(),
        "metrics": {
            "T0": certs.get("T0_counting"),
            "T1": certs.get("T1_counting"),
            "T2": certs.get("T2_FCS"),
            "geometry": {
                "T0": certs.get("T0_geometry"),
                "T1": certs.get("T1_geometry"),
            },
            "prediction_lock": (
                certs.get("pipeline", {}).get("prediction_lock")
                if isinstance(certs.get("pipeline"), Mapping)
                else None
            ),
        },
    }
    return summary, records


def execute_program(
    *,
    contract: SharedGeneratorContract = MODEL_CONTRACT,
    gate_overrides: Mapping[str, bool] | None = None,
) -> tuple[dict[str, object], list[dict[str, object]]]:
    """Execute only from the sealed canonical certificate construction."""

    return _execute_from_certificates(build_certificates(contract), gate_overrides=gate_overrides)

from __future__ import annotations

import copy
import inspect
import json
import tempfile
import threading
import time
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest
from typer.testing import CliRunner

from experiments.shared_generator_counting_curvature_proof import (
    artifacts as artifact_module,
    contract as contract_module,
    counting_lane,
    generator as generator_module,
    run as run_module,
    theorem as theorem_module,
)
from experiments.shared_generator_counting_curvature_proof.artifacts import (
    _RESERVED_TRANSACTION_LEAVES,
    ArtifactGenerationRefused,
    ArtifactTransactionCrash,
    ArtifactVerificationError,
    artifact_transaction_paths,
    clean_cli_local_module_paths,
    expected_artifact_bytes,
    material_source_paths,
    predecessor_inventories,
    preflight_destination,
    require_semantic_pass,
    verify_artifacts,
    write_artifacts,
)
from experiments.shared_generator_counting_curvature_proof.contract import (
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
    canonical_registry_record,
    sha256_payload,
    validate_reviewed_registry,
)
from experiments.shared_generator_counting_curvature_proof.counting_lane import (
    t0_counting_certificate,
    t1_counting_certificate,
    t2_fcs_certificate,
    zero_current_null_certificate,
)
from experiments.shared_generator_counting_curvature_proof.firewall import (
    analyze_role_source,
    authenticated_role_sources,
)
from experiments.shared_generator_counting_curvature_proof.generator import (
    branch_derivative_identities,
    current_row,
    drazin_identity_errors,
    exact_branch_response,
    liouvillian,
    t0_response,
    t1_response,
)
from experiments.shared_generator_counting_curvature_proof.geometry_lane import (
    t0_geometry_certificate,
    t1_geometry_certificate,
)
from experiments.shared_generator_counting_curvature_proof.oracle_lane import exact_oracle_record
from experiments.shared_generator_counting_curvature_proof.pipeline import (
    FalsificationCriterion,
    OracleCapability,
    PipelineSession,
    PredictionLock,
)
from experiments.shared_generator_counting_curvature_proof.theorem import (
    REVIEWED_CERTIFICATE_RECORD_SHA256_ITEMS,
    _execute_from_certificates,
    build_certificates,
    execute_program,
    natural_gate_results,
)


def _criterion() -> FalsificationCriterion:
    return FalsificationCriterion(
        criterion_id="T0_T1_exact_B_F_before_oracle_v1",
        t0_B=FORMAL_T0_RESPONSE_ONE_FORM,
        t0_F=FORMAL_T0_RESPONSE_CURVATURE,
        t1_B=FORMAL_T1_RESPONSE_ONE_FORM,
        t1_F=FORMAL_T1_RESPONSE_CURVATURE,
    )


def _primitive_hash() -> str:
    return sha256_payload(MODEL_CONTRACT.jsonable())


def _oracle_capability() -> OracleCapability:
    return OracleCapability.issue(
        PredictionLock.create(MODEL_CONTRACT.experiment_id, _criterion(), _primitive_hash())
    )


def test_reviewed_registry_is_exact_and_ordered() -> None:
    validate_reviewed_registry()
    registry = canonical_registry_record()
    assert [item["gate_id"] for item in registry["ordered_gates"]] == [f"G{index}" for index in range(14)]
    assert len({item["gate_id"] for item in registry["ordered_gates"]}) == 14


def test_t0_exact_response_and_classical_geometry() -> None:
    counting = t0_counting_certificate()
    geometry = t0_geometry_certificate()
    assert counting["response_one_form"] == FORMAL_T0_RESPONSE_ONE_FORM
    assert counting["response_curvature"] == FORMAL_T0_RESPONSE_CURVATURE
    assert counting["all_curvature_components_nonzero"]
    assert geometry["projective_curvature_exact"] == "0"
    assert geometry["commuting_density_Uhlmann_curvature_exact"] == "0"
    assert geometry["radial_scaling_null_exact"]
    assert geometry["metric_rank"] == 2
    assert geometry["uniform_full_rank_floor"] == FORMAL_T0_UNIFORM_FLOOR
    assert geometry["delta_box_unique_full_rank_branch"]


def test_t1_exact_rank_floor_symmetry_and_response() -> None:
    counting = t1_counting_certificate()
    geometry = t1_geometry_certificate()
    assert counting["response_one_form"] == FORMAL_T1_RESPONSE_ONE_FORM
    assert counting["response_curvature"] == FORMAL_T1_RESPONSE_CURVATURE
    assert counting["all_curvature_components_nonzero"]
    assert geometry["uniform_full_rank_floor"] == FORMAL_T1_UNIFORM_FLOOR
    assert geometry["h_box_certified_without_shrink"]
    assert geometry["tangent_Gram_determinant"] > 0
    assert geometry["SLD_metric_determinant"] > 0
    assert geometry["SLD_metric_rank"] == 3
    assert geometry["fixed_gauge_stationary_real_symmetric"]
    assert geometry["fixed_gauge_tangents_real_symmetric"]
    assert geometry["fixed_gauge_SLDs_real_symmetric"]
    assert geometry["mean_Uhlmann_curvature_zero_exact"]


@pytest.mark.parametrize("certificate", [t0_geometry_certificate(), t1_geometry_certificate()])
def test_uniform_floor_norm_budget_is_computed_exactly(certificate) -> None:
    floor = certificate["uniform_floor_certificate"]
    assert floor["identity_generator_norm_terms"] == (
        Fraction(147, 1000),
        Fraction(784, 1000),
        Fraction(3000, 1000),
    )
    assert floor["identity_generator_norm_total"] == Fraction(3931, 1000)
    assert floor["time_cutoff"] == Fraction(1, 40)
    assert floor["identity_generator_norm_domain"] == (
        "superoperator_norm_induced_by_matrix_spectral_operator_norm"
    )
    assert floor["identity_generator_induced_operator_norm_bound"] == Fraction(3931, 1000)
    assert floor["semigroup_series_parameter"] == Fraction(3931, 40000)
    assert floor["semigroup_series_parameter_in_unit_interval"] is True
    assert floor["exponential_series_majorant"] == Fraction(3931, 36069)
    assert floor["semigroup_difference_spectral_norm_bound"] == Fraction(3931, 180345)
    assert floor["continuity_pointwise_floor"] == Fraction(32138, 180345)
    assert floor["continuity_pointwise_floor"] > Fraction(3, 20)
    assert floor["integral_floor"] == certificate["uniform_full_rank_floor"]
    assert floor["all_inequalities_strictly_positive"]


def test_G2_center_and_box_contraction_Drazin_and_no_reset_premises_are_exact() -> None:
    t0 = t0_geometry_certificate()
    t1 = t1_geometry_certificate()
    assert t0["center_trace_norm_contraction_rate"] == Fraction(1, 25)
    assert t1["center_trace_norm_contraction_rate"] == Fraction(1, 25)
    assert t0["center_Drazin_trace_norm_bound"] == 25
    assert t1["center_Drazin_trace_norm_bound"] == 25
    assert t0["delta_box_uniform_trace_norm_contraction_rate"] == Fraction(1, 50)
    assert t0["delta_box_uniform_Drazin_trace_norm_bound"] == 50
    assert t0["uniform_floor_certificate"]["no_depolarizing_reset_probability_lower"] == Fraction(1997, 2000)
    assert t1["uniform_floor_certificate"]["no_depolarizing_reset_probability_lower"] == Fraction(999, 1000)
    assert t0["uniform_floor_certificate"]["nonnegative_L0_rates_imply_CPTP_semigroup"]
    assert t1["uniform_floor_certificate"]["nonnegative_L0_rates_imply_CPTP_semigroup"]


@pytest.mark.parametrize("response", [t0_response(), t1_response()])
def test_exact_drazin_identities(response) -> None:
    assert all(drazin_identity_errors(response).values())


def test_exact_first_and_second_branch_derivatives() -> None:
    t0 = branch_derivative_identities(
        t0_response(),
        lambda b, d, delta: liouvillian(b, d, Fraction(0), delta),
    )
    t1 = branch_derivative_identities(
        t1_response(),
        lambda b, d, h: liouvillian(b, d, h, Fraction(1, 25)),
    )
    assert all(t0.values())
    assert all(t1.values())


def test_fcs_extended_connection_sign_factor_and_scope() -> None:
    certificate = t2_fcs_certificate()
    for case in ("T0", "T1"):
        item = certificate[case]
        assert item["B_equals_minus_partial_q_A"]
        assert item["F_equals_minus_partial_q_dA"]
        assert item["F_from_independent_normal_connection_curl"] == item["F_value"]
        assert item["first_q_jet_has_only_forward_and_reverse_counted_gains"]
        assert item["first_q_jet_losses_unchanged"]
        assert item["reverse_count_negates_B_and_F"]
        assert item["reverse_count_B_recomputed_independently"]
        assert item["reverse_count_F_recomputed_independently"]
        assert item["qanti_factor"] == Fraction(1, 2)
        assert item["full_orientation_difference_factor"] == 2
        assert item["extended_eigenbundle_normal_jet_is_distinct_from_state_CGT"]


def test_zero_current_covector_is_an_exact_null() -> None:
    def zero(_b, _d, _third):
        return [current * 0 for current in current_row(Fraction(0), Fraction(1, 4))]

    response = exact_branch_response(
        control_names=("b", "d", "h"),
        center=MODEL_CONTRACT.t1_center,
        generator_builder=lambda b, d, h: liouvillian(b, d, h, Fraction(1, 25)),
        current_builder=zero,
    )
    assert response.response_one_form == (0, 0, 0)
    assert response.response_curvature == (0, 0, 0)
    assert zero_current_null_certificate()["same_exact_stationary_branch"]
    assert zero_current_null_certificate()["B_and_F_zero_exact"]


def test_h_zero_and_radial_nulls_are_computed_from_the_actual_t0_branch() -> None:
    geometry = t0_geometry_certificate()
    certificates = build_certificates()
    assert geometry["stationary_is_diagonal"]
    assert geometry["all_tangents_are_diagonal"]
    assert geometry["projective_curvature_exact"] == "0"
    assert geometry["commuting_density_Uhlmann_curvature_exact"] == "0"
    assert geometry["radial_scaling_null_exact"]
    assert certificates["nulls"]["h_zero_actual_branch_is_diagonal_and_geometry_zero"]
    assert certificates["nulls"]["radial_scaling_null_exact"]


def test_authenticated_lanes_are_separate() -> None:
    records = authenticated_role_sources()
    assert set(records) == {"geometry", "counting", "oracle"}
    assert all(item["authenticated"] and not item["firewall_issues"] for item in records.values())
    geometry = t1_geometry_certificate()
    assert geometry["input_capability_fields"] == (
        "control_names",
        "center",
        "stationary",
        "tangents",
    )
    assert geometry["input_capability_excludes_current_B_and_F"]


@pytest.mark.parametrize(
    ("role", "source"),
    [
        ("geometry", "from .counting_lane import t0_counting_certificate"),
        ("counting", "from .geometry_lane import t1_geometry_certificate"),
        ("oracle", "from .counting_lane import t0_counting_certificate"),
        ("oracle", "def f():\n    return omega()"),
        ("oracle", "def f(current_builder):\n    return current_builder()"),
    ],
)
def test_lane_firewall_rejects_cross_lane_access(role: str, source: str) -> None:
    assert analyze_role_source(role, source)


@pytest.mark.parametrize(
    "source",
    [
        (
            "import importlib\nmod=importlib.import_module("
            "'experiments.shared_generator_counting_curvature_proof.geometry_lane')"
        ),
        "loader=__builtins__['__im'+'port__'];mod=loader('experiments.shared_generator_counting_curvature_proof.counting_lane')",
        "import operator\nloader=operator.itemgetter('__import__')(__builtins__)",
        "import sys\nmod=sys.modules['experiments.shared_generator_counting_curvature_proof.oracle_lane']",
        "loader=getattr(__builtins__,'__import__')",
        "name=''.join(['geometry_','lane']);loader(name)",
    ],
)
@pytest.mark.parametrize("role", ["geometry", "counting", "oracle"])
def test_lane_firewall_rejects_dynamic_reflection_and_import_recovery(role: str, source: str) -> None:
    assert analyze_role_source(role, source)


def test_lane_firewall_allows_benign_exact_instance_methods() -> None:
    source = """from __future__ import annotations
from .exact import Gaussian
def f(value: Gaussian):
    return value.conjugate().is_zero()
"""
    assert analyze_role_source("geometry", source) == []


def test_oracle_does_not_import_or_depend_on_counting_lane(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(counting_lane, "t0_counting_certificate", lambda: {"forged": True})
    monkeypatch.setattr(generator_module, "exact_branch_response", lambda *args, **kwargs: {"forged": True})
    record = exact_oracle_record(_oracle_capability())
    assert record["T0"]["B"] == FORMAL_T0_RESPONSE_ONE_FORM
    assert record["T0"]["F"] == FORMAL_T0_RESPONSE_CURVATURE
    source = Path(exact_oracle_record.__code__.co_filename).read_text(encoding="utf-8")
    assert "counting_lane" not in source
    assert "exact_branch_response" not in source


def test_pipeline_requires_lock_and_exact_event_order() -> None:
    session = PipelineSession(MODEL_CONTRACT.experiment_id)
    lock = session.lock_prediction(_criterion(), primitive_contract_sha256=_primitive_hash())
    result = session.run_oracle(lock, exact_oracle_record)
    assert result["T0"] == {
        "B": FORMAL_T0_RESPONSE_ONE_FORM,
        "F": FORMAL_T0_RESPONSE_CURVATURE,
    }
    assert session.verify(lock) == ("INIT", "PREDICTION_LOCKED", "ORACLE_RUN", "VERIFIED")


def test_pipeline_rejects_oracle_before_lock() -> None:
    session = PipelineSession(MODEL_CONTRACT.experiment_id)
    lock = PredictionLock.create(MODEL_CONTRACT.experiment_id, _criterion(), _primitive_hash())
    with pytest.raises(RuntimeError, match="oracle_without_current_authentic_lock"):
        session.run_oracle(lock, exact_oracle_record)


def test_pipeline_rejects_wrong_lock_replay_and_post_oracle_predictor() -> None:
    session = PipelineSession(MODEL_CONTRACT.experiment_id)
    current_lock = session.lock_prediction(_criterion(), primitive_contract_sha256=_primitive_hash())
    wrong = replace(current_lock, criterion_sha256="0" * 64)
    with pytest.raises(RuntimeError, match="oracle_without_current_authentic_lock"):
        session.run_oracle(wrong, exact_oracle_record)

    replay = PipelineSession(MODEL_CONTRACT.experiment_id)
    current = replay.lock_prediction(_criterion(), primitive_contract_sha256=_primitive_hash())
    replay.run_oracle(current, exact_oracle_record)
    with pytest.raises(RuntimeError, match="predictor_access_after_oracle"):
        replay.predictor_access_after_oracle()


def test_prediction_lock_wrong_contract_and_response_reordering_poison() -> None:
    wrong_contract = PipelineSession(MODEL_CONTRACT.experiment_id)
    lock = wrong_contract.lock_prediction(_criterion(), primitive_contract_sha256=_primitive_hash())
    forged = replace(lock, primitive_contract_sha256="0" * 64)
    with pytest.raises(RuntimeError, match="oracle_without_current_authentic_lock"):
        wrong_contract.run_oracle(forged, exact_oracle_record)

    falsified = PipelineSession(MODEL_CONTRACT.experiment_id)
    current = falsified.lock_prediction(_criterion(), primitive_contract_sha256=_primitive_hash())
    with pytest.raises(RuntimeError, match="oracle_result_schema_or_values_invalid"):
        falsified.run_oracle(
            current,
            lambda _capability: {
                "T0": {"B": FORMAL_T0_RESPONSE_ONE_FORM, "F": (0, 0, 0)},
                "T1": {"B": FORMAL_T1_RESPONSE_ONE_FORM, "F": FORMAL_T1_RESPONSE_CURVATURE},
            },
        )


def test_prohibited_positive_criterion_is_refused_before_lock_or_oracle() -> None:
    session = PipelineSession(MODEL_CONTRACT.experiment_id)
    prohibited = replace(
        _criterion(),
        same_curvature_or_zero_preserving_homogeneous_map_inference_requested=True,
    )
    with pytest.raises(RuntimeError, match="unreviewed_falsification_criterion"):
        session.lock_prediction(prohibited, primitive_contract_sha256=_primitive_hash())
    assert session.state.value == "POISONED"
    assert "PREDICTION_LOCKED" not in session.events
    assert "ORACLE_RUN" not in session.events
    assert "VERIFIED" not in session.events


def test_oracle_capability_payload_and_contract_hash_are_authenticated() -> None:
    capability = _oracle_capability()
    assert capability.authentic()
    assert exact_oracle_record(capability)["capability_payload_authenticated"]

    bad_digest = replace(capability, payload_sha256="0" * 64)
    with pytest.raises(RuntimeError, match="oracle capability is invalid"):
        exact_oracle_record(bad_digest)

    self_consistent_but_wrong = replace(capability, primitive_contract_sha256="0" * 64)
    assert not self_consistent_but_wrong.authentic()
    with pytest.raises(RuntimeError, match="oracle capability is invalid"):
        exact_oracle_record(self_consistent_but_wrong)

    forged_criterion = replace(capability, criterion_sha256="0" * 64)
    assert not forged_criterion.authentic()
    with pytest.raises(RuntimeError, match="oracle capability is invalid"):
        exact_oracle_record(forged_criterion)


@pytest.mark.parametrize(
    "criterion",
    [
        replace(_criterion(), criterion_id="PROVE_POSITIVE_ALIGNMENT"),
        replace(_criterion(), comparison_rule="same_curvature_map_is_confirmed"),
        replace(
            _criterion(),
            same_curvature_or_zero_preserving_homogeneous_map_inference_requested=0,
        ),
        replace(_criterion(), t0_B=(1, *_criterion().t0_B[1:])),
    ],
)
def test_unreviewed_or_weakly_typed_criterion_is_refused_before_lock(criterion) -> None:
    session = PipelineSession(MODEL_CONTRACT.experiment_id)
    with pytest.raises(RuntimeError, match="unreviewed_falsification_criterion"):
        session.lock_prediction(criterion, primitive_contract_sha256=_primitive_hash())
    assert session.state.value == "POISONED"
    assert "PREDICTION_LOCKED" not in session.events
    assert "ORACLE_RUN" not in session.events
    assert "VERIFIED" not in session.events


def test_equal_int_oracle_payload_is_rejected_and_cannot_self_canonicalize(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class EqualInt(int):
        def __eq__(self, other) -> bool:
            return True

        def __ne__(self, other) -> bool:
            return False

    def forged(capability: OracleCapability) -> dict[str, object]:
        zeros = tuple(EqualInt(0) for _ in range(3))
        return {
            "authority": "independent_exact_stationary_Drazin_response_from_generator_primitives",
            "accepted_inputs": "typed_generator_primitives_plus_authenticated_criterion_digest",
            "capability_payload_sha256": capability.payload_sha256,
            "capability_payload_authenticated": capability.authentic(),
            "criterion_digest_received": True,
            "raw_prediction_values_or_geometry_payload_received": False,
            "T0": {"B": zeros, "F": zeros},
            "T1": {"B": zeros, "F": zeros},
        }

    session = PipelineSession(MODEL_CONTRACT.experiment_id)
    lock = session.lock_prediction(_criterion(), primitive_contract_sha256=_primitive_hash())
    with pytest.raises(RuntimeError, match="oracle_result_schema_or_values_invalid"):
        session.run_oracle(lock, forged)
    assert "ORACLE_RUN" not in session.events
    assert "VERIFIED" not in session.events

    monkeypatch.setattr(theorem_module, "exact_oracle_record", forged)
    theorem_module._canonical_certificate_bytes.cache_clear()
    try:
        with pytest.raises(RuntimeError, match="reviewed oracle callable identity mismatch"):
            theorem_module.execute_program()
    finally:
        theorem_module._canonical_certificate_bytes.cache_clear()


def test_runtime_geometry_producer_cannot_redefine_its_reviewed_record_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = copy.deepcopy(t1_geometry_certificate())

    def forged_geometry() -> dict[str, object]:
        record = copy.deepcopy(original)
        record["SLD_metric_determinant"] = Fraction(-1)
        return record

    monkeypatch.setattr(theorem_module, "t1_geometry_certificate", forged_geometry)
    theorem_module._canonical_certificate_bytes.cache_clear()
    try:
        summary, _records = theorem_module.execute_program()
        assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
        assert {"G2", "G4"} <= set(summary["failed_gates"])
    finally:
        theorem_module._canonical_certificate_bytes.cache_clear()


def test_all_authoritative_certificate_records_have_frozen_literal_digests() -> None:
    items = REVIEWED_CERTIFICATE_RECORD_SHA256_ITEMS
    assert len(items) == len({key for key, _digest in items}) == 19
    assert all(len(digest) == 64 and digest != "TO_FREEZE" for _key, digest in items)


def test_all_G0_through_G13_pass_and_cases_are_exact() -> None:
    summary, records = execute_program()
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["failed_gates"] == []
    assert [item["gate_id"] for item in records] == [f"G{index}" for index in range(14)]
    assert all(item["natural_status"] == item["status"] == "pass" for item in records)
    assert summary["case_dispositions"] == dict(REVIEWED_CASE_DISPOSITION_ITEMS)


def test_public_execute_api_has_no_certificate_injection_and_cases_own_G8() -> None:
    assert "certificates" not in inspect.signature(execute_program).parameters
    case_gates = dict(REVIEWED_CASE_GATE_ITEMS)
    assert "G8" in case_gates["T0"]
    assert "G8" in case_gates["T1"]
    assert "G8" in case_gates["T2"]


@pytest.mark.parametrize("mutation", ["extra", "missing", "wrong_type"])
def test_private_certificate_path_is_full_schema_fail_closed(mutation: str) -> None:
    certificates = copy.deepcopy(build_certificates())
    if mutation == "extra":
        certificates["forged"] = {}
    elif mutation == "missing":
        del certificates["T2_FCS"]
    else:
        certificates["T0_geometry"] = []
    summary, records = _execute_from_certificates(certificates)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert summary["failed_gates"] == [f"G{index}" for index in range(14)]
    assert all(record["natural_status"] == record["status"] == "fail" for record in records)


def test_exact_formal_G2_nested_zero_and_999_mutation_fails() -> None:
    certificates = copy.deepcopy(build_certificates())
    for case in ("T0_geometry", "T1_geometry"):
        certificates[case]["uniform_trace_norm_contraction_rate"] = {
            "fraction": "0/1",
            "numerator": 0,
            "denominator": 1,
            "float": 0.0,
        }
        certificates[case]["uniform_Drazin_trace_norm_bound"] = {
            "fraction": "999/1",
            "numerator": 999,
            "denominator": 1,
            "float": 999.0,
        }
    summary, _records = _execute_from_certificates(certificates)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "G2" in summary["failed_gates"]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("identity_generator_norm_domain", "FORGED_NORM_DOMAIN"),
        ("identity_generator_induced_operator_norm_bound", {"fraction": "0/1"}),
        ("semigroup_series_parameter_in_unit_interval", False),
        ("exponential_series_majorant_identity", "FORGED_SERIES_PREMISE"),
        ("semigroup_difference_spectral_norm_bound", {"fraction": "0/1"}),
        ("operator_floor_from_spectral_distance", "FORGED_FLOOR_INFERENCE"),
    ],
)
def test_G2_induced_norm_and_exponential_series_premise_mutations_fail(
    field: str, replacement: object
) -> None:
    certificates = copy.deepcopy(build_certificates())
    certificates["T1_geometry"]["uniform_floor_certificate"][field] = replacement
    summary, _records = _execute_from_certificates(certificates)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "G2" in summary["failed_gates"]


def test_exact_formal_nested_geometry_center_and_source_forgery_fails() -> None:
    certificates = copy.deepcopy(build_certificates())
    certificates["T1_geometry"]["stationary_trace_exact"] = {
        "fraction": "7/1",
        "numerator": 7,
        "denominator": 1,
        "float": 7.0,
    }
    certificates["T1_geometry"]["stationary_hermitian_exact"] = False
    certificates["T1_geometry"]["tangents_hermitian_exact"] = False
    certificates["T1_counting"]["center"] = "FORGED"
    certificates["core_source_bindings"] = {key: {} for key in certificates["core_source_bindings"]}
    summary, _records = _execute_from_certificates(certificates)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert {"G1", "G2", "G4", "G6"} <= set(summary["failed_gates"])


def test_forged_reverse_count_F_fails_G11() -> None:
    certificates = copy.deepcopy(build_certificates())
    for case in ("T0", "T1"):
        certificates["T2_FCS"][case]["reverse_count_F"] = "FORGED"
    summary, _records = _execute_from_certificates(certificates)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "G11" in summary["failed_gates"]


@pytest.mark.parametrize(
    ("path", "replacement", "gate_id"),
    [
        (("T0_geometry", "delta_box_unique_full_rank_branch"), 1, "G2"),
        (("T1_geometry", "h_box_certified_without_shrink"), 1, "G2"),
        (("pipeline", "oracle_matches_locked_criterion"), 1, "G9"),
        (("mapping_scope", "same_curvature_refuted"), 1, "G7"),
        (("orientation_scope", "finite_time_loop_claimed"), 0, "G12"),
        (("T1_geometry", "center_Drazin_trace_norm_bound", "numerator"), 25.0, "G2"),
    ],
)
def test_nested_certificate_equality_is_strict_by_json_type(
    path: tuple[str, ...], replacement: object, gate_id: str
) -> None:
    certificates = copy.deepcopy(build_certificates())
    record = certificates
    for key in path[:-1]:
        record = record[key]
    record[path[-1]] = replacement
    summary, _records = _execute_from_certificates(certificates)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert gate_id in summary["failed_gates"]


def test_G12_is_local_orientation_algebra_not_a_finite_time_claim() -> None:
    scope = build_certificates()["orientation_scope"]
    assert scope["accepted_scope"] == "exact_local_parameter_curvature_and_orientation_algebra_only"
    assert scope["qanti_factor"]["fraction"] == "1/2"
    assert scope["full_orientation_difference_factor"]["fraction"] == "2/1"
    assert not scope["finite_time_loop_claimed"]
    assert not scope["finite_time_remainder_claimed"]
    assert not scope["asymptotic_rate_claimed"]
    assert "generic_remainder" not in scope


@pytest.mark.parametrize(
    "attribute",
    [
        "REVIEWED_GATE_ITEMS",
        "REVIEWED_GATE_OWNER_ITEMS",
        "REVIEWED_CASE_DISPOSITION_ITEMS",
        "REVIEWED_CASE_GATE_ITEMS",
    ],
)
def test_registry_relabel_rebinding_or_cross_owner_mutation_fails(
    monkeypatch: pytest.MonkeyPatch, attribute: str
) -> None:
    original = getattr(contract_module, attribute)
    mutated = tuple(reversed(original))
    monkeypatch.setattr(contract_module, attribute, mutated)
    with pytest.raises(RuntimeError, match="registry fingerprint mismatch"):
        contract_module.validate_reviewed_registry()


@pytest.mark.parametrize("gate_id", [item[0] for item in REVIEWED_GATE_ITEMS])
def test_every_gate_can_only_be_forced_from_pass_to_fail(gate_id: str) -> None:
    summary, records = execute_program(gate_overrides={gate_id: False})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert gate_id in summary["failed_gates"]
    record = next(item for item in records if item["gate_id"] == gate_id)
    assert record["natural_status"] == "pass"
    assert record["status"] == "fail"


@pytest.mark.parametrize(
    ("gate_id", "mutator"),
    [
        ("G0", lambda c: c["contract_issues"].append("MUTATED")),
        ("G1", lambda c: c["core_regression"].__setitem__("used_by_theorem_pass", True)),
        ("G2", lambda c: c["T1_geometry"].__setitem__("uniform_full_rank_floor", {"fraction": "0/1"})),
        ("G3", lambda c: c["T0_Drazin"].__setitem__(next(iter(c["T0_Drazin"])), False)),
        ("G4", lambda c: c["T1_geometry"].__setitem__("input_capability_excludes_current_B_and_F", False)),
        ("G5", lambda c: c["T2_FCS"]["T0"].__setitem__("first_q_jet_losses_unchanged", False)),
        ("G6", lambda c: c["T0_counting"].__setitem__("response_curvature", [])),
        ("G7", lambda c: c["mapping_scope"].__setitem__("affine_map_status", "REFUTED")),
        ("G8", lambda c: c["lane_authentication"]["oracle"].__setitem__("authenticated", False)),
        ("G9", lambda c: c["pipeline"].__setitem__("final_state", "INIT")),
        ("G10", lambda c: c["units_and_local_form"].__setitem__("T0_component_units", [])),
        ("G11", lambda c: c["nulls"].__setitem__("reverse_count_negates_B_and_F", False)),
        ("G12", lambda c: c["orientation_scope"].__setitem__("finite_time_remainder_claimed", True)),
        ("G13", lambda c: c["claim_semantics"].__setitem__("disposition", "PASS_STUDY")),
    ],
)
def test_true_override_cannot_rescue_natural_failure(gate_id: str, mutator) -> None:
    certificates = copy.deepcopy(build_certificates())
    mutator(certificates)
    assert not natural_gate_results(certificates)[gate_id][0]
    summary, _records = _execute_from_certificates(certificates, gate_overrides={gate_id: True})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert gate_id in summary["failed_gates"]


@pytest.mark.parametrize(
    "replacement",
    [
        {"h_bounds": (Fraction(1, 20), Fraction(1, 5))},
        {"edge_rate": Fraction(1, 4)},
        {"dephasing_rate": Fraction(1, 4)},
        {"positive_count_definition": "q_positive_counts_the_reverse_edge"},
        {"time_domain": "calibrated_physical_time"},
        {"core_calls_are_acceptance_authority": True},
        {"finite_differences_are_acceptance_authority": True},
        {"positive_map_claim_allowed": True},
        {"empirical_claim_allowed": True},
    ],
)
def test_contract_mutation_fails_G0_and_overall(replacement: dict[str, object]) -> None:
    mutated = replace(MODEL_CONTRACT, **replacement)
    summary, _records = execute_program(contract=mutated, gate_overrides={"G0": True})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "G0" in summary["failed_gates"]


@pytest.mark.parametrize(
    "replacement",
    [
        {"node_count": 5.0},
        {"theta_value": 0.0},
        {"core_calls_are_acceptance_authority": 0},
        {"positive_map_claim_allowed": 0},
        {"node_count": float("nan")},
        {"node_count": float("inf")},
    ],
)
def test_contract_fields_require_exact_types_and_finite_canonical_values(
    replacement: dict[str, object],
) -> None:
    mutated = replace(MODEL_CONTRACT, **replacement)
    summary, _records = execute_program(contract=mutated, gate_overrides={"G0": True})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "G0" in summary["failed_gates"]


def test_unknown_or_nonboolean_override_is_refused() -> None:
    with pytest.raises(ValueError, match="invalid gate override"):
        execute_program(gate_overrides={"G14": False})
    with pytest.raises(ValueError, match="invalid gate override"):
        execute_program(gate_overrides={"G0": 1})  # type: ignore[dict-item]


def test_positive_map_is_refused_without_fabricated_heldout_success() -> None:
    summary, _records = execute_program()
    assert (
        summary["case_dispositions"]["POSITIVE_MAP"] == dict(REVIEWED_CASE_DISPOSITION_ITEMS)["POSITIVE_MAP"]
    )
    lock = summary["metrics"]["prediction_lock"]
    assert not lock["positive_map_inference_requested"]
    assert summary["metrics"]["geometry"]["T0"]["metric_rank"] == 2
    assert summary["metrics"]["geometry"]["T1"]["mean_Uhlmann_curvature_zero_exact"]
    assert "affine, nonlinear, and generator-dependent maps remain open" in summary["claim_ceiling"]


def test_claim_ceiling_and_numerical_scope_are_fail_closed() -> None:
    summary, _records = execute_program()
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert summary["relation_scope"] == "MODEL_SPECIFIC_RELATIONS_ONLY"
    assert "not universal" in summary["claim_ceiling"]
    assert not MODEL_CONTRACT.core_calls_are_acceptance_authority
    assert not MODEL_CONTRACT.finite_differences_are_acceptance_authority


def test_float_core_regression_cannot_replace_or_widen_exact_acceptance() -> None:
    certificates = copy.deepcopy(build_certificates())
    exact_t0 = copy.deepcopy(certificates["T0_counting"])
    exact_t1 = copy.deepcopy(certificates["T1_counting"])
    certificates["core_regression"]["maximum_absolute_error"] = float("inf")
    summary, records = _execute_from_certificates(certificates)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "G1" in summary["failed_gates"]
    assert certificates["T0_counting"] == exact_t0
    assert certificates["T1_counting"] == exact_t1
    assert next(record for record in records if record["gate_id"] == "G1")["status"] == "fail"

    certificates["core_regression"]["used_by_theorem_pass"] = True
    blocked, _records = _execute_from_certificates(certificates, gate_overrides={"G1": True})
    assert blocked["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "G1" in blocked["failed_gates"]


def test_material_sources_and_predecessors_are_exact_recursive_closures() -> None:
    sources = material_source_paths()
    clean_modules = clean_cli_local_module_paths()
    predecessors = predecessor_inventories()
    assert len(sources) == 53
    assert len(clean_modules) == 50
    assert set(clean_modules) < set(sources)
    assert set(predecessors) == {
        "benchmark_d_lindblad_response_proof",
        "constitutive_map_3d_proof",
        "response_theorem_proof_program",
    }
    assert all(
        item["closure"] == "recursive_path_and_type_bound_no_symlink_or_reparse"
        for item in predecessors.values()
    )
    assert all(item["entry_count"] >= 5 for item in predecessors.values())


@pytest.mark.parametrize(
    "mutation",
    [
        lambda summary, _records: summary.__setitem__("claim_ceiling", "UNIVERSAL_ALIGNMENT_PROVED"),
        lambda summary, _records: summary.__setitem__("disposition", "PASS_STUDY"),
        lambda summary, _records: summary.__setitem__("failed_gates", ["G0"]),
        lambda _summary, records: records.append(copy.deepcopy(records[0])),
        lambda _summary, records: records[0].__setitem__("natural_status", "fail"),
        lambda _summary, records: records[0].__setitem__("gate_id", "G13"),
    ],
)
def test_semantic_artifact_validator_rejects_claim_status_and_gate_forgery(mutation) -> None:
    summary, records = execute_program()
    mutation(summary, records)
    with pytest.raises(ArtifactGenerationRefused, match="semantic shared-generator proof record refused"):
        require_semantic_pass(summary, records)


def test_expected_artifact_mapping_is_exact_canonical_and_strict_lf() -> None:
    expected = expected_artifact_bytes()
    assert set(expected) == {
        "CHECKSUMS.json",
        "PROVENANCE.json",
        "REPORT.md",
        "records.json",
        "summary.json",
    }
    assert all(b"\r" not in payload for payload in expected.values())
    for name in ("CHECKSUMS.json", "PROVENANCE.json", "records.json", "summary.json"):
        assert json.loads(expected[name].decode("utf-8"))


def test_transactional_write_and_verify_temporary_generation(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    paths = write_artifacts(destination)
    assert set(paths) == set(expected_artifact_bytes())
    result = verify_artifacts(destination)
    assert result["status"] == "PASS_INTERNAL_ANALYTIC"
    assert result["artifact_count"] == 5
    assert not list(tmp_path.glob(".cwt-cgt-artifacts-transaction-v1*"))


def test_external_temp_generation_uses_its_verified_parent_as_trust_anchor() -> None:
    with tempfile.TemporaryDirectory(prefix="cwt_sg_external_") as temporary:
        parent = Path(temporary)
        destination = parent / "artifacts"
        paths = write_artifacts(destination)
        assert all(path.parent.samefile(destination) for path in paths.values())
        assert verify_artifacts(destination)["artifact_count"] == 5
        assert not list(parent.glob(".cwt-cgt-artifacts-transaction-v1*"))


@pytest.mark.parametrize("had_old", [False, True], ids=["absent", "old_generation"])
def test_predecessor_race_rolls_back_new_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    had_old: bool,
) -> None:
    destination = tmp_path / "artifacts"
    if had_old:
        write_artifacts(destination)
    before = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    original = artifact_module.predecessor_inventories
    calls = 0

    def changed_on_publication():
        nonlocal calls
        calls += 1
        record = original()
        if calls >= 3:
            mutated = copy.deepcopy(record)
            mutated["constitutive_map_3d_proof"]["entry_count"] += 1
            return mutated
        return record

    monkeypatch.setattr(artifact_module, "predecessor_inventories", changed_on_publication)
    with pytest.raises(ArtifactVerificationError, match="changed during publication"):
        write_artifacts(destination)
    after = {
        path.relative_to(tmp_path).as_posix(): path.read_bytes()
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert not list(tmp_path.glob(".cwt-cgt-artifacts-transaction-v1*"))


def test_tampered_artifact_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    write_artifacts(destination)
    (destination / "summary.json").write_text("{}\n", encoding="utf-8", newline="\n")
    with pytest.raises(ArtifactVerificationError, match="artifact content mismatch"):
        verify_artifacts(destination)


def test_destination_overlap_is_zero_write_refused() -> None:
    source = Path(__file__).resolve().parents[2] / "experiments" / "shared_generator_counting_curvature_proof"
    before = sorted(path.relative_to(source).as_posix() for path in source.rglob("*"))
    with pytest.raises(ArtifactGenerationRefused, match="overlaps current experiment"):
        preflight_destination(source / "nested-output")
    after = sorted(path.relative_to(source).as_posix() for path in source.rglob("*"))
    assert before == after


def test_transaction_crash_after_old_move_recovers_complete_generation(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    write_artifacts(destination)

    def crash(checkpoint: str) -> None:
        if checkpoint == "after_old_to_backup":
            raise ArtifactTransactionCrash(checkpoint)

    with pytest.raises(ArtifactTransactionCrash):
        write_artifacts(destination, _fault_injector=crash)
    assert verify_artifacts(destination)["status"] == "PASS_INTERNAL_ANALYTIC"


def test_first_publication_crash_after_prepared_journal_recovers_new_generation(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"

    def crash(checkpoint: str) -> None:
        if checkpoint == "after_journal_prepared":
            raise ArtifactTransactionCrash(checkpoint)

    with pytest.raises(ArtifactTransactionCrash):
        write_artifacts(destination, _fault_injector=crash)
    assert verify_artifacts(destination)["status"] == "PASS_INTERNAL_ANALYTIC"
    assert set(path.name for path in destination.iterdir()) == set(expected_artifact_bytes())


def test_reviewed_source_path_set_rejects_reordering_or_substitution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        artifact_module,
        "REVIEWED_MATERIAL_SOURCE_PATHS",
        tuple(reversed(artifact_module.REVIEWED_MATERIAL_SOURCE_PATHS)),
    )
    with pytest.raises(ArtifactVerificationError, match="reviewed closure"):
        material_source_paths()


def test_recursive_closure_rejects_nested_link_or_reparse(tmp_path: Path) -> None:
    root = tmp_path / "closure"
    root.mkdir()
    (root / "record.json").write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / "nested-link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create a test directory link: {exc}")
    with pytest.raises(ArtifactVerificationError, match="link/reparse"):
        artifact_module.recursive_raw_inventory(root, trust_anchor=tmp_path)


@pytest.mark.parametrize("reserved_leaf", _RESERVED_TRANSACTION_LEAVES)
@pytest.mark.parametrize("existing", [False, True], ids=["absent", "existing"])
def test_reserved_transaction_targets_are_zero_touch_refused(
    tmp_path: Path,
    reserved_leaf: str,
    existing: bool,
) -> None:
    destination = tmp_path / reserved_leaf
    marker = destination / "preserve.bin"
    if existing:
        destination.mkdir()
        marker.write_bytes(b"preserve")
    before = sorted(
        (path.relative_to(tmp_path).as_posix(), path.read_bytes() if path.is_file() else None)
        for path in tmp_path.rglob("*")
    )
    with pytest.raises(ArtifactVerificationError, match="reserved transaction"):
        artifact_transaction_paths(destination)
    after = sorted(
        (path.relative_to(tmp_path).as_posix(), path.read_bytes() if path.is_file() else None)
        for path in tmp_path.rglob("*")
    )
    assert after == before


def test_public_writer_refuses_reserved_namespace_before_any_byte_write(tmp_path: Path) -> None:
    destination = tmp_path / ".cwt-cgt-artifacts-transaction-v1.stage"
    before = list(tmp_path.iterdir())
    with pytest.raises(ArtifactVerificationError, match="reserved transaction"):
        write_artifacts(destination)
    assert list(tmp_path.iterdir()) == before


def test_destination_reparse_ancestor_is_zero_write_refused(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "linked"
    try:
        link.symlink_to(real, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create a test directory link: {exc}")
    before = list(real.iterdir())
    with pytest.raises((ArtifactGenerationRefused, ArtifactVerificationError), match="link/reparse"):
        preflight_destination(link / "artifacts")
    assert list(real.iterdir()) == before


def test_concurrent_guarded_reader_blocks_until_complete_publish(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    write_artifacts(destination)
    writer_inside_swap = threading.Event()
    release_writer = threading.Event()
    reader_done = threading.Event()
    errors: list[BaseException] = []

    def fault(checkpoint: str) -> None:
        if checkpoint == "after_old_to_backup":
            writer_inside_swap.set()
            if not release_writer.wait(10):
                raise RuntimeError("test writer release timed out")

    def writer() -> None:
        try:
            write_artifacts(destination, _fault_injector=fault)
        except BaseException as exc:  # pragma: no cover - surfaced by assertion
            errors.append(exc)

    def reader() -> None:
        try:
            assert verify_artifacts(destination)["artifact_count"] == 5
        except BaseException as exc:  # pragma: no cover - surfaced by assertion
            errors.append(exc)
        finally:
            reader_done.set()

    writer_thread = threading.Thread(target=writer)
    writer_thread.start()
    assert writer_inside_swap.wait(10)
    reader_thread = threading.Thread(target=reader)
    reader_thread.start()
    time.sleep(0.1)
    assert not reader_done.is_set()
    release_writer.set()
    writer_thread.join(20)
    reader_thread.join(20)
    assert not writer_thread.is_alive()
    assert not reader_thread.is_alive()
    assert errors == []


def test_competing_writers_are_serialized(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    write_artifacts(destination)
    first_holds_lock = threading.Event()
    release_first = threading.Event()
    second_done = threading.Event()
    errors: list[BaseException] = []

    def first_fault(checkpoint: str) -> None:
        if checkpoint == "after_staging_verify":
            first_holds_lock.set()
            if not release_first.wait(10):
                raise RuntimeError("test first writer release timed out")

    def first_writer() -> None:
        try:
            write_artifacts(destination, _fault_injector=first_fault)
        except BaseException as exc:  # pragma: no cover - surfaced by assertion
            errors.append(exc)

    def second_writer() -> None:
        try:
            write_artifacts(destination)
        except BaseException as exc:  # pragma: no cover - surfaced by assertion
            errors.append(exc)
        finally:
            second_done.set()

    first = threading.Thread(target=first_writer)
    first.start()
    assert first_holds_lock.wait(10)
    second = threading.Thread(target=second_writer)
    second.start()
    time.sleep(0.1)
    assert not second_done.is_set()
    release_first.set()
    first.join(20)
    second.join(20)
    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert verify_artifacts(destination)["status"] == "PASS_INTERNAL_ANALYTIC"


def test_cli_status_run_and_verify_fail_closed_without_misleading_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = CliRunner()
    status = runner.invoke(run_module.app, ["status"])
    assert status.exit_code == 0, status.stdout
    assert "PASS_INTERNAL_ANALYTIC" in status.stdout

    summary, records = execute_program()
    mutated = copy.deepcopy(summary)
    mutated["claim_ceiling"] = "UNIVERSAL_ALIGNMENT_PROVED"
    writes: list[object] = []
    monkeypatch.setattr(run_module, "execute_program", lambda: (mutated, records))
    monkeypatch.setattr(run_module, "write_artifacts", lambda: writes.append(object()))
    refused_run = runner.invoke(run_module.app, ["run"])
    assert refused_run.exit_code != 0
    assert "PASS_INTERNAL_ANALYTIC" not in refused_run.stdout + refused_run.stderr
    assert writes == []

    monkeypatch.setattr(
        run_module,
        "verify_artifacts",
        lambda: (_ for _ in ()).throw(ArtifactVerificationError("tampered closure")),
    )
    refused_status = runner.invoke(run_module.app, ["status"])
    refused_verify = runner.invoke(run_module.app, ["verify"])
    assert refused_status.exit_code != 0
    assert refused_verify.exit_code != 0
    assert "PASS_INTERNAL_ANALYTIC" not in refused_status.stdout + refused_status.stderr
    assert "PASS_INTERNAL_ANALYTIC" not in refused_verify.stdout + refused_verify.stderr


def test_missing_disk_generation_is_refused_by_verifier(tmp_path: Path) -> None:
    with pytest.raises(ArtifactVerificationError):
        verify_artifacts(tmp_path / "missing-artifacts")

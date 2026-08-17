"""Focused analytic and fail-closed tests for the 3D constitutive-map program."""

from __future__ import annotations

import ast
import copy
import inspect
import json
import math
import shutil
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from cwt.cgt.benchmarks import get_benchmark
from cwt.operator.L_map import qp1_eigenvalues
from experiments.constitutive_map_3d_proof import artifacts, response_oracle, run as proof_run
from experiments.constitutive_map_3d_proof.artifacts import (
    ArtifactGenerationRefused,
    ArtifactVerificationError,
    canonical_source_text_bytes,
    expected_artifact_bytes,
    material_source_relative_paths,
    predecessor_inventories,
    preflight_artifact_destination,
    recursive_raw_inventory,
    render_report,
    require_semantic_pass,
    source_hashes,
    verify_artifacts,
)
from experiments.constitutive_map_3d_proof.bc3_core_regression import (
    authored_predecessor_identity,
    live_core_sample_regression,
)
from experiments.constitutive_map_3d_proof.bc3_primitives import analytic_box_certificate
from experiments.constitutive_map_3d_proof.bc3_remainder import (
    FORMAL_ENVELOPE_CEILINGS,
    FORMAL_SCALES,
    FORMAL_STEPS_PER_EDGE,
    assess_oracle_enclosures,
    density_envelope,
    exact_remainder_certificate,
)
from experiments.constitutive_map_3d_proof.benchmark_c_alpha import (
    beta_components,
    directed_form_intervals,
    factorization_certificate,
    form_components,
)
from experiments.constitutive_map_3d_proof.classifier import (
    apply_fail_only_overrides,
    case_dispositions,
    gate_owner,
    registry_gate_names,
)
from experiments.constitutive_map_3d_proof.contract import (
    MODEL_CONTRACT,
    canonical_registry_record,
    case_gate_ownership,
    contract_issues,
    expected_case_dispositions,
    validate_reviewed_registry_constants,
)
from experiments.constitutive_map_3d_proof.exact import (
    RationalInterval,
    cos_interval,
    exp_interval,
    sin_interval,
    strict_cross,
)
from experiments.constitutive_map_3d_proof.firewall import (
    ALLOWED_IMPORT_MODULES_BY_ROLE,
    ROLE_POLICIES,
    analyze_source_text,
    source_authentication_records,
)
from experiments.constitutive_map_3d_proof.pipeline import (
    OracleAccess,
    PipelineSession,
    PipelineState,
    PipelineViolation,
    create_prediction_lock,
)
from experiments.constitutive_map_3d_proof.qp1_ambient import (
    hamiltonian,
    hamiltonian_derivatives,
    projector,
)
from experiments.constitutive_map_3d_proof.qp1_geometry import (
    curvature_tensor,
    geometry_certificate,
    two_form_vector,
)
from experiments.constitutive_map_3d_proof.qp1_kubo import kubo_certificate, spectral_kubo_tensor
from experiments.constitutive_map_3d_proof.response_oracle import (
    DIAGNOSTIC_DENSITY_CEILING,
    assess_scalar_diagnostics,
    scalar_diagnostic_record,
)
from experiments.constitutive_map_3d_proof.theorem import (
    build_certificates,
    execute_program,
    natural_gate_inputs,
    publication_disposition,
)
from experiments.independent_response_theorem.response import circulation_current


@pytest.fixture(scope="module")
def program_result():
    return execute_program()


@pytest.fixture(scope="module")
def program_certificates():
    return build_certificates()


@pytest.fixture(scope="module")
def natural_inputs(program_certificates):
    return natural_gate_inputs(program_certificates)


def _factorization_only():
    session = PipelineSession()
    prediction = session.build_prediction(lambda access: factorization_certificate(access))
    lock = session.lock_prediction(prediction)
    return session, prediction, lock


def test_pipeline_requires_one_current_lock_and_exact_event_order() -> None:
    session = PipelineSession()
    captured = {}

    def build(access):
        captured["access"] = access
        return {"prediction": "sealed"}

    prediction = session.build_prediction(build)
    lock = session.lock_prediction(prediction)
    observed = session.run_oracle(lock, lambda access: access.require_current().lock_sha256)
    assert observed == lock.lock_sha256
    assert session.verify(lock) == (
        "INIT",
        "PREDICTION_LOCKED",
        "ORACLE_RUN",
        "VERIFIED",
    )
    with pytest.raises(PipelineViolation):
        captured["access"].require_current()
    assert session.state is PipelineState.POISONED


def test_pipeline_refuses_oracle_before_lock_wrong_lock_replay_and_wrapper_reordering() -> None:
    early = PipelineSession()
    forged = create_prediction_lock({"forged": True})
    with pytest.raises(PipelineViolation):
        OracleAccess(early, forged).require_current()

    wrong = PipelineSession()
    prediction = wrong.build_prediction(lambda access: {"value": 1})
    current = wrong.lock_prediction(prediction)
    foreign = create_prediction_lock({"value": 2})
    assert current != foreign
    with pytest.raises(PipelineViolation):
        wrong.run_oracle(foreign, lambda access: None)

    replay = PipelineSession()
    prediction = replay.build_prediction(lambda access: {"value": 1})
    lock = replay.lock_prediction(prediction)
    replay.run_oracle(lock, lambda access: access.require_current().lock_sha256)
    with pytest.raises(PipelineViolation):
        replay.run_oracle(lock, lambda access: None)

    wrapper = PipelineSession()
    captured = {}

    def builder(access):
        captured["access"] = access
        return {"value": 1}

    prediction = wrapper.build_prediction(builder)
    lock = wrapper.lock_prediction(prediction)
    with pytest.raises(PipelineViolation):
        wrapper.run_oracle(lock, lambda access: factorization_certificate(captured["access"]))


def test_current_authenticated_firewall_sources_have_no_issues() -> None:
    records = source_authentication_records()
    assert set(records) == {policy.role for policy in ROLE_POLICIES}
    assert all(record["authenticated"] is True for record in records.values())
    for policy in ROLE_POLICIES:
        path = artifacts.SIM_ROOT.joinpath(*policy.relative_path.split("/"))
        assert analyze_source_text(path.read_text(encoding="utf-8"), policy)["issues"] == []


def test_sample_invisible_arithmetic_source_mutation_invalidates_authenticated_role(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import experiments.constitutive_map_3d_proof.firewall as firewall_module

    for policy in ROLE_POLICIES:
        source = artifacts.SIM_ROOT.joinpath(*policy.relative_path.split("/"))
        destination = tmp_path.joinpath(*policy.relative_path.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source.read_bytes())
    geometry_policy = next(item for item in ROLE_POLICIES if item.role == "qp3_geometry")
    geometry_path = tmp_path.joinpath(*geometry_policy.relative_path.split("/"))
    geometry_path.write_bytes(geometry_path.read_bytes() + b"# sample-invisible arithmetic perturbation\n")
    monkeypatch.setattr(firewall_module, "SIM_ROOT", tmp_path)
    records = source_authentication_records()
    assert records["qp3_geometry"]["issues"] == []
    assert records["qp3_geometry"]["authenticated"] is False
    assert all(record["authenticated"] is True for role, record in records.items() if role != "qp3_geometry")


@pytest.mark.parametrize(
    ("role", "source"),
    (
        ("bc3_predictor", "from .response_oracle import response_sum as safe"),
        ("bc3_predictor", "from .response_oracle import *"),
        ("bc3_predictor", "import importlib\nimportlib.import_module('response_oracle')"),
        ("bc3_predictor", "import response_oracle as safe\nwrapped=safe.response_sum\nwrapped()"),
        ("bc3_predictor", "def safe(held_out_response):\n    local_outcome=held_out_response"),
        ("bc3_response_oracle", "from .benchmark_c_alpha import form_components"),
        ("qp3_kubo", "from .qp1_geometry import curvature_tensor as spectral_input"),
        ("qp3_kubo", "import importlib as loader\nloader.import_module('qp1_geometry')"),
    ),
)
def test_ast_firewalls_reject_alias_star_dynamic_relative_and_normalized_tokens(
    role: str,
    source: str,
) -> None:
    policy = next(item for item in ROLE_POLICIES if item.role == role)
    assert analyze_source_text(source, policy)["issues"]


@pytest.mark.parametrize(
    ("role", "source"),
    (
        (
            "bc3_predictor",
            "import importlib\n"
            "loader=getattr(importlib,'import_module')\n"
            "mod=loader('experiments.constitutive_map_3d_proof.response_oracle')\n"
            "q=getattr(mod,'response_sum')\nq()",
        ),
        (
            "qp3_kubo",
            "import importlib\n"
            "loader=importlib.__dict__['import_module']\n"
            "mod=loader('experiments.constitutive_map_3d_proof.qp1_geometry')\n"
            "curv=mod.__dict__['curvature_tensor']\ncurv(None)",
        ),
        (
            "bc3_predictor",
            "import importlib as il\n"
            "load=il.import_module\nalias=load\n"
            "suffix='response_'+'oracle'\n"
            "mod=alias(f'experiments.constitutive_map_3d_proof.{suffix}')",
        ),
        (
            "bc3_predictor",
            "from importlib import import_module as load\n"
            "mod=load('experiments.constitutive_map_3d_proof.response_oracle')",
        ),
        (
            "bc3_predictor",
            "mod=__import__('experiments.constitutive_map_3d_proof.response_oracle')",
        ),
        (
            "bc3_predictor",
            "scope=globals()\nq=scope['response_'+'sum']\nq()",
        ),
        (
            "bc3_predictor",
            "import response_oracle as safe\nq=getattr(safe,'response_sum')\nq()",
        ),
        (
            "qp3_kubo",
            "import qp1_geometry as geom\ncurv=vars(geom)['curvature_tensor']\ncurv(None)",
        ),
        (
            "qp3_kubo",
            "source=compile('curvature_tensor()', '<dynamic>', 'exec')\nexec(source)",
        ),
        (
            "bc3_predictor",
            "import importlib\n"
            "def identity(value):\n    return value\n"
            "loader=identity(importlib.import_module)\n"
            "mod=loader('experiments.constitutive_map_3d_proof.response_oracle')",
        ),
        (
            "bc3_predictor",
            "import operator\nimport response_oracle as mod\n"
            "q=operator.attrgetter('response_'+'sum')(mod)\nq()",
        ),
        (
            "bc3_predictor",
            "loader=__builtins__['__im'+'port__']\n"
            "name=''.join(['experiments.constitutive_map_3d_proof.','response_','oracle'])\n"
            "mod=loader(name,{}, {},['x'],0)",
        ),
        (
            "bc3_predictor",
            "import operator\n"
            "loader=operator.itemgetter('__im'+'port__')(__builtins__)\n"
            "mod=loader('experiments.constitutive_map_3d_proof.response_oracle')",
        ),
        (
            "bc3_predictor",
            "import builtins\n"
            "scope=vars(builtins)\nloader=scope['__im'+'port__']\n"
            "name='experiments.constitutive_map_3d_proof.{}'.format('response_oracle')\n"
            "mod=loader(name)",
        ),
        (
            "binary64_interval_kernel",
            "import sys\n" "mod=sys.modules['experiments.constitutive_map_3d_proof.'+'response_oracle']",
        ),
        (
            "bc3_predictor",
            "import runpy\nrunpy.run_module('experiments.constitutive_map_3d_proof.response_oracle')",
        ),
        ("bc3_predictor", "def safe():\n    loader('value')"),
    ),
)
def test_firewalls_reject_reflective_dynamic_callable_recovery(
    role: str,
    source: str,
) -> None:
    policy = next(item for item in ROLE_POLICIES if item.role == role)
    issues = analyze_source_text(source, policy)["issues"]
    assert issues
    assert any(
        marker in issue
        for issue in issues
        for marker in (
            "REFLECTION",
            "REFLECTIVE",
            "DYNAMIC_IMPORT",
            "DYNAMIC_FORBIDDEN_TARGET",
            "FORBIDDEN_IMPORT",
            "UNKNOWN_CALL_TARGET",
        )
    )


@pytest.mark.parametrize(
    ("role", "source"),
    (
        ("bc3_predictor", "import math as m\nvalue=m.sin(m.pi/4)"),
        (
            "bc3_response_oracle",
            "from .bc3_primitives import frozen_centered_readout as read\nvalue=read(0.,0.,0.,0.)",
        ),
        (
            "binary64_interval_kernel",
            "class Box:\n    pass\nobject.__setattr__(Box(), 'lower', 0.0)",
        ),
        ("qp3_kubo", "import numpy as np\nvalue=np.asarray([1.,2.])[0]"),
    ),
)
def test_firewalls_allow_statically_resolved_benign_math_and_attributes(
    role: str,
    source: str,
) -> None:
    policy = next(item for item in ROLE_POLICIES if item.role == role)
    assert analyze_source_text(source, policy)["issues"] == []


def test_per_role_import_allowlists_are_exact_and_fingerprinted(monkeypatch) -> None:
    import experiments.constitutive_map_3d_proof.firewall as firewall_module

    assert set(ALLOWED_IMPORT_MODULES_BY_ROLE) == {policy.role for policy in ROLE_POLICIES}
    predictor = next(item for item in ROLE_POLICIES if item.role == "bc3_predictor")
    assert analyze_source_text("import random", predictor)["issues"] == ["IMPORT_NOT_ALLOWLISTED:random"]
    mutated = dict(ALLOWED_IMPORT_MODULES_BY_ROLE)
    mutated["bc3_predictor"] = (*mutated["bc3_predictor"], "random")
    monkeypatch.setattr(firewall_module, "ALLOWED_IMPORT_MODULES_BY_ROLE", mutated)
    with pytest.raises(RuntimeError, match="allowlist fingerprint"):
        source_authentication_records()


def test_formal_remainder_constants_ladder_and_envelope_are_exact() -> None:
    certificate = exact_remainder_certificate()
    assert tuple(MODEL_CONTRACT.bc3_scales) == FORMAL_SCALES
    assert tuple(MODEL_CONTRACT.bc3_steps_per_edge) == FORMAL_STEPS_PER_EDGE
    assert certificate["all_envelopes_within_reviewed_ceilings"] is True
    assert certificate["s_times_N_strictly_doubles"] is True
    for scale, steps, ceiling in zip(
        FORMAL_SCALES,
        FORMAL_STEPS_PER_EDGE,
        FORMAL_ENVELOPE_CEILINGS,
        strict=True,
    ):
        assert density_envelope(scale, steps) <= ceiling


def test_directed_oracle_enclosures_are_authenticated_negative_and_conjunctive(
    program_certificates,
) -> None:
    certificates = program_certificates
    assessment = certificates["bc3_directed_enclosure_assessment"]
    assert assessment["status"] == "AUTHENTICATED_DIRECTED_ENCLOSURES_PASS"
    assert assessment["all_rows_pass"] is True
    assert [row["row_role"] for row in assessment["rows"]] == [
        "development_regression",
        "development_regression",
        "locked_synthetic_holdout",
        "locked_synthetic_holdout",
    ]
    for row in assessment["rows"]:
        assert row["density_interval"]["width"] <= 1.0e-6
        assert row["density_interval"]["upper"] < 0.0
        assert all(row["conjuncts"].values())
    diagnostics = []
    for oracle_row in certificates["bc3_oracle"]["rows"]:
        diagnostic = oracle_row["scalar_diagnostic"]
        diagnostics.append(diagnostic)
        assert diagnostic["authority"] == "NON_AUTHORITATIVE_DIAGNOSTIC"
        assert diagnostic["used_by_formal_pass"] is False
        assert diagnostic["unioned_into_authoritative_interval"] is False
        assert diagnostic["development_selected_density_ceiling"] == 1.0e-6
        assert diagnostic["density_distance_to_authoritative_interval"] <= 1.0e-6
        assert diagnostic["diagnostic_status"] == "PASS_NONAUTHORITATIVE_REGRESSION"
        lattice = oracle_row["lattice"]
        assert lattice["start_equals_end_exact"] is True
        assert lattice["reverse_equals_forward_index_reverse_exact"] is True
        assert lattice["corner_state_carried_without_reset_or_duplicate_sample"] is True
        assert lattice["final_initial_control_sampled_once"] is True
    runtime = certificates["bc3_oracle"]["binary64_interval_runtime"]
    assert runtime["passed"] is True
    assert runtime["libm_transcendentals_used"] is False
    assert runtime["fma_reassociation_or_fast_math_used"] is False
    assert any(not item["density_inside_authoritative_interval"] for item in diagnostics)
    diagnostic_assessment = certificates["bc3_oracle"]["scalar_diagnostic_assessment"]
    assert diagnostic_assessment["diagnostic_status"] == "PASS_NONAUTHORITATIVE_REGRESSION"
    assert diagnostic_assessment["unioned_into_authoritative_interval"] is False


def test_scalar_diagnostic_drift_never_changes_formal_intervals_or_gates(
    program_certificates,
) -> None:
    original = copy.deepcopy(program_certificates)
    mutated = copy.deepcopy(program_certificates)
    row = mutated["bc3_oracle"]["rows"][-1]
    scale = float(row["scale"])
    q_interval = row["q_anti_interval"]
    density_interval = row["density_interval"]
    scalar_q = float(q_interval["upper"]) + 2.0e-6 * scale * scale
    row["scalar_diagnostic"] = scalar_diagnostic_record(
        scalar_q,
        scale,
        (float(q_interval["lower"]), float(q_interval["upper"])),
        (float(density_interval["lower"]), float(density_interval["upper"])),
    )
    mutated_assessment = assess_scalar_diagnostics(mutated["bc3_oracle"]["rows"])
    mutated["bc3_oracle"]["scalar_diagnostic_assessment"] = mutated_assessment
    mutated["bc3_oracle"]["diagnostic_status"] = mutated_assessment["diagnostic_status"]

    original_intervals = [
        (item["q_anti_interval"], item["density_interval"]) for item in original["bc3_oracle"]["rows"]
    ]
    mutated_intervals = [
        (item["q_anti_interval"], item["density_interval"]) for item in mutated["bc3_oracle"]["rows"]
    ]
    assert mutated_intervals == original_intervals
    assert natural_gate_inputs(mutated) == natural_gate_inputs(original)
    assert mutated_assessment["diagnostic_status"] == "BLOCKED_DIAGNOSTIC_DRIFT"
    assert publication_disposition(
        MODEL_CONTRACT.disposition,
        mutated_assessment["diagnostic_status"],
    ) == ("BLOCKED_DIAGNOSTIC_DRIFT", ["bc3_scalar_non_authoritative_diagnostic"])


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_scalar_diagnostic_blocks_without_widening(value, program_certificates) -> None:
    rows = copy.deepcopy(program_certificates["bc3_oracle"]["rows"])
    row = rows[-1]
    row["scalar_diagnostic"] = scalar_diagnostic_record(
        value,
        float(row["scale"]),
        (float(row["q_anti_interval"]["lower"]), float(row["q_anti_interval"]["upper"])),
        (float(row["density_interval"]["lower"]), float(row["density_interval"]["upper"])),
    )
    assessment = assess_scalar_diagnostics(rows)
    assert assessment["diagnostic_status"] == "BLOCKED_DIAGNOSTIC_DRIFT"
    assert row["scalar_diagnostic"]["q_anti"] is None
    assert row["scalar_diagnostic"]["density"] is None


def test_scalar_diagnostic_ceiling_is_fixed_non_authoritative_metadata(
    program_certificates,
) -> None:
    oracle = program_certificates["bc3_oracle"]
    assert DIAGNOSTIC_DENSITY_CEILING == 1.0e-6
    assert oracle["scalar_diagnostic_policy"] == {
        "authority": "NON_AUTHORITATIVE_DIAGNOSTIC",
        "used_by_formal_pass": False,
        "unioned_into_authoritative_interval": False,
        "development_selected_density_ceiling": 1.0e-6,
    }


def test_prediction_lock_contains_complete_formal_source_tube_and_ladder_closure(
    program_certificates,
) -> None:
    prediction = program_certificates["bc3_prediction"]
    assert prediction["formal_remainder_certificate"]["contract_ladder_matches"] is True
    assert prediction["formal_remainder_certificate"]["orientation_remainder_cancellation_assumed"] is False
    assert prediction["locked_midpoint_predictions"]["response_oracle_imported"] is False
    assert prediction["locked_midpoint_predictions"]["heldout_response_used"] is False
    assert prediction["branch_box_certificate"]["phase_bounds"] == ["349/8000", "1101/8000"]
    assert len(prediction["authenticated_role_sources"]) == 9
    assert all(
        record["authenticated"] is True for record in prediction["authenticated_role_sources"].values()
    )


def test_missing_enclosure_is_indeterminate_and_violation_is_fail(program_certificates) -> None:
    assert assess_oracle_enclosures(None, None)["status"].startswith("INDETERMINATE")
    certificates = program_certificates
    rows = copy.deepcopy(certificates["bc3_oracle"]["rows"])
    rows[-1]["density_interval"] = {"lower": 0.1, "upper": 0.2, "width": 0.1}
    violated = assess_oracle_enclosures(
        certificates["bc3_prediction"]["locked_midpoint_predictions"],
        rows,
    )
    assert violated["status"].startswith("FAIL_")
    assert violated["all_rows_pass"] is False


def test_classifier_distinguishes_indeterminate_from_finite_violation(natural_inputs) -> None:
    gate_name = "bc3_generic_ladder_and_nulls"
    pending = dict(natural_inputs)
    pending[gate_name] = (None, pending[gate_name][1], {"missing": "authenticated enclosure"})
    pending_gates = apply_fail_only_overrides(pending, {gate_name: True})
    assert next(gate for gate in pending_gates if gate.name == gate_name).status == "indeterminate"
    assert case_dispositions(pending_gates)["BC3"].startswith("INDETERMINATE_INTERNAL_ANALYTIC")
    failed_gates = apply_fail_only_overrides(pending, {gate_name: False})
    assert next(gate for gate in failed_gates if gate.name == gate_name).status == "fail"


def test_program_has_exact_internal_model_specific_ceiling(program_result) -> None:
    summary, _ = program_result
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert summary["relation_scope"] == "MODEL_SPECIFIC_RELATIONS_ONLY"
    assert "universal" in summary["claim_ceiling"]
    assert summary["failed_gates"] == []
    assert summary["case_dispositions"] == expected_case_dispositions()


def test_registry_is_immutable_ordered_unique_and_fingerprinted(program_result) -> None:
    summary, records = program_result
    names = tuple(record["name"] for record in records if record["record_type"] == "gate")
    assert names == registry_gate_names()
    assert len(names) == len(set(names)) == 17
    assert summary["registry"] == canonical_registry_record()
    assert len(summary["registry"]["gate_ownership_sha256"]) == 64
    assert len(summary["registry"]["case_dispositions_sha256"]) == 64
    assert {gate_owner(name) for name in names} == {"BC3", "QP3", "REFUSALS", "SCOPE"}


def test_registry_fingerprints_reject_relabel_cross_owner_swap_duplicate_and_rebinding(
    monkeypatch,
) -> None:
    import experiments.constitutive_map_3d_proof.contract as contract_module

    original = contract_module.REVIEWED_CASE_GATE_OWNERSHIP
    mutations = []
    relabelled = list(original)
    relabelled[0] = (relabelled[0][0], ("forged_gate", *relabelled[0][1][1:]))
    mutations.append(tuple(relabelled))
    cross_owner = list(original)
    bc3_name = cross_owner[0][1][0]
    qp3_name = cross_owner[1][1][0]
    cross_owner[0] = (cross_owner[0][0], (qp3_name, *cross_owner[0][1][1:]))
    cross_owner[1] = (cross_owner[1][0], (bc3_name, *cross_owner[1][1][1:]))
    mutations.append(tuple(cross_owner))
    duplicated = list(original)
    duplicated[0] = (duplicated[0][0], (*duplicated[0][1], duplicated[0][1][0]))
    mutations.append(tuple(duplicated))
    for mutated in mutations:
        with monkeypatch.context() as context:
            context.setattr(contract_module, "REVIEWED_CASE_GATE_OWNERSHIP", mutated)
            with pytest.raises(RuntimeError, match="fingerprint"):
                validate_reviewed_registry_constants()

    with monkeypatch.context() as context:
        swapped = tuple(reversed(contract_module.REVIEWED_CASE_DISPOSITION_ITEMS))
        context.setattr(contract_module, "REVIEWED_CASE_DISPOSITION_ITEMS", swapped)
        with pytest.raises(RuntimeError, match="fingerprint"):
            validate_reviewed_registry_constants()


@pytest.mark.parametrize("gate_name", registry_gate_names())
def test_every_live_gate_can_only_be_forced_to_fail(gate_name: str, natural_inputs) -> None:
    gates = apply_fail_only_overrides(natural_inputs, {gate_name: False})
    cases = case_dispositions(gates)
    assert next(gate for gate in gates if gate.name == gate_name).passed is False
    assert cases[gate_owner(gate_name)].startswith("FAIL_INTERNAL_ANALYTIC:")


def test_true_override_cannot_rescue_natural_contract_failure() -> None:
    invalid = replace(MODEL_CONTRACT, universal_claim_allowed=True)
    summary, records = execute_program(
        invalid,
        gate_overrides={"claim_ceiling_and_evidence_scope": True},
    )
    gate = next(record for record in records if record.get("name") == "claim_ceiling_and_evidence_scope")
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert gate["natural_status"] == "fail"
    assert gate["status"] == "fail"


def test_unknown_and_nonboolean_overrides_fail_closed() -> None:
    with pytest.raises(KeyError):
        execute_program(gate_overrides={"unknown": False})
    with pytest.raises(TypeError):
        execute_program(gate_overrides={registry_gate_names()[0]: 1})  # type: ignore[dict-item]


def test_contract_rejects_area_claim_and_control_inflation() -> None:
    assert "BC3_AREA_VECTOR_MISMATCH" in contract_issues(replace(MODEL_CONTRACT, bc3_area_vector=(2, 1, 2)))
    assert "FORBIDDEN_SCOPE_ENABLED" in contract_issues(replace(MODEL_CONTRACT, gain_as_control_allowed=True))


def test_qp3_projector_hamiltonian_and_gap_are_exact_regressions() -> None:
    point = np.asarray((1.0, 2.0, 2.0)) / 3.0
    p_plus = projector(point)
    operator = hamiltonian(point)
    values = np.linalg.eigvalsh(operator)
    assert np.max(np.abs(p_plus @ p_plus - p_plus)) < 1.0e-15
    assert np.max(np.abs(operator - operator.conj().T)) < 1.0e-15
    assert values == pytest.approx((3.0 / 5.0, 1.0), abs=1.0e-14)
    assert values[1] - values[0] == pytest.approx(2.0 / 5.0, abs=1.0e-14)


def test_qp3_derivatives_match_operator_finite_differences() -> None:
    point = np.asarray((0.4, -0.3, 0.8), dtype=float)
    step = 1.0e-6
    for axis, derivative in enumerate(hamiltonian_derivatives(point)):
        direction = np.eye(3)[axis]
        finite = (hamiltonian(point + step * direction) - hamiltonian(point - step * direction)) / (2 * step)
        assert np.max(np.abs(derivative - finite)) < 2.0e-10


def test_qp3_kubo_positive_conventional_and_factor_two() -> None:
    for point in (*MODEL_CONTRACT.qp3_centers, MODEL_CONTRACT.qp3_heldout):
        control = np.asarray([float(item) for item in point])
        omega = curvature_tensor(control)
        positive = spectral_kubo_tensor(control, +1.0)
        conventional = spectral_kubo_tensor(control, -1.0)
        assert positive == pytest.approx(omega, abs=1.0e-12)
        assert conventional == pytest.approx(-omega, abs=1.0e-12)
        assert positive - positive.T == pytest.approx(2.0 * positive, abs=1.0e-14)


def test_qp3_centers_rank_three_and_heldout_density_is_half() -> None:
    geometry = geometry_certificate()
    kubo = kubo_certificate()
    assert geometry["center_vector_rank"] == 3
    assert kubo["center_vector_rank"] == 3
    assert geometry["heldout_density_exact"]["fraction"] == "1/2"
    assert kubo["heldout_density_exact"]["fraction"] == "1/2"
    heldout = np.asarray([float(item) for item in MODEL_CONTRACT.qp3_heldout])
    assert two_form_vector(curvature_tensor(heldout)) @ heldout == pytest.approx(0.5, abs=1.0e-14)


def test_qp3_is_not_the_existing_two_dimensional_builder() -> None:
    old_gap = qp1_eigenvalues({"x": 0.1, "y": 0.5})[0] - qp1_eigenvalues({"x": 0.1, "y": 0.5})[1]
    assert old_gap.real == pytest.approx(1.0 / 5.0)
    assert MODEL_CONTRACT.qp3_gap == Fraction(2, 5)
    assert kubo_certificate()["existing_qp1_builder_claimed"] is False


def test_qp3_rotation_covariance_closure_chern_and_constant_null() -> None:
    certificate = geometry_certificate()
    assert certificate["proper_rotation_covariance"]["proper_rotation_covariance_error"] < 1.0e-14
    assert certificate["integrability"] == "dOmega=0_on_R3_without_origin"
    assert certificate["chern_number"] == 1
    assert certificate["global_smooth_connection_exists"] is False
    assert certificate["constant_projector_curvature_max"] == 0.0


def test_qp3_nonscalar_constant_map_fails_integrability() -> None:
    certificate = kubo_certificate()
    assert certificate["nonscalar_map"] == "K=diag(2,1,1)"
    assert certificate["nonscalar_mapped_form_divergence_at_heldout"]["fraction"] == "1/3"
    assert certificate["nonscalar_map_is_integrable"] is False


def test_directed_interval_helpers_enclose_transcendentals() -> None:
    for value in (Fraction(-1, 5), Fraction(0), Fraction(1, 3)):
        exp_bounds = exp_interval(value)
        assert (
            float(exp_bounds.lower) - 1.0e-15 <= math.exp(float(value)) <= float(exp_bounds.upper) + 1.0e-15
        )
        sin_bounds = sin_interval(value)
        assert (
            float(sin_bounds.lower) - 1.0e-15 <= math.sin(float(value)) <= float(sin_bounds.upper) + 1.0e-15
        )
        cos_bounds = cos_interval(value)
        assert (
            float(cos_bounds.lower) - 1.0e-15 <= math.cos(float(value)) <= float(cos_bounds.upper) + 1.0e-15
        )
    with pytest.raises(ZeroDivisionError):
        RationalInterval(Fraction(-1), Fraction(1)).reciprocal()


def test_bc3_core_c0_equivalence_clip_and_wrap_margins() -> None:
    regression = live_core_sample_regression()
    box = analytic_box_certificate()
    assert regression["maximum_core_error"] < 1.0e-13
    assert regression["acceptance_authority"] is False
    assert box["clip_margin"] == "1/8"
    assert box["clip_inactive_everywhere"] is True
    assert box["wrap_inactive_everywhere"] is True
    assert authored_predecessor_identity()["authenticated"] is True


def test_sample_invisible_live_core_perturbation_has_no_acceptance_authority_or_hash_bypass(
    monkeypatch,
    tmp_path: Path,
) -> None:
    import experiments.constitutive_map_3d_proof.bc3_core_regression as regression_module

    destination = tmp_path / "cwt" / "cgt" / "benchmarks.py"
    destination.parent.mkdir(parents=True)
    source = artifacts.SIM_ROOT / "cwt" / "cgt" / "benchmarks.py"
    destination.write_bytes(source.read_bytes() + b"# interior-only perturbation\n")
    monkeypatch.setattr(regression_module, "SIM_ROOT", tmp_path)
    assert regression_module.authored_predecessor_identity()["authenticated"] is False
    theorem_source = inspect.getsource(__import__(execute_program.__module__, fromlist=["execute_program"]))
    assert "live_core_sample_regression" not in theorem_source


def test_bc3_factorization_area_vector_and_directed_nonzero_margins() -> None:
    _, certificate, _ = _factorization_only()
    assert strict_cross(MODEL_CONTRACT.bc3_tangent_1, MODEL_CONTRACT.bc3_tangent_2) == (1, 2, 2)
    assert certificate["derived_area_vector"] == [1, 2, 2]
    assert certificate["all_response_components_nonzero"] is True
    assert certificate["heldout_density_nonzero"] is True
    intervals = directed_form_intervals(Fraction(3, 25), Fraction(2, 25), Fraction(1, 3))
    assert all(
        intervals[name].excludes_zero for name in ("F_v_alpha", "F_alpha_u", "F_u_v", "heldout_density")
    )


def test_bc3_formula_matches_independent_finite_derivative_regression() -> None:
    point = np.asarray((0.12, 0.08, 1.0 / 3.0), dtype=float)
    step = 2.0e-6
    tensor = np.zeros((3, 3), dtype=float)
    for first in range(3):
        for second in range(3):
            d_first_beta_second = (
                beta_components(point + step * np.eye(3)[first])[second]
                - beta_components(point - step * np.eye(3)[first])[second]
            ) / (2 * step)
            d_second_beta_first = (
                beta_components(point + step * np.eye(3)[second])[first]
                - beta_components(point - step * np.eye(3)[second])[first]
            ) / (2 * step)
            tensor[first, second] = d_first_beta_second - d_second_beta_first
    observed = np.asarray((tensor[1, 2], tensor[2, 0], tensor[0, 1]))
    expected_values = form_components(*point)
    expected = np.asarray(
        (expected_values["F_v_alpha"], expected_values["F_alpha_u"], expected_values["F_u_v"])
    )
    assert observed == pytest.approx(expected, abs=2.0e-9)


def test_bc3_geometry_is_alpha_independent_but_response_is_not() -> None:
    _, certificate, _ = _factorization_only()
    assert certificate["geometry_rank"] == 1
    assert certificate["geometry_vector"][:2] == [0.0, 0.0]
    assert certificate["alpha_endpoint_omega_intervals_equal"] is True
    assert certificate["alpha_endpoint_fiber_response_separated"] is True
    assert certificate["scalar_omega_only_map_possible"] is False


def test_bc3_gain_and_alpha_scoped_nulls() -> None:
    gain_zero = form_components(0.12, 0.08, 1.0 / 3.0, 0.0)
    assert all(abs(gain_zero[name]) < 1.0e-15 for name in ("F_v_alpha", "F_alpha_u", "F_u_v"))
    alpha_one = form_components(0.12, 0.08, 1.0, 0.45)
    assert alpha_one["F_u_v"] == pytest.approx(0.0, abs=1.0e-15)
    assert abs(alpha_one["F_v_alpha"]) > 0.0


def test_bc3_global_phase_invariance_of_geometry_blind_readout() -> None:
    candidate = get_benchmark("benchmark_c").resolve_candidate_by_id(0.12, 0.08, "C0")
    assert candidate is not None
    state = candidate.state
    base = circulation_current(state.p, state.theta, state.kernel, 0.45)
    shifted = circulation_current(state.p, state.theta + 1.2345, state.kernel, 0.45)
    assert shifted == pytest.approx(base, abs=1.0e-15)


def test_response_oracle_has_no_geometry_predictor_or_forbidden_inputs() -> None:
    source = Path(inspect.getsourcefile(response_oracle) or "").read_text(encoding="utf-8")
    imports = [node.module or "" for node in ast.walk(ast.parse(source)) if isinstance(node, ast.ImportFrom)]
    assert not any("benchmark_c_alpha" in item or "qp1_geometry" in item for item in imports)
    assert "Omega" not in source and "Phi" not in source
    assert set(inspect.signature(response_oracle.response_sum).parameters) == {
        "controls",
        "oracle_access",
        "gain",
        "contract",
    }


def test_response_oracle_right_endpoint_reverse_factor_and_pure_alpha_null(
    program_certificates,
) -> None:
    certificate = program_certificates["bc3_oracle"]
    assert certificate["right_endpoint_update_then_sample"] is True
    assert certificate["equilibrium_initialization"] is True
    assert certificate["exact_reverse_used"] is True
    assert certificate["pure_alpha_loop_absolute_response"] < 1.0e-14
    assert (
        program_certificates["bc3_prediction"]["exact_null_and_factor_identities"][
            "ordinary_difference_equals_two_q_anti_by_definition"
        ]
        is True
    )


def test_bc3_fixed_and_shrinking_ladders_are_theorem_safe_regressions(
    program_certificates,
) -> None:
    certificates = program_certificates
    oracle = certificates["bc3_oracle"]
    prediction = certificates["bc3_prediction"]
    assert oracle["s_times_updates_strictly_increasing"] is True
    assert oracle["all_loops_inside_domain"] is True
    fixed_errors = [
        abs(row["q_anti"] - expected["line_integral"])
        for row, expected in zip(
            oracle["fixed_loop_rows"], prediction["fixed_loop_line_integrals"], strict=True
        )
    ]
    shrinking_errors = [
        abs(row["scalar_diagnostic"]["q_anti"] - expected["line_integral"])
        for row, expected in zip(oracle["rows"], prediction["shrinking_loop_line_integrals"], strict=True)
    ]
    local = prediction["regression_float_view"]["heldout_density"]
    density_errors = [abs(row["scalar_diagnostic"]["density"] - local) for row in oracle["rows"]]
    assert all(right < left for left, right in zip(fixed_errors[:-1], fixed_errors[1:], strict=True))
    assert all(right < left for left, right in zip(shrinking_errors[:-1], shrinking_errors[1:], strict=True))
    assert all(right < left for left, right in zip(density_errors[:-1], density_errors[1:], strict=True))


def test_prediction_is_hash_locked_before_oracle_and_uses_no_response(
    program_certificates,
) -> None:
    certificates = program_certificates
    prediction = certificates["bc3_prediction"]
    assert certificates["bc3_pipeline_final_state"] == "VERIFIED"
    assert certificates["bc3_pipeline_event_log"] == [
        "INIT",
        "PREDICTION_LOCKED",
        "ORACLE_RUN",
        "VERIFIED",
    ]
    assert len(certificates["bc3_prediction_lock"]["lock_sha256"]) == 64
    assert prediction["prediction_uses_response"] is False
    assert prediction["response_oracle_imported"] is False


def test_ineligible_circular_and_pseudoholdout_matrix_is_complete(program_certificates) -> None:
    certificates = program_certificates
    refused = certificates["refusals"]
    assert refused["all_refused"] is True
    assert len(refused["refused"]) == 11
    assert all(refused["refused"].values())


def test_case_classifier_rejects_duplicate_or_reordered_gates(program_result) -> None:
    _, records = program_result
    from experiments.constitutive_map_3d_proof.classifier import Gate

    gates = [
        Gate(
            name=record["name"],
            natural_status=record["natural_status"],
            status=record["status"],
            requirement=record["requirement"],
            observed=record["observed"],
        )
        for record in records
        if record["record_type"] == "gate"
    ]
    with pytest.raises(RuntimeError):
        case_dispositions(gates + [gates[0]])
    with pytest.raises(RuntimeError):
        case_dispositions(list(reversed(gates)))


def test_natural_gate_set_matches_exact_ownership(natural_inputs) -> None:
    natural = natural_inputs
    assert tuple(natural) == registry_gate_names()
    assert set(natural) == {name for _, names in case_gate_ownership() for name in names}


def test_canonical_source_hash_domain_is_lf_only() -> None:
    assert canonical_source_text_bytes(b"alpha\r\nbeta\r\n") == b"alpha\nbeta\n"
    assert canonical_source_text_bytes(b"alpha\nbeta\n") == b"alpha\nbeta\n"
    with pytest.raises(ValueError, match="BOM"):
        canonical_source_text_bytes(b"\xef\xbb\xbfalpha\n")
    with pytest.raises(ValueError, match="bare CR"):
        canonical_source_text_bytes(b"alpha\rbeta\n")
    with pytest.raises(ValueError, match="UTF-8"):
        canonical_source_text_bytes(b"\xff")


def test_material_source_closure_includes_clean_cli_package_test_and_predecessors() -> None:
    clean = artifacts.clean_cli_local_module_paths()
    paths = material_source_relative_paths(clean)
    hashes = source_hashes(paths)
    assert set(clean).issubset(paths)
    assert "tests/experiments/test_constitutive_map_3d_proof.py" in paths
    assert "experiments/constitutive_map_3d_proof/run.py" in paths
    assert "experiments/constitutive_map_3d_proof/MODEL_CONTRACT.md" in paths
    assert "experiments/response_theorem_proof_program/THEOREM.md" in paths
    assert all(item["hash_domain"] == "sha256_utf8_lf_v1" for item in hashes.values())
    assert all(len(item["sha256"]) == 64 for item in hashes.values())


def test_predecessor_closure_is_recursive_path_type_and_hash_bound() -> None:
    inventories = predecessor_inventories()
    assert set(inventories) == set(artifacts.PREDECESSOR_ARTIFACT_DIRS)
    for inventory in inventories.values():
        assert inventory["entry_count"] == len(inventory["entries"])
        assert len(inventory["inventory_sha256"]) == 64
        assert all(item["type"] in {"directory", "file"} for item in inventory["entries"].values())


def test_reviewed_source_clean_module_and_predecessor_path_sets_reject_substitution(
    monkeypatch,
) -> None:
    clean = artifacts.clean_cli_local_module_paths()
    with pytest.raises(ArtifactVerificationError, match="material-source path set"):
        material_source_relative_paths((*clean, "experiments/forged.py"))
    with monkeypatch.context() as context:
        forged = dict(artifacts.PREDECESSOR_ARTIFACT_DIRS)
        forged["renamed"] = forged.pop("curvature_identity_audit")
        context.setattr(artifacts, "PREDECESSOR_ARTIFACT_DIRS", forged)
        with pytest.raises(ArtifactVerificationError, match="role/path set"):
            predecessor_inventories()


def test_recursive_inventory_rejects_nested_symlink(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    nested = root / "nested"
    target = tmp_path / "target"
    nested.mkdir(parents=True)
    target.mkdir()
    link = nested / "linked"
    try:
        link.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create the required directory symlink: {exc}")
    with pytest.raises(ArtifactVerificationError, match="link/reparse"):
        recursive_raw_inventory(root, trust_anchor=tmp_path)


def test_recursive_inventory_and_preflight_reject_link_in_ancestor_without_writing(
    tmp_path: Path,
) -> None:
    real = tmp_path / "real"
    real.mkdir()
    (real / "payload.txt").write_text("preserve\n", encoding="utf-8")
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(real, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create the required ancestor directory link: {exc}")
    before = (real / "payload.txt").read_bytes()
    with pytest.raises(ArtifactVerificationError, match="link/reparse"):
        recursive_raw_inventory(linked, trust_anchor=tmp_path)
    with pytest.raises(ArtifactGenerationRefused, match="link/reparse"):
        preflight_artifact_destination(linked / "nested" / "artifacts")
    assert (real / "payload.txt").read_bytes() == before
    assert not (real / "nested").exists()


def test_artifact_destination_refuses_source_predecessor_and_nested_content(
    tmp_path: Path,
) -> None:
    refused = [
        artifacts.EXPERIMENT_DIR / "alternate",
        artifacts.ARTIFACTS_DIR / "nested",
        next(iter(artifacts.PREDECESSOR_ARTIFACT_DIRS.values())) / "nested",
    ]
    for destination in refused:
        with pytest.raises(ArtifactGenerationRefused, match="overlap"):
            preflight_artifact_destination(destination)

    destination = tmp_path / "artifacts"
    hidden = destination / "hidden"
    hidden.mkdir(parents=True)
    (hidden / "outcome.json").write_bytes(b"{}\n")
    before = recursive_raw_inventory(destination, trust_anchor=tmp_path)
    with pytest.raises(ArtifactGenerationRefused, match="nonordinary"):
        artifacts.write_artifacts(destination)
    assert recursive_raw_inventory(destination, trust_anchor=tmp_path) == before


def test_semantic_validator_rejects_claim_registry_case_and_gate_mutations(
    program_result,
) -> None:
    summary, records = program_result
    require_semantic_pass(summary, records)
    summary_mutations = []

    claim = copy.deepcopy(summary)
    claim["claim_ceiling"] = "UNIVERSAL_CWT_CGT_ALIGNMENT_PROVED"
    summary_mutations.append(claim)

    relation = copy.deepcopy(summary)
    relation["relation_scope"] = "UNIVERSAL_ALIGNMENT"
    summary_mutations.append(relation)

    registry = copy.deepcopy(summary)
    registry["registry"]["gate_ownership"][0]["gate_names"][0] = "relabelled"
    summary_mutations.append(registry)

    cases = copy.deepcopy(summary)
    cases["case_dispositions"]["BC3"] = "SAME_CURVATURE"
    summary_mutations.append(cases)

    for mutated in summary_mutations:
        with pytest.raises(ArtifactGenerationRefused):
            require_semantic_pass(mutated, records)

    duplicate = copy.deepcopy(records)
    gate = next(item for item in duplicate if item["record_type"] == "gate")
    duplicate.append(copy.deepcopy(gate))
    failed = copy.deepcopy(records)
    failed_gate = next(item for item in failed if item["record_type"] == "gate")
    failed_gate["status"] = "fail"
    for mutated_records in (duplicate, failed):
        with pytest.raises(ArtifactGenerationRefused):
            require_semantic_pass(summary, mutated_records)


def test_claim_mutation_refuses_report_payload_write_and_status_cli(
    monkeypatch,
    tmp_path: Path,
    program_result,
) -> None:
    summary, records = program_result
    mutated = copy.deepcopy(summary)
    mutated["claim_ceiling"] = "UNIVERSAL_CWT_CGT_ALIGNMENT_PROVED"
    with pytest.raises(ArtifactGenerationRefused):
        render_report(mutated, records)

    monkeypatch.setattr(artifacts, "execute_program", lambda: (mutated, records))
    with pytest.raises(ArtifactGenerationRefused):
        expected_artifact_bytes()
    destination = tmp_path / "artifacts"
    with pytest.raises(ArtifactGenerationRefused):
        artifacts.write_artifacts(destination)
    assert not destination.exists()

    monkeypatch.setattr(proof_run, "execute_program", lambda: (mutated, records))
    result = CliRunner().invoke(proof_run.app, ["status"])
    assert result.exit_code == 2
    assert "SEMANTIC_VALIDATION_FAILED" in result.stdout + result.stderr
    assert "PASS_INTERNAL_ANALYTIC" not in result.stdout + result.stderr


def test_diagnostic_drift_blocks_publication_and_cli_but_not_formal_disposition(
    monkeypatch,
    tmp_path: Path,
    program_result,
) -> None:
    summary, records = program_result
    mutated = copy.deepcopy(summary)
    mutated["disposition"] = "BLOCKED_DIAGNOSTIC_DRIFT"
    mutated["publication_blockers"] = ["bc3_scalar_non_authoritative_diagnostic"]
    mutated["metrics"]["bc3_scalar_non_authoritative_diagnostic"]["assessment"][
        "diagnostic_status"
    ] = "BLOCKED_DIAGNOSTIC_DRIFT"
    assert mutated["formal_disposition"] == "PASS_INTERNAL_ANALYTIC"
    with pytest.raises(ArtifactGenerationRefused):
        require_semantic_pass(mutated, records)
    with pytest.raises(ArtifactGenerationRefused):
        render_report(mutated, records)

    monkeypatch.setattr(artifacts, "execute_program", lambda: (mutated, records))
    with pytest.raises(ArtifactGenerationRefused):
        expected_artifact_bytes()
    destination = tmp_path / "artifacts"
    with pytest.raises(ArtifactGenerationRefused):
        artifacts.write_artifacts(destination)
    assert not destination.exists()

    monkeypatch.setattr(proof_run, "execute_program", lambda: (mutated, records))
    status = CliRunner().invoke(proof_run.app, ["status"])
    assert status.exit_code == 2
    assert "PASS_INTERNAL_ANALYTIC" not in status.stdout + status.stderr


def test_artifact_generation_refuses_failed_gate_without_writing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary, records = execute_program(gate_overrides={registry_gate_names()[0]: False})
    monkeypatch.setattr(artifacts, "execute_program", lambda: (summary, records))
    destination = tmp_path / "artifacts"
    with pytest.raises(ArtifactGenerationRefused):
        artifacts.write_artifacts(destination)
    assert not destination.exists()


def test_frozen_artifacts_verify_strict_lf_and_checksum_closure() -> None:
    result = verify_artifacts()
    assert result == {
        "status": "PASS_INTERNAL_ANALYTIC",
        "evidence_status": "NO_EMPIRICAL_EVIDENCE",
        "relation_scope": "MODEL_SPECIFIC_RELATIONS_ONLY",
        "artifact_count": 5,
        "source_count": result["source_count"],
        "clean_cli_local_module_count": result["clean_cli_local_module_count"],
        "predecessor_count": 3,
    }
    assert result["source_count"] >= result["clean_cli_local_module_count"]
    for path in artifacts.ARTIFACTS_DIR.iterdir():
        assert b"\r" not in path.read_bytes()
    checksums = json.loads((artifacts.ARTIFACTS_DIR / "CHECKSUMS.json").read_text(encoding="utf-8"))
    assert set(checksums["files"]) == {
        "PROVENANCE.json",
        "REPORT.md",
        "records.json",
        "summary.json",
    }


def test_artifact_verifier_rejects_content_and_nested_addition(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    shutil.copytree(artifacts.ARTIFACTS_DIR, destination)
    (destination / "summary.json").write_bytes(b"{}\n")
    with pytest.raises(ArtifactVerificationError):
        verify_artifacts(destination)
    shutil.rmtree(destination)
    shutil.copytree(artifacts.ARTIFACTS_DIR, destination)
    hidden = destination / "hidden"
    hidden.mkdir()
    (hidden / "outcome.json").write_bytes(b"{}\n")
    with pytest.raises(ArtifactVerificationError):
        verify_artifacts(destination)


def test_cli_status_run_and_verify_are_fail_closed(tmp_path: Path, monkeypatch) -> None:
    runner = CliRunner()
    status = runner.invoke(proof_run.app, ["status"])
    assert status.exit_code == 0, status.stdout
    assert "PASS_INTERNAL_ANALYTIC" in status.stdout
    verify = runner.invoke(proof_run.app, ["verify"])
    assert verify.exit_code == 0, verify.stdout
    assert "MODEL_SPECIFIC_RELATIONS_ONLY" in verify.stdout

    monkeypatch.setattr(artifacts, "ARTIFACTS_DIR", tmp_path / "unused")
    assert "confirm" not in {command.name for command in proof_run.app.registered_commands}

from __future__ import annotations

import copy
import inspect
import json
import os
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from cwt.cgt.models import BranchState
from cwt.cgt.open_system import apply_local_open_step
from experiments.benchmark_d_open_response_proof import (
    artifacts as artifact_module,
    theorem as theorem_module,
)
from experiments.benchmark_d_open_response_proof.adapter import (
    affine_population_components,
    analytic_d0_kernel,
    authored_probability_inactivity,
    benchmark_d_three_step_diagnostics,
    constant_projective_reference_certificate,
    core_affine_equivalence,
    core_config,
    core_d0_state,
    core_readout_certificate,
    mean_position_operator,
    phase10_benchmark_c_two_step_diagnostics,
)
from experiments.benchmark_d_open_response_proof.artifacts import (
    CLEAN_CLI_LOCAL_MODULE_PATHS,
    SOURCE_PATHS,
    ArtifactGenerationRefused,
    ArtifactVerificationError,
    assert_clean_cli_source_closure,
    canonical_source_text_bytes,
    phase10_identity_records,
    require_semantic_pass,
    source_hashes,
    verify_artifacts,
    write_artifacts,
)
from experiments.benchmark_d_open_response_proof.contract import (
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    FORMAL_RESPONSE_CURVATURE,
    MODEL_CONTRACT,
)
from experiments.benchmark_d_open_response_proof.exact_oracle import (
    exact_margin_certificate,
    exact_response_oracle,
)
from experiments.benchmark_d_open_response_proof.fixed_branch import (
    ContractionCertificateError,
    analytic_response_curvature,
    contraction_certificate,
    fixed_branch_bundle,
    fixed_branch_certificates,
    numerical_response_curvature,
)
from experiments.benchmark_d_open_response_proof.response import (
    core_cycle_equivalence,
    d0_path_is_within_contract,
    fixed_loop_refinement,
    loop_domain_diagnostics,
    null_control_diagnostics,
    orientation_pair,
    reverse_loop,
    shrinking_loop_refinement,
    square_loop,
)
from experiments.benchmark_d_open_response_proof.run import app
from experiments.benchmark_d_open_response_proof.theorem import (
    Gate,
    derive_case_dispositions,
    execute_program,
)

RUNNER = CliRunner()


@pytest.fixture(scope="module")
def program_result() -> tuple[dict[str, object], list[dict[str, object]]]:
    return execute_program()


def test_frozen_contract_and_named_core_binding() -> None:
    contract = MODEL_CONTRACT
    assert contract.benchmark_id == "benchmark_d"
    assert contract.branch_id == "D0"
    assert contract.center_bias == Fraction(3, 100)
    assert contract.center_diffusion == Fraction(9, 40)
    assert contract.depolarizing == Fraction(1, 125)
    assert contract.dephasing == Fraction(3, 10)
    assert contract.coherent_scale == 0
    assert contract.site_potential_scale == 0
    assert contract.observable_name == "mean_position"
    assert apply_local_open_step.__module__ == "cwt.cgt.open_system"
    assert np.array_equal(np.diag(mean_position_operator()).real, np.arange(1, 6))


@pytest.mark.parametrize(
    ("bias", "diffusion"),
    [(0.01, 0.205), (0.01, 0.245), (0.05, 0.205), (0.05, 0.245), (0.03, 0.225)],
)
def test_experiment_kernel_equals_named_d0_kernel(bias: float, diffusion: float) -> None:
    state = core_d0_state(bias, diffusion)
    assert np.array_equal(state.kernel, analytic_d0_kernel(bias, diffusion))
    assert state.extras == {"b": bias, "d": diffusion}


def test_core_kraus_affine_projection_and_fixed_api_equivalence() -> None:
    result = core_affine_equivalence()
    assert result["max_kernel_error"] == 0.0
    assert result["max_affine_error"] <= 5e-14
    assert result["max_kraus_tp_error"] <= 5e-14
    assert result["max_projection_delta"] <= 5e-13
    assert result["max_fixed_point_api_error"] <= 2e-11
    assert core_cycle_equivalence()["absolute_error"] <= 5e-10
    assert authored_probability_inactivity() <= 1e-15


def test_exact_clip_support_rescale_sqrt_and_contraction_margins() -> None:
    margins = exact_margin_certificate()
    assert margins["k_plus_min"]["fraction"] == "43/200"
    assert margins["k_plus_max"]["fraction"] == "59/200"
    assert margins["k_minus_min"]["fraction"] == "31/200"
    assert margins["k_minus_max"]["fraction"] == "47/200"
    assert margins["clip_margin"]["fraction"] == "27/200"
    assert margins["minimum_active_kernel_entry"]["fraction"] == "31/200"
    assert margins["maximum_sum_term"]["fraction"] == "1791/25000"
    assert margins["rescale_margin"]["fraction"] == "22709/25000"
    assert margins["sqrt_radicand_margin"]["fraction"] == "23209/25000"
    assert margins["global_trace_and_l1_contraction"]["fraction"] == "124/125"
    assert margins["depolarizing_full_rank_floor"]["fraction"] == "1/625"
    assert margins["maximum_exact_tp_error"]["fraction"] == "0/1"
    assert all(item["fraction"] == "1/1" for item in margins["center_source_tp_totals"])


def test_true_fixed_branch_is_full_rank_varying_and_residual_certified() -> None:
    result = fixed_branch_certificates()
    assert result["max_fixed_residual_l1"] <= 1e-14
    assert result["banach_error_upper_bound_l1"] <= 2e-12
    assert result["max_trace_error"] <= 2e-14
    assert result["global_depolarizing_eigenvalue_floor"] == 1.0 / 625.0
    assert result["sampled_minimum_fixed_eigenvalue"] >= 0.14
    assert result["sampled_fixed_branch_variation_l2"] >= 0.05
    assert result["sampled_mesh_points_per_axis"] == 5.0
    assert result["max_raw_fixed_step_delta_fro"] <= 1e-14


def test_true_fixed_branch_does_not_use_authored_stationary_probability() -> None:
    bundle = fixed_branch_bundle(0.03, 0.225)
    state = core_d0_state(0.03, 0.225)
    assert np.linalg.norm(bundle.population - state.p) > 0.1
    source = inspect.getsource(fixed_branch_bundle)
    assert "stationary_from_row_stochastic" not in source
    assert "np.linalg.solve" in source


def test_exact_fraction_oracle_is_recomputed_and_matches_formal_value() -> None:
    oracle = exact_response_oracle()
    assert oracle.matches_formal_fraction
    assert oracle.response_curvature_bd == FORMAL_RESPONSE_CURVATURE
    assert sum(oracle.fixed_population) == 1
    assert min(oracle.fixed_population) > 0
    assert oracle.response_curvature_bd < 0
    assert len(str(oracle.response_curvature_bd.numerator)) > 50


def test_float_analytic_and_independent_numerical_curl_match_exact_oracle() -> None:
    exact = float(exact_response_oracle().response_curvature_bd)
    analytic = analytic_response_curvature(0.03, 0.225)
    numerical = numerical_response_curvature()
    assert analytic == pytest.approx(exact, abs=1e-8)
    assert numerical == pytest.approx(exact, abs=1e-4)
    assert exact < -500.0


def test_global_contraction_certificate_and_zero_depolarizing_refusal() -> None:
    certificate = contraction_certificate(1.0 / 125.0)
    assert certificate["factor"] == 124.0 / 125.0
    with pytest.raises(ContractionCertificateError):
        contraction_certificate(0.0)


def test_fixed_loop_converges_at_one_over_n() -> None:
    result = fixed_loop_refinement()
    assert result["line_integral_target"] < 0.0
    assert -1.05 <= result["tail_log_slope"] <= -0.95
    assert result["tail_scaled_error_ratio"] <= 1.02
    errors = [row["absolute_error"] for row in result["rows"]]
    assert all(right < left for left, right in zip(errors[-4:-1], errors[-3:]))
    assert result["rows"][-1]["q_anti"] < 0.0


def test_shrinking_loop_requires_growing_n_times_s_and_converges_to_curl() -> None:
    result = shrinking_loop_refinement()
    rows = result["rows"]
    ns = [row["updates_times_side"] for row in rows]
    assert [row["side"] for row in rows] == [0.04, 0.02, 0.01, 0.005]
    assert max(row["side"] for row in rows) <= 0.04
    assert np.allclose(np.asarray(ns[1:]) / np.asarray(ns[:-1]), 2.0)
    assert max(result["successive_error_ratios"]) <= 0.60
    assert result["finest_relative_density_error"] <= 0.10
    assert result["max_centering_budget_to_observed_density_error"] <= 1e-3
    assert result["numerical_tolerances_selected_during_harness_development"] is True
    assert rows[-1]["response_density"] < 0.0


def test_every_registered_loop_is_in_box_and_out_of_domain_mutation_fails() -> None:
    diagnostics = loop_domain_diagnostics()
    assert diagnostics["all_registered_loops_contained"] is True
    assert all(row["contained"] and row["side"] <= 0.04 for row in diagnostics["rows"])
    escaped = square_loop((0.03, 0.225), 0.04, 8)
    escaped[3, 0] = 0.009
    assert d0_path_is_within_contract(escaped) is False


def test_right_endpoint_exact_reverse_and_single_close_conventions() -> None:
    path = square_loop((0.03, 0.225), 0.02, 7)
    reverse = reverse_loop(path)
    assert len(path) == 29
    assert np.array_equal(path[0], path[-1])
    assert np.array_equal(reverse, path[::-1])
    pair = orientation_pair(0.02, 7)
    assert pair["updates_per_cycle"] == 28.0


def test_identity_constant_branch_and_benchmark_c_true_fixed_nulls() -> None:
    result = null_control_diagnostics()
    assert abs(result["identity_readout"]["q_anti"]) <= 1e-10
    assert abs(result["constant_branch"]["q_anti"]) <= 1e-12
    benchmark_c = result["benchmark_c"]
    assert benchmark_c["branch_id"] == "C0"
    assert benchmark_c["max_kernel_column_error"] <= 5e-15
    assert benchmark_c["max_true_fixed_to_identity_over_three_fro"] <= 5e-14
    assert abs(benchmark_c["centered_primary_cycle_sum"]) <= 1e-12


def test_constant_projective_reference_is_exactly_constant_and_zero_curvature() -> None:
    result = constant_projective_reference_certificate()
    assert result["definition_sha256"] == ("97fcd1ee64b25bf2c437a367ce6b9699df233cbe177a65bc51231ee68fd4ee02")
    assert result["maximum_probability_variation"] == 0.0
    assert result["maximum_phase_variation"] == 0.0
    assert result["maximum_normalized_psi_variation"] == 0.0
    assert result["psi_norm_error"] == 0.0
    assert result["maximum_executed_p_to_declared_error"] == 0.0
    assert result["maximum_executed_theta_to_declared_error"] == 0.0
    assert result["maximum_executed_psi_to_declared_gauge_aligned_error"] == 0.0
    assert result["maximum_executed_projector_to_declared_error"] == 0.0
    assert result["omega_bd_exact_fraction"] == "0/1"
    assert result["authored_stationary_probability_used_as_projective_branch"] is False
    assert result["channel_equivalence_error"] == 0.0


def test_core_readout_is_bound_to_named_mean_position_operator() -> None:
    result = core_readout_certificate()
    assert result["observable_name"] == "mean_position"
    assert result["core_function"] == "cwt.cgt.open_system.observable_operator"
    assert result["expected_diagonal"] == [1, 2, 3, 4, 5]
    assert result["maximum_absolute_error"] == 0.0
    assert result["hermiticity_error"] == 0.0


def test_tracked_phase10_is_two_step_benchmark_c_and_diagnostic_is_separate() -> None:
    phase10 = phase10_benchmark_c_two_step_diagnostics()
    assert phase10["benchmark_id"] == "benchmark_c"
    assert phase10["branch_id"] == "C0"
    assert phase10["recorded_branch_steps"] == 2
    assert phase10["historical_entry_explicit_branch_steps"] == 2
    assert phase10["current_library_default_branch_steps"] == 3
    assert phase10["historical_entry_script"] == "scripts/cgt/run_phase10_analysis.py"
    assert phase10["current_recomputation_implementation"] == "cwt/cgt/analysis/phase10_analysis.py"
    assert phase10["recorded_dephasing_gamma"] == 0.2
    assert phase10["surrogate_fixed_residual_fro"] == pytest.approx(0.04111010278213111)
    assert phase10["surrogate_to_true_fixed_fro"] == pytest.approx(0.7267336696958832)
    assert phase10["historical_provenance_claim"].endswith("not_original_run_proof")

    benchmark_d = benchmark_d_three_step_diagnostics()
    assert benchmark_d["benchmark_id"] == "benchmark_d"
    assert benchmark_d["branch_steps"] == 3
    assert benchmark_d["relationship_to_tracked_phase10"] == "separate_diagnostic_not_validation"


def test_complete_case_disposition_mapping(program_result) -> None:
    summary, records = program_result
    assert summary["case_dispositions"] == EXPECTED_CASE_DISPOSITIONS
    actual = {
        record["case_id"]: record["disposition"]
        for record in records
        if record["record_type"] == "case_disposition"
    }
    assert actual == EXPECTED_CASE_DISPOSITIONS


@pytest.mark.parametrize("case_id", list(EXPECTED_CASE_DISPOSITIONS))
def test_every_case_disposition_fails_when_a_registered_gate_fails(case_id: str, program_result) -> None:
    summary, _records = program_result
    gates = [Gate(gate["name"], gate["requirement"], gate["status"] == "pass") for gate in summary["gates"]]
    failed_name = CASE_GATE_MAP[case_id][0]
    mutated = [
        Gate(gate.name, gate.requirement, False if gate.name == failed_name else gate.passed)
        for gate in gates
    ]
    dispositions = derive_case_dispositions(mutated)
    assert dispositions[case_id].startswith("FAIL_INTERNAL_ANALYTIC[")
    assert failed_name in dispositions[case_id]


def test_case_registry_rejects_unknown_gate(monkeypatch: pytest.MonkeyPatch, program_result) -> None:
    summary, _records = program_result
    gates = [Gate(gate["name"], gate["requirement"], gate["status"] == "pass") for gate in summary["gates"]]
    mutated = dict(CASE_GATE_MAP)
    mutated["C1"] = ("undeclared_gate",)
    monkeypatch.setattr(theorem_module, "CASE_GATE_MAP", mutated)
    with pytest.raises(AssertionError, match="registry mismatch"):
        derive_case_dispositions(gates)


def test_live_gate_registry_exactly_equals_case_registry(program_result) -> None:
    summary, _records = program_result
    live = {gate["name"] for gate in summary["gates"]}
    registered = {name for names in CASE_GATE_MAP.values() for name in names}
    assert live == registered
    assert len(live) == len(summary["gates"])
    assert all(len(names) == len(set(names)) for names in CASE_GATE_MAP.values())


@pytest.mark.parametrize(
    "gate_name",
    sorted({name for names in CASE_GATE_MAP.values() for name in names}),
)
def test_every_live_gate_failure_blocks_a_case_overall_artifacts_and_cli(
    gate_name: str,
    program_result,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    summary, records = program_result
    gates = [Gate(gate["name"], gate["requirement"], gate["name"] != gate_name) for gate in summary["gates"]]
    dispositions = derive_case_dispositions(gates)
    dependent = [case_id for case_id, names in CASE_GATE_MAP.items() if gate_name in names]
    assert dependent
    assert all(dispositions[case_id].startswith("FAIL_INTERNAL_ANALYTIC[") for case_id in dependent)

    failed_summary = copy.deepcopy(summary)
    failed_summary["all_gates_pass"] = False
    failed_summary["failed_gates"] = [gate_name]
    failed_summary["disposition"] = "FAIL_INTERNAL_ANALYTIC"
    failed_summary["case_dispositions"] = dispositions
    for gate in failed_summary["gates"]:
        if gate["name"] == gate_name:
            gate["status"] = "fail"
    with pytest.raises(ArtifactGenerationRefused, match="semantic proof gates"):
        require_semantic_pass(failed_summary)

    from experiments.benchmark_d_open_response_proof import run as run_module

    monkeypatch.setattr(run_module, "execute_program", lambda: (failed_summary, records))
    status = RUNNER.invoke(app, ["status"])
    assert status.exit_code != 0
    assert "PASS_INTERNAL_ANALYTIC" not in status.output


def test_readout_mutation_fails_core_case_and_semantic_disposition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.benchmark_d_open_response_proof import adapter

    original = adapter.observable_operator

    def altered(*args, **kwargs):
        operator = original(*args, **kwargs).copy()
        operator[0, 0] += 0.25
        return operator

    theorem_module._execute_program_cached.cache_clear()
    monkeypatch.setattr(adapter, "observable_operator", altered)
    try:
        summary, _records = theorem_module.execute_program()
        assert "named_core_readout_binding" in summary["failed_gates"]
        assert summary["case_dispositions"]["C1"].startswith("FAIL_INTERNAL_ANALYTIC[")
        assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    finally:
        theorem_module._execute_program_cached.cache_clear()


@pytest.mark.parametrize("mutation", ("nonuniform_p", "nonzero_theta"))
def test_executed_constant_reference_mutation_blocks_semantic_artifact_and_cli_pass(
    mutation: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from experiments.benchmark_d_open_response_proof import adapter, run as run_module

    original = adapter.theorem_d0_state

    def altered(bias: float, diffusion: float) -> BranchState:
        state = original(bias, diffusion)
        p = state.p.copy()
        theta = state.theta.copy()
        if mutation == "nonuniform_p":
            p = np.asarray((0.1, 0.1, 0.1, 0.1, 0.6))
        else:
            theta = np.full(5, 0.7)
        return BranchState(p=p, theta=theta, kernel=state.kernel, extras=dict(state.extras))

    theorem_module._execute_program_cached.cache_clear()
    monkeypatch.setattr(adapter, "theorem_d0_state", altered)
    output = tmp_path / mutation
    monkeypatch.setattr(
        run_module,
        "write_artifacts",
        lambda: artifact_module.write_artifacts(output),
    )
    try:
        summary, records = theorem_module.execute_program()
        assert "constant_projective_reference_zero" in summary["failed_gates"]
        assert summary["case_dispositions"]["C3"].startswith("FAIL_INTERNAL_ANALYTIC[")
        assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
        reference = next(
            record for record in records if record["record_type"] == "constant_projective_reference"
        )
        if mutation == "nonuniform_p":
            assert reference["maximum_executed_p_to_declared_error"] > 0.0
            assert reference["maximum_executed_projector_to_declared_error"] > 0.0
        else:
            assert reference["maximum_executed_theta_to_declared_error"] == pytest.approx(0.7)

        with pytest.raises(ArtifactGenerationRefused, match="semantic proof gates"):
            artifact_module.write_artifacts(output)
        assert not output.exists()
        for command in ("status", "run", "verify"):
            result = RUNNER.invoke(app, [command])
            assert result.exit_code != 0
            assert "PASS_INTERNAL_ANALYTIC" not in result.output
    finally:
        theorem_module._execute_program_cached.cache_clear()


def test_program_pass_is_internal_analytic_only(program_result) -> None:
    summary, _records = program_result
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert summary["central_empirical_external_claim_status"] == "PROOF_INCOMPLETE"
    assert summary["numerics_are_not_the_analytic_proof"] is True
    assert summary["no_study_pass"] is True
    assert summary["failed_gates"] == []
    assert all(gate["status"] == "pass" for gate in summary["gates"])
    ceiling = summary["claim_ceiling"].lower()
    for required in ("internal synthetic", "not the full scheduler", "physical time", "cgt alignment"):
        assert required in ceiling


def test_artifacts_are_strict_closed_and_tamper_evident(tmp_path: Path) -> None:
    output = tmp_path / "artifacts"
    paths = write_artifacts(output)
    assert set(paths) == {
        "CHECKSUMS.json",
        "PROVENANCE.json",
        "REPORT.md",
        "records.json",
        "summary.json",
    }
    result = verify_artifacts(output)
    assert result["status"] == "PASS_INTERNAL_ANALYTIC"
    for path in paths.values():
        assert b"\r" not in path.read_bytes()
    provenance = json.loads(paths["PROVENANCE.json"].read_text(encoding="utf-8"))
    assert provenance["no_empirical_or_external_data"] is True
    assert provenance["no_full_scheduler_or_physical_time_claim"] is True
    assert provenance["no_cgt_alignment_claim"] is True
    assert provenance["clean_cli_local_module_paths"] == list(CLEAN_CLI_LOCAL_MODULE_PATHS)
    assert provenance["phase10_identity_records"] == phase10_identity_records()
    assert "experiments/response_theorem_proof_program/THEOREM.md" in provenance["source_hashes"]
    paths["summary.json"].write_bytes(b"{}\n")
    with pytest.raises(ArtifactVerificationError, match="content mismatch"):
        verify_artifacts(output)


def test_artifact_verifier_rejects_nested_or_unexpected_entries(tmp_path: Path) -> None:
    output = tmp_path / "artifacts"
    write_artifacts(output)
    hidden = output / "hidden"
    hidden.mkdir()
    (hidden / "outcome.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ArtifactVerificationError, match="closure mismatch"):
        verify_artifacts(output)


def test_source_hash_domain_is_lf_crlf_equivalent_and_fail_closed() -> None:
    assert canonical_source_text_bytes(b"alpha\nbeta\n") == b"alpha\nbeta\n"
    assert canonical_source_text_bytes(b"alpha\r\nbeta\r\n") == b"alpha\nbeta\n"
    with pytest.raises(ValueError, match="bare CR"):
        canonical_source_text_bytes(b"alpha\rbeta")
    with pytest.raises(ValueError, match="BOM"):
        canonical_source_text_bytes(b"\xef\xbb\xbfalpha\n")
    with pytest.raises(ValueError, match="UTF-8"):
        canonical_source_text_bytes(b"\xff")


def test_clean_cli_local_source_closure_is_exact_and_tamper_evident(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    actual = assert_clean_cli_source_closure()
    assert actual == CLEAN_CLI_LOCAL_MODULE_PATHS
    for required in (
        "cwt/cgt/__init__.py",
        "cwt/cgt/runner.py",
        "cwt/cgt/continuation.py",
        "cwt/cgt/loop_protocols.py",
        "cwt/geometry/branch_distance.py",
        "cwt/geometry/coherence.py",
        "cwt/geometry/psi.py",
        "cwt/geometry/stats.py",
    ):
        assert required in actual
    monkeypatch.setattr(
        artifact_module,
        "CLEAN_CLI_LOCAL_MODULE_PATHS",
        CLEAN_CLI_LOCAL_MODULE_PATHS[:-1],
    )
    with pytest.raises(ArtifactVerificationError, match="source closure mismatch"):
        artifact_module.assert_clean_cli_source_closure()


def test_source_and_phase10_byte_hash_closure_is_path_bound() -> None:
    hashes = source_hashes()
    assert len(hashes) == len(SOURCE_PATHS)
    assert list(hashes) == sorted(hashes)
    assert "cwt/cgt/analysis/phase10_analysis.py" in hashes
    assert "scripts/cgt/run_phase10_analysis.py" in hashes
    assert "experiments/response_theorem_proof_program/THEOREM.md" in hashes
    identities = phase10_identity_records()
    assert identities == {
        "cgt_benchmarks/results/benchmark_C_ring/benchmark_c_phase10.json": {
            "role": "tracked_historical_phase10_result_json_with_branch_steps_2",
            "hash_domain": "sha256_raw_bytes_v1",
            "sha256": "7e7ca8d8a81637910a0c60604f016e4cdf7bfeb4845d7536ed86b4cec464191b",
            "git_blob_oid": "1c7b7c5556956434be22a6ca809cf1c3e55c80b2",
            "identity_bytes_equal_git_index_blob": True,
        },
        "cwt/cgt/analysis/phase10_analysis.py": {
            "role": "current_phase10_recomputation_implementation_module",
            "hash_domain": "sha256_utf8_lf_v1",
            "sha256": "62af7092c77101df9b24ea5e56137b140608bbc1d7e5e6d9077d0208e9c4cc70",
            "git_blob_oid": "162bc7fde71f80e6f105d49765bb20c8e0c265ca",
            "identity_bytes_equal_git_index_blob": True,
        },
        "scripts/cgt/run_phase10_analysis.py": {
            "role": "historical_phase10_entry_script_explicitly_selecting_branch_steps_2",
            "hash_domain": "sha256_utf8_lf_v1",
            "sha256": "19c58910cc90833eacaefbec81c895b5ca5b83a351efe770451cbd6e2dbbfee2",
            "git_blob_oid": "eb732dba6c1704c4c9c1ba4c7beb9bb1ff23a0f5",
            "identity_bytes_equal_git_index_blob": True,
        },
    }


@pytest.mark.parametrize(
    "relative",
    ["cwt/cgt/analysis/phase10_analysis.py", "scripts/cgt/run_phase10_analysis.py"],
)
def test_phase10_python_identity_canonical_bytes_equal_git_index_blob(relative: str) -> None:
    oid, index_blob = artifact_module._git_index_blob(relative)
    raw = (artifact_module.SIM_ROOT / relative).read_bytes()
    assert len(oid) == 40
    assert canonical_source_text_bytes(raw) == index_blob
    assert canonical_source_text_bytes(index_blob.replace(b"\n", b"\r\n")) == index_blob
    with pytest.raises(ArtifactVerificationError, match="differs from Git index blob"):
        artifact_module._canonical_text_identity_bytes(raw + b"# semantic mutation\n", index_blob, relative)


def test_artifact_verification_invalidates_on_source_hash_tamper(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "artifacts"
    write_artifacts(output)
    original = artifact_module.source_hashes

    def altered_hashes() -> dict[str, str]:
        result = original()
        first = next(iter(result))
        result[first] = "0" * 64
        return result

    monkeypatch.setattr(artifact_module, "source_hashes", altered_hashes)
    with pytest.raises(ArtifactVerificationError, match="content mismatch"):
        verify_artifacts(output)


def test_phase10_three_identity_byte_binding_tamper_invalidates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = tmp_path / "artifacts"
    write_artifacts(output)
    original = artifact_module.phase10_identity_records

    def altered_records() -> dict[str, dict[str, object]]:
        result = original()
        result["scripts/cgt/run_phase10_analysis.py"]["sha256"] = "0" * 64
        return result

    monkeypatch.setattr(artifact_module, "phase10_identity_records", altered_records)
    with pytest.raises(ArtifactVerificationError, match="content mismatch"):
        verify_artifacts(output)


def test_verifier_passes_from_exact_git_checkout_index_reconstruction(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[3].resolve()
    # Keep the prefix short enough for deeply nested tracked paths on Windows.
    checkout = (tmp_path.parent / "idx").resolve()
    with pytest.raises(ValueError):
        checkout.relative_to(repo_root)
    checkout.mkdir()
    prefix = checkout.as_posix() + "/"
    git_dir = Path(
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--absolute-git-dir"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    ).resolve()
    index_value = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--git-path", "index"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    index_path = Path(index_value)
    if not index_path.is_absolute():
        index_path = (repo_root / index_path).resolve()
    assert git_dir.is_dir()
    assert index_path.is_file()
    git_env = os.environ.copy()
    git_env.update(
        {
            "GIT_DIR": str(git_dir),
            "GIT_INDEX_FILE": str(index_path),
            "GIT_WORK_TREE": str(checkout),
        }
    )
    subprocess.run(
        ["git", "-C", str(repo_root), "checkout-index", "--all", f"--prefix={prefix}"],
        check=True,
        capture_output=True,
        env=git_env,
    )
    assert not (checkout / ".git").exists()
    env = git_env.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONPATH"] = str(checkout / "cwt-sim")
    command = [
        sys.executable,
        "-m",
        "experiments.benchmark_d_open_response_proof.run",
        "verify",
    ]
    result = subprocess.run(
        command,
        cwd=checkout / "cwt-sim",
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE" in result.stdout

    unbound_env = env.copy()
    for variable in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        unbound_env.pop(variable)
    unbound = subprocess.run(
        [
            *command,
        ],
        cwd=checkout / "cwt-sim",
        env=unbound_env,
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert unbound.returncode != 0
    assert "cannot resolve Git index blob" in unbound.stdout + unbound.stderr


def test_artifact_write_verify_and_cli_fail_closed_on_semantic_gate_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, program_result
) -> None:
    summary, records = program_result
    existing = tmp_path / "existing"
    artifact_module.write_artifacts(existing)
    failed_summary = copy.deepcopy(summary)
    failed_summary["all_gates_pass"] = False
    failed_summary["failed_gates"] = ["named_core_readout_binding"]
    failed_summary["disposition"] = "FAIL_INTERNAL_ANALYTIC"
    failed_summary["case_dispositions"]["C1"] = "FAIL_INTERNAL_ANALYTIC[named_core_readout_binding]"
    for gate in failed_summary["gates"]:
        if gate["name"] == "named_core_readout_binding":
            gate["status"] = "fail"

    output = tmp_path / "refused"
    monkeypatch.setattr(artifact_module, "execute_program", lambda: (failed_summary, records))
    with pytest.raises(ArtifactGenerationRefused, match="semantic proof gates"):
        artifact_module.write_artifacts(output)
    assert not output.exists()
    with pytest.raises(ArtifactGenerationRefused, match="semantic proof gates"):
        artifact_module.verify_artifacts(existing)

    from experiments.benchmark_d_open_response_proof import run as run_module

    monkeypatch.setattr(run_module, "write_artifacts", lambda: artifact_module.write_artifacts(output))
    monkeypatch.setattr(
        run_module,
        "verify_artifacts",
        lambda: artifact_module.verify_artifacts(existing),
    )
    monkeypatch.setattr(run_module, "execute_program", lambda: (failed_summary, records))
    for command in ("status", "run", "verify"):
        result = RUNNER.invoke(app, [command])
        assert result.exit_code != 0
        assert "PASS_INTERNAL_ANALYTIC" not in result.output


def test_standalone_cli_status_run_and_verify(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    status = RUNNER.invoke(app, ["status"])
    assert status.exit_code == 0, status.output
    assert "PASS_INTERNAL_ANALYTIC" in status.output
    assert "NO_EMPIRICAL_EVIDENCE" in status.output

    from experiments.benchmark_d_open_response_proof import artifacts, run as run_module

    output = tmp_path / "artifacts"
    monkeypatch.setattr(run_module, "EXPERIMENT_DIR", tmp_path)
    monkeypatch.setattr(run_module, "write_artifacts", lambda: artifacts.write_artifacts(output))
    run = RUNNER.invoke(app, ["run"])
    assert run.exit_code == 0, run.output
    assert "PASS_INTERNAL_ANALYTIC / NO_EMPIRICAL_EVIDENCE" in run.output
    assert not (tmp_path / "results").exists()


def test_config_has_no_coherent_or_site_term_and_dephasing_is_fixed() -> None:
    config = core_config()
    assert config.coherent_scale == 0.0
    assert config.site_potential_scale == 0.0
    assert config.dephasing_values == (0.3,)
    assert config.dt == 0.18
    assert config.edge_jump_scale == 0.20
    assert config.depolarizing == 0.008
    matrix, offset = affine_population_components(0.03, 0.225)
    assert matrix.shape == (5, 5)
    assert np.all(offset == pytest.approx(1.0 / 625.0))

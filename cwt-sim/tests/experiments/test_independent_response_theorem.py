from __future__ import annotations

import hashlib
import inspect
import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.loop_protocols import run_single_loop
from cwt.cgt.models import LoopConfig
from experiments.independent_response_theorem import run
from experiments.independent_response_theorem.provenance import (
    PRE_CORRECTION_ARTIFACT_SHA256,
    PRE_CORRECTION_CRLF_EXECUTION,
    PRE_CORRECTION_SOURCE_BUNDLE_SHA256,
    SOURCE_PATHS,
    SOURCE_TEXT_HASH_DOMAIN,
    SourceTextIntegrityError,
    build_source_manifest,
    canonical_source_text_bytes,
    source_bundle_payload,
    source_bundle_sha256,
    source_text_sha256,
    verify_source_manifest,
)
from experiments.independent_response_theorem.response import (
    calculate_response_trace,
    circulation_current,
    circulation_phase_gradient,
)
from experiments.independent_response_theorem.theorem import (
    DEFAULT_CONFIG,
    evaluate_loop,
    execute_protocol,
)

RUNNER = CliRunner()


@pytest.fixture(scope="module")
def protocol_result() -> tuple[dict, list[dict]]:
    return execute_protocol(DEFAULT_CONFIG)


def test_response_api_is_geometry_blind_and_preserves_legacy_mean() -> None:
    parameters = tuple(inspect.signature(calculate_response_trace).parameters)
    assert parameters == (
        "branch_states",
        "path",
        "phase_relaxation",
        "current_phase_gain",
    )
    assert not {"orientation", "signed_flux", "omega", "phi"}.intersection(parameters)

    config = LoopConfig(
        shape="square",
        steps_per_segment=24,
        phase_relaxation=0.35,
        current_phase_gain=0.45,
    )
    legacy = run_single_loop(
        benchmark=get_benchmark("benchmark_c"),
        center=(0.0, 0.0),
        side=0.08,
        orientation="ccw",
        config=config,
    )
    local = evaluate_loop(
        center=(0.0, 0.0),
        side=0.08,
        steps_per_segment=24,
        orientation="ccw",
        phase_relaxation=0.35,
        current_phase_gain=0.45,
    )
    assert local.response.legacy_mean_response == pytest.approx(legacy["response"], abs=1e-15)
    assert local.response.discrete_cycle_sum_surrogate == pytest.approx(
        local.response.legacy_mean_response * local.response.path_length,
        abs=1e-14,
    )
    assert local.response.max_lag_recurrence_residual <= 5e-15


def test_exact_circulation_gradient_matches_centered_difference() -> None:
    state = get_benchmark("benchmark_c").branch_state_fn(0.18, 0.04)
    analytic = circulation_phase_gradient(
        state.p,
        state.theta,
        state.kernel,
        current_phase_gain=0.45,
    )
    numerical = np.zeros(3, dtype=float)
    step = 1e-6
    for index in range(3):
        theta_plus = state.theta.copy()
        theta_minus = state.theta.copy()
        theta_plus[index] += step
        theta_minus[index] -= step
        numerical[index] = (
            circulation_current(state.p, theta_plus, state.kernel, 0.45)
            - circulation_current(state.p, theta_minus, state.kernel, 0.45)
        ) / (2.0 * step)
    assert np.allclose(analytic, numerical, rtol=2e-9, atol=2e-11)
    assert float(np.sum(analytic)) == pytest.approx(0.0, abs=1e-15)


def test_locked_protocol_passes_scoped_deterministic_gates(
    protocol_result: tuple[dict, list[dict]],
) -> None:
    summary, records = protocol_result
    assert summary["status"] == "pass"
    assert summary["central_empirical_external_claim_status"] == "proof_incomplete"
    assert summary["estimand"] == "discrete_cycle_sum_surrogate"
    assert summary["failed_gates"] == []
    assert summary["indeterminate_gates"] == []
    assert len(summary["gates"]) == 16
    assert all(gate["status"] == "pass" for gate in summary["gates"])

    metrics = summary["metrics"]
    assert metrics["response_curvature_center"] == pytest.approx(-0.07935107, rel=2e-6)
    assert metrics["projective_curvature_center"] == pytest.approx(0.14583333, rel=2e-6)
    assert metrics["legacy_mean_log_slope"] == pytest.approx(-1.0, abs=0.02)
    assert metrics["summed_tangent_remainder_log_slope"] == pytest.approx(-1.0, abs=0.06)
    assert metrics["max_local_quotient_consistency_relative_error"] < 0.005
    assert metrics["local_two_form_quotient_spread"] > 0.15
    assert summary["two_dimensional_pointwise_proportionality_is_algebraic"] is True
    assert summary["quotient_consistency_is_not_predictive_evidence"] is True
    assert summary["estimand_and_thresholds_selected_after_exploratory_probe"] is True

    null_records = [record for record in records if record["record_type"] == "same_observable_exact_null"]
    assert {record["null_name"] for record in null_records} == {
        "current_phase_gain_zero",
        "phase_relaxation_one",
    }
    assert max(record["max_abs_q_sample"] for record in null_records) <= 1e-14

    quotient_records = [
        record for record in records if record["record_type"] == "local_two_form_quotient_consistency"
    ]
    assert len(quotient_records) == len(DEFAULT_CONFIG.quotient_centers)
    assert all(record["quotient_has_independent_predictive_content"] is False for record in quotient_records)


def test_coupled_refinement_and_cyclic_start_are_explicit(
    protocol_result: tuple[dict, list[dict]],
) -> None:
    _, records = protocol_result
    area = [record for record in records if record["record_type"] == "coupled_area_tick_refinement"]
    assert [record["side"] for record in area] == [0.16, 0.08, 0.04, 0.02]
    assert [record["steps_per_segment"] for record in area] == [38, 150, 600, 2400]
    response_errors = [record["response_density_relative_error"] for record in area]
    flux_errors = [record["flux_density_relative_error"] for record in area]
    assert all(later < earlier for earlier, later in zip(response_errors, response_errors[1:]))
    assert all(later < earlier for earlier, later in zip(flux_errors, flux_errors[1:]))
    assert all(record["ccw"]["signed_area"] > 0.0 for record in area)
    assert all(record["cw"]["signed_area"] < 0.0 for record in area)

    cyclic = [record for record in records if record["record_type"] == "cyclic_start_refinement"]
    assert len(cyclic) == len(DEFAULT_CONFIG.cyclic_steps) * len(DEFAULT_CONFIG.cyclic_start_fractions)
    spreads = []
    for steps in DEFAULT_CONFIG.cyclic_steps:
        values = [
            record["discrete_cycle_sum_surrogate_anti"]
            for record in cyclic
            if record["steps_per_segment"] == steps
        ]
        spreads.append(max(values) - min(values))
    assert all(later < earlier for earlier, later in zip(spreads, spreads[1:]))


def test_cli_writes_strict_self_describing_artifacts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    protocol_result: tuple[dict, list[dict]],
) -> None:
    monkeypatch.setattr(run, "ARTIFACTS_DIR", tmp_path)
    monkeypatch.setattr(run, "execute_protocol", lambda config: protocol_result)

    result = RUNNER.invoke(run.app, [])

    assert result.exit_code == 0, result.output
    expected = {
        "PROVENANCE.json",
        "PROVENANCE_CORRECTION.json",
        "PROVENANCE_CORRECTION.sha256",
        "records.json",
        "summary.json",
        "REPORT.md",
    }
    assert {path.name for path in tmp_path.iterdir()} == expected
    summary = json.loads((tmp_path / "summary.json").read_text(encoding="utf-8"))
    provenance = json.loads((tmp_path / "PROVENANCE.json").read_text(encoding="utf-8"))
    ledger = json.loads((tmp_path / "PROVENANCE_CORRECTION.json").read_text(encoding="utf-8"))
    records = json.loads((tmp_path / "records.json").read_text(encoding="utf-8"))
    report = (tmp_path / "REPORT.md").read_text(encoding="utf-8")

    assert summary["status"] == "pass"
    assert len(records) == 34
    assert provenance["evidence_tier"] == "internal_synthetic_analytic_fixture"
    assert provenance["schema_version"] == 2
    assert provenance["source_text_hash_domain_id"] == SOURCE_TEXT_HASH_DOMAIN
    assert provenance["source_bundle_is_sorted_and_path_bound"] is True
    assert provenance["canonical_source_hashes_are_repository_identity_not_execution_bytes"] is True
    assert provenance["external_raw_data_runnable"] is False
    assert provenance["not_transported_charge_or_physical_pump"] is True
    assert "acceptance thresholds were selected" in provenance["discovery_disclosure"]
    assert "not CGT-predictive evidence" in provenance["two_dimensional_quotient_disclosure"]
    assert len(provenance["protocol_sha256"]) == 64
    assert len(provenance["source_bundle_sha256"]) == 64
    assert provenance["source_bundle_sha256"] == source_bundle_sha256(provenance["source_text_dependencies"])
    assert provenance["summary_canonical_json_sha256"] == run._json_sha256(summary)
    assert provenance["records_canonical_json_sha256"] == run._json_sha256(records)
    assert "Central empirical/external CWT claim:** `PROOF INCOMPLETE`" in report
    assert "not external evidence" in report
    assert "no independent CGT-predictive content" in report
    assert ledger["correction_status"] == "PACKAGING_CORRECTION_NO_NUMERIC_CHANGE"
    assert ledger["previous"]["artifact_sha256_raw_bytes"] == PRE_CORRECTION_ARTIFACT_SHA256
    assert (
        ledger["previous"]["source_bundle_sha256_ambiguous_raw_checkout_domain"]
        == PRE_CORRECTION_SOURCE_BUNDLE_SHA256
    )
    assert len(ledger["affected_paths"]) == 10
    assert {entry["path"] for entry in ledger["affected_paths"]} == set(PRE_CORRECTION_CRLF_EXECUTION)
    sidecar = (tmp_path / "PROVENANCE_CORRECTION.sha256").read_text(encoding="utf-8").split()
    assert sidecar == [
        run._sha256(tmp_path / "PROVENANCE_CORRECTION.json"),
        "PROVENANCE_CORRECTION.json",
    ]
    run.verify_artifacts(tmp_path)


def test_source_text_hash_domain_is_lf_crlf_portable_and_fail_closed() -> None:
    lf = b"alpha\nbeta\n"
    crlf = b"alpha\r\nbeta\r\n"
    assert canonical_source_text_bytes(lf) == lf
    assert canonical_source_text_bytes(crlf) == lf
    assert source_text_sha256(lf) == source_text_sha256(crlf)
    assert source_text_sha256(b"alpha\ngamma\n") != source_text_sha256(lf)

    with pytest.raises(SourceTextIntegrityError, match="bare CR"):
        canonical_source_text_bytes(b"alpha\rbeta\n")
    with pytest.raises(SourceTextIntegrityError, match="BOM"):
        canonical_source_text_bytes(b"\xef\xbb\xbfalpha\n")
    with pytest.raises(SourceTextIntegrityError, match="strict UTF-8"):
        canonical_source_text_bytes(b"alpha\xff\n")


def test_source_manifest_binds_sorted_paths_and_rejects_dependency_changes(tmp_path: Path) -> None:
    (tmp_path / "a.py").write_bytes(b"a = 1\r\n")
    (tmp_path / "b.py").write_bytes(b"b = 2\n")
    manifest = build_source_manifest(tmp_path, ("b.py", "a.py"))
    payload = source_bundle_payload(manifest)
    assert [entry["path"] for entry in payload] == ["a.py", "b.py"]
    verify_source_manifest(tmp_path, manifest, ("a.py", "b.py"))

    renamed = {"renamed.py": manifest["a.py"], "b.py": manifest["b.py"]}
    assert source_bundle_sha256(renamed) != source_bundle_sha256(manifest)
    with pytest.raises(SourceTextIntegrityError, match="path set differs"):
        verify_source_manifest(tmp_path, renamed, ("a.py", "b.py"))

    (tmp_path / "a.py").write_bytes(b"a = 3\r\n")
    with pytest.raises(SourceTextIntegrityError, match="manifest differs"):
        verify_source_manifest(tmp_path, manifest, ("a.py", "b.py"))


def test_declared_source_hashes_match_staged_or_head_git_blobs() -> None:
    manifest = build_source_manifest(run.SIM_ROOT)
    assert tuple(sorted(manifest)) == tuple(sorted(SOURCE_PATHS))
    repo_root = run.SIM_ROOT.parent
    for relative, record in manifest.items():
        repository_path = f"cwt-sim/{relative}"
        blob = subprocess.run(
            ["git", "show", f":{repository_path}"],
            cwd=repo_root,
            check=True,
            capture_output=True,
        ).stdout
        assert canonical_source_text_bytes((run.SIM_ROOT / relative).read_bytes()) == blob
        assert hashlib.sha256(blob).hexdigest() == record["sha256"]
        assert len(blob) == record["size_bytes"]


def test_correction_ledger_proves_only_crlf_to_lf_for_exact_ten_paths() -> None:
    manifest = build_source_manifest(run.SIM_ROOT)
    ledger = run.build_correction_ledger(
        run.SIM_ROOT,
        manifest,
        PRE_CORRECTION_ARTIFACT_SHA256,
    )
    assert ledger["correction_status"] == "PACKAGING_CORRECTION_NO_NUMERIC_CHANGE"
    assert len(ledger["affected_paths"]) == 10
    for entry in ledger["affected_paths"]:
        assert entry["path"] in PRE_CORRECTION_CRLF_EXECUTION
        assert entry["transformation_proof"]["bare_cr_count"] == 0
        assert entry["transformation_proof"]["operation"] == "CRLF_to_LF_only"
        assert entry["transformation_proof"]["reconstructed_execution_hash_and_size_match"]

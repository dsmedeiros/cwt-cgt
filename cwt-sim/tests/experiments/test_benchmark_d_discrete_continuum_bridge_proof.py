"""Regression tests for the exact Benchmark-D rational bridge proof."""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from experiments.benchmark_d_discrete_continuum_bridge_proof import adapter
from experiments.benchmark_d_discrete_continuum_bridge_proof.artifacts import (
    ArtifactGenerationRefused,
    ArtifactVerificationError,
    canonical_source_text_bytes,
    expected_artifact_bytes,
    verify_artifacts,
    write_artifacts,
)
from experiments.benchmark_d_discrete_continuum_bridge_proof.contract import (
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    FORMAL_CENTER_FIRST_H_COEFFICIENT,
    FORMAL_CT_CENTER_CURVATURE,
    MODEL_CONTRACT,
)
from experiments.benchmark_d_discrete_continuum_bridge_proof.exact_math import (
    algebra_certificate,
    bridge_components,
    curvature_domain_certificate,
    effective_edge,
    exact_response_oracle,
    fixed_time_certificate,
    fixed_time_certificate_issues,
    fraction_item,
    identity,
    matrix_add,
    scale_matrix,
    stationary_population,
)
from experiments.benchmark_d_discrete_continuum_bridge_proof.run import app
from experiments.benchmark_d_discrete_continuum_bridge_proof.theorem import (
    _verify_context_directory,
    all_certificates,
    build_gates,
    derive_case_dispositions,
    execute_program,
)

SIM_ROOT = Path(__file__).resolve().parents[2]
EXPERIMENT_DIR = SIM_ROOT / "experiments" / "benchmark_d_discrete_continuum_bridge_proof"


def test_program_passes_internal_analytic_only() -> None:
    summary, records = execute_program()
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert summary["all_gates_pass"] is True
    assert summary["failed_gates"] == []
    assert summary["case_dispositions"] == EXPECTED_CASE_DISPOSITIONS
    assert records


def test_live_gate_registry_is_exact() -> None:
    summary, _ = execute_program()
    live = {item["name"] for item in summary["gates"]}
    registered = {name for names in CASE_GATE_MAP.values() for name in names}
    assert live == registered
    assert len(live) == len(summary["gates"])


@pytest.mark.parametrize("gate_name", sorted({name for names in CASE_GATE_MAP.values() for name in names}))
def test_every_live_gate_fails_closed(gate_name: str) -> None:
    summary, _ = execute_program(gate_overrides={gate_name: False})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert gate_name in summary["failed_gates"]
    owners = [case_id for case_id, names in CASE_GATE_MAP.items() if gate_name in names]
    assert owners
    assert all(
        summary["case_dispositions"][case_id] != EXPECTED_CASE_DISPOSITIONS[case_id] for case_id in owners
    )


def test_true_override_cannot_rescue_natural_failure() -> None:
    bad = replace(MODEL_CONTRACT, depolarizing_rule="q_h=1/125")
    summary, _ = execute_program(bad, gate_overrides={"contract_exact_primary_family": True})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "contract_exact_primary_family" in summary["failed_gates"]


def test_unknown_override_is_refused() -> None:
    with pytest.raises(ValueError, match="unknown bridge gate override"):
        execute_program(gate_overrides={"invented": False})


def test_exact_center_oracles_and_sign() -> None:
    certificate = curvature_domain_certificate()
    assert certificate["center_limit"]["fraction"] == fraction_item(FORMAL_CT_CENTER_CURVATURE)["fraction"]
    assert (
        certificate["first_h_coefficient"]["fraction"]
        == fraction_item(FORMAL_CENTER_FIRST_H_COEFFICIENT)["fraction"]
    )
    assert certificate["curvature_interval"]["upper"]["numerator"] < 0
    assert certificate["derivative_absolute_upper"]["float"] < 88


@pytest.mark.parametrize("h", [Fraction(1, 5), Fraction(1, 10), Fraction(1, 20), Fraction(1, 40)])
def test_exact_map_generator_and_source_identity(h: Fraction) -> None:
    matrix, source, generator = bridge_components(
        h,
        MODEL_CONTRACT.center_bias,
        MODEL_CONTRACT.center_diffusion,
    )
    assert matrix == matrix_add(identity(5), scale_matrix(generator, h))
    assert source == [h / 125] * 5
    assert effective_edge(h) == Fraction(1, 5) * (1 - h / 25)


def test_nonrational_or_out_of_domain_h_is_refused() -> None:
    with pytest.raises(TypeError, match="exact Fraction"):
        bridge_components(0.1, MODEL_CONTRACT.center_bias, MODEL_CONTRACT.center_diffusion)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="0<h<=1/5"):
        bridge_components(Fraction(0), MODEL_CONTRACT.center_bias, MODEL_CONTRACT.center_diffusion)
    with pytest.raises(ValueError, match="0<h<=1/5"):
        bridge_components(Fraction(1, 4), MODEL_CONTRACT.center_bias, MODEL_CONTRACT.center_diffusion)


def test_exact_hF_identity_and_gradient_curl() -> None:
    certificate = algebra_certificate()
    assert certificate["hF_exact_identity"] is True
    assert certificate["closed_loop_gradient_curl"]["fraction"] == "0/1"
    assert certificate["uniform_generator_error_coefficient"]["fraction"] == "49/6250"
    assert certificate["source_generator_error"]["fraction"] == "0/1"


def test_identity_readout_has_zero_curvature() -> None:
    oracle = exact_response_oracle(Fraction(1, 5), readout=[Fraction(1)] * 5)
    assert oracle.curvature_bd == 0


def test_readout_scaling_covariance() -> None:
    base = exact_response_oracle(Fraction(1, 5)).curvature_bd
    scaled = exact_response_oracle(
        Fraction(1, 5),
        readout=[Fraction(-2 * (index + 1)) for index in range(5)],
    ).curvature_bd
    assert scaled == -2 * base


def test_exact_stationary_branch_normalizes() -> None:
    population = stationary_population(
        MODEL_CONTRACT.center_bias,
        MODEL_CONTRACT.center_diffusion,
        effective_edge(Fraction(1, 5)),
    )
    assert sum(population) == 1
    assert min(population) > Fraction(4, 69)


def test_fixed_time_bound_and_limit_order_are_analytic() -> None:
    certificate = fixed_time_certificate()
    assert certificate["fixed_time_bound"]["directed_circle_coefficient"]["fraction"] == "42600/113"
    assert certificate["trajectory_or_finite_ladder_used_for_acceptance"] is False
    assert certificate["limits"]["primary_order"] == [
        "h_to_0_at_fixed_T_s_with_positive_integer_T_over_h",
        "T_to_infinity",
        "optional_s_to_0_within_declared_scale_domain",
    ]
    assert certificate["limits"]["interchangeability_claimed"] is False
    assert fixed_time_certificate_issues(certificate) == []


@pytest.mark.parametrize(
    ("path", "value", "expected_gate"),
    [
        (("local_defect", "static_coefficient"), fraction_item(Fraction(0)), "fixed_time_bridge_bound"),
        (
            ("local_defect", "speed_pi_coefficient"),
            fraction_item(Fraction(7, 5)),
            "fixed_time_bridge_bound",
        ),
        (
            ("fixed_time_bound", "time_coefficient"),
            fraction_item(Fraction(204, 25)),
            "fixed_time_bridge_bound",
        ),
        (
            ("clock_path_initialization", "positive_integer_N_with_Nh_equal_T"),
            False,
            "loop_clock_reversal_endpoint_contract",
        ),
        (
            ("clock_path_initialization", "discrete_exact_xbar_h_at_common_start"),
            False,
            "loop_clock_reversal_endpoint_contract",
        ),
        (
            ("clock_path_initialization", "continuous_exact_xbar_at_common_start"),
            False,
            "loop_clock_reversal_endpoint_contract",
        ),
        (
            ("contraction", "product_uses_elapsed_model_time_kh"),
            False,
            "fixed_time_bridge_bound",
        ),
        (
            ("clock_path_initialization", "minus_is_exact_reverse_of_plus"),
            False,
            "loop_clock_reversal_endpoint_contract",
        ),
        (
            ("clock_path_initialization", "right_endpoint_update_then_sample"),
            False,
            "loop_clock_reversal_endpoint_contract",
        ),
        (
            ("clock_path_initialization", "same_uniform_circle_and_affine_clock"),
            False,
            "loop_clock_reversal_endpoint_contract",
        ),
        (("response_reducer", "q_step_power"), 0, "fixed_time_bridge_bound"),
    ],
)
def test_fixed_time_structured_premise_mutations_fail_closed(
    path: tuple[str, str],
    value: object,
    expected_gate: str,
) -> None:
    certificates = copy.deepcopy(all_certificates())
    certificates["fixed_time"][path[0]][path[1]] = value
    gates = {item.name: item.passed for item in build_gates(certificates)}
    assert gates[expected_gate] is False
    assert gates["fixed_time_bridge_bound"] is False


def test_scale_domain_is_exact_uniform_and_out_of_domain_fails() -> None:
    registered = fixed_time_certificate()
    assert registered["exact_circle_extrema"]["minimum_face_margin"]["fraction"] == "1/100"
    assert registered["uniform_over_declared_scale_domain"] is True

    smaller = fixed_time_certificate(scale=Fraction(1, 200))
    assert fixed_time_certificate_issues(smaller, require_registered_scale=False) == []
    assert smaller["exact_circle_extrema"]["minimum_face_margin"]["fraction"] == "3/200"

    with pytest.raises(ValueError, match="0<s<=1/100"):
        fixed_time_certificate(scale=Fraction(0))
    with pytest.raises(ValueError, match="0<s<=1/100"):
        fixed_time_certificate(scale=Fraction(1, 99))
    with pytest.raises(TypeError, match="exact Fraction"):
        fixed_time_certificate(scale=0.005)  # type: ignore[arg-type]


def test_core_binding_is_finite_regression_not_uniform_proof() -> None:
    certificate = adapter.core_binding_certificate()
    assert certificate["population_basis_count"] == 5
    assert certificate["traceless_diagonal_deviation_basis_count"] == 4
    assert certificate["semantic_scope"] == (
        "finite_float_core_regression_and_provenance_only_not_uniform_runtime_proof"
    )
    assert certificate["uniform_family_proof_source"] == (
        "exact_fraction_symbolic_affine_identity_not_runtime_samples"
    )
    assert (
        max(
            certificate["maximum_affine_error"],
            certificate["maximum_deviation_error"],
            certificate["maximum_projection_delta"],
            certificate["maximum_kraus_tp_error"],
        )
        < 1e-14
    )


def test_core_mutation_at_corner_breaks_semantic_equivalence(monkeypatch: pytest.MonkeyPatch) -> None:
    original = adapter.raw_core_step

    def altered(rho, state, config, dephasing):
        result = original(rho, state, config, dephasing)
        coefficient = state.kernel[1, 0] - 0.195
        return result + coefficient * np.diag([1, -1, 0, 0, 0])

    monkeypatch.setattr(adapter, "raw_core_step", altered)
    certificate = adapter.core_binding_certificate()
    assert certificate["maximum_affine_error"] > 1e-4


def test_sample_invisible_core_perturbation_cannot_upgrade_finite_regression(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = adapter.raw_core_step

    def altered(rho, state, config, dephasing):
        result = original(rho, state, config, dephasing)
        b = state.extras["b"]
        d = state.extras["d"]
        polynomial = (b - 0.01) * (b - 0.05) * (d - 0.205) * (d - 0.245) * (b - 0.03)
        return result - 937_500_000.0 * polynomial * np.diag([1, -1, 0, 0, 0])

    monkeypatch.setattr(adapter, "raw_core_step", altered)
    certificate = adapter.core_binding_certificate()
    assert certificate["maximum_affine_error"] < 1e-14
    assert certificate["semantic_scope"].endswith("not_uniform_runtime_proof")

    state = adapter.theorem_state(0.02, 0.225)
    rho = np.diag([1.0, 0.0, 0.0, 0.0, 0.0]).astype(complex)
    config = adapter.core_config(Fraction(1, 10))
    baseline = original(rho, state, config, float(MODEL_CONTRACT.actual_dephasing))
    perturbed = altered(rho, state, config, float(MODEL_CONTRACT.actual_dephasing))
    assert np.max(np.abs(perturbed - baseline)) == pytest.approx(1.125)
    summary, _ = execute_program()
    assert summary["all_gates_pass"] is True
    assert summary["contract"]["theorem_family_scope"] == (
        "abstract_exact_fraction_D0_diagonal_population_family"
    )


def test_core_float_adapter_refuses_tiny_h_underflow_scope() -> None:
    with pytest.raises(ValueError, match="representable runtime domain"):
        adapter.core_config(Fraction(1, 10**400))
    config = adapter.core_config(MODEL_CONTRACT.core_runtime_h_min)
    assert config.dt > 0
    assert config.depolarizing > 0


def test_named_readout_mutation_breaks_core_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "mean_position_operator", lambda state=None: np.eye(5))
    certificate = adapter.core_binding_certificate()
    assert certificate["observable_maximum_absolute_error"] == 4.0


def test_exact_safety_margins() -> None:
    certificate = adapter.safety_certificate()
    assert certificate["maximum_no_jump_loss"]["fraction"] == "199/2500"
    assert certificate["no_jump_radicand_floor"]["fraction"] == "2301/2500"
    assert certificate["clip_inactive"] is True
    assert certificate["rescale_inactive"] is True


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("depolarizing_rule", "q_h=1/125"),
        ("depolarizing_rule", "q_h=1-exp(-delta*h)"),
        ("theorem_family_scope", "runtime_float_samples_define_uniform_family"),
        ("core_regression_scope", "finite_samples_prove_uniform_runtime_identity"),
        ("core_runtime_h_min", Fraction(1, 10**400)),
        ("edge_jump_scale", Fraction(1, 4)),
        ("depolarizing_rate", Fraction(0)),
        ("transpose_convention", "row_population_uses_K"),
        ("affine_source_formula", "c_h=0"),
        ("response_scaling", "Q=sum_without_h"),
        ("response_centering", "continuous_xbar"),
        ("update_convention", "sample_then_update"),
        ("reversal_convention", "independent_clockwise_path"),
        ("slow_clock", "nonuniform_u=(t/T)^2"),
        ("scale_domain", "unbounded_positive_s"),
        ("scale_upper", Fraction(1, 50)),
        ("circle_scale", Fraction(1, 50)),
        ("fixed_point_helper_policy", "iterative_allowed"),
        ("stationary_positivity_bound", "q_h/5"),
        ("proof_mode", "finite_ladder_is_proof"),
        ("limit_interchangeability", "claimed"),
        ("claim_ceiling", "universal empirical CGT proof"),
    ],
)
def test_refusal_mutations_fail_contract(field: str, value: object) -> None:
    summary, _ = execute_program(replace(MODEL_CONTRACT, **{field: value}))
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "contract_exact_primary_family" in summary["failed_gates"]


def test_legacy_open_point_is_off_family() -> None:
    summary, records = execute_program()
    context = next(item["value"] for item in records if item.get("name") == "context")
    assert context["legacy_open_point"] == {
        "h": "9/50",
        "q": "1/125",
        "primary_family_q": "9/1250",
        "q_mismatch": "1/1250",
        "off_primary_family": True,
    }
    assert summary["case_dispositions"]["C10"] == EXPECTED_CASE_DISPOSITIONS["C10"]


def test_canonical_source_domain_equates_lf_and_crlf() -> None:
    assert canonical_source_text_bytes(b"alpha\nbeta\n") == canonical_source_text_bytes(b"alpha\r\nbeta\r\n")


@pytest.mark.parametrize("payload", [b"\xef\xbb\xbfalpha\n", b"alpha\rbeta\n", b"\xff\xfe"])
def test_canonical_source_domain_rejects_invalid_bytes(payload: bytes) -> None:
    with pytest.raises(ValueError):
        canonical_source_text_bytes(payload)


def test_cli_has_only_status_run_verify() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "status" in result.stdout
    assert "run" in result.stdout
    assert "verify" in result.stdout
    assert "confirm" not in result.stdout.lower()
    assert "outcome" not in result.stdout.lower()


def test_status_cli_reports_internal_only() -> None:
    result = CliRunner().invoke(app, ["status"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert payload["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"


def test_artifact_generation_refuses_failed_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    import experiments.benchmark_d_discrete_continuum_bridge_proof.artifacts as artifact_module

    summary, records = execute_program(gate_overrides={"exact_hF_identity": False})
    monkeypatch.setattr(artifact_module, "execute_program", lambda: (copy.deepcopy(summary), records))
    with pytest.raises(ArtifactGenerationRefused):
        write_artifacts(tmp_path / "refused")
    assert not (tmp_path / "refused").exists()


def test_artifact_round_trip_and_nested_file_refusal(tmp_path: Path) -> None:
    output = tmp_path / "artifacts"
    write_artifacts(output)
    result = verify_artifacts(output)
    assert result["status"] == "PASS_INTERNAL_ANALYTIC"
    nested = output / "hidden"
    nested.mkdir()
    (nested / "result.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(ArtifactVerificationError, match="closure mismatch"):
        verify_artifacts(output)


def test_expected_artifacts_are_strict_lf_and_canonical_json() -> None:
    payloads = expected_artifact_bytes()
    assert set(payloads) == {"CHECKSUMS.json", "PROVENANCE.json", "REPORT.md", "records.json", "summary.json"}
    for name, payload in payloads.items():
        assert b"\r" not in payload
        if name.endswith(".json"):
            assert payload.endswith(b"\n")
            json.loads(payload.decode("utf-8"))


def _copied_context_bundle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    import experiments.benchmark_d_discrete_continuum_bridge_proof.theorem as theorem_module

    source = SIM_ROOT / "experiments" / "benchmark_d_open_response_proof" / "artifacts"
    target = tmp_path / "context"
    shutil.copytree(source, target)
    monkeypatch.setattr(theorem_module, "SIM_ROOT", tmp_path)
    return target


def test_predecessor_context_recursive_closure_accepts_exact_copy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _copied_context_bundle(tmp_path, monkeypatch)
    certificate = _verify_context_directory(target)
    assert certificate["recursive_inventory_exact"] is True
    assert set(certificate["entry_types"].values()) == {"file"}


@pytest.mark.parametrize("mutation", ["addition", "omission", "type_substitution", "path_substitution"])
def test_predecessor_context_recursive_closure_rejects_inventory_mutations(
    mutation: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _copied_context_bundle(tmp_path, monkeypatch)
    declared_file = next(path for path in target.iterdir() if path.name != "CHECKSUMS.json")
    if mutation == "addition":
        nested = target / "nested"
        nested.mkdir()
        (nested / "hidden.json").write_text("{}\n", encoding="utf-8")
    elif mutation == "omission":
        declared_file.unlink()
    elif mutation == "type_substitution":
        declared_file.unlink()
        declared_file.mkdir()
    else:
        checksums = json.loads((target / "CHECKSUMS.json").read_text(encoding="utf-8"))
        value = checksums["files"].pop(declared_file.name)
        checksums["files"][f"nested/../{declared_file.name}"] = value
        (target / "CHECKSUMS.json").write_text(
            json.dumps(checksums, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    with pytest.raises(RuntimeError, match="context|inventory|path-bound"):
        _verify_context_directory(target)


def test_predecessor_context_recursive_closure_rejects_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = _copied_context_bundle(tmp_path, monkeypatch)
    link = target / "nested-link"
    try:
        os.symlink(target / "REPORT.md", link)
    except OSError as exc:
        pytest.skip(f"host cannot create test symlink: {exc}")
    with pytest.raises(RuntimeError, match="link/reparse"):
        _verify_context_directory(target)


def test_clean_cli_import_does_not_expose_data_or_confirmation_path() -> None:
    script = EXPERIMENT_DIR / "run.py"
    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=SIM_ROOT,
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    lowered = result.stdout.lower()
    assert "confirm" not in lowered
    assert "raw data" not in lowered


def test_case_disposition_derivation_detects_failure() -> None:
    summary, _ = execute_program()
    raw_gates = [
        type("TestGate", (), {"name": item["name"], "passed": item["status"] == "pass"})
        for item in summary["gates"]
    ]
    target = next(index for index, item in enumerate(raw_gates) if item.name == "exact_hF_identity")
    raw_gates[target].passed = False
    dispositions = derive_case_dispositions(raw_gates)
    assert dispositions["C6"] != EXPECTED_CASE_DISPOSITIONS["C6"]


def test_build_gates_rejects_missing_live_gate() -> None:
    from experiments.benchmark_d_discrete_continuum_bridge_proof.theorem import all_certificates

    certificates = all_certificates()
    gates = build_gates(certificates)
    assert {item.name for item in gates} == {name for names in CASE_GATE_MAP.values() for name in names}

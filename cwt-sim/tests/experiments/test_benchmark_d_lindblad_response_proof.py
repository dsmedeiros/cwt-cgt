from __future__ import annotations

from dataclasses import replace
from fractions import Fraction

import numpy as np
import pytest
from typer.testing import CliRunner

from experiments.benchmark_d_lindblad_response_proof.adapter import (
    core_affine_equivalence_certificate,
    core_binding_certificate,
    explicit_projective_no_go_certificate,
)
from experiments.benchmark_d_lindblad_response_proof.artifacts import (
    CLEAN_CLI_LOCAL_MODULE_PATHS,
    EXPECTED_ARTIFACT_NAMES,
    ArtifactGenerationRefused,
    ArtifactVerificationError,
    assert_clean_cli_source_closure,
    canonical_source_text_bytes,
    expected_artifact_bytes,
    phase11_identity_records,
    sha256_bytes,
    verify_artifacts,
    write_artifacts,
)
from experiments.benchmark_d_lindblad_response_proof.certificates import (
    all_certificates,
    exact_stationary_certificate,
    loop_convention_certificate,
)
from experiments.benchmark_d_lindblad_response_proof.contract import (
    CASE_GATE_MAP,
    EXPECTED_CASE_DISPOSITIONS,
    FORMAL_RESPONSE_CURVATURE,
    MODEL_CONTRACT,
    contract_issues,
)
from experiments.benchmark_d_lindblad_response_proof.exact_math import (
    RationalInterval,
    dynamic_ladder_certificate,
    exact_response_oracle,
    fraction_item,
)
from experiments.benchmark_d_lindblad_response_proof.run import app
from experiments.benchmark_d_lindblad_response_proof.theorem import (
    _base_certificates,
    build_gates,
    derive_case_dispositions,
    execute_program,
)


def test_exact_response_oracle_recomputes_formal_fraction_and_sign() -> None:
    oracle = exact_response_oracle()
    assert oracle.response_curvature_bd == FORMAL_RESPONSE_CURVATURE
    assert oracle.response_curvature_bd < 0
    assert oracle.stationary_population == tuple(
        Fraction(value, 188723821) for value in (31700513, 35255285, 37350521, 39686093, 44731409)
    )


def test_core_binding_uses_named_d0_kernel_readout_and_explicit_config() -> None:
    result = core_binding_certificate()
    assert result["maximum_kernel_error"] < 2e-15
    assert result["observable_maximum_absolute_error"] == 0.0
    assert result["all_config_fields_explicit_and_equal"] is True
    assert result["clipping_inactive_on_box"] is True
    assert result["lower_clip_support_margin"] == pytest.approx(0.135)
    assert result["upper_clip_support_margin"] == pytest.approx(0.165)


def test_complete_diagonal_core_rhs_and_superoperator_equal_affine_reduction() -> None:
    result = core_affine_equivalence_certificate()
    assert result["semantic_scope"] == "complete_diagonal_invariant_subspace_not_full_superoperator"
    assert result["control_point_count"] == 5
    assert result["diagonal_population_basis_count"] == 5
    assert result["traceless_diagonal_deviation_basis_count"] == 4
    assert result["maximum_diagonal_rhs_error"] < 1e-14
    assert result["maximum_offdiagonal_rhs_error"] == 0.0
    assert result["maximum_trace_preservation_error"] < 1e-14
    assert result["maximum_superoperator_deviation_error"] < 1e-14
    assert result["maximum_affine_source_error"] == 0.0


def test_true_stationary_branch_has_exact_residual_and_uniform_floor() -> None:
    result = exact_stationary_certificate()
    assert result["maximum_exact_stationary_residual"]["fraction"] == "0/1"
    assert result["maximum_exact_trace_error"]["fraction"] == "0/1"
    assert result["uniform_full_rank_floor"]["fraction"] == "4/69"
    assert result["uniform_floor_below_sampled_minimum"] is True


def test_interval_arithmetic_is_directed() -> None:
    left = RationalInterval(Fraction(-2), Fraction(3))
    right = RationalInterval(Fraction(4), Fraction(5))
    assert left * right == RationalInterval(Fraction(-10), Fraction(15))
    assert right / RationalInterval(Fraction(2), Fraction(4)) == RationalInterval(Fraction(1), Fraction(5, 2))


def test_dynamic_certificate_uses_reviewed_power_of_two_rule_and_no_trajectory() -> None:
    result = dynamic_ladder_certificate()
    primary = result["scale_certificates"][0]
    assert primary["duration_rule"] == "T0=2^ceil(log2(4*C(s)/L_min(s)))"
    assert primary["minimum_duration_T0"] == 1_048_576
    assert primary["negative_sign_certified"] is True
    assert primary["remainder_units"] == "mean_position_index_times_model_time_squared"
    assert result["trajectory_used_for_acceptance"] is False
    assert result["all_signs_certified"] is True
    assert result["slow_drive_clock_id"] == "uniform_affine_normalized_clock_v1"
    assert result["slow_drive_clock_definition"] == MODEL_CONTRACT.slow_drive_clock_definition
    assert all(
        row["model_time_speed_bound"] == "sup_t||lambda_dot(t)||<=2*pi*s/T"
        and row["model_time_acceleration_bound"] == "sup_t||lambda_double_dot(t)||<=(2*pi)^2*s/T^2"
        for row in result["scale_certificates"]
    )


def test_joint_ladder_has_growing_sT_and_decreasing_relative_bound() -> None:
    result = dynamic_ladder_certificate()
    rows = result["joint_area_relative_ladder"]
    st_values = [Fraction(row["s_times_T_over_tau"]["fraction"]) for row in rows]
    ratios = [Fraction(row["remainder_over_line_lower"]["fraction"]) for row in rows]
    assert all(right > left for left, right in zip(st_values, st_values[1:]))
    assert all(2 * right <= left for left, right in zip(ratios, ratios[1:]))
    assert result["joint_area_relative_ratios_contract_by_at_least_one_half"] is True
    assert all(row["two_times_right_le_left"] for row in result["successive_joint_remainder_bounds"])


def test_loop_circle_exact_extrema_are_strictly_inside_with_one_hundredth_margins() -> None:
    result = loop_convention_certificate()
    assert [item["fraction"] for item in result["analytic_bias_extrema"]] == ["1/50", "1/25"]
    assert [item["fraction"] for item in result["analytic_diffusion_extrema"]] == [
        "43/200",
        "47/200",
    ]
    assert [item["fraction"] for item in result["exact_face_margins"]] == ["1/100"] * 4
    assert result["analytic_extrema_inside_box"] is True
    assert result["sampling_role"] == "diagnostic_only_not_domain_acceptance"


def test_projective_no_go_uses_explicit_smooth_real_state() -> None:
    result = explicit_projective_no_go_certificate()
    assert result["channel_equivalent_under_frozen_generator"] is True
    assert result["is_current_core_helper_branch_state_geometry"] is False
    assert result["stationary_eigenvector_helper_used"] is False
    assert result["minimum_exact_corner_probability"] > 0.0
    assert result["psi_norm_error"] < 1e-14
    assert result["numerical_projective_curvature_bd"] == 0.0
    assert result["projective_curvature_bd_exact_fraction"] == "0/1"


def test_identity_readout_and_benchmark_c_are_exact_nulls() -> None:
    certificates = all_certificates()
    assert certificates["nulls_and_covariance"]["identity_readout_curvature"]["fraction"] == "0/1"
    assert certificates["benchmark_c_null"]["response_curvature_exact_fraction"] == "0/1"
    assert certificates["benchmark_c_null"]["maximum_fixed_rhs_error"] < 1e-14


def test_readout_sign_and_scale_covariance_are_exact() -> None:
    result = all_certificates()["nulls_and_covariance"]
    primary = FORMAL_RESPONSE_CURVATURE
    assert result["scaled_covariance_exact"] is True
    assert Fraction(result["scaled_readout_curvatures"]["-2"]["fraction"]) == -2 * primary
    assert Fraction(result["scaled_readout_curvatures"]["3"]["fraction"]) == 3 * primary


@pytest.mark.parametrize(
    "mutated",
    [
        replace(MODEL_CONTRACT, depolarizing_rate=Fraction(0)),
        replace(MODEL_CONTRACT, coherent_scale=Fraction(1, 10)),
        replace(MODEL_CONTRACT, site_potential_scale=Fraction(1, 10)),
        replace(MODEL_CONTRACT, flow_backend="euler_plus_psd_projection"),
        replace(MODEL_CONTRACT, dt=Fraction(1, 10)),
        replace(MODEL_CONTRACT, time_domain="physical_seconds_without_calibration"),
        replace(MODEL_CONTRACT, slow_drive_clock_id="nonuniform_quadratic_clock_v1"),
        replace(MODEL_CONTRACT, slow_drive_clock_definition="u=(t/T)^2"),
        replace(MODEL_CONTRACT, slow_drive_clock_definition=""),
        replace(
            MODEL_CONTRACT,
            slow_drive_clock_definition=(
                "u=t/T;lambda_plus(t)=gamma_plus(u);" "lambda_minus(t)=independent_schedule;0<=t<T"
            ),
        ),
        replace(MODEL_CONTRACT, reversal_convention="not_exact_reverse"),
        replace(MODEL_CONTRACT, initialization="arbitrary"),
    ],
)
def test_invalid_contract_variants_fail_closed(mutated) -> None:
    assert contract_issues(mutated)
    summary, _ = execute_program(mutated)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert summary["all_gates_pass"] is False


@pytest.mark.parametrize(
    "mutated",
    [
        replace(MODEL_CONTRACT, depolarizing_rate=Fraction(0)),
        replace(MODEL_CONTRACT, coherent_scale=Fraction(1, 10)),
        replace(MODEL_CONTRACT, site_potential_scale=Fraction(1, 10)),
        replace(MODEL_CONTRACT, flow_backend="euler_plus_psd_projection"),
        replace(MODEL_CONTRACT, initialization="arbitrary"),
        replace(MODEL_CONTRACT, reversal_convention="not_exact_reverse"),
        replace(MODEL_CONTRACT, time_domain="physical_seconds_without_calibration"),
        replace(MODEL_CONTRACT, slow_drive_clock_id="nonuniform_quadratic_clock_v1"),
    ],
)
def test_true_overrides_cannot_rescue_invalid_contracts(mutated) -> None:
    every_true = {name: True for names in CASE_GATE_MAP.values() for name in names}
    summary, _ = execute_program(mutated, gate_overrides=every_true)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert summary["all_gates_pass"] is False
    assert summary["failed_gates"]
    assert summary["case_dispositions"] != EXPECTED_CASE_DISPOSITIONS


def test_gate_overrides_are_monotone_fail_only_and_typed() -> None:
    failed, _ = execute_program(gate_overrides={"exact_center_oracle": False})
    assert failed["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    with pytest.raises(ValueError, match="unknown gate override"):
        execute_program(gate_overrides={"not_a_live_gate": False})
    with pytest.raises(TypeError, match="must be booleans"):
        execute_program(gate_overrides={"exact_center_oracle": 1})


def test_zero_depolarization_true_override_cannot_reach_artifact_or_cli_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import experiments.benchmark_d_lindblad_response_proof.artifacts as artifacts
    import experiments.benchmark_d_lindblad_response_proof.run as run_module

    mutated = replace(MODEL_CONTRACT, depolarizing_rate=Fraction(0))
    every_true = {name: True for names in CASE_GATE_MAP.values() for name in names}
    failed_summary, failed_records = execute_program(mutated, gate_overrides=every_true)
    assert failed_summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    monkeypatch.setattr(artifacts, "execute_program", lambda: (failed_summary, failed_records))
    monkeypatch.setattr(run_module, "execute_program", lambda: (failed_summary, failed_records))

    with pytest.raises(ArtifactGenerationRefused):
        artifacts.expected_artifact_bytes()
    runner = CliRunner()
    for command in (["status"], ["run"], ["verify"]):
        result = runner.invoke(app, command)
        assert result.exit_code != 0
        assert "PASS_INTERNAL_ANALYTIC" not in result.stdout


def test_nonuniform_clock_true_overrides_cannot_reach_artifact_or_cli_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import experiments.benchmark_d_lindblad_response_proof.artifacts as artifacts
    import experiments.benchmark_d_lindblad_response_proof.run as run_module

    mutated = replace(
        MODEL_CONTRACT,
        slow_drive_clock_id="nonuniform_quadratic_clock_v1",
        slow_drive_clock_definition="u=(t/T)^2;lambda_plus(t)=gamma_plus(u)",
    )
    every_true = {name: True for names in CASE_GATE_MAP.values() for name in names}
    failed_summary, failed_records = execute_program(mutated, gate_overrides=every_true)
    assert failed_summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "uniform_affine_slow_drive_clock" in failed_summary["failed_gates"]
    monkeypatch.setattr(artifacts, "execute_program", lambda: (failed_summary, failed_records))
    monkeypatch.setattr(run_module, "execute_program", lambda: (failed_summary, failed_records))

    with pytest.raises(ArtifactGenerationRefused):
        artifacts.expected_artifact_bytes()
    runner = CliRunner()
    for command in (["status"], ["run"], ["verify"]):
        result = runner.invoke(app, command)
        assert result.exit_code != 0
        assert "PASS_INTERNAL_ANALYTIC" not in result.stdout


def test_forbidden_euler_helpers_are_not_called(monkeypatch: pytest.MonkeyPatch) -> None:
    import cwt.cgt.lindblad as lindblad

    def forbidden(*_args, **_kwargs):
        raise AssertionError("forbidden Euler/projection helper called")

    monkeypatch.setattr(lindblad, "apply_lindblad_step", forbidden)
    monkeypatch.setattr(lindblad, "lindblad_branch_density", forbidden)
    summary, _ = execute_program()
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"


def test_gate_registry_exactly_equals_case_union() -> None:
    gates = build_gates(all_certificates())
    live = {gate.name for gate in gates}
    registered = {name for names in CASE_GATE_MAP.values() for name in names}
    assert live == registered
    assert len(live) == len(gates)
    assert set(CASE_GATE_MAP) == set(EXPECTED_CASE_DISPOSITIONS)


@pytest.mark.parametrize(
    "gate_name",
    [name for names in CASE_GATE_MAP.values() for name in names],
)
def test_every_live_gate_mutation_fails_its_cases_and_overall(gate_name: str) -> None:
    summary, _ = execute_program(gate_overrides={gate_name: False})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert gate_name in summary["failed_gates"]
    owners = [case_id for case_id, names in CASE_GATE_MAP.items() if gate_name in names]
    assert owners
    for case_id in owners:
        assert summary["case_dispositions"][case_id].endswith("_FAIL")


def test_case_dispositions_are_derived_not_unconditional() -> None:
    gates = build_gates(all_certificates())
    mutated = [
        type(gate)(
            gate.name,
            False if gate.name == "exact_center_oracle" else gate.passed,
            gate.requirement,
            gate.observed,
        )
        for gate in gates
    ]
    dispositions = derive_case_dispositions(mutated)
    assert dispositions["C5"] == "EXACT_RESPONSE_CURVATURE_FAIL"
    assert dispositions != EXPECTED_CASE_DISPOSITIONS


def test_program_pass_is_internal_only_and_never_empirical() -> None:
    summary, records = execute_program()
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert summary["all_gates_pass"] is True
    assert summary["failed_gates"] == []
    assert summary["case_dispositions"] == EXPECTED_CASE_DISPOSITIONS
    assert records


def test_affine_source_omission_mutation_breaks_gate() -> None:
    certificates = all_certificates()
    certificates["nulls_and_covariance"]["affine_source_omission_changes_fixed_equation"] = False
    gates = build_gates(certificates)
    gate = next(item for item in gates if item.name == "affine_source_omission_refused")
    assert gate.passed is False


def test_loop_domain_containment_mutation_breaks_gate() -> None:
    certificates = all_certificates()
    certificates["loop_convention"]["every_sampled_loop_point_inside_box"] = False
    gates = build_gates(certificates)
    gate = next(item for item in gates if item.name == "circle_orientation_reversal")
    assert gate.passed is False


def test_exact_loop_containment_mutation_breaks_gate() -> None:
    certificates = all_certificates()
    certificates["loop_convention"]["analytic_extrema_inside_box"] = False
    gates = build_gates(certificates)
    gate = next(item for item in gates if item.name == "circle_orientation_reversal")
    assert gate.passed is False


def test_clock_bound_formula_mutation_breaks_slow_drive_gate() -> None:
    certificates = all_certificates()
    certificates["dynamic"]["scale_certificates"][0][
        "model_time_speed_bound"
    ] = "arbitrary_nonuniform_schedule"
    gates = build_gates(certificates)
    gate = next(item for item in gates if item.name == "uniform_affine_slow_drive_clock")
    assert gate.passed is False


def test_diagonal_core_equivalence_detects_corner_only_rhs_perturbation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import experiments.benchmark_d_lindblad_response_proof.adapter as adapter
    import experiments.benchmark_d_lindblad_response_proof.artifacts as artifacts

    original = adapter.lindblad_rhs

    def corner_only_perturbation(rho, state, config, dephasing):
        result = np.asarray(original(rho, state, config, dephasing)).copy()
        if result.shape != (5, 5):
            return result
        coefficient = float(state.kernel[1, 0]) - 0.195
        result += coefficient * np.diag([1.0, -1.0, 0.0, 0.0, 0.0])
        return result

    monkeypatch.setattr(adapter, "lindblad_rhs", corner_only_perturbation)
    _base_certificates.cache_clear()
    try:
        certificate = core_affine_equivalence_certificate()
        old_collinear = [
            row
            for row in certificate["control_point_errors"]
            if abs(row["diffusion"] - row["bias"] - 0.195) < 1e-15
        ]
        corner = next(
            row
            for row in certificate["control_point_errors"]
            if row["bias"] == 0.05 and row["diffusion"] == 0.205
        )
        assert old_collinear
        assert max(row["maximum_diagonal_rhs_error"] for row in old_collinear) < 1e-14
        assert corner["maximum_diagonal_rhs_error"] > 0.01

        summary, _ = execute_program()
        assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
        assert "diagonal_invariant_subspace_core_equivalence" in summary["failed_gates"]
        with pytest.raises(ArtifactGenerationRefused):
            artifacts.expected_artifact_bytes()

        runner = CliRunner()
        status = runner.invoke(app, ["status"])
        verify = runner.invoke(app, ["verify"])
        assert status.exit_code != 0
        assert verify.exit_code != 0
        assert "PASS_INTERNAL_ANALYTIC" not in status.stdout
        assert "PASS_INTERNAL_ANALYTIC" not in verify.stdout
    finally:
        _base_certificates.cache_clear()


def test_model_time_units_are_explicit_and_physical_calibration_is_absent() -> None:
    assert MODEL_CONTRACT.time_domain == "uncalibrated_continuous_model_time"
    assert MODEL_CONTRACT.generator_rate_units == "inverse_model_time"
    assert MODEL_CONTRACT.duration_units == "model_time"
    assert MODEL_CONTRACT.readout_units == "dimensionless_mean_position_index"
    assert MODEL_CONTRACT.integrated_response_units == "mean_position_index_times_model_time"
    assert MODEL_CONTRACT.physical_time_calibration_status.startswith("absent_requires_external")


def test_exact_fraction_serializer_is_stable() -> None:
    assert fraction_item(Fraction(-3, 7))["fraction"] == "-3/7"


def test_source_text_hash_domain_is_lf_portable_and_fail_closed() -> None:
    assert canonical_source_text_bytes(b"alpha\r\nbeta\r\n") == b"alpha\nbeta\n"
    assert canonical_source_text_bytes(b"alpha\nbeta\n") == b"alpha\nbeta\n"
    with pytest.raises(ValueError, match="BOM"):
        canonical_source_text_bytes(b"\xef\xbb\xbfalpha\n")
    with pytest.raises(ValueError, match="bare CR"):
        canonical_source_text_bytes(b"alpha\rbeta\n")
    with pytest.raises(ValueError, match="strict UTF-8"):
        canonical_source_text_bytes(b"\xff")
    assert sha256_bytes(canonical_source_text_bytes(b"alpha\n")) != sha256_bytes(
        canonical_source_text_bytes(b"alphb\n")
    )


def test_clean_cli_local_source_closure_is_exact_sorted_and_path_bound() -> None:
    assert tuple(sorted(CLEAN_CLI_LOCAL_MODULE_PATHS)) == CLEAN_CLI_LOCAL_MODULE_PATHS
    assert assert_clean_cli_source_closure() == CLEAN_CLI_LOCAL_MODULE_PATHS


def test_phase11_identity_roles_are_explicit_and_nonexecuting() -> None:
    records = phase11_identity_records()
    assert records["scripts/cgt/run_phase11_analysis.py"]["role"].startswith(
        "historical_phase11_entry_script"
    )
    assert records["cwt/cgt/analysis/phase11_analysis.py"]["role"].startswith(
        "current_phase11_recomputation_implementation"
    )
    assert records["cgt_benchmarks/reports/phase11_summary.json"]["hash_domain"] == ("sha256_raw_bytes_v1")


def test_expected_artifact_payload_is_strict_lf_and_closed() -> None:
    payloads = expected_artifact_bytes()
    assert set(payloads) == EXPECTED_ARTIFACT_NAMES
    assert all(b"\r" not in payload for payload in payloads.values())
    summary = __import__("json").loads(payloads["summary.json"])
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    report = payloads["REPORT.md"].decode("utf-8")
    assert "continuous model-time integral" in report
    assert "physical-time integral" not in report
    assert "not the current core helper `BranchState` geometry" in " ".join(report.split())
    assert "`u=t/T`" in report
    assert "`lambda_-(t)=lambda_+(T-t)=gamma_+(1-u)`" in report


def test_artifact_write_and_verify_are_isolated(tmp_path) -> None:
    output = tmp_path / "artifacts"
    paths = write_artifacts(output)
    assert set(paths) == EXPECTED_ARTIFACT_NAMES
    result = verify_artifacts(output)
    assert result["status"] == "PASS_INTERNAL_ANALYTIC"
    assert result["artifact_count"] == 5


def test_artifact_verifier_rejects_nested_or_unexpected_entries(tmp_path) -> None:
    output = tmp_path / "artifacts"
    write_artifacts(output)
    hidden = output / "hidden"
    hidden.mkdir()
    (hidden / "outcome.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactVerificationError, match="closure mismatch"):
        verify_artifacts(output)


def test_artifact_generation_refuses_mutated_gate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import experiments.benchmark_d_lindblad_response_proof.artifacts as artifacts

    summary, records = execute_program(gate_overrides={"exact_center_oracle": False})
    monkeypatch.setattr(artifacts, "execute_program", lambda: (summary, records))
    with pytest.raises(ArtifactGenerationRefused):
        artifacts.expected_artifact_bytes()


def test_cli_status_and_run_fail_closed_without_misleading_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import experiments.benchmark_d_lindblad_response_proof.run as run_module

    runner = CliRunner()
    failed_summary, records = execute_program(gate_overrides={"exact_center_oracle": False})
    monkeypatch.setattr(run_module, "execute_program", lambda: (failed_summary, records))
    status = runner.invoke(app, ["status"])
    assert status.exit_code != 0
    assert "PASS_INTERNAL_ANALYTIC" not in status.stdout

    def refuse():
        raise ArtifactGenerationRefused("forced gate failure")

    monkeypatch.setattr(run_module, "write_artifacts", refuse)
    run = runner.invoke(app, ["run"])
    assert run.exit_code != 0
    assert "PASS_INTERNAL_ANALYTIC" not in run.stdout

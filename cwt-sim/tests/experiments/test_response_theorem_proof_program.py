from __future__ import annotations

import copy
import inspect
import json
import math
from pathlib import Path

import numpy as np
import pytest
from typer.main import get_command
from typer.testing import CliRunner

from experiments.response_theorem_proof_program.artifacts import (
    ArtifactVerificationError,
    canonical_source_text_bytes,
    verify_artifacts,
    write_artifacts,
)
from experiments.response_theorem_proof_program.counterexamples import (
    EXPECTED_CASE_DISPOSITIONS,
    case_dispositions_match,
    counterexample_matrix,
    covariance_checks,
    nonnormal_fixed_gap_case,
    positive_control,
    propagator_decay_without_frozen_invertibility,
    realizability_identity_error,
)
from experiments.response_theorem_proof_program.forms import (
    area_bivector,
    closed_circle_path,
    conditional_alignment_bound,
    exterior_derivative,
    line_integral,
    log_slope,
    rotational_one_form,
)
from experiments.response_theorem_proof_program.models import (
    alpha_from_dt,
    continuous_harmonic_cycle,
    interaction_pair,
    realizability_pair,
    realized_tangent_one_form,
)
from experiments.response_theorem_proof_program.run import app
from experiments.response_theorem_proof_program.theorem import DEFAULT_CONFIG, execute_program

RUNNER = CliRunner()


def test_sign_factor_and_right_endpoint_response_contract() -> None:
    beta = rotational_one_form(1.25)
    curvature = exterior_derivative(beta, np.asarray((0.3, -0.2)))
    assert np.isclose(curvature[0, 1], 1.25, atol=1e-10)
    assert np.isclose(curvature[1, 0], -1.25, atol=1e-10)

    path = closed_circle_path(np.asarray((0.3, -0.2)), 0.2, 512)
    assert np.array_equal(path[0], path[-1])
    assert area_bivector(path)[0, 1] > 0.0
    pair = realizability_pair(beta, path, 0.65)
    assert pair.positive.samples.shape == (512,)
    assert pair.reverse.samples.shape == (512,)
    assert pair.anti > 0.0
    assert line_integral(beta, path) > 0.0


def test_nonzero_B0_interaction_and_ordinary_did_factor_two() -> None:
    path = closed_circle_path(np.asarray((0.3, -0.2)), 0.2, 2048)
    result = interaction_pair(
        rotational_one_form(2.0),
        rotational_one_form(0.5),
        path,
        0.65,
        initialization="periodic",
    )
    target = 1.5 * line_integral(rotational_one_form(1.0), path)
    assert abs(result["qanti_zero"]) > 0.01
    assert np.isclose(result["interaction_D"], target, rtol=2e-3)
    assert result["ordinary_difference_in_differences"] == 2.0 * result["interaction_D"]


def test_fixed_loop_generic_and_periodic_rates_are_separate() -> None:
    beta = rotational_one_form(1.0)
    center = np.asarray((0.3, -0.2))
    steps = [128, 256, 512, 1024, 2048]
    errors: dict[str, list[float]] = {"equilibrium": [], "periodic": []}
    for initialization in errors:
        for count in steps:
            path = closed_circle_path(center, 0.2, count)
            pair = realizability_pair(beta, path, 0.65, initialization=initialization)
            errors[initialization].append(abs(pair.anti - line_integral(beta, path)))
    generic_slope = log_slope(steps[-4:], errors["equilibrium"][-4:])
    periodic_slope = log_slope(steps[-4:], errors["periodic"][-4:])
    assert -1.2 <= generic_slope <= -0.8
    assert -2.2 <= periodic_slope <= -1.8


def test_scaled_generic_and_periodic_bounds_and_area_relative_condition() -> None:
    summary, _records = execute_program(DEFAULT_CONFIG)
    metrics = summary["metrics"]
    assert metrics["max_generic_scaled_bound_ratio"] <= 4.0
    assert metrics["max_periodic_scaled_bound_ratio"] <= 2.0
    assert metrics["generic_fixed_Ns_tail_ratio"] >= 0.85
    assert metrics["periodic_area_relative_slope_at_fixed_Ns"] >= 1.8


def test_exact_realizability_for_arbitrary_beta_and_augmented_state_independence() -> None:
    assert realizability_identity_error() <= 1e-14

    def beta(point: np.ndarray) -> np.ndarray:
        x, y, z = point
        return np.asarray((y + z**2, np.sin(x) - z, x * y + np.cos(z)))

    point = np.asarray((0.2, -0.1, 0.3))
    assert np.allclose(realized_tangent_one_form(beta, point, 0.63), beta(point), atol=1e-14)
    assert tuple(inspect.signature(realized_tangent_one_form).parameters) == ("beta", "point", "rho")


def test_frozen_no_go_counterexample_matrix() -> None:
    cases = {case["case_id"]: case for case in counterexample_matrix()}
    assert list(cases) == ["C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "P1"]
    assert abs(cases["C1"]["omega_uv"]) > 0.1
    assert abs(cases["C1"]["response_curvature_uv"]) <= 1e-8
    assert abs(cases["C2"]["omega_uv"]) <= 1e-8
    assert abs(cases["C2"]["response_curvature_uv"]) > 0.5
    assert np.allclose(cases["C3"]["kappa_values"], [-1.0, 0.0, 1.0], atol=1e-7)
    assert cases["C3"]["max_alignment_error"] <= 1e-7
    assert cases["C4"]["readout_coefficients"] == [-2.0, 0.0, 3.0]
    assert cases["C4"]["projective_vs_analytic_connection_error"] <= 1e-7
    assert max(cases["C4"]["max_coefficient_identity_errors"]) <= 1e-7
    assert cases["C5"]["disposition"] == "INELIGIBLE_TAUTOLOGY"
    assert cases["C5"]["pointwise_quotient"] == pytest.approx(-0.6)
    assert cases["C5"]["quotient_identity_error"] <= 1e-10
    assert abs(cases["C6"]["independent_constant_state_omega_uv"]) <= 1e-10
    assert cases["C6"]["coarse_odd_remainder"] > cases["C6"]["fine_odd_remainder"]
    assert cases["C6"]["coarse_to_fine_even_reduction"] > 100.0


@pytest.mark.parametrize("case_id", list(EXPECTED_CASE_DISPOSITIONS))
def test_every_case_disposition_mutation_breaks_complete_mapping(case_id: str) -> None:
    cases = counterexample_matrix()
    assert case_dispositions_match(cases)
    mutation = copy.deepcopy(cases)
    next(case for case in mutation if case["case_id"] == case_id)["disposition"] = "MUTATED"
    assert not case_dispositions_match(mutation)


def test_three_dimensional_deliberately_aligned_oracle_is_local_only() -> None:
    result = positive_control()
    assert result["disposition"] == "PASS_LOCAL_INTERNAL"
    assert result["frozen_kappa"] == 2.0
    assert result["area_rank"] == 3
    assert result["normalized_area_condition"] <= 3.01
    assert result["heldout_cosine_max"] < 0.9
    assert result["max_tensor_error"] <= 1e-6
    assert result["heldout_absolute_error"] <= 1e-6
    assert result["control_role"] == "deliberately_aligned_oracle_positive_implementation_control"


def test_gauge_and_coordinate_covariance() -> None:
    result = covariance_checks()
    assert max(result.values()) <= 1e-7


def test_fixed_gap_nonnormal_case_is_explicitly_out_of_scope() -> None:
    result = nonnormal_fixed_gap_case()
    assert result["disposition"] == "OUT_OF_SCOPE"
    assert result["minimum_gap"] == 1.0
    assert result["right_only_curvature"] == 0.0
    assert result["biorthogonal_curvature"] == [-2.0, 2.0]
    assert result["nonnormal_commutator_norm"] > 0.1


def test_continuous_stable_ode_rates_and_alpha_mapping() -> None:
    beta = rotational_one_form(1.0)
    center = np.asarray((0.3, -0.2))
    target = math.pi * 0.2**2
    periods = [16.0, 32.0, 64.0, 128.0]
    errors: dict[str, list[float]] = {"equilibrium": [], "periodic": []}
    for initialization in errors:
        for period in periods:
            result = continuous_harmonic_cycle(
                beta,
                center,
                0.2,
                0.5,
                period,
                initialization=initialization,
                samples=16384,
            )
            errors[initialization].append(abs(result["total_response"] - target))
    assert -1.4 <= log_slope(periods, errors["equilibrium"]) <= -0.8
    assert -2.2 <= log_slope(periods, errors["periodic"]) <= -1.7
    alpha = alpha_from_dt(0.02, 0.4)
    assert 1.0 - alpha == math.exp(-0.02 / 0.4)


def test_driven_decay_does_not_supply_frozen_branch_inverse() -> None:
    result = propagator_decay_without_frozen_invertibility()
    assert result["uniform_frozen_inverse_exists"] is False
    assert result["frozen_jacobian_at_pi_over_two"] == 0.0
    assert result["sampled_max_prefactor_ratio"] <= result["decay_prefactor_bound"] + 1e-12


def test_variable_kappa_center_approximation_includes_lipschitz_term() -> None:
    bound = conditional_alignment_bound(
        0.2,
        0.03,
        0.004,
        kappa_lipschitz=0.5,
        omega_comass_sup=0.4,
        surface_diameter=0.1,
    )
    assert bound == pytest.approx(0.014)
    assert conditional_alignment_bound(0.2, 0.03, 0.004) == pytest.approx(0.01)


def test_program_disposition_is_analytic_only_and_all_gates_pass() -> None:
    summary, records = execute_program()
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert summary["central_empirical_external_claim_status"] == "PROOF_INCOMPLETE"
    assert summary["numerics_prove_theorem"] is False
    assert summary["no_study_pass"] is True
    assert summary["failed_gates"] == []
    assert all(gate["status"] == "pass" for gate in summary["gates"])
    assert any(record["record_type"] == "alignment_characterization" for record in records)


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
    assert result == {
        "status": "PASS_INTERNAL_ANALYTIC",
        "evidence_status": "NO_EMPIRICAL_EVIDENCE",
        "artifact_count": 5,
        "source_count": 9,
    }
    for path in paths.values():
        raw = path.read_bytes()
        assert b"\r" not in raw
        if path.suffix == ".json":
            json.loads(raw.decode("utf-8"))

    (output / "hidden").mkdir()
    (output / "hidden" / "result.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ArtifactVerificationError, match="closure mismatch"):
        verify_artifacts(output)


def test_source_hash_domain_and_cli_are_portable_and_non_empirical() -> None:
    assert canonical_source_text_bytes(b"a\r\nb\r\n") == b"a\nb\n"
    with pytest.raises(ValueError, match="bare CR"):
        canonical_source_text_bytes(b"a\rb")
    with pytest.raises(ValueError, match="BOM"):
        canonical_source_text_bytes(b"\xef\xbb\xbfa")

    command_names = set(get_command(app).commands)
    assert command_names == {"status", "run", "verify"}
    assert not {"confirm", "study", "outcome", "external"}.intersection(command_names)
    result = RUNNER.invoke(app, ["status"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert payload["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"

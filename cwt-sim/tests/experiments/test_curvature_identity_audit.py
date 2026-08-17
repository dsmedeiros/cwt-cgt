"""Focused analytic, fail-closed, and provenance tests for the identity audit."""

from __future__ import annotations

import copy
import json
import math
import shutil
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import numpy as np
import pytest
from typer.testing import CliRunner

from experiments.curvature_identity_audit import artifacts, run as audit_run
from experiments.curvature_identity_audit.artifacts import (
    ArtifactGenerationRefused,
    ArtifactVerificationError,
    canonical_source_text_bytes,
    expected_artifact_bytes,
    predecessor_inventories,
    preflight_artifact_destination,
    recursive_raw_inventory,
    render_report,
    require_semantic_pass,
    source_hashes,
    verify_artifacts,
)
from experiments.curvature_identity_audit.benchmark_c import (
    EXPECTED_J_XK_RESPONSE_GRADIENT,
    EXPECTED_J_XP_RESPONSE_CENTER,
    EXPECTED_OMEGA_CENTER,
    EXPECTED_QUOTIENT_CENTER,
    EXPECTED_QUOTIENT_GRADIENT,
    EXPECTED_RESPONSE_CENTER,
    analytic_branch,
    benchmark_c_certificate,
    exact_center_certificate,
)
from experiments.curvature_identity_audit.benchmark_d import (
    benchmark_d_certificate,
    exact_stationary_population,
    projective_lift,
)
from experiments.curvature_identity_audit.classifier import (
    Gate,
    apply_fail_only_overrides,
    case_dispositions,
    gate_owner,
    registry_gate_names,
)
from experiments.curvature_identity_audit.common_origin import (
    common_origin_certificate,
    future_alignment_requirements,
    obstruction_certificate,
    refusal_certificate,
)
from experiments.curvature_identity_audit.contract import (
    CANONICAL_CASE_DISPOSITION_ITEMS,
    CANONICAL_CASE_GATE_OWNERSHIP,
    MODEL_CONTRACT,
    canonical_registry_record,
    case_gate_ownership,
    expected_case_dispositions,
)
from experiments.curvature_identity_audit.qp1 import (
    analytic_connection_x,
    analytic_curvature,
    qp1_certificate,
)
from experiments.curvature_identity_audit.theorem import (
    build_certificates,
    execute_program,
    natural_gate_inputs,
)


@pytest.fixture(scope="module")
def program_result():
    return execute_program()


def _fraction(item: dict[str, object]) -> Fraction:
    return Fraction(int(item["numerator"]), int(item["denominator"]))


def test_program_is_internal_analytic_only(program_result) -> None:
    summary, records = program_result
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert summary["all_gates_pass"] is True
    assert summary["failed_gates"] == []
    assert summary["case_dispositions"] == expected_case_dispositions()
    assert len(summary["gates"]) == 25
    assert records


def test_live_gate_registry_has_exact_unique_ownership(program_result) -> None:
    summary, _ = program_result
    flattened = [name for _, names in case_gate_ownership() for name in names]
    assert len(flattened) == len(set(flattened))
    assert tuple(flattened) == registry_gate_names()
    assert {item["name"] for item in summary["gates"]} == set(flattened)


def test_canonical_registry_is_immutable_ordered_and_independently_fingerprinted(program_result) -> None:
    summary, _ = program_result
    record = canonical_registry_record()
    assert isinstance(CANONICAL_CASE_DISPOSITION_ITEMS, tuple)
    assert isinstance(CANONICAL_CASE_GATE_OWNERSHIP, tuple)
    assert tuple(item["case_id"] for item in record["case_dispositions"]) == tuple(
        case_id for case_id, _ in CANONICAL_CASE_DISPOSITION_ITEMS
    )
    assert tuple(item["case_id"] for item in record["gate_ownership"]) == tuple(
        case_id for case_id, _ in CANONICAL_CASE_GATE_OWNERSHIP
    )
    assert len(record["case_dispositions_sha256"]) == 64
    assert len(record["gate_ownership_sha256"]) == 64
    assert record["case_dispositions_sha256"] != record["gate_ownership_sha256"]
    assert summary["canonical_registry"] == record
    with pytest.raises(TypeError):
        CANONICAL_CASE_GATE_OWNERSHIP[0][1][0] = "relabelled"  # type: ignore[index]


def test_cross_owner_relabel_or_swap_cannot_classify() -> None:
    natural = natural_gate_inputs(build_certificates())
    gates = apply_fail_only_overrides(natural)
    relabelled = list(gates)
    relabelled[0] = Gate(
        name=gates[-1].name,
        natural_passed=True,
        passed=True,
        requirement=gates[0].requirement,
        observed=gates[0].observed,
    )
    with pytest.raises(RuntimeError, match="ordered unique canonical"):
        case_dispositions(relabelled)
    swapped = list(gates)
    swapped[0], swapped[-1] = swapped[-1], swapped[0]
    with pytest.raises(RuntimeError, match="ordered unique canonical"):
        case_dispositions(swapped)


@pytest.mark.parametrize("gate_name", registry_gate_names())
def test_every_gate_mutation_fails_its_owned_case(gate_name: str) -> None:
    summary, _ = execute_program(gate_overrides={gate_name: False})
    owner = gate_owner(gate_name)
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert gate_name in summary["failed_gates"]
    assert summary["case_dispositions"][owner].startswith("FAIL_INTERNAL_ANALYTIC:")


@pytest.mark.parametrize("gate_name", registry_gate_names())
def test_true_override_cannot_rescue_a_natural_failure(gate_name: str) -> None:
    certificates = build_certificates()
    natural = natural_gate_inputs(certificates)
    requirement, observed = natural[gate_name][1:]
    mutated = dict(natural)
    mutated[gate_name] = (False, requirement, observed)
    gates = apply_fail_only_overrides(mutated, {gate_name: True})
    gate = next(item for item in gates if item.name == gate_name)
    owner = gate_owner(gate_name)
    assert gate.natural_passed is False
    assert gate.passed is False
    assert case_dispositions(gates)[owner].startswith("FAIL_INTERNAL_ANALYTIC:")


def test_unknown_or_nonboolean_override_is_refused() -> None:
    with pytest.raises(KeyError):
        execute_program(gate_overrides={"unknown": False})
    with pytest.raises(TypeError):
        execute_program(gate_overrides={registry_gate_names()[0]: 1})  # type: ignore[dict-item]


def test_contract_mutation_cannot_be_rescued() -> None:
    invalid = replace(MODEL_CONTRACT, fitted_or_pointwise_normalization_allowed=True)
    summary, _ = execute_program(invalid, {"alignment_refusal_matrix": True, "claim_ceiling": True})
    assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
    assert "alignment_refusal_matrix" in summary["failed_gates"]
    assert "claim_ceiling" in summary["failed_gates"]


def test_common_origin_theorem_is_exactly_branch_tangent() -> None:
    certificate = common_origin_certificate()
    assert certificate["necessary"] is True
    assert certificate["sufficient"] is True
    assert certificate["alignment_coefficient"] == "kappa in C^infty(Lambda;R)"
    assert certificate["response_one_form_pullback"] == "B_R=sigma^*beta_R in Omega^1(Lambda)"
    assert certificate["berry_connection_pullback"] == "A_Lambda=sigma^*P^*a_B in Omega^1(U)"
    assert certificate["necessary_and_sufficient_condition"] == (
        "sigma^*(d beta_R)-kappa sigma^*(P^*omega_FS)=0"
    )
    assert certificate["ambient_equality_not_required"] is True
    assert certificate["off_branch_normal_components_unconstrained"] is True


def test_local_and_global_obstructions_are_not_collapsed() -> None:
    certificate = obstruction_certificate()
    assert "d(B_R-kappa*A_Lambda)=0" in certificate["constant_kappa_local_statement"]
    assert "B_R-kappa*A_Lambda=d chi" in certificate["constant_kappa_local_statement"]
    assert "dkappa wedge A_Lambda" in certificate["variable_kappa_warning"]
    assert "pulled-back periods" in certificate["noncontractible_period_condition"]
    assert certificate["periods_required"] is True
    assert certificate["chern_flux_required"] is True
    assert certificate["global_smooth_connection_claimed"] is False


def test_invalid_alignment_shortcuts_are_refused() -> None:
    certificate = refusal_certificate()
    assert certificate["all_refused"] is True
    assert all(certificate["refused"].values())
    assert "one-dimensional" in certificate["two_dimensional_reason"]


def test_future_positive_alignment_is_not_instantiated() -> None:
    requirements = future_alignment_requirements()
    assert requirements["minimum_full_rank_area_directions"] == 3
    assert requirements["heldout_oblique_direction_required"] is True
    assert requirements["pointwise_division_forbidden"] is True
    assert requirements["tensor_map_frozen_before_response"] is True
    assert requirements["current_audit_supplies_future_alignment_pass"] is False


def test_qp1_exact_connection_curvature_gap_and_chern() -> None:
    certificate = qp1_certificate()
    assert analytic_connection_x(0.5) == pytest.approx(math.pi)
    assert analytic_curvature(0.5) == pytest.approx(-(math.pi**2))
    assert certificate["gap_interval"] == ["1/5", "3/5"]
    assert certificate["chern_integral"] == "integral_[0,1]x[0,1] Omega=-2*pi"
    assert certificate["chern_number"] == -1
    assert certificate["global_smooth_connection_exists"] is False


def test_qp1_kubo_sign_and_factor_are_explicit() -> None:
    certificate = qp1_certificate()
    assert certificate["positive_observable_result"] == "K_[xy]=(K_xy-K_yx)/2=+Omega_xy"
    assert certificate["conventional_observable_result"] == "K_[xy]=-Omega_xy"
    assert certificate["full_antisymmetrization"] == "K_xy-K_yx=2*K_[xy]"
    assert certificate["finite_speed_response_claimed"] is False
    assert certificate["live_cwt_response_claimed"] is False


def test_qp1_spectral_evaluation_is_regression_only() -> None:
    regression = qp1_certificate()["regression"]
    assert regression["role"] == "numerical_spectral_implementation_regression_not_proof"
    assert regression["maximum_positive_sign_error"] < 1.0e-7
    assert regression["maximum_conventional_negative_sign_error"] < 1.0e-7
    assert regression["maximum_projector_error"] < 1.0e-12


def test_qp1_semantic_mutation_fails_naturally() -> None:
    certificates = build_certificates()
    certificates["qp1"]["positive_observable_result"] = "wrong sign"
    natural = natural_gate_inputs(certificates)
    assert natural["qp1_kubo_sign_and_antisymmetrization"][0] is False


def test_benchmark_c_exact_center_and_nonconstant_quotient() -> None:
    center = exact_center_certificate()
    assert _fraction(center["omega_center"]) == EXPECTED_OMEGA_CENTER
    assert _fraction(center["response_curvature_center"]) == EXPECTED_RESPONSE_CENTER
    assert _fraction(center["quotient_center"]) == EXPECTED_QUOTIENT_CENTER
    assert tuple(_fraction(item) for item in center["quotient_gradient"]) == EXPECTED_QUOTIENT_GRADIENT
    assert center["quotient_gradient_nonzero"] is True


def test_benchmark_c_branch_matches_core_without_clip() -> None:
    certificate = benchmark_c_certificate()
    regression = certificate["core_branch_regression"]
    assert regression["maximum_probability_error"] < 1.0e-12
    assert regression["maximum_phase_error"] < 1.0e-12
    assert regression["maximum_kernel_error"] < 1.0e-12
    probability, theta, kernel = analytic_branch(0.0, 0.0)
    assert np.array_equal(probability, np.full(3, 1.0 / 3.0))
    assert np.array_equal(theta, np.zeros(3))
    assert np.allclose(
        kernel,
        np.asarray(
            [
                [0.64, 0.18, 0.18],
                [0.18, 0.64, 0.18],
                [0.18, 0.18, 0.64],
            ]
        ),
    )


def test_benchmark_c_exact_response_decomposition() -> None:
    center = exact_center_certificate()
    decomposition = center["decomposition"]
    assert center["response_exterior_derivative_formula"] == "d beta_R=-m dJ_x wedge dtheta"
    assert center["phase_gradient_total_derivative_formula"] == ("dJ_x=J_xp dp+J_xx dtheta+J_xK dK")
    assert center["J_xx_is_symmetric_hessian"] is True
    assert _fraction(decomposition["response_curvature_J_xp_dp"]["center"]) == (EXPECTED_J_XP_RESPONSE_CENTER)
    assert (
        tuple(_fraction(item) for item in decomposition["response_curvature_J_xK_dK"]["gradient"])
        == EXPECTED_J_XK_RESPONSE_GRADIENT
    )
    assert any(_fraction(item) != 0 for item in decomposition["response_curvature_J_xK_dK"]["gradient"])
    for name in ("response_curvature_J_xx_dtheta", "response_curvature_d2theta"):
        assert _fraction(decomposition[name]["center"]) == 0
        assert all(_fraction(item) == 0 for item in decomposition[name]["gradient"])
    assert _fraction(center["decomposition_residual"]["center"]) == 0
    assert all(_fraction(item) == 0 for item in center["decomposition_residual"]["gradient"])
    assert all(_fraction(item) == 0 for item in center["theta_hessian_antisymmetric_residual"])


def test_benchmark_c_decomposition_mutations_fail_naturally() -> None:
    def assert_failed(mutator) -> None:
        certificates = build_certificates()
        mutator(certificates["benchmark_c"]["center"])
        natural = natural_gate_inputs(certificates)
        assert natural["benchmark_c_exact_response_decomposition"][0] is False

    assert_failed(lambda center: center.__setitem__("response_exterior_derivative_formula", "wrong"))
    assert_failed(lambda center: center.__setitem__("J_xx_is_symmetric_hessian", False))
    assert_failed(
        lambda center: center["decomposition"]["response_curvature_J_xp_dp"]["center"].__setitem__(
            "numerator", 0
        )
    )
    assert_failed(
        lambda center: center["decomposition"]["response_curvature_J_xK_dK"]["gradient"][0].__setitem__(
            "numerator", 0
        )
    )
    assert_failed(lambda center: center["decomposition_residual"]["center"].__setitem__("numerator", 1))


def test_benchmark_c_gain_scaling_and_nulls_are_exact() -> None:
    certificate = benchmark_c_certificate()
    assert _fraction(certificate["gain_zero_response"]) == 0
    assert _fraction(certificate["alpha_one_response"]) == 0
    assert certificate["gain_scaling_exact"] is True
    assert certificate["omega_independent_of_gain_and_alpha"] is True


def test_benchmark_c_numerics_are_regressions_only() -> None:
    certificate = benchmark_c_certificate()
    regression = certificate["numerical_regressions"]
    assert regression["role"] == "finite_difference_and_wilson_implementation_regressions_not_proof"
    assert regression["response_absolute_error"] < 1.0e-9
    assert regression["projective_absolute_error"] < 1.0e-9
    assert regression["wilson_absolute_error"] < 1.0e-8
    assert certificate["finite_difference_or_wilson_used_as_analytic_acceptance"] is False


def test_benchmark_c_cycle_sum_is_not_legacy_mean() -> None:
    certificate = benchmark_c_certificate()
    assert certificate["response_statistic_scope"] == "fixed_tick_cycle_sum_not_legacy_mean"
    assert certificate["legacy_mean_is_same_curvature_response"] is False


def test_benchmark_c_semantic_mutation_fails_naturally() -> None:
    certificates = build_certificates()
    certificates["benchmark_c"]["center"]["omega_center"]["numerator"] = 8
    natural = natural_gate_inputs(certificates)
    assert natural["benchmark_c_exact_berry_pullback"][0] is False


def test_benchmark_d_stationary_branch_is_exact_positive_and_unrepaired() -> None:
    certificate = benchmark_d_certificate()
    assert all(_fraction(item) == 0 for item in certificate["center_stationary_residual"])
    assert _fraction(certificate["center_trace"]) == 1
    assert _fraction(certificate["uniform_positive_lower_bound"]) == Fraction(4, 69)
    assert certificate["encoding_probability_floor_applied"] is False
    assert certificate["encoding_clip_applied"] is False
    assert certificate["encoding_projection_or_normalization_repair_applied"] is False


def test_benchmark_d_projective_lift_is_actual_real_stationary_branch() -> None:
    population = exact_stationary_population(Fraction(3, 100), Fraction(9, 40))
    psi = projective_lift(population)
    assert np.vdot(psi, psi).real == pytest.approx(1.0, abs=1.0e-15)
    assert np.max(np.abs(psi.imag)) == 0.0
    certificate = benchmark_d_certificate()
    assert certificate["projective_curvature_fraction"] == "0/1"
    assert certificate["projective_regression"]["projective_curvature"] == 0.0
    assert certificate["auxiliary_or_authored_constant_state_used"] is False
    assert certificate["finite_step_branch_used"] is False


@pytest.mark.parametrize(
    "population",
    [
        [Fraction(0), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4), Fraction(1, 4)],
        [Fraction(1, 6)] * 5,
    ],
)
def test_benchmark_d_projective_lift_refuses_invalid_population(population) -> None:
    with pytest.raises(ValueError):
        projective_lift(population)


def test_benchmark_d_same_A_c_O_has_zero_set_obstruction() -> None:
    certificate = benchmark_d_certificate()
    assert certificate["same_A_c_O_provenance"] is True
    assert certificate["model_identity_sha256"] == certificate["geometry_model_identity_sha256"]
    assert certificate["model_identity_sha256"] == certificate["response_model_identity_sha256"]
    response = certificate["response_oracle"]["response_curvature_bd"]
    assert response["fraction"] == "-28888766872100000000000/235345963257301712101"
    assert certificate["response_curvature_nonzero"] is True
    assert certificate["finite_scalar_kappa_exists_at_center"] is False
    assert certificate["zero_preserving_homogeneous_linear_tensor_map_can_match"] is False
    assert certificate["arbitrary_nonlinear_or_affine_omega_only_map_ruled_out"] is False
    assert "finite scalar" in certificate["zero_set_obstruction"]
    assert "zero-preserving homogeneous linear" in certificate["zero_set_obstruction"]


@pytest.mark.parametrize(
    "field,value",
    [
        ("finite_scalar_kappa_exists_at_center", True),
        ("zero_preserving_homogeneous_linear_tensor_map_can_match", True),
        ("arbitrary_nonlinear_or_affine_omega_only_map_ruled_out", True),
    ],
)
def test_benchmark_d_zero_set_scope_mutation_fails(field: str, value: bool) -> None:
    certificates = build_certificates()
    certificates["benchmark_d"][field] = value
    natural = natural_gate_inputs(certificates)
    assert natural["benchmark_d_zero_set_obstruction"][0] is False


def test_benchmark_d_mixed_density_statement_is_separate() -> None:
    certificate = benchmark_d_certificate()
    assert certificate["projective_encoding_is_mixed_density"] is False
    assert certificate["mixed_density_used_to_prove_projective_zero"] is False
    assert "separate commuting" in certificate["mixed_density_statement"]


def test_benchmark_d_semantic_mutation_fails_naturally() -> None:
    certificates = build_certificates()
    certificates["benchmark_d"]["response_model_identity_sha256"] = "0" * 64
    natural = natural_gate_inputs(certificates)
    assert natural["benchmark_d_shared_model_provenance"][0] is False


def test_canonical_source_hash_domain_is_lf_only() -> None:
    assert canonical_source_text_bytes(b"alpha\r\nbeta\r\n") == b"alpha\nbeta\n"
    assert canonical_source_text_bytes(b"alpha\nbeta\n") == b"alpha\nbeta\n"
    with pytest.raises(ValueError):
        canonical_source_text_bytes(b"\xef\xbb\xbfalpha\n")
    with pytest.raises(ValueError):
        canonical_source_text_bytes(b"alpha\rbeta\n")
    with pytest.raises(ValueError):
        canonical_source_text_bytes(b"\xff")


def test_recursive_predecessor_inventory_is_path_and_type_bound(tmp_path: Path) -> None:
    root = tmp_path / "tree"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "a.txt").write_bytes(b"a")
    (nested / "b.json").write_bytes(b"{}\n")
    first = recursive_raw_inventory(root)
    assert first["entries"]["a.txt"]["type"] == "file"
    assert first["entries"]["nested"]["type"] == "directory"
    assert first["entries"]["nested/b.json"]["type"] == "file"
    (nested / "extra.bin").write_bytes(b"x")
    second = recursive_raw_inventory(root)
    assert first["inventory_sha256"] != second["inventory_sha256"]


def test_recursive_inventory_refuses_link_or_reparse(monkeypatch, tmp_path: Path) -> None:
    root = tmp_path / "tree"
    root.mkdir()
    bad = root / "bad"
    bad.write_bytes(b"x")
    original = artifacts._is_link_or_reparse
    monkeypatch.setattr(
        artifacts,
        "_is_link_or_reparse",
        lambda path: path.name == "bad" or original(path),
    )
    with pytest.raises(ArtifactVerificationError, match="link/reparse"):
        recursive_raw_inventory(root)


def test_recursive_inventory_refuses_actual_ancestor_symlink(tmp_path: Path) -> None:
    anchor = tmp_path / "anchor"
    anchor.mkdir()
    real_parent = tmp_path / "outside_real_parent"
    root = real_parent / "tree"
    root.mkdir(parents=True)
    (root / "payload.json").write_bytes(b"{}\n")
    linked_parent = anchor / "linked_parent"
    try:
        linked_parent.symlink_to(real_parent, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create the required directory symlink: {exc}")
    with pytest.raises(ArtifactVerificationError, match="ancestor is a link/reparse"):
        recursive_raw_inventory(linked_parent / "tree", trust_anchor=anchor)

    original = artifacts._is_link_or_reparse
    try:
        artifacts._is_link_or_reparse = lambda _path: False
        with pytest.raises(ArtifactVerificationError, match="resolved path escapes"):
            recursive_raw_inventory(linked_parent / "tree", trust_anchor=anchor)
    finally:
        artifacts._is_link_or_reparse = original


def test_recursive_inventory_refuses_reparse_ancestor(monkeypatch, tmp_path: Path) -> None:
    anchor = tmp_path / "anchor"
    middle = anchor / "middle"
    root = middle / "tree"
    root.mkdir(parents=True)
    (root / "payload.json").write_bytes(b"{}\n")
    original = artifacts._is_link_or_reparse
    monkeypatch.setattr(
        artifacts,
        "_is_link_or_reparse",
        lambda path: path == middle or original(path),
    )
    with pytest.raises(ArtifactVerificationError, match="ancestor is a link/reparse"):
        recursive_raw_inventory(root, trust_anchor=anchor)


def test_live_predecessor_artifacts_are_three_exact_ordinary_closures() -> None:
    inventories = predecessor_inventories()
    assert set(inventories) == {
        "benchmark_c_independent_response",
        "generic_response_theorem",
        "benchmark_d_lindblad_response",
    }
    for inventory in inventories.values():
        assert inventory["entry_count"] >= 4
        assert len(inventory["inventory_sha256"]) == 64
        assert all(item["type"] in {"file", "directory"} for item in inventory["entries"].values())


@pytest.mark.parametrize(
    "destination",
    [
        artifacts.EXPERIMENT_DIR,
        artifacts.EXPERIMENT_DIR / "alternate_output",
        artifacts.ARTIFACTS_DIR / "nested",
        next(iter(artifacts.PREDECESSOR_ARTIFACT_DIRS.values())) / "nested",
        artifacts.REPO_ROOT,
    ],
)
def test_artifact_destination_overlap_is_refused_before_write(destination: Path) -> None:
    existed = destination.exists()
    with pytest.raises(ArtifactGenerationRefused, match="overlap"):
        preflight_artifact_destination(destination)
    assert destination.exists() is existed


def test_artifact_destination_reparse_is_refused_without_touching_target(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    linked = tmp_path / "linked"
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"host cannot create the required directory symlink: {exc}")
    before = tuple(target.iterdir())
    with pytest.raises(ArtifactGenerationRefused, match="link/reparse"):
        preflight_artifact_destination(linked)
    assert tuple(target.iterdir()) == before


def test_existing_destination_nested_tree_is_refused_before_write(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    nested = destination / "hidden"
    nested.mkdir(parents=True)
    (nested / "outcome.json").write_bytes(b"{}\n")
    before = recursive_raw_inventory(destination, trust_anchor=tmp_path)
    with pytest.raises(ArtifactGenerationRefused, match="non-file entry"):
        artifacts.write_artifacts(destination)
    assert recursive_raw_inventory(destination, trust_anchor=tmp_path) == before


def test_existing_destination_reparse_entry_is_refused_before_write(
    monkeypatch,
    tmp_path: Path,
) -> None:
    destination = tmp_path / "artifacts"
    destination.mkdir()
    artifact_file = destination / "summary.json"
    artifact_file.write_bytes(b"do-not-touch\n")
    original = artifacts._is_link_or_reparse
    monkeypatch.setattr(
        artifacts,
        "_is_link_or_reparse",
        lambda path: path == artifact_file or original(path),
    )
    before = artifact_file.read_bytes()
    with pytest.raises(ArtifactGenerationRefused, match="link/reparse entry"):
        artifacts.write_artifacts(destination)
    assert artifact_file.read_bytes() == before


def test_write_refusal_preserves_every_predecessor_byte_and_tree() -> None:
    before = predecessor_inventories()
    destination = next(iter(artifacts.PREDECESSOR_ARTIFACT_DIRS.values())) / "forbidden_output"
    assert not destination.exists()
    with pytest.raises(ArtifactGenerationRefused, match="overlap"):
        artifacts.write_artifacts(destination)
    assert not destination.exists()
    assert predecessor_inventories() == before


def test_write_refusal_preserves_source_tree_before_any_byte_write() -> None:
    before = recursive_raw_inventory(artifacts.EXPERIMENT_DIR, trust_anchor=artifacts.SIM_ROOT)
    destination = artifacts.EXPERIMENT_DIR / "forbidden_alternate_output"
    assert not destination.exists()
    with pytest.raises(ArtifactGenerationRefused, match="overlap"):
        artifacts.write_artifacts(destination)
    assert not destination.exists()
    assert (
        recursive_raw_inventory(
            artifacts.EXPERIMENT_DIR,
            trust_anchor=artifacts.SIM_ROOT,
        )
        == before
    )


def test_source_hash_closure_includes_every_clean_module_and_test() -> None:
    hashes = source_hashes()
    assert set(artifacts.CLEAN_CLI_LOCAL_MODULE_PATHS).issubset(hashes)
    assert "tests/experiments/test_curvature_identity_audit.py" in hashes
    assert all(item["hash_domain"] == "sha256_utf8_lf_v1" for item in hashes.values())
    assert all(len(item["sha256"]) == 64 for item in hashes.values())


def test_semantic_validator_rejects_duplicate_shadow_and_forged_gate_lists() -> None:
    summary, _ = execute_program()
    require_semantic_pass(summary)

    duplicate = copy.deepcopy(summary)
    duplicate["gates"][-1] = copy.deepcopy(duplicate["gates"][0])
    assert len(duplicate["gates"]) == 25
    with pytest.raises(ArtifactGenerationRefused):
        require_semantic_pass(duplicate)

    forged = copy.deepcopy(summary)
    forged["gates"] = [
        {
            "name": f"forged_gate_{index:02d}",
            "status": "pass",
            "natural_status": "pass",
            "requirement": "forged",
            "observed": {},
        }
        for index in range(25)
    ]
    with pytest.raises(ArtifactGenerationRefused):
        require_semantic_pass(forged)


def test_semantic_validator_rejects_registry_case_and_natural_status_mutations() -> None:
    summary, _ = execute_program()
    mutations = []

    registry = copy.deepcopy(summary)
    registry["canonical_registry"]["gate_ownership"][0]["gate_names"][0] = "relabelled"
    mutations.append(registry)

    cases = copy.deepcopy(summary)
    cases["case_dispositions"]["T0"], cases["case_dispositions"]["QP1"] = (
        cases["case_dispositions"]["QP1"],
        cases["case_dispositions"]["T0"],
    )
    mutations.append(cases)

    natural = copy.deepcopy(summary)
    natural["gates"][0]["natural_status"] = "fail"
    mutations.append(natural)

    for mutated in mutations:
        with pytest.raises(ArtifactGenerationRefused):
            require_semantic_pass(mutated)


def test_semantic_validator_binds_claim_and_duplicate_contract_status_fields() -> None:
    summary, records = execute_program()
    require_semantic_pass(summary, records)

    summary_mutations = []
    top_level_claim = copy.deepcopy(summary)
    top_level_claim["claim_ceiling"] = "UNIVERSAL_CWT_CGT_ALIGNMENT_PROVED"
    summary_mutations.append(top_level_claim)

    claim_gate = copy.deepcopy(summary)
    claim_row = next(item for item in claim_gate["gates"] if item["name"] == "claim_ceiling")
    claim_row["observed"]["claim_ceiling"] = "UNIVERSAL_CWT_CGT_ALIGNMENT_PROVED"
    summary_mutations.append(claim_gate)

    experiment = copy.deepcopy(summary)
    experiment["experiment_id"] = "forged_identity_audit"
    summary_mutations.append(experiment)

    duplicate_status = copy.deepcopy(summary)
    duplicate_status["status"] = "PASS_INTERNAL_ANALYTIC"
    summary_mutations.append(duplicate_status)

    duplicate_gate_status = copy.deepcopy(summary)
    duplicate_gate_status["gates"][0]["result_status"] = "pass"
    summary_mutations.append(duplicate_gate_status)

    for mutated in summary_mutations:
        with pytest.raises(ArtifactGenerationRefused):
            require_semantic_pass(mutated, records)

    contract_claim = copy.deepcopy(records)
    contract_claim[0]["value"]["claim_ceiling"] = "UNIVERSAL_CWT_CGT_ALIGNMENT_PROVED"

    contract_status = copy.deepcopy(records)
    contract_status[0]["value"]["disposition"] = "UNIVERSAL_PASS"

    gate_status = copy.deepcopy(records)
    gate_record = next(item for item in gate_status if item["record_type"] == "gate")
    gate_record["natural_status"] = "fail"

    certificate_claim = copy.deepcopy(records)
    certificate_record = next(item for item in certificate_claim if item["record_type"] == "certificate")
    certificate_record["value"]["claim_ceiling"] = "UNIVERSAL_CWT_CGT_ALIGNMENT_PROVED"

    for mutated_records in [contract_claim, contract_status, gate_status, certificate_claim]:
        with pytest.raises(ArtifactGenerationRefused):
            require_semantic_pass(summary, mutated_records)


def test_claim_ceiling_mutation_refuses_render_artifacts_and_every_cli_surface(
    monkeypatch,
    tmp_path: Path,
) -> None:
    summary, records = execute_program()
    mutated = copy.deepcopy(summary)
    mutated["claim_ceiling"] = "UNIVERSAL_CWT_CGT_ALIGNMENT_PROVED"
    canonical_before = recursive_raw_inventory(
        artifacts.ARTIFACTS_DIR,
        trust_anchor=artifacts.SIM_ROOT,
    )

    with pytest.raises(ArtifactGenerationRefused):
        render_report(mutated)

    monkeypatch.setattr(artifacts, "execute_program", lambda: (mutated, records))
    with pytest.raises(ArtifactGenerationRefused):
        expected_artifact_bytes()

    destination = tmp_path / "artifacts"
    with pytest.raises(ArtifactGenerationRefused):
        artifacts.write_artifacts(destination)
    assert not destination.exists()

    runner = CliRunner()
    run_result = runner.invoke(audit_run.app, ["run"])
    assert run_result.exit_code != 0
    assert " / NO_EMPIRICAL_EVIDENCE" not in run_result.stdout
    assert "CHECKSUMS.json:" not in run_result.stdout

    verify_result = runner.invoke(audit_run.app, ["verify"])
    assert verify_result.exit_code != 0
    assert " / NO_EMPIRICAL_EVIDENCE" not in verify_result.stdout

    monkeypatch.setattr(audit_run, "execute_program", lambda: (mutated, records))
    status_result = runner.invoke(audit_run.app, ["status"])
    assert status_result.exit_code == 2
    assert "SEMANTIC_VALIDATION_FAILED" in status_result.stdout + status_result.stderr
    assert "PASS_INTERNAL_ANALYTIC" not in status_result.stdout + status_result.stderr

    assert (
        recursive_raw_inventory(
            artifacts.ARTIFACTS_DIR,
            trust_anchor=artifacts.SIM_ROOT,
        )
        == canonical_before
    )


def test_artifact_generation_refuses_failed_semantics(monkeypatch, tmp_path: Path) -> None:
    summary, records = execute_program(gate_overrides={registry_gate_names()[0]: False})
    monkeypatch.setattr(artifacts, "execute_program", lambda: (summary, records))
    with pytest.raises(ArtifactGenerationRefused):
        artifacts.write_artifacts(tmp_path / "artifacts")
    assert not (tmp_path / "artifacts").exists()


def test_frozen_artifacts_verify_and_are_strict_lf() -> None:
    result = verify_artifacts()
    assert result["status"] == "PASS_INTERNAL_ANALYTIC"
    assert result["evidence_status"] == "NO_EMPIRICAL_EVIDENCE"
    assert result["artifact_count"] == 5
    for path in artifacts.ARTIFACTS_DIR.iterdir():
        assert b"\r" not in path.read_bytes()


def test_artifact_verifier_rejects_content_and_nested_addition(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    shutil.copytree(artifacts.ARTIFACTS_DIR, destination)
    (destination / "summary.json").write_bytes(b"{}\n")
    with pytest.raises(ArtifactVerificationError):
        verify_artifacts(destination)
    shutil.rmtree(destination)
    shutil.copytree(artifacts.ARTIFACTS_DIR, destination)
    nested = destination / "hidden"
    nested.mkdir()
    (nested / "outcome.json").write_bytes(b"{}\n")
    with pytest.raises(ArtifactVerificationError):
        verify_artifacts(destination)


def test_provenance_and_checksums_close_the_artifact_dag() -> None:
    provenance = json.loads((artifacts.ARTIFACTS_DIR / "PROVENANCE.json").read_text(encoding="utf-8"))
    checksums = json.loads((artifacts.ARTIFACTS_DIR / "CHECKSUMS.json").read_text(encoding="utf-8"))
    assert provenance["no_empirical_or_external_data"] is True
    assert provenance["no_general_alignment_claim"] is True
    assert provenance["numerical_regressions_used_as_analytic_proof"] is False
    assert set(provenance["predecessor_artifact_inventories"]) == set(artifacts.PREDECESSOR_ARTIFACT_DIRS)
    assert "predecessor_artifacts_modified" not in provenance
    nonmutation = provenance["predecessor_nonmutation_evidence"]
    assert nonmutation["unchanged"] is True
    assert nonmutation["before_inventory_sha256"] == nonmutation["after_inventory_sha256"]
    assert provenance["canonical_registry"] == canonical_registry_record()
    assert set(checksums["files"]) == {"PROVENANCE.json", "REPORT.md", "records.json", "summary.json"}


def test_cli_status_and_verify_are_fail_closed() -> None:
    runner = CliRunner()
    status = runner.invoke(audit_run.app, ["status"])
    assert status.exit_code == 0, status.stdout
    assert "PASS_INTERNAL_ANALYTIC" in status.stdout
    verify = runner.invoke(audit_run.app, ["verify"])
    assert verify.exit_code == 0, verify.stdout
    assert "NO_EMPIRICAL_EVIDENCE" in verify.stdout


@pytest.mark.parametrize("mutation", ["evidence", "status", "case", "natural_gate"])
def test_cli_status_uses_full_semantic_validator(monkeypatch, mutation: str) -> None:
    summary, records = execute_program()
    mutated = copy.deepcopy(summary)
    if mutation == "evidence":
        mutated["evidence_status"] = "EMPIRICAL_EVIDENCE"
    elif mutation == "status":
        mutated["disposition"] = "FAIL_INTERNAL_ANALYTIC"
    elif mutation == "case":
        mutated["case_dispositions"]["T0"] = "FORGED_PASS"
    else:
        mutated["gates"][0]["natural_status"] = "fail"
    monkeypatch.setattr(audit_run, "execute_program", lambda: (mutated, records))
    result = CliRunner().invoke(audit_run.app, ["status"])
    assert result.exit_code == 2
    assert "SEMANTIC_VALIDATION_FAILED" in result.stdout + result.stderr


def test_no_pass_claim_exceeds_the_model_contract(program_result) -> None:
    summary, _ = program_result
    claim = summary["claim_ceiling"].lower()
    assert "not universal cwt" in claim
    assert "not" in claim and "empirical evidence" in claim
    assert "physical" in claim

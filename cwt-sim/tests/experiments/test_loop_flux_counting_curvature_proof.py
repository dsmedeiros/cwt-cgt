from __future__ import annotations

import ast
import copy
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import replace
from fractions import Fraction
from pathlib import Path

import pytest
from typer.testing import CliRunner

from experiments.loop_flux_counting_curvature_proof import (
    artifacts as artifact_module,
    contract,
    counting_lane,
    run as run_module,
    source_lock as source_lock_module,
    theorem,
)
from experiments.loop_flux_counting_curvature_proof.contract import MODEL_CONTRACT
from experiments.loop_flux_counting_curvature_proof.counting_lane import (
    counted_q_jet,
    counting_record,
    fcs_record,
    null_record,
)
from experiments.loop_flux_counting_curvature_proof.firewall import (
    analyze_role_source,
    authenticated_role_sources,
)
from experiments.loop_flux_counting_curvature_proof.generator import (
    branch_bundle,
    chord,
    chord_derivatives,
    derivative_identities,
    drazin_identities,
    liouvillian,
)
from experiments.loop_flux_counting_curvature_proof.geometry_lane import (
    floor_record,
    flux_conjugation_record,
    flux_record,
    geometry_record,
)
from experiments.loop_flux_counting_curvature_proof.oracle_lane import exact_oracle_record
from experiments.loop_flux_counting_curvature_proof.pipeline import (
    REVIEWED_CRITERION,
    FalsificationCriterion,
    OracleCapability,
    PipelineSession,
    PipelineState,
)
from experiments.loop_flux_counting_curvature_proof.source_lock import GitIndexBinding
from experiments.loop_flux_counting_curvature_proof.transaction import (
    _RESERVED_TRANSACTION_LEAVES,
    ArtifactGenerationRefused,
    ArtifactTransactionCrash,
    ArtifactVerificationError,
    _publish_artifact_mapping,
    artifact_access_guard,
    artifact_transaction_paths,
    recover_artifact_transaction,
    sha256_bytes,
    strict_json_bytes,
)


def _transaction_generation(label: str) -> dict[str, bytes]:
    payloads = {
        "PROVENANCE.json": strict_json_bytes({"generation": label, "kind": "provenance"}),
        "REPORT.md": f"# generation {label}\n".encode(),
        "records.json": strict_json_bytes({"generation": label}),
        "summary.json": strict_json_bytes({"generation": label}),
    }
    checksums = {
        "files": {name: sha256_bytes(payload) for name, payload in sorted(payloads.items())},
        "hash_domain": "sha256_raw_bytes_v1",
        "schema_version": 1,
    }
    return {"CHECKSUMS.json": strict_json_bytes(checksums), **payloads}


def _read_generation(destination: Path) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in sorted(destination.iterdir())}


def _source_git_environment(binding: GitIndexBinding) -> dict[str, str]:
    environment = {key: value for key, value in os.environ.items() if not key.upper().startswith("GIT_")}
    environment.update(
        {
            "GIT_DIR": str(binding.git_dir),
            "GIT_INDEX_FILE": str(binding.index_file),
            "GIT_WORK_TREE": str(binding.work_tree),
            "GIT_OPTIONAL_LOCKS": "0",
        }
    )
    return environment


def _source_git(binding: GitIndexBinding, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=binding.work_tree,
        env=_source_git_environment(binding),
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def _source_git_with_input(binding: GitIndexBinding, payload: bytes, *arguments: str) -> bytes:
    return subprocess.run(
        ["git", *arguments],
        cwd=binding.work_tree,
        env=_source_git_environment(binding),
        input=payload,
        check=True,
        capture_output=True,
        timeout=30,
    ).stdout


def _trusted_git_executable() -> Path:
    discovered = shutil.which("git")
    assert discovered is not None
    resolved = Path(discovered).resolve(strict=True)
    assert resolved.is_absolute() and resolved.is_file()
    return resolved


def _trusted_python_executable() -> Path:
    resolved = Path(sys.executable).resolve(strict=True)
    assert resolved.is_absolute() and resolved.is_file()
    return resolved


def _materialize_index_checkout(
    binding: GitIndexBinding,
    checkout: Path,
    *,
    all_index_entries: bool = False,
) -> Path:
    checkout.mkdir(parents=True, exist_ok=True)
    assert not any(checkout.iterdir())
    arguments = [
        str(_trusted_git_executable()),
        "--no-replace-objects",
        "-c",
        f"safe.directory={binding.work_tree}",
        "checkout-index",
        "--force",
        f"--prefix={checkout.as_posix()}/",
    ]
    if all_index_entries:
        arguments.append("--all")
    else:
        arguments.extend(
            [
                "--",
                "cwt-sim/experiments/loop_flux_counting_curvature_proof/source_lock.py",
                "cwt-sim/experiments/loop_flux_counting_curvature_proof/transaction.py",
            ]
        )
    subprocess.run(
        arguments,
        cwd=binding.work_tree,
        env=_source_git_environment(binding),
        check=True,
        capture_output=True,
        timeout=60,
    )
    assert not (checkout / ".git").exists()
    return checkout


def _fresh_cli_environment(
    binding: GitIndexBinding | None,
    lock_path: Path | None,
    *,
    python_path: Path | None = None,
) -> dict[str, str]:
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
        and key not in {source_lock_module.SOURCE_LOCK_ENV, "PYTHONPATH"}
    }
    environment.update(
        {
            source_lock_module.GIT_EXECUTABLE_ENV: str(_trusted_git_executable()),
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1",
        }
    )
    if binding is not None:
        environment.update(
            {
                "GIT_DIR": str(binding.git_dir.resolve(strict=True)),
                "GIT_INDEX_FILE": str(binding.index_file.resolve(strict=True)),
                "GIT_WORK_TREE": str(binding.work_tree.resolve(strict=True)),
                "GIT_OPTIONAL_LOCKS": "0",
            }
        )
    if lock_path is not None:
        environment[source_lock_module.SOURCE_LOCK_ENV] = str(lock_path.resolve(strict=True))
    if python_path is not None:
        environment["PYTHONPATH"] = str(python_path.resolve(strict=True))
    return environment


def _run_fresh_source_lock_cli(
    binding: GitIndexBinding | None,
    lock_path: Path | None,
    checkout: Path,
    *,
    python_path: Path | None = None,
) -> subprocess.CompletedProcess[bytes]:
    verifier = checkout / "cwt-sim" / "experiments" / "loop_flux_counting_curvature_proof" / "source_lock.py"
    return subprocess.run(
        [str(_trusted_python_executable()), "-I", str(verifier), "verify-json"],
        cwd=checkout,
        env=_fresh_cli_environment(binding, lock_path, python_path=python_path),
        check=False,
        capture_output=True,
        timeout=90,
    )


def _run_fresh_package_verify_cli(
    binding: GitIndexBinding,
    checkout: Path,
) -> subprocess.CompletedProcess[bytes]:
    package_root = checkout / "cwt-sim" / "experiments" / "loop_flux_counting_curvature_proof"
    return subprocess.run(
        [str(_trusted_python_executable()), "-I", str(package_root / "run.py"), "verify"],
        cwd=checkout / "cwt-sim",
        env=_fresh_cli_environment(binding, package_root / "SOURCE_LOCK.json"),
        check=False,
        capture_output=True,
        timeout=180,
    )


def _add_index_file(binding: GitIndexBinding, relative: str, payload: bytes) -> None:
    destination = binding.work_tree.joinpath(*Path(relative).parts)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(payload)
    _source_git(binding, "add", "-f", "--", relative)


def _temporary_source_authority(root: Path) -> tuple[GitIndexBinding, Path]:
    work_tree = root / "worktree"
    work_tree.mkdir(parents=True)
    for relative in source_lock_module.REVIEWED_GIT_INDEX_SOURCE_PATHS:
        source = source_lock_module.REPO_ROOT.joinpath(*Path(relative).parts)
        destination = work_tree.joinpath(*Path(relative).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(source_lock_module.canonical_source_text_bytes(source.read_bytes()))
    authority_git_dir = Path(
        subprocess.run(
            ["git", "-C", str(source_lock_module.REPO_ROOT), "rev-parse", "--absolute-git-dir"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout.strip()
    )
    git_dir = root / "git"
    (git_dir / "objects" / "info").mkdir(parents=True)
    (git_dir / "refs").mkdir()
    (git_dir / "HEAD").write_bytes(f"{source_lock_module.REVIEWED_PARENT_COMMIT_OID}\n".encode("ascii"))
    (git_dir / "config").write_bytes(
        b"[core]\n\trepositoryformatversion = 0\n\tfilemode = false\n\tbare = false\n"
    )
    (git_dir / "objects" / "info" / "alternates").write_bytes(
        f"{(authority_git_dir / 'objects').as_posix()}\n".encode("utf-8")
    )
    index_file = root / "source.index"
    binding = GitIndexBinding(git_dir, index_file, work_tree, True)
    _source_git(binding, "read-tree", "HEAD")
    _source_git(binding, "add", "-f", "--", *source_lock_module.REVIEWED_GIT_INDEX_SOURCE_PATHS)
    lock_path = root / "SOURCE_LOCK.json"
    lock_path.write_bytes(source_lock_module.build_source_lock_bytes(binding))
    return binding, lock_path


def _activate_source_authority(
    monkeypatch: pytest.MonkeyPatch,
    binding: GitIndexBinding,
    lock_path: Path,
) -> None:
    monkeypatch.setenv("GIT_DIR", str(binding.git_dir))
    monkeypatch.setenv("GIT_INDEX_FILE", str(binding.index_file))
    monkeypatch.setenv("GIT_WORK_TREE", str(binding.work_tree))
    monkeypatch.setenv(source_lock_module.SOURCE_LOCK_ENV, str(lock_path))


@pytest.fixture(scope="module", autouse=True)
def source_index_authority(tmp_path_factory: pytest.TempPathFactory):
    root = tmp_path_factory.mktemp("loop-flux-source-index")
    binding, lock_path = _temporary_source_authority(root)
    names = ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE", source_lock_module.SOURCE_LOCK_ENV)
    previous = {name: os.environ.get(name) for name in names}
    os.environ.update(
        {
            "GIT_DIR": str(binding.git_dir),
            "GIT_INDEX_FILE": str(binding.index_file),
            "GIT_WORK_TREE": str(binding.work_tree),
            source_lock_module.SOURCE_LOCK_ENV: str(lock_path),
        }
    )
    try:
        yield binding, lock_path
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def test_exact_contract_and_box() -> None:
    assert not contract.contract_issues()
    assert MODEL_CONTRACT.center == (Fraction(3, 100), Fraction(9, 40), Fraction(1, 2))
    assert MODEL_CONTRACT.b_bounds == (Fraction(1, 100), Fraction(1, 20))
    assert MODEL_CONTRACT.d_bounds == (Fraction(41, 200), Fraction(49, 200))
    assert MODEL_CONTRACT.t_bounds == (Fraction(1, 3), Fraction(2, 3))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("node_count", 5.0),
        ("edge_rate", 0.2),
        ("local_curvature_only", 1),
        ("finite_time_pumping_claimed", 0),
        ("positive_general_map_claimed", 0),
        ("controls", ["b", "d", "t"]),
    ],
)
def test_contract_type_and_value_mutations_fail(field: str, value: object) -> None:
    assert contract.contract_issues(replace(MODEL_CONTRACT, **{field: value}))


def test_exact_chord_and_derivatives() -> None:
    value = chord(Fraction(1, 2))
    first, second = chord_derivatives(Fraction(1, 2))
    assert (value.real, value.imag) == (Fraction(3, 100), Fraction(1, 25))
    assert (first.real, first.imag) == (Fraction(-8, 125), Fraction(6, 125))
    assert (second.real, second.imag) == (Fraction(-16, 625), Fraction(-88, 625))


def test_flux_and_gauge_record() -> None:
    record = flux_record()
    assert record["radius_squared"] == Fraction(1, 400)
    assert record["Wilson_H10_H21_H02"] == record["Wilson_expected"]
    assert record["reverse_is_conjugate"] is True
    assert record["box_imaginary_flux_positive"] is True
    assert record["matrix_index_convention"] == "H_destination_source"
    assert record["loop_orientation"] == (0, 1, 2, 0)
    assert record["oriented_cycle"] == "0_to_1_to_2_to_0"
    assert record["diagonal_gauge_exponent_coefficients"] == (0, 0, 0, 0, 0)
    assert record["diagonal_gauge_exponents_cancel"] is True
    assert record["constant_diagonal_gauge_Wilson_equal"] is True


def test_floor_certificate_exact() -> None:
    record = floor_record()
    assert record["induced_operator_norm_budget"] == Fraction(1991, 500)
    assert record["pointwise_floor"] == Fraction(16018, 90045)
    assert record["stationary_full_rank_floor"] == Fraction(2997, 20_000_000)
    assert record["trace_norm_contraction_rate"] == Fraction(1, 25)
    assert record["Drazin_trace_norm_bound"] == 25


def test_exact_stationary_drazin_and_derivatives() -> None:
    bundle = branch_bundle()
    assert all(drazin_identities(bundle).values())
    assert all(derivative_identities(bundle).values())


def test_geometry_exact_rank_and_curvature() -> None:
    record = geometry_record()
    assert record["tangent_Gram_determinant"] > 0
    assert record["SLD_metric_determinant"] > 0
    assert record["mean_Uhlmann_signs"] == (-1, 1, -1)
    assert all(item != 0 for item in record["mean_Uhlmann_vector"])
    assert record["constant_diagonal_gauge_metric_equal"] is True
    assert record["constant_diagonal_gauge_curvature_equal"] is True
    assert record["cartesian_quadrature_pullback_Wt_equal"] is True
    assert record["cartesian_chord_jacobian_dt"] == (Fraction(-8, 125), Fraction(6, 125))
    assert record["cartesian_to_t_mean_Uhlmann_pullback_equal"] is True


def test_geometry_float_values_are_regression_only() -> None:
    values = tuple(float(item) for item in geometry_record()["mean_Uhlmann_vector"])
    assert values == pytest.approx(
        (-3.735937244399392e-6, 1.153100438888939e-6, -1.2876653638951542e-7),
        rel=1e-13,
    )


def test_counting_exact_response_and_signs() -> None:
    record = counting_record()
    assert record["forward_gain_rate"] == Fraction(51, 1000)
    assert record["reverse_gain_rate"] == Fraction(39, 1000)
    assert record["direct_response_curl_signs"] == (-1, -1, -1)
    assert all(item != 0 for item in record["direct_response_curl"])
    assert record["cartesian_to_t_response_pullback_equal"] is True
    assert record["cartesian_response"]["chord_jacobian_dt"] == (
        Fraction(-8, 125),
        Fraction(6, 125),
    )


def test_counting_float_values_are_regression_only() -> None:
    record = counting_record()
    assert tuple(float(item) for item in record["direct_response_one_form"]) == pytest.approx(
        (0.3166985595098677, -0.006665127165702507, -7.976048687028195e-5),
        rel=1e-13,
    )
    assert tuple(float(item) for item in record["direct_response_curl"]) == pytest.approx(
        (-2.861575935806458e-4, -2.308976588314011e-3, -1.0027208218898975),
        rel=1e-13,
    )


def test_q_jet_is_only_the_counted_physical_edge() -> None:
    jet = counted_q_jet(Fraction(3, 100), Fraction(9, 40))
    entries = [
        (row, column)
        for row, values in enumerate(jet)
        for column, item in enumerate(values)
        if not item.is_zero()
    ]
    assert entries == [(6, 12), (12, 6)]


def test_fcs_normal_connection_identity() -> None:
    direct = counting_record()
    fcs = fcs_record()
    assert fcs["fcs_left_q_eigenvector_equation"] is True
    assert fcs["fcs_right_q_eigenvector_equation"] is True
    assert fcs["fcs_minus_partial_q_connection_one_form"] == direct["direct_response_one_form"]
    assert fcs["fcs_minus_partial_q_connection_one_form"] is not direct["direct_response_one_form"]
    assert fcs["fcs_normal_connection_curl"] == direct["direct_response_curl"]
    assert fcs["fcs_normal_connection_curl"] is not direct["direct_response_curl"]
    assert all(type(item) is Fraction for item in fcs["fcs_normal_connection_curl"])


def test_direct_and_fcs_producers_have_separate_call_graphs() -> None:
    tree = ast.parse(inspect.getsource(counting_lane))
    functions = {
        node.name: node for node in tree.body if type(node) in {ast.FunctionDef, ast.AsyncFunctionDef}
    }

    def calls(name: str) -> set[str]:
        return {
            node.func.id
            for node in ast.walk(functions[name])
            if type(node) is ast.Call and type(node.func) is ast.Name
        }

    direct_calls = calls("_direct_response_curl_record")
    fcs_jet_calls = calls("_fcs_normal_connection_jet_record")
    fcs_record_calls = calls("fcs_record")
    assert "_fcs_normal_connection_jet_record" not in direct_calls
    assert "_direct_response_curl_record" not in fcs_jet_calls
    assert "counting_record" not in fcs_jet_calls
    assert "counting_record" not in fcs_record_calls
    assert "_direct_response_curl_record" not in fcs_record_calls


def test_direct_response_lane_perturbation_fails_G6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = counting_lane._direct_response_curl_record

    def perturbed(*args: object, **kwargs: object) -> dict[str, object]:
        record = dict(original(*args, **kwargs))
        curl = record["direct_response_curl"]
        assert type(curl) is tuple
        record["direct_response_curl"] = (curl[0] + 1, curl[1], curl[2])
        return record

    monkeypatch.setattr(counting_lane, "_direct_response_curl_record", perturbed)
    counting_record.cache_clear()
    null_record.cache_clear()
    try:
        records = theorem.build_records()
        assert theorem.natural_gate_results(records)["G6_counting_and_fcs_identity"] is False
    finally:
        counting_record.cache_clear()
        null_record.cache_clear()


def test_fcs_normal_connection_lane_perturbation_fails_G6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = counting_lane._fcs_normal_connection_jet_record

    def perturbed(*args: object, **kwargs: object) -> dict[str, object]:
        record = dict(original(*args, **kwargs))
        curl = record["fcs_normal_connection_curl"]
        assert type(curl) is tuple
        record["fcs_normal_connection_curl"] = (curl[0], curl[1] + 1, curl[2])
        return record

    monkeypatch.setattr(counting_lane, "_fcs_normal_connection_jet_record", perturbed)
    fcs_record.cache_clear()
    try:
        records = theorem.build_records()
        assert theorem.natural_gate_results(records)["G6_counting_and_fcs_identity"] is False
    finally:
        fcs_record.cache_clear()


def test_fcs_one_sided_B_alias_fails_G6(monkeypatch: pytest.MonkeyPatch) -> None:
    original = counting_lane._fcs_normal_connection_jet_record

    def aliased(*args: object, **kwargs: object) -> dict[str, object]:
        record = dict(original(*args, **kwargs))
        record["fcs_minus_partial_q_connection_one_form"] = counting_record()["direct_response_one_form"]
        return record

    monkeypatch.setattr(counting_lane, "_fcs_normal_connection_jet_record", aliased)
    counting_record.cache_clear()
    fcs_record.cache_clear()
    null_record.cache_clear()
    try:
        records = theorem.build_records()
        assert (
            records["fcs"]["fcs_minus_partial_q_connection_one_form"]
            is records["counting"]["direct_response_one_form"]
        )
        assert theorem.natural_gate_results(records)["G6_counting_and_fcs_identity"] is False
        summary, _records = theorem.execute_program()
        assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
        assert "G6_counting_and_fcs_identity" in summary["failed_gates"]
    finally:
        counting_record.cache_clear()
        fcs_record.cache_clear()
        null_record.cache_clear()


def test_oracle_producer_aliasing_direct_response_objects_fails_G6(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = theorem.exact_oracle_record

    def aliased(capability: OracleCapability) -> dict[str, object]:
        record = dict(original(capability))
        direct = counting_record()
        record["B"] = direct["direct_response_one_form"]
        record["F"] = direct["direct_response_curl"]
        return record

    monkeypatch.setattr(theorem, "exact_oracle_record", aliased)
    counting_record.cache_clear()
    fcs_record.cache_clear()
    null_record.cache_clear()
    try:
        records = theorem.build_records()
        assert records["pipeline"]["oracle"]["B"] is records["counting"]["direct_response_one_form"]
        assert records["pipeline"]["oracle"]["F"] is records["counting"]["direct_response_curl"]
        assert theorem.natural_gate_results(records)["G6_counting_and_fcs_identity"] is False
        summary, _records = theorem.execute_program()
        assert summary["disposition"] == "FAIL_INTERNAL_ANALYTIC"
        assert "G6_counting_and_fcs_identity" in summary["failed_gates"]
    finally:
        counting_record.cache_clear()
        fcs_record.cache_clear()
        null_record.cache_clear()


@pytest.mark.parametrize(
    ("oracle_field", "owner", "source_field"),
    (
        ("B", "counting", "direct_response_one_form"),
        ("F", "counting", "direct_response_curl"),
        ("B", "fcs", "fcs_minus_partial_q_connection_one_form"),
        ("F", "fcs", "fcs_normal_connection_curl"),
    ),
)
def test_record_only_oracle_alias_fails_G6(
    oracle_field: str,
    owner: str,
    source_field: str,
) -> None:
    records = theorem.build_records()
    records["pipeline"]["oracle"][oracle_field] = records[owner][source_field]
    assert records["pipeline"]["oracle"][oracle_field] is records[owner][source_field]
    assert theorem.natural_gate_results(records)["G6_counting_and_fcs_identity"] is False


def test_G6_refuses_equality_overriding_order_sign_and_oracle_fields() -> None:
    class EqualAny:
        def __eq__(self, _other: object) -> bool:
            return True

        def __ne__(self, _other: object) -> bool:
            return False

    canonical = theorem.build_records()
    mutations = (
        ("counting", "direct_response_curl_order"),
        ("counting", "direct_response_curl_signs"),
        ("fcs", "fcs_normal_connection_curl_order"),
        ("fcs", "fcs_normal_connection_curl_signs"),
        ("oracle", "B"),
        ("oracle", "F"),
    )
    for owner, field in mutations:
        records = copy.deepcopy(canonical)
        target = records["pipeline"]["oracle"] if owner == "oracle" else records[owner]
        target[field] = EqualAny()
        assert theorem.natural_gate_results(records)["G6_counting_and_fcs_identity"] is False


def test_reverse_count_zero_current_and_zero_chord_controls() -> None:
    record = null_record()
    assert record["reverse_count_negates_B"] is True
    assert record["reverse_count_negates_F"] is True
    assert record["zero_current_B_and_F_zero"] is True
    assert record["zero_current_operator_constructed_independently"] is True
    assert record["zero_current_response_recomputed"] is True
    assert all(item.is_zero() for row in record["zero_current_q_jet"] for item in row)
    assert record["zero_chord_t_tangent_zero"] is True
    assert record["zero_chord_t_curvature_components_zero"] is True


def test_flux_conjugation_is_recomputed_not_assumed_odd() -> None:
    record = flux_conjugation_record()
    assert record["Wilson_flux_reversed"] is True
    assert record["componentwise_oddness_assumed"] is False
    assert record["conjugate_metric_determinant"] > 0


def test_canonical_program_passes_without_digest_bypass() -> None:
    assert "enforce_reviewed_digests" not in inspect.signature(theorem.execute_program).parameters
    summary, _records = theorem.execute_program()
    assert summary["status"] == "PASS"
    assert summary["failed_gates"] == []


def test_reviewed_record_digests_are_independent_and_exact() -> None:
    summary, records = theorem.execute_program()
    assert summary["status"] == "PASS"
    assert contract.record_digest_issues(records) == []
    assert all(value != "TO_BE_FROZEN" for value in contract.REVIEWED_RECORD_DIGESTS.values())


def test_lane_record_monkeypatch_cannot_self_canonicalize(monkeypatch: pytest.MonkeyPatch) -> None:
    original = theorem.geometry_record

    def forged() -> dict[str, object]:
        record = dict(original())
        record["SLD_metric_determinant"] = Fraction(-1)
        return record

    monkeypatch.setattr(theorem, "geometry_record", forged)
    summary, _records = theorem.execute_program()
    assert summary["status"] == "FAIL"
    assert "G4_drazin_derivatives_and_rank" in summary["failed_gates"]
    assert "G12_provenance_registry_and_claim_ceiling" in summary["failed_gates"]


@pytest.mark.parametrize("gate", contract.ORDERED_GATES)
def test_every_gate_can_only_be_forced_from_pass_to_fail(gate: str) -> None:
    summary, _records = theorem.execute_program(
        gate_overrides={gate: False},
    )
    assert summary["status"] == "FAIL"
    assert gate in summary["failed_gates"]
    owners = [name for name, gates in contract.CASE_GATE_MAP.items() if gate in gates]
    assert owners and all(summary["cases"][name]["status"] == "FAIL" for name in owners)


def test_true_override_cannot_rescue_natural_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(theorem, "contract_issues", lambda: ["forced natural failure"])
    summary, _records = theorem.execute_program(
        gate_overrides={"G0_exact_config": True},
    )
    assert summary["gates"]["G0_exact_config"] is False
    assert summary["status"] == "FAIL"


def test_unknown_and_nonboolean_overrides_refuse() -> None:
    with pytest.raises(ValueError):
        theorem.execute_program(gate_overrides={"UNKNOWN": False})
    with pytest.raises(TypeError):
        theorem.execute_program(gate_overrides={"G0_exact_config": 0})


def test_pipeline_exact_state_order_and_capability() -> None:
    session = PipelineSession()
    lock = session.lock_prediction(REVIEWED_CRITERION)
    capability = session.capability()
    result = exact_oracle_record(capability)
    session.accept_oracle(capability, result)
    session.verify()
    assert session.state is PipelineState.VERIFIED
    assert session.record()["event_log_exact"] is True
    assert capability.payload_sha256 == lock.payload_sha256


def test_pipeline_refuses_oracle_before_lock() -> None:
    session = PipelineSession()
    with pytest.raises(RuntimeError):
        session.capability()
    assert session.state is PipelineState.POISONED


@pytest.mark.parametrize(
    "criterion",
    [
        FalsificationCriterion(criterion_id="PROVE_GENERAL_MAP"),
        FalsificationCriterion(general_linear_map_refutation_requested=True),
        FalsificationCriterion(affine_or_nonlinear_map_refutation_requested=True),
        FalsificationCriterion(heldout_claim_requested=True),
    ],
)
def test_pipeline_refuses_unreviewed_or_stronger_criteria(
    criterion: FalsificationCriterion,
) -> None:
    with pytest.raises(RuntimeError):
        PipelineSession().lock_prediction(criterion)


def test_wrong_oracle_capability_refuses() -> None:
    session = PipelineSession()
    session.lock_prediction(REVIEWED_CRITERION)
    capability = session.capability()
    wrong = replace(capability, payload_sha256="0" * 64)
    with pytest.raises(RuntimeError):
        session.accept_oracle(wrong, exact_oracle_record(capability))


def test_self_consistent_arbitrary_oracle_capability_refuses() -> None:
    experiment_id = "FORGED_EXPERIMENT"
    contract_sha = "1" * 64
    criterion_sha = "2" * 64
    payload_sha = contract.sha256_record(
        {
            "experiment_id": experiment_id,
            "contract_sha256": contract_sha,
            "criterion_sha256": criterion_sha,
        }
    )
    forged = OracleCapability(experiment_id, contract_sha, criterion_sha, payload_sha)
    assert forged.authentic() is False
    with pytest.raises(RuntimeError):
        exact_oracle_record(forged)


def test_equal_int_oracle_forgery_refuses(monkeypatch: pytest.MonkeyPatch) -> None:
    class EqualInt(int):
        def __eq__(self, _other: object) -> bool:
            return True

    def forged(capability: OracleCapability) -> dict[str, object]:
        zero = tuple(EqualInt(0) for _ in range(3))
        return {
            "authority": "independent_exact_generator_Drazin_oracle",
            "accepted_inputs": "generator_primitives_plus_authenticated_criterion_digest",
            "capability_payload_sha256": capability.payload_sha256,
            "capability_payload_authenticated": True,
            "prediction_or_geometry_payload_received": False,
            "B": zero,
            "F": zero,
        }

    session = PipelineSession()
    session.lock_prediction(REVIEWED_CRITERION)
    capability = session.capability()
    with pytest.raises(RuntimeError):
        session.accept_oracle(capability, forged(capability))


def test_live_role_sources_pass_strict_firewalls() -> None:
    records = authenticated_role_sources()
    assert tuple(records) == ("geometry", "counting", "oracle")
    assert all(item["authenticated"] is True for item in records.values())


@pytest.mark.parametrize(
    ("role", "source"),
    [
        ("geometry", "from .counting_lane import counting_record\ncounting_record()\n"),
        ("counting", "from .geometry_lane import geometry_record\ngeometry_record()\n"),
        ("oracle", "import importlib\nimportlib.import_module('x.geometry_lane')\n"),
        ("oracle", "loader=__builtins__['__im'+'port__']\nloader('x.counting_lane')\n"),
        ("oracle", "import operator\noperator.itemgetter('__import__')(__builtins__)\n"),
    ],
)
def test_firewalls_reject_cross_lane_and_reflective_attacks(role: str, source: str) -> None:
    assert analyze_role_source(role, source)


def test_generator_is_exact_fraction_family_not_core_float_authority() -> None:
    matrix = liouvillian(*MODEL_CONTRACT.center)
    assert len(matrix) == 25 and all(len(row) == 25 for row in matrix)
    assert MODEL_CONTRACT.core_calls_are_acceptance_authority is False


def test_fraction_subclass_is_not_canonical() -> None:
    class ForgedFraction(Fraction):
        pass

    with pytest.raises(TypeError):
        contract.canonical_bytes({"value": ForgedFraction(1, 2)})


def test_fraction_subclass_cannot_spoof_a_reviewed_exact_record(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ForgedFraction(Fraction):
        pass

    original = theorem.geometry_record

    def forged() -> dict[str, object]:
        record = dict(original())
        record["SLD_metric_determinant"] = ForgedFraction(1, 1)
        return record

    monkeypatch.setattr(theorem, "geometry_record", forged)
    summary, _records = theorem.execute_program()
    assert summary["status"] == "FAIL"
    assert "G12_provenance_registry_and_claim_ceiling" in summary["failed_gates"]


def test_scope_refuses_general_map_and_heldout_claims() -> None:
    _summary, records = theorem.execute_program()
    scope = records["scope"]
    assert scope["finite_scalar_kappa_refuted"] is True
    assert scope["generic_linear_map_refuted"] is False
    assert scope["affine_map_refuted"] is False
    assert scope["nonlinear_map_refuted"] is False
    assert scope["generator_dependent_map_open"] is True
    assert scope["heldout_prediction_claimed"] is False
    assert scope["cartesian_geometry_pullback_equal"] is True
    assert scope["cartesian_response_pullback_equal"] is True
    assert scope["third_jet_or_dF_closure_claimed"] is False
    authority = scope["provenance_authority"]
    assert authority["outer_staged_index_audit_is_publication_authority"] is True
    assert authority["post_generation_fresh_CLI_verify_required"] is True
    assert authority["in_process_helpers_authoritative"] is False

    forged_records = copy.deepcopy(records)
    forged_records["scope"]["provenance_authority"]["in_process_helpers_authoritative"] = True
    assert theorem.natural_gate_results(forged_records)["G12_provenance_registry_and_claim_ceiling"] is False


def test_claim_ceiling_has_no_inflated_language() -> None:
    text = MODEL_CONTRACT.claim_ceiling.casefold()
    assert "no full-cwt" in text
    assert "universal" in text
    assert "empirical" in text


def test_dependency_policy_is_closed_and_producer_is_independently_validated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = artifact_module.dependency_policy_record()
    artifact_module.validate_dependency_policy_record(record)
    forged = dict(record)
    forged["authority"] = "FORGED"
    with pytest.raises(ArtifactVerificationError):
        artifact_module.validate_dependency_policy_record(forged)
    monkeypatch.setattr(artifact_module, "dependency_policy_record", lambda: forged)
    with pytest.raises(ArtifactVerificationError):
        artifact_module.expected_artifact_bytes()


@pytest.mark.parametrize(
    "path",
    ["./requirements.test.txt", "subdir/../requirements.test.txt", "requirements.test.txt/"],
)
def test_dependency_policy_path_must_be_exact_lexical_value(
    monkeypatch: pytest.MonkeyPatch,
    path: str,
) -> None:
    monkeypatch.setattr(artifact_module, "DEPENDENCY_POLICY_PATH", path)
    with pytest.raises(ArtifactVerificationError):
        artifact_module.dependency_policy_record()


def test_dependency_policy_refuses_redirected_repository_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "requirements.test.txt").write_bytes(
        (artifact_module.REVIEWED_REPO_ROOT / "requirements.test.txt").read_bytes()
    )
    monkeypatch.setattr(artifact_module, "REPO_ROOT", tmp_path)
    with pytest.raises(ArtifactVerificationError, match="repository root differs"):
        artifact_module.dependency_policy_record()


def test_dependency_policy_refuses_link_even_with_identical_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    target = tmp_path / "identical-requirements.txt"
    target.write_bytes((artifact_module.REVIEWED_REPO_ROOT / "requirements.test.txt").read_bytes())
    link = root / "requirements.test.txt"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"host cannot create a file link: {exc}")
    monkeypatch.setattr(artifact_module, "REPO_ROOT", root)
    monkeypatch.setattr(artifact_module, "REVIEWED_REPO_ROOT", root)
    with pytest.raises(ArtifactVerificationError, match="link/reparse"):
        artifact_module.dependency_policy_record()


def test_git_index_source_lock_is_exact_and_excludes_self_and_generated_artifacts() -> None:
    assert len(source_lock_module.REVIEWED_GIT_INDEX_SOURCE_PATHS) == 18
    assert len(source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS) == 16
    assert len(source_lock_module.REVIEWED_PARENT_TRACKED_DEPENDENCY_PATHS) == 2
    assert set(source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS).isdisjoint(
        source_lock_module.REVIEWED_PARENT_TRACKED_DEPENDENCY_PATHS
    )
    paths = artifact_module.material_source_paths()
    observed = artifact_module.source_hashes(paths)
    assert tuple(observed) == source_lock_module.REVIEWED_GIT_INDEX_SOURCE_PATHS
    assert source_lock_module.SOURCE_LOCK_RELATIVE_PATH not in observed
    assert not any("/artifacts/" in path for path in observed)
    authority = source_lock_module.verify_source_lock()
    assert authority.record["schema"] == "git_index_source_lock_v1"
    assert authority.record["parent_commit_oid"] == source_lock_module.REVIEWED_PARENT_COMMIT_OID
    assert authority.record["git_object_format"] == "sha1"
    assert all(entry["mode"] == "100644" for entry in authority.record["entries"])


def test_source_lock_refuses_worktree_and_index_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "worktree-drift")
    _activate_source_authority(monkeypatch, binding, lock_path)
    path = source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS[0]
    target = binding.work_tree.joinpath(*Path(path).parts)
    target.write_bytes(target.read_bytes() + b"# worktree drift\n")
    with pytest.raises(ArtifactVerificationError, match="differs from Git index"):
        source_lock_module.verify_source_lock()

    binding, lock_path = _temporary_source_authority(tmp_path / "index-drift")
    _activate_source_authority(monkeypatch, binding, lock_path)
    path = source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS[0]
    target = binding.work_tree.joinpath(*Path(path).parts)
    target.write_bytes(target.read_bytes() + b"# indexed drift\n")
    _source_git(binding, "add", "-f", "--", path)
    with pytest.raises(ArtifactVerificationError, match="differs from selected Git index"):
        source_lock_module.verify_source_lock()


def test_source_lock_refuses_missing_and_non_file_index_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "missing")
    _activate_source_authority(monkeypatch, binding, lock_path)
    path = source_lock_module.REVIEWED_GIT_INDEX_SOURCE_PATHS[0]
    _source_git(binding, "update-index", "--force-remove", "--", path)
    with pytest.raises(ArtifactVerificationError, match="path set/order"):
        source_lock_module.verify_source_lock()

    binding, lock_path = _temporary_source_authority(tmp_path / "mode")
    _activate_source_authority(monkeypatch, binding, lock_path)
    record = source_lock_module.parse_source_lock(lock_path.read_bytes())
    entry = next(
        item
        for item in record["entries"]
        if item["path"] == source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS[0]
    )
    _source_git(
        binding,
        "update-index",
        "--add",
        "--cacheinfo",
        f"120000,{entry['blob_oid']},{entry['path']}",
    )
    with pytest.raises(ArtifactVerificationError, match="mode is not 100644"):
        source_lock_module.verify_source_lock()

    binding, lock_path = _temporary_source_authority(tmp_path / "submodule-mode")
    _activate_source_authority(monkeypatch, binding, lock_path)
    record = source_lock_module.parse_source_lock(lock_path.read_bytes())
    entry = next(
        item
        for item in record["entries"]
        if item["path"] == source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS[0]
    )
    _source_git(
        binding,
        "update-index",
        "--add",
        "--cacheinfo",
        f"160000,{source_lock_module.REVIEWED_PARENT_COMMIT_OID},{entry['path']}",
    )
    with pytest.raises(ArtifactVerificationError, match="mode is not 100644"):
        source_lock_module.verify_source_lock()


@pytest.mark.parametrize(
    "extra_path",
    [
        source_lock_module.SOURCE_LOCK_RELATIVE_PATH,
        "cwt-sim/experiments/loop_flux_counting_curvature_proof/artifacts/summary.json",
        "cwt-sim/experiments/loop_flux_counting_curvature_proof/unreviewed.txt",
    ],
)
def test_full_selected_index_delta_refuses_extra_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    extra_path: str,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "extra-index-path")
    _activate_source_authority(monkeypatch, binding, lock_path)
    _add_index_file(binding, extra_path, b"{}\n")
    with pytest.raises(ArtifactVerificationError, match="unreviewed source-generation delta"):
        source_lock_module.build_source_lock_bytes(binding)


def test_full_selected_index_delta_refuses_delete_and_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "delete-parent-path")
    _activate_source_authority(monkeypatch, binding, lock_path)
    _source_git(binding, "update-index", "--force-remove", "--", "requirements.test.txt")
    with pytest.raises(ArtifactVerificationError, match="unreviewed source-generation delta"):
        source_lock_module.build_source_lock_bytes(binding)

    binding, lock_path = _temporary_source_authority(tmp_path / "rename-proof-path")
    _activate_source_authority(monkeypatch, binding, lock_path)
    original = source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS[0]
    renamed = f"{original}.renamed"
    payload = binding.work_tree.joinpath(*Path(original).parts).read_bytes()
    _source_git(binding, "update-index", "--force-remove", "--", original)
    _add_index_file(binding, renamed, payload)
    with pytest.raises(ArtifactVerificationError, match="unreviewed source-generation delta"):
        source_lock_module.build_source_lock_bytes(binding)


def test_git_object_replacement_refs_cannot_rewrite_index_blob_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "replace-object")
    _activate_source_authority(monkeypatch, binding, lock_path)
    record = source_lock_module.parse_source_lock(lock_path.read_bytes())
    original_oid = record["entries"][0]["blob_oid"]
    forged = b"# replace-object forged source\n"
    forged_oid = (
        _source_git_with_input(binding, forged, "hash-object", "-w", "--stdin").decode("ascii").strip()
    )
    replacement = binding.git_dir / "refs" / "replace" / original_oid
    replacement.parent.mkdir(parents=True, exist_ok=True)
    replacement.write_text(f"{forged_oid}\n", encoding="ascii")
    assert _source_git(binding, "cat-file", "blob", original_oid) == forged
    authority = source_lock_module.verify_source_lock()
    assert authority.record["entries"][0]["blob_oid"] == original_oid
    assert (
        authority.source_hashes[record["entries"][0]["path"]]["sha256"] == record["entries"][0]["sha256_raw"]
    )


def test_in_process_source_lock_alias_checks_are_defense_in_depth_diagnostics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "sealed-consumer")
    _activate_source_authority(monkeypatch, binding, lock_path)
    forged = source_lock_module.VerifiedSourceLock(
        record={},
        raw_sha256="0" * 64,
        bundle_sha256="0" * 64,
        source_hashes={},
    )
    monkeypatch.setattr(artifact_module, "verify_source_lock", lambda: forged, raising=False)
    monkeypatch.setattr(source_lock_module, "verify_source_lock", lambda: forged)
    payloads = artifact_module.expected_artifact_bytes()
    provenance = json.loads(payloads["PROVENANCE.json"])
    assert provenance["source_lock"]["sha256_raw"] != "0" * 64
    assert len(provenance["source_hashes"]) == len(source_lock_module.REVIEWED_GIT_INDEX_SOURCE_PATHS)
    boundary = provenance["provenance_acceptance_boundary"]
    assert boundary["in_process_helpers_authoritative"] is False
    assert boundary["outer_staged_index_audit_is_publication_authority"] is True

    lock_path.unlink()
    with pytest.raises(ArtifactVerificationError, match="source lock"):
        artifact_module.expected_artifact_bytes()


def test_defense_in_depth_helper_has_no_mutable_inline_bootstrap() -> None:
    assert not hasattr(artifact_module, "_SOURCE_LOCK_AUTHORITY_SCRIPT")
    assert not hasattr(artifact_module, "_source_authority_import_root")


@pytest.mark.parametrize("relative", ["source_lock.py", "transaction.py"])
def test_in_process_diagnostic_executes_index_verifier_and_rejects_worktree_only_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    relative: str,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / relative.removesuffix(".py"))
    _activate_source_authority(monkeypatch, binding, lock_path)
    target = binding.work_tree / "cwt-sim" / "experiments" / "loop_flux_counting_curvature_proof" / relative
    if relative == "source_lock.py":
        saved = source_lock_module.verify_source_lock(binding)
        target.write_text(
            "from types import SimpleNamespace\n"
            "def verify_source_lock():\n"
            "    return SimpleNamespace(\n"
            f"        record={saved.record!r},\n"
            f"        raw_sha256={saved.raw_sha256!r},\n"
            f"        bundle_sha256={saved.bundle_sha256!r},\n"
            f"        source_hashes={saved.source_hashes!r},\n"
            "    )\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        target.write_bytes(target.read_bytes() + b"# worktree-only verifier dependency drift\n")
    with pytest.raises(ArtifactVerificationError, match="clean Git-index source authority refused"):
        artifact_module._verified_source_lock()


def test_in_process_runner_identity_check_is_a_diagnostic_refusal(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forged_run(*_args, **_kwargs):
        return subprocess.CompletedProcess([], 0, stdout=b"{}\n", stderr=b"")

    monkeypatch.setattr(artifact_module.subprocess, "run", forged_run)
    with pytest.raises(ArtifactVerificationError, match="runner identity differs"):
        artifact_module._verified_source_lock()

    boundary = theorem.build_records()["scope"]["provenance_authority"]
    assert boundary["in_process_runner_identity_checks"] == "defense_in_depth_diagnostics_only"
    assert boundary["arbitrary_process_memory_syscall_binary_or_admin_compromise"] == (
        "outside_claimed_boundary"
    )


def test_fresh_index_cli_is_the_authoritative_provenance_boundary(
    tmp_path: Path,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "fresh-cli-authority")
    with tempfile.TemporaryDirectory(prefix="cwt-loop-flux-fresh-cli-") as temporary:
        checkout = _materialize_index_checkout(binding, Path(temporary).resolve())

        exact = _run_fresh_source_lock_cli(binding, lock_path, checkout)
        assert exact.returncode == 0, exact.stderr.decode("utf-8", errors="replace")
        payload = json.loads(exact.stdout)
        assert payload["record"]["schema"] == "git_index_source_lock_v1"
        assert payload["raw_sha256"] == sha256_bytes(lock_path.read_bytes())

        contamination = tmp_path / "import-contamination"
        contamination.mkdir()
        marker = contamination / "CONTAMINATION_RAN"
        (contamination / "sitecustomize.py").write_text(
            f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
            encoding="utf-8",
            newline="\n",
        )
        contaminated = _run_fresh_source_lock_cli(
            binding,
            lock_path,
            checkout,
            python_path=contamination,
        )
        assert contaminated.returncode == 0
        assert not marker.exists()

        unbound = _run_fresh_source_lock_cli(None, None, checkout)
        assert unbound.returncode != 0
        assert b"unavailable" in unbound.stderr or b"incomplete" in unbound.stderr

        forged_record = source_lock_module.parse_source_lock(lock_path.read_bytes())
        forged_record["parent_commit_oid"] = "0" * 40
        forged_lock = tmp_path / "FORGED_SOURCE_LOCK.json"
        forged_lock.write_bytes(source_lock_module._canonical_json_bytes(forged_record))
        forged = _run_fresh_source_lock_cli(binding, forged_lock, checkout)
        assert forged.returncode != 0

        worktree_verifier = (
            binding.work_tree
            / "cwt-sim"
            / "experiments"
            / "loop_flux_counting_curvature_proof"
            / "source_lock.py"
        )
        worktree_verifier.write_bytes(worktree_verifier.read_bytes() + b"# worktree-only drift\n")
        drifted = _run_fresh_source_lock_cli(binding, lock_path, checkout)
        assert drifted.returncode != 0
        assert b"worktree" in drifted.stderr.lower() or b"differs" in drifted.stderr.lower()


@pytest.mark.parametrize(
    "mutation",
    ["parent", "path_set", "entries_digest", "entry_hash_and_bundle"],
)
def test_artifact_parent_parser_refuses_forged_disk_lock_before_acceptance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / mutation)
    _activate_source_authority(monkeypatch, binding, lock_path)
    record = source_lock_module.parse_source_lock(lock_path.read_bytes())
    if mutation == "parent":
        record["parent_commit_oid"] = "0" * 40
    elif mutation == "path_set":
        record["path_set_sha256"] = "0" * 64
    elif mutation == "entries_digest":
        record["entries_sha256"] = "0" * 64
    else:
        record["entries"][0]["sha256_raw"] = "0" * 64
        record["entries_sha256"] = source_lock_module._entries_sha256(record["entries"])
    lock_path.write_bytes(source_lock_module._canonical_json_bytes(record))
    with pytest.raises(ArtifactVerificationError):
        artifact_module._verified_source_lock()


def test_source_lock_generation_and_final_publication_delta_are_phase_split(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, external_lock = _temporary_source_authority(tmp_path / "publication-phases")
    _activate_source_authority(monkeypatch, binding, external_lock)
    payloads = artifact_module.expected_artifact_bytes()

    package_root = binding.work_tree / "cwt-sim" / "experiments" / "loop_flux_counting_curvature_proof"
    package_lock = package_root / "SOURCE_LOCK.json"
    package_lock.write_bytes(external_lock.read_bytes())
    artifact_root = package_root / "artifacts"
    artifact_root.mkdir()
    for name, payload in payloads.items():
        (artifact_root / name).write_bytes(payload)
    final_paths = [
        source_lock_module.SOURCE_LOCK_RELATIVE_PATH,
        *(
            f"cwt-sim/experiments/loop_flux_counting_curvature_proof/artifacts/{name}"
            for name in sorted(payloads)
        ),
    ]
    _source_git(binding, "add", "-f", "--", *final_paths)
    monkeypatch.delenv(source_lock_module.SOURCE_LOCK_ENV)

    assert source_lock_module.verify_source_lock(binding).record["entries"]
    publication = source_lock_module.verify_final_publication_index_delta(binding)
    assert publication["path_count"] == 22
    assert artifact_module.verify_artifacts(artifact_root)["status"] == "PASS_INTERNAL_ANALYTIC"
    with tempfile.TemporaryDirectory(prefix="cwt-loop-flux-postgen-cli-") as temporary:
        checkout = _materialize_index_checkout(
            binding,
            Path(temporary).resolve(),
            all_index_entries=True,
        )
        fresh_verify = _run_fresh_package_verify_cli(binding, checkout)
        assert fresh_verify.returncode == 0, fresh_verify.stderr.decode("utf-8", errors="replace")
        assert json.loads(fresh_verify.stdout)["status"] == "PASS_INTERNAL_ANALYTIC"

    _add_index_file(binding, "cwt-sim/future-nonsemantic.txt", b"future\n")
    assert source_lock_module.verify_source_lock(binding).record["entries"]
    assert artifact_module.verify_artifacts(artifact_root)["status"] == "PASS_INTERNAL_ANALYTIC"
    with pytest.raises(ArtifactVerificationError, match="unreviewed final-publication delta"):
        source_lock_module.verify_final_publication_index_delta(binding)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_entry",
        "extra_entry",
        "mode",
        "mode_type",
        "blob_oid",
        "blob_oid_type",
        "size",
        "size_type",
        "sha256_raw",
        "sha256_raw_type",
        "path_alias",
        "duplicate_path",
        "schema",
        "parent_commit_oid",
        "parent_commit_oid_type",
        "git_object_format",
        "path_set_sha256",
        "entries_sha256",
        "extra_top_level",
    ],
)
def test_source_lock_schema_and_identity_forgeries_fail(
    source_index_authority: tuple[GitIndexBinding, Path],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    binding, canonical_lock = source_index_authority
    payload = source_lock_module.parse_source_lock(canonical_lock.read_bytes())
    forged = copy.deepcopy(payload)
    if mutation == "missing_entry":
        forged["entries"].pop()
    elif mutation == "extra_entry":
        forged["entries"].append(copy.deepcopy(forged["entries"][-1]))
        forged["entries"][-1]["path"] = "cwt-sim/tests/experiments/extra.py"
    elif mutation in {"mode", "blob_oid", "size", "sha256_raw"}:
        values = {"mode": "120000", "blob_oid": "0" * 40, "size": -1, "sha256_raw": "0" * 64}
        forged["entries"][0][mutation] = values[mutation]
    elif mutation == "mode_type":
        forged["entries"][0]["mode"] = 100644
    elif mutation == "blob_oid_type":
        forged["entries"][0]["blob_oid"] = False
    elif mutation == "size_type":
        forged["entries"][0]["size"] = 1.0
    elif mutation == "sha256_raw_type":
        forged["entries"][0]["sha256_raw"] = False
    elif mutation == "path_alias":
        forged["entries"][0]["path"] = f"./{forged['entries'][0]['path']}"
    elif mutation == "duplicate_path":
        forged["entries"][1]["path"] = forged["entries"][0]["path"]
    elif mutation == "schema":
        forged["schema"] = "git_index_source_lock_v2"
    elif mutation == "parent_commit_oid":
        forged[mutation] = "0" * 40
    elif mutation == "parent_commit_oid_type":
        forged[mutation] = 0
    elif mutation == "git_object_format":
        forged[mutation] = "sha256"
    elif mutation in {"path_set_sha256", "entries_sha256"}:
        forged[mutation] = "0" * 64
    else:
        forged["extra"] = False
    forged_path = tmp_path / f"{mutation}.json"
    forged_path.write_bytes(source_lock_module._canonical_json_bytes(forged))
    _activate_source_authority(monkeypatch, binding, forged_path)
    with pytest.raises(ArtifactVerificationError):
        source_lock_module.verify_source_lock()


@pytest.mark.parametrize("variant", ["bom", "crlf", "pretty", "duplicate_key"])
def test_source_lock_noncanonical_bytes_fail(
    source_index_authority: tuple[GitIndexBinding, Path],
    variant: str,
) -> None:
    _binding, lock_path = source_index_authority
    raw = lock_path.read_bytes()
    payload = source_lock_module.parse_source_lock(raw)
    if variant == "bom":
        forged = b"\xef\xbb\xbf" + raw
    elif variant == "crlf":
        forged = raw.replace(b"\n", b"\r\n")
    elif variant == "pretty":
        forged = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    else:
        forged = raw[:-2] + b',"schema":"git_index_source_lock_v1"}\n'
    with pytest.raises(ArtifactVerificationError):
        source_lock_module.parse_source_lock(forged)


def test_source_lock_binding_requires_exact_absolute_existing_paths(
    source_index_authority: tuple[GitIndexBinding, Path],
) -> None:
    binding, _lock_path = source_index_authority
    with pytest.raises(ArtifactVerificationError, match="binding schema"):
        source_lock_module.verify_source_lock(
            GitIndexBinding(binding.git_dir, binding.index_file, binding.work_tree, 1)
        )
    with pytest.raises(ArtifactVerificationError, match="absolute"):
        source_lock_module.verify_source_lock(
            GitIndexBinding(Path("relative-git"), binding.index_file, binding.work_tree, True)
        )


def test_source_lock_refuses_noncanonical_text_blob(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    binding, lock_path = _temporary_source_authority(tmp_path / "bom")
    _activate_source_authority(monkeypatch, binding, lock_path)
    path = source_lock_module.REVIEWED_GIT_INDEX_ADDED_PATHS[0]
    target = binding.work_tree.joinpath(*Path(path).parts)
    target.write_bytes(b"\xef\xbb\xbf" + target.read_bytes())
    _source_git(binding, "add", "-f", "--", path)
    with pytest.raises(ArtifactVerificationError, match="strict UTF-8/LF"):
        source_lock_module.build_source_lock_bytes(binding)


def test_external_unbound_checkout_and_partial_binding_have_no_fallback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    external = tmp_path / "unbound"
    external.mkdir()
    for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(source_lock_module, "REPO_ROOT", external)
    with pytest.raises(ArtifactVerificationError, match="unavailable"):
        source_lock_module.resolve_git_index_binding()

    monkeypatch.setenv("GIT_DIR", str(tmp_path))
    with pytest.raises(ArtifactVerificationError, match="incomplete"):
        source_lock_module.resolve_git_index_binding()


def test_source_lock_override_requires_explicit_git_metadata(
    source_index_authority: tuple[GitIndexBinding, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _binding, lock_path = source_index_authority
    for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(source_lock_module.SOURCE_LOCK_ENV, str(lock_path))
    with pytest.raises(ArtifactVerificationError, match="override requires explicit"):
        source_lock_module.verify_source_lock()


def test_source_lock_override_refusal_precedes_git_discovery(
    source_index_authority: tuple[GitIndexBinding, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _binding, lock_path = source_index_authority
    discovery_called = False

    def forbidden_discovery() -> GitIndexBinding:
        nonlocal discovery_called
        discovery_called = True
        raise AssertionError("implicit Git discovery must not run")

    for name in ("GIT_DIR", "GIT_INDEX_FILE", "GIT_WORK_TREE"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv(source_lock_module.SOURCE_LOCK_ENV, str(lock_path))
    monkeypatch.setattr(source_lock_module, "resolve_git_index_binding", forbidden_discovery)
    with pytest.raises(ArtifactVerificationError, match="override requires explicit"):
        source_lock_module.verify_source_lock()
    assert not discovery_called


def test_predecessor_inventory_internal_digest_is_recomputed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = artifact_module.recursive_raw_inventory

    def forged(path: Path, *, trust_anchor: Path) -> dict[str, object]:
        record = original(path, trust_anchor=trust_anchor)
        if path == artifact_module.PREDECESSOR_ARTIFACT_DIRS["constitutive_map_3d_proof"]:
            record = copy.deepcopy(record)
            record["entries"]["stable-forgery.bin"] = {
                "type": "file",
                "hash_domain": artifact_module.RAW_HASH_DOMAIN,
                "sha256": "0" * 64,
            }
            record["entry_count"] += 1
        return record

    monkeypatch.setattr(artifact_module, "recursive_raw_inventory", forged)
    with pytest.raises(ArtifactVerificationError, match="content digest"):
        artifact_module.predecessor_inventories()


def test_expected_bundle_is_exact_five_file_mapping() -> None:
    expected = artifact_module.expected_artifact_bytes()
    assert set(expected) == artifact_module.EXPECTED_ARTIFACT_NAMES
    assert all(b"\r" not in payload for payload in expected.values())


def test_transaction_crash_recovery_preserves_one_complete_generation(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    old = _transaction_generation("old")
    new = _transaction_generation("new")
    _publish_artifact_mapping(destination, old)

    def crash(checkpoint: str) -> None:
        if checkpoint == "after_old_to_backup":
            raise ArtifactTransactionCrash(checkpoint)

    with pytest.raises(ArtifactTransactionCrash):
        _publish_artifact_mapping(destination, new, fault_injector=crash)
    recover_artifact_transaction(destination)
    assert _read_generation(destination) in (old, new)
    paths = artifact_transaction_paths(destination)
    assert not any(path.exists() for path in (paths.journal, paths.journal_temp, paths.stage, paths.backup))


def test_first_publication_crash_after_prepared_recovers(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    generation = _transaction_generation("first")

    def crash(checkpoint: str) -> None:
        if checkpoint == "after_journal_prepared":
            raise ArtifactTransactionCrash(checkpoint)

    with pytest.raises(ArtifactTransactionCrash):
        _publish_artifact_mapping(destination, generation, fault_injector=crash)
    recover_artifact_transaction(destination)
    assert _read_generation(destination) == generation


@pytest.mark.parametrize("leaf", _RESERVED_TRANSACTION_LEAVES)
def test_reserved_transaction_namespace_is_zero_touch_refused(tmp_path: Path, leaf: str) -> None:
    destination = tmp_path / leaf
    before = tuple(tmp_path.iterdir())
    with pytest.raises(ArtifactVerificationError, match="reserved transaction"):
        artifact_transaction_paths(destination)
    assert tuple(tmp_path.iterdir()) == before


def test_guarded_reader_blocks_until_writer_releases_complete_generation(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    old = _transaction_generation("old")
    new = _transaction_generation("new")
    _publish_artifact_mapping(destination, old)
    writer_ready = threading.Event()
    writer_release = threading.Event()
    observed: list[dict[str, bytes]] = []

    def writer() -> None:
        def pause(checkpoint: str) -> None:
            if checkpoint == "after_old_to_backup":
                writer_ready.set()
                assert writer_release.wait(5)

        _publish_artifact_mapping(destination, new, fault_injector=pause)

    def reader() -> None:
        assert writer_ready.wait(5)
        with artifact_access_guard(destination):
            observed.append(_read_generation(destination))

    writer_thread = threading.Thread(target=writer)
    reader_thread = threading.Thread(target=reader)
    writer_thread.start()
    reader_thread.start()
    assert writer_ready.wait(5)
    writer_release.set()
    writer_thread.join(10)
    reader_thread.join(10)
    assert not writer_thread.is_alive() and not reader_thread.is_alive()
    assert observed == [new]


def test_destination_overlap_is_refused_before_write() -> None:
    package = Path(theorem.__file__).resolve().parent
    before = tuple(sorted(path.relative_to(package).as_posix() for path in package.rglob("*")))
    with pytest.raises(ArtifactGenerationRefused, match="overlaps experiment source tree"):
        artifact_module.preflight_artifact_destination(package / "nested-output")
    after = tuple(sorted(path.relative_to(package).as_posix() for path in package.rglob("*")))
    assert after == before


def test_public_transactional_write_verify_and_tamper_refusal(tmp_path: Path) -> None:
    destination = tmp_path / "artifacts"
    paths = artifact_module.write_artifacts(destination)
    assert set(paths) == artifact_module.EXPECTED_ARTIFACT_NAMES
    result = artifact_module.verify_artifacts(destination)
    assert result == {
        "status": "PASS_INTERNAL_ANALYTIC",
        "files": 5,
        "sources": len(artifact_module.REVIEWED_MATERIAL_SOURCE_PATHS),
        "predecessors": 3,
        "record_digests": 11,
    }
    provenance_path = destination / "PROVENANCE.json"
    provenance = json.loads(provenance_path.read_text(encoding="utf-8"))
    provenance["dependency_policy"]["authority"] = "FORGED"
    provenance_path.write_bytes(artifact_module.strict_json_bytes(provenance))
    with pytest.raises(ArtifactVerificationError, match="dependency policy"):
        artifact_module.verify_artifacts(destination)


def test_public_verifier_holds_guard_through_summary_return_and_writer_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifacts"
    artifact_module.write_artifacts(destination)
    original_expected = artifact_module.expected_artifact_bytes
    verifier_inside = threading.Event()
    release_verifier = threading.Event()
    writer_finished = threading.Event()
    results: list[dict[str, object]] = []
    errors: list[BaseException] = []

    def blocked_expected() -> dict[str, bytes]:
        verifier_inside.set()
        if not release_verifier.wait(5):
            raise RuntimeError("test verifier handoff timed out")
        return original_expected()

    monkeypatch.setattr(artifact_module, "expected_artifact_bytes", blocked_expected)

    def verifier() -> None:
        try:
            results.append(artifact_module.verify_artifacts(destination))
        except BaseException as exc:  # pragma: no cover - asserted through errors
            errors.append(exc)

    def writer() -> None:
        try:
            _publish_artifact_mapping(destination, _transaction_generation("after-verifier"))
        except BaseException as exc:  # pragma: no cover - asserted through errors
            errors.append(exc)
        finally:
            writer_finished.set()

    verifier_thread = threading.Thread(target=verifier)
    writer_thread = threading.Thread(target=writer)
    verifier_thread.start()
    assert verifier_inside.wait(5)
    writer_thread.start()
    assert not writer_finished.wait(0.2)
    release_verifier.set()
    verifier_thread.join(15)
    writer_thread.join(15)
    assert not errors
    assert results[0]["status"] == "PASS_INTERNAL_ANALYTIC"
    assert writer_finished.is_set()


def test_predecessor_race_rolls_back_first_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "artifacts"
    original = artifact_module.predecessor_inventories
    calls = 0

    def changed_at_publication() -> dict[str, dict[str, object]]:
        nonlocal calls
        calls += 1
        observed = original()
        if calls >= 4:
            forged = copy.deepcopy(observed)
            forged["constitutive_map_3d_proof"]["entry_count"] += 1
            return forged
        return observed

    monkeypatch.setattr(artifact_module, "predecessor_inventories", changed_at_publication)
    with pytest.raises(ArtifactVerificationError, match="changed during publication"):
        artifact_module.write_artifacts(destination)
    assert not destination.exists()
    assert not list(tmp_path.glob(".cwt-cgt-artifacts-transaction-v1*"))


def test_semantic_summary_claim_or_gate_mutations_refuse() -> None:
    summary, records = theorem.execute_program()
    forged_claim = copy.deepcopy(summary)
    forged_claim["claim_ceiling"] = "UNIVERSAL_ALIGNMENT_PROVED"
    with pytest.raises(RuntimeError):
        artifact_module.require_semantic_pass(forged_claim, records)
    forged_gate = copy.deepcopy(summary)
    forged_gate["gates"]["G7_scalar_noncollinearity_obstruction"] = False
    with pytest.raises(RuntimeError):
        artifact_module.require_semantic_pass(forged_gate, records)


def test_cli_status_is_nonzero_and_never_prints_pass_on_verifier_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def refused() -> dict[str, object]:
        raise ArtifactVerificationError("forced disk mismatch")

    monkeypatch.setattr(run_module, "verify_artifacts", refused)
    result = CliRunner().invoke(run_module.app, ["status"])
    assert result.exit_code != 0
    assert "REFUSED" in result.output
    assert "PASS_INTERNAL_ANALYTIC" not in result.output

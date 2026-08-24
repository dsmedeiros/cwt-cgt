"""Source-only tests for the sealed generator-tensor response adapter."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import sys
from dataclasses import replace
from fractions import Fraction
from pathlib import Path
from types import FunctionType, ModuleType

import pytest
from typer.testing import CliRunner

from experiments.generator_tensor_response_protocol import (
    anchors,
    authority,
    broker as broker_module,
    contract as contract_module,
    geometry_plan as geometry_module,
    protocol as protocol_module,
)
from experiments.generator_tensor_response_protocol.broker import (
    LockedProducerCallable,
    OneShotResponseBroker,
    ResponseSample,
    _execute_reviewed_phase_child,
    _validate_producer_records,
    _validate_sample,
    normalize_curvature,
)
from experiments.generator_tensor_response_protocol.contract import (
    CALIBRATION_CENTERS,
    CHORD_RADIUS,
    COMPONENT_ORDER,
    CONFIRMATION_CENTERS,
    HELDOUT_AREA_VECTOR,
    HELDOUT_CENTER,
    MODEL_CONTRACT,
    NORMALIZED_CURVATURE_SCALES,
    ORDERED_GATES,
    PRODUCER_CALLABLES,
    ZERO_RADIUS,
    calibration_call_plan,
    confirmation_call_plan,
    contract_issues,
    heldout_call_plan,
)
from experiments.generator_tensor_response_protocol.exact import (
    canonical_json_bytes,
    canonical_sha256,
    matrix_multiply,
    matrix_vector,
)
from experiments.generator_tensor_response_protocol.firewall import (
    EXPECTED_PACKAGE_FILES,
    analyze_source_text,
    source_firewall_record,
)
from experiments.generator_tensor_response_protocol.fit import (
    commit_predictions,
    fit_exact,
    fit_passes,
    fit_record,
    prediction_record,
    validate_canonical_prediction_payload,
)
from experiments.generator_tensor_response_protocol.geometry_plan import (
    geometry_plan,
    geometry_plan_record,
    geometry_plan_valid,
)
from experiments.generator_tensor_response_protocol.protocol import (
    ProtocolSession,
    ProtocolState,
    nonauthoritative_source_test_model,
    nonauthoritative_source_test_trace,
)
from experiments.generator_tensor_response_protocol.run import ACCESS_REFUSAL, app
from experiments.generator_tensor_response_protocol.theorem import execute_program


def _producer_modules() -> tuple[str, ...]:
    prefix = "experiments.loop_flux_counting_curvature_proof"
    return tuple(sorted(name for name in sys.modules if name == prefix or name.startswith(prefix + ".")))


def _focused_test_git_binding() -> tuple[Path, Path]:
    selected_worktree = authority.REPO_ROOT.resolve(strict=True)
    local_git_dir = selected_worktree / ".git"
    local_index = local_git_dir / "index"
    if local_git_dir.is_dir() and local_index.is_file():
        return local_git_dir.resolve(strict=True), local_index.resolve(strict=True)
    configured_dir = os.environ.get(authority.GIT_DIR_ENV)
    configured_index = os.environ.get(authority.GIT_INDEX_ENV)
    configured_worktree = os.environ.get(authority.GIT_WORK_TREE_ENV)
    assert all(
        type(value) is str and value for value in (configured_dir, configured_index, configured_worktree)
    )
    git_dir = Path(configured_dir)  # type: ignore[arg-type]
    git_index = Path(configured_index)  # type: ignore[arg-type]
    worktree = Path(configured_worktree)  # type: ignore[arg-type]
    assert git_dir.is_absolute() and git_index.is_absolute() and worktree.is_absolute()
    assert worktree.resolve(strict=True) == selected_worktree
    return git_dir.resolve(strict=True), git_index.resolve(strict=True)


def _fresh_detached_child(
    tmp_path: Path,
    *,
    contaminate_pythonpath: bool = False,
    omit_git_binding: bool = False,
    stale_pyc: bool = False,
) -> subprocess.CompletedProcess[str]:
    source_package = (authority.SIM_ROOT / "experiments/generator_tensor_response_protocol").resolve(
        strict=True
    )
    detached = tmp_path / "detached"
    experiments = detached / "cwt-sim/experiments"
    experiments.mkdir(parents=True)
    (experiments / "__init__.py").write_text("", encoding="utf-8", newline="\n")
    shutil.copytree(source_package, experiments / source_package.name)
    predictor = experiments / "generator_tensor_prediction_protocol"
    producer = experiments / "loop_flux_counting_curvature_proof"
    predictor.mkdir()
    producer.mkdir()
    cache_prefix = tmp_path / "external-pycache"
    cache_prefix.mkdir()
    durable_ledger = tmp_path / "outer-durable-ledger"
    durable_ledger.mkdir()
    if stale_pyc:
        source = experiments / source_package.name / "broker.py"
        cache = producer / "__pycache__"
        cache.mkdir()
        pyc = cache / "generator.cpython-311.pyc"
        pyc.write_bytes(b"x" * source.stat().st_size)
        os.utime(pyc, ns=(source.stat().st_atime_ns, source.stat().st_mtime_ns))
    git_dir, git_index = _focused_test_git_binding()
    git_executable = shutil.which("git")
    assert git_executable is not None
    environment = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
        "WINDIR": os.environ.get("WINDIR", ""),
        "TEMP": str(tmp_path),
        "TMP": str(tmp_path),
        "PYTHONDONTWRITEBYTECODE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONPYCACHEPREFIX": str(cache_prefix),
        authority.GIT_EXECUTABLE_ENV: str(Path(git_executable).resolve(strict=True)),
        authority.PYTHON_EXECUTABLE_ENV: str(Path(sys.executable).resolve(strict=True)),
        authority.DURABLE_LEDGER_ROOT_ENV: str(durable_ledger.resolve(strict=True)),
    }
    if not omit_git_binding:
        environment.update(
            {
                authority.GIT_DIR_ENV: str(git_dir.resolve(strict=True)),
                authority.GIT_INDEX_ENV: str(git_index.resolve(strict=True)),
                authority.GIT_WORK_TREE_ENV: str(detached.resolve(strict=True)),
            }
        )
    if contaminate_pythonpath:
        environment["PYTHONPATH"] = "FORGED_IMPORT_ROOT"
    run_path = experiments / source_package.name / "run.py"
    return subprocess.run(
        [sys.executable, "-I", "-B", str(run_path), "phase-child", "1" * 40],
        cwd=detached,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )


def _synthetic_git(repo: Path, *arguments: str, stdin: bytes | None = None) -> bytes:
    environment = dict(os.environ)
    environment.update(
        {
            "GIT_AUTHOR_EMAIL": "source-test@example.invalid",
            "GIT_AUTHOR_NAME": "Source Test",
            "GIT_COMMITTER_EMAIL": "source-test@example.invalid",
            "GIT_COMMITTER_NAME": "Source Test",
        }
    )
    return subprocess.run(
        ["git", "--no-replace-objects", *arguments],
        cwd=repo,
        env=environment,
        input=stdin,
        check=True,
        capture_output=True,
    ).stdout


def _synthetic_commit(
    repo: Path,
    parent_oid: str,
    payloads: dict[str, bytes],
    *,
    label: str,
) -> str:
    index = repo / f".{label}.index"
    environment = dict(os.environ)
    environment["GIT_INDEX_FILE"] = str(index)
    environment.update(
        {
            "GIT_AUTHOR_EMAIL": "source-test@example.invalid",
            "GIT_AUTHOR_NAME": "Source Test",
            "GIT_COMMITTER_EMAIL": "source-test@example.invalid",
            "GIT_COMMITTER_NAME": "Source Test",
        }
    )

    def run(*arguments: str, stdin: bytes | None = None) -> bytes:
        return subprocess.run(
            ["git", "--no-replace-objects", *arguments],
            cwd=repo,
            env=environment,
            input=stdin,
            check=True,
            capture_output=True,
        ).stdout

    run("read-tree", parent_oid)
    for relative, raw in sorted(payloads.items()):
        blob_oid = run("hash-object", "-w", "--stdin", stdin=raw).decode("ascii").strip()
        run("update-index", "--add", "--cacheinfo", f"100644,{blob_oid},{relative}")
    tree_oid = run("write-tree").decode("ascii").strip()
    return run("commit-tree", tree_oid, "-p", parent_oid, stdin=f"{label}\n".encode()).decode("ascii").strip()


def _forged_internal_phase() -> authority._VerifiedPhaseAuthorization:
    return authority._VerifiedPhaseAuthorization(
        phase="CAL",
        sequence=1,
        session_id="1" * 64,
        authority_commit_oid="2" * 40,
        raw_sha256="3" * 64,
        plan_sha256=geometry_plan().plan_sha256,
        adapter_source_lock_commit_oid="4" * 40,
        adapter_source_lock_sha256="5" * 64,
        adapter_source_commit_oid="6" * 40,
        adapter_source_tree_oid="7" * 40,
        prior_authority_commit_oid="4" * 40,
        prior_record_sha256="5" * 64,
        prior_state="ADAPTER_SOURCE_LOCKED",
        prediction_sha256=None,
        request_ids=authority.phase_request_ids("CAL"),
        seal=authority._VERIFIED_SEAL,
    )


def _sample(
    *,
    label: str = "A1",
    center=CALIBRATION_CENTERS[0],
    radius: Fraction = CHORD_RADIUS,
    vector=(Fraction(1), Fraction(2), Fraction(3)),
) -> ResponseSample:
    direct = tuple(item for item in vector)
    fcs = tuple(item + Fraction(0) for item in vector)
    one_form = (center[0] + center[1], center[1] + center[2], center[2] + center[0])
    return ResponseSample(
        label=label,
        center=center,
        radius=radius,
        orientation=1,
        component_order=COMPONENT_ORDER,
        direct_response_one_form=tuple(item for item in one_form),
        fcs_normal_connection_one_form=tuple(item + Fraction(0) for item in one_form),
        raw_direct_response_curl=direct,
        raw_independent_fcs_curl=fcs,
        normalized_direct_response_curl=normalize_curvature(direct),
        normalized_independent_fcs_curl=normalize_curvature(fcs),
    )


def _direct_record(vector=(Fraction(1), Fraction(-2), Fraction(3))) -> dict[str, object]:
    derivatives = [
        [Fraction(0), Fraction(0), vector[1]],
        [vector[2], Fraction(0), Fraction(0)],
        [Fraction(0), vector[0], Fraction(0)],
    ]
    return {
        "direct_response_one_form": (Fraction(4), Fraction(5), Fraction(6)),
        "direct_response_derivative_matrix": derivatives,
        "direct_response_curl_order": COMPONENT_ORDER,
        "direct_response_curl": tuple(item for item in vector),
        "direct_response_curl_signs": tuple(1 if item > 0 else -1 for item in vector),
        "all_direct_response_curl_components_nonzero": all(item != 0 for item in vector),
        "orientation": 1,
    }


def _fcs_record(vector=(Fraction(1), Fraction(-2), Fraction(3))) -> dict[str, object]:
    derivatives = [
        [Fraction(0), vector[2], Fraction(0)],
        [Fraction(0), Fraction(0), vector[0]],
        [vector[1], Fraction(0), Fraction(0)],
    ]
    return {
        "fcs_left_q_eigenvector_equation": True,
        "fcs_right_q_eigenvector_equation": True,
        "fcs_left_q_gauge": True,
        "fcs_right_q_gauge": True,
        "fcs_minus_partial_q_connection_one_form": (
            Fraction(4),
            Fraction(5),
            Fraction(6),
        ),
        "fcs_normal_connection_derivative_matrix": derivatives,
        "fcs_normal_connection_curl_order": tuple(item for item in COMPONENT_ORDER),
        "fcs_normal_connection_curl": tuple(item + Fraction(0) for item in vector),
        "fcs_normal_connection_curl_signs": tuple(1 if item > 0 else -1 for item in vector),
    }


def _exact_observations(coefficients: tuple[Fraction, Fraction, Fraction]):
    plan = geometry_plan()
    return tuple(matrix_vector(matrix, coefficients) for matrix in plan.calibration_matrices)


def test_locked_source_anchor_uses_ast_without_importing_response() -> None:
    assert _producer_modules() == ()
    record = anchors.anchor_record()
    assert record["predictor_source_commit_oid"] == MODEL_CONTRACT.predictor_source_commit_oid
    assert record["predictor_metadata_commit_oid"] == MODEL_CONTRACT.predictor_metadata_commit_oid
    assert record["producer_source_lock_sha256"] == MODEL_CONTRACT.producer_source_lock_sha256
    assert len(record["producer_callable_records"]) == 3
    assert all(
        set(item)
        == {
            "label",
            "module",
            "qualname",
            "blob_oid",
            "sha256_raw",
            "signature",
            "source_span_sha256",
            "canonical_ast_sha256",
            "transitive_call_graph_sha256",
        }
        for item in record["producer_callable_records"]
    )
    assert record["response_values_read"] is False
    assert record["producer_modules_imported"] is False
    assert _producer_modules() == ()


def test_anchor_refuses_lock_hash_callable_ast_or_callgraph_drift(monkeypatch) -> None:
    monkeypatch.setattr(anchors, "PRODUCER_SOURCE_LOCK_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="raw hash refused"):
        anchors.anchor_record()
    monkeypatch.undo()
    for field in ("signature", "canonical_ast_sha256", "transitive_call_graph_sha256"):
        forged = copy.deepcopy({key: dict(value) for key, value in PRODUCER_CALLABLES.items()})
        forged["build_branch_bundle"][field] = "0" * 64
        monkeypatch.setattr(anchors, "PRODUCER_CALLABLES", forged)
        with pytest.raises(RuntimeError, match="callable anchor refused"):
            anchors.anchor_record()
        monkeypatch.undo()


@pytest.mark.parametrize("drifted_name", ["connection_eligibility.py", "counting_lane.py"])
def test_anchor_refuses_any_locked_dependency_worktree_drift(monkeypatch, drifted_name: str) -> None:
    original = anchors._read_reviewed_file

    def drift_once(path: Path) -> bytes:
        raw = original(path)
        return raw + b"# drift\n" if path.name == drifted_name else raw

    monkeypatch.setattr(anchors, "_read_reviewed_file", drift_once)
    with pytest.raises(RuntimeError, match="locked worktree bytes refused"):
        anchors.anchor_record()
    assert _producer_modules() == ()


def test_contract_geometry_and_call_plans_are_exact_and_response_blind() -> None:
    assert not contract_issues()
    plan = geometry_plan()
    record = geometry_plan_record()
    assert plan.calibration_centers == CALIBRATION_CENTERS
    assert plan.confirmation_centers == CONFIRMATION_CENTERS
    assert plan.heldout_center == HELDOUT_CENTER
    assert plan.heldout_area_vector == HELDOUT_AREA_VECTOR
    assert record["response_accessed"] is False
    assert record["producer_capability_received"] is False
    assert MODEL_CONTRACT.durable_outer_ledger_binding_required is True
    assert MODEL_CONTRACT.durable_outer_ledger_outside_detached_worktree is True
    assert MODEL_CONTRACT.durable_outer_ledger_keyed_by_authority_session_sequence is True
    assert MODEL_CONTRACT.outer_provisions_and_verifies_durable_ledger is True
    assert MODEL_CONTRACT.outer_refuses_launch_when_exact_ledger_key_exists is True
    assert MODEL_CONTRACT.child_atomically_consumes_ledger_key_before_producer_import is True
    assert MODEL_CONTRACT.durable_outer_ledger_process_controlled_not_cryptographic is True
    assert MODEL_CONTRACT.durable_ledger_evidence_requires_later_external_commit is True
    assert calibration_call_plan() == tuple(
        (f"A{index}", center, radius)
        for index, center in enumerate(CALIBRATION_CENTERS, start=1)
        for radius in (CHORD_RADIUS, ZERO_RADIUS)
    )
    assert len(calibration_call_plan()) == 12
    assert len(confirmation_call_plan()) == 4
    assert heldout_call_plan() == (
        ("H", HELDOUT_CENTER, CHORD_RADIUS),
        ("H", HELDOUT_CENTER, ZERO_RADIUS),
    )
    assert _producer_modules() == ()


def test_geometry_plan_strict_types_refuse_bool_as_int_at_every_consumer() -> None:
    plan = geometry_plan()
    forged = replace(plan, heldout_area_vector=(True, -1, 3))
    assert not geometry_plan_valid(forged)
    observations = _exact_observations((Fraction(1), Fraction(2), Fraction(3)))
    with pytest.raises(TypeError, match="exact geometry-plan"):
        fit_exact(forged, observations)
    with pytest.raises(TypeError, match="exact reviewed geometry plan"):
        ProtocolSession(forged)


def test_reviewed_contract_and_geometry_digests_are_independent_literals(monkeypatch) -> None:
    monkeypatch.setattr(contract_module, "CONTRACT_SHA256", "0" * 64)
    assert "reviewed_contract_sha256" in contract_module.contract_issues()
    monkeypatch.undo()
    geometry_module._geometry_plan_fields.cache_clear()
    monkeypatch.setattr(geometry_module, "REVIEWED_GEOMETRY_PLAN_SHA256", "0" * 64)
    with pytest.raises(RuntimeError, match="geometry-plan digest refused"):
        geometry_module.geometry_plan()
    monkeypatch.undo()
    geometry_module._geometry_plan_fields.cache_clear()
    assert geometry_module.geometry_plan() == geometry_plan()


def test_mutating_one_returned_geometry_plan_cannot_poison_future_authority() -> None:
    plan = geometry_plan()
    original_row = plan.heldout_projection_row
    object.__setattr__(plan, "heldout_projection_row", (Fraction(0), Fraction(0), Fraction(0)))
    assert not geometry_plan_valid(plan)
    fresh = geometry_plan()
    assert fresh is not plan
    assert fresh.heldout_projection_row == original_row
    assert geometry_plan_valid(fresh)
    assert canonical_sha256(geometry_plan_record()) == geometry_module.REVIEWED_GEOMETRY_RECORD_SHA256


def test_prelock_source_cannot_bind_arbitrary_hex_or_authorize_any_phase() -> None:
    plan = geometry_plan()
    session = ProtocolSession(plan)
    broker = OneShotResponseBroker(plan_sha256=plan.plan_sha256)
    with pytest.raises(PermissionError, match="source lock refused"):
        session.bind_adapter_source_lock("1" * 40)
    assert session.state is ProtocolState.PREDICTOR_LOCKED
    assert session.source_lock is None
    for operation in (
        broker.calibration_deltas,
        broker.confirmation_deltas,
        broker.heldout_scalar,
    ):
        with pytest.raises(PermissionError, match="whole-phase child"):
            operation(object())  # type: ignore[arg-type]
    assert broker.call_count == 0
    with pytest.raises(AttributeError, match="read-only"):
        broker._terminal = False
    with pytest.raises(AttributeError, match="read-only"):
        broker._used_phases = ()
    assert _producer_modules() == ()


def test_focused_fixture_requires_explicit_external_git_binding_without_dot_git(
    monkeypatch,
    tmp_path: Path,
) -> None:
    expected_git_dir, expected_git_index = _focused_test_git_binding()
    selected = tmp_path / "selected-index-without-dot-git"
    selected.mkdir()
    monkeypatch.setattr(authority, "REPO_ROOT", selected)
    monkeypatch.setenv(authority.GIT_DIR_ENV, str(expected_git_dir))
    monkeypatch.setenv(authority.GIT_INDEX_ENV, str(expected_git_index))
    monkeypatch.setenv(authority.GIT_WORK_TREE_ENV, str(selected.resolve(strict=True)))
    git_dir, git_index = _focused_test_git_binding()
    assert git_dir == expected_git_dir
    assert git_index == expected_git_index
    monkeypatch.delenv(authority.GIT_WORK_TREE_ENV)
    with pytest.raises(AssertionError):
        _focused_test_git_binding()
    assert _producer_modules() == ()


def test_private_structural_phase_record_rebinds_git_before_any_access() -> None:
    plan = geometry_plan()
    forged = _forged_internal_phase()
    broker = OneShotResponseBroker(plan_sha256=plan.plan_sha256)
    with pytest.raises(PermissionError, match="whole-phase child"):
        broker.calibration_deltas(forged)
    with pytest.raises(PermissionError, match="nonauthoritative"):
        LockedProducerCallable()._call_authorized(
            forged,
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
            orientation=1,
        )
    with pytest.raises(TypeError, match="construction refused"):
        OneShotResponseBroker(plan_sha256="0" * 64)
    assert not hasattr(broker, "_sample")
    assert not hasattr(broker, "_vector_batch")
    assert not hasattr(broker, "_begin")
    assert broker.call_count == 0
    assert not authority.ACCESS_LEDGER_DIR.exists()
    assert _producer_modules() == ()


def test_public_hash_constructors_and_structural_authority_types_do_not_exist() -> None:
    for name in (
        "AdapterSourceLockBinding",
        "PhaseAuthorization",
        "make_phase_authorization",
        "BrokerCapability",
        "make_broker_capability",
    ):
        assert not hasattr(protocol_module, name)
        assert not hasattr(broker_module, name)
    assert "producer" not in inspect.signature(OneShotResponseBroker).parameters


def test_locked_producer_direct_call_refuses_before_import() -> None:
    locked = LockedProducerCallable()
    with pytest.raises(PermissionError, match="whole-phase child process"):
        locked(
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
            orientation=1,
        )
    with pytest.raises(AttributeError, match="read-only"):
        locked._runtime_callables = ()
    assert _producer_modules() == ()


def test_inprocess_authorization_and_whole_phase_direct_calls_refuse_before_import() -> None:
    plan = geometry_plan()
    session = ProtocolSession(plan)
    object.__setattr__(session, "_authorization", _forged_internal_phase())
    object.__setattr__(session, "_ProtocolSession__source_lock", object())
    with pytest.raises(PermissionError, match="nonauthoritative"):
        session._broker_authorization("CAL")
    assert tuple(inspect.signature(_execute_reviewed_phase_child).parameters) == ("authority_commit_oid",)
    with pytest.raises(PermissionError, match="fresh isolated phase child"):
        _execute_reviewed_phase_child("1" * 40)
    assert _producer_modules() == ()


def test_request_ids_are_exact_fixed_phase_sets_without_generic_plan_input() -> None:
    cal = authority.phase_request_ids("CAL")
    validation = authority.phase_request_ids("V")
    heldout = authority.phase_request_ids("H")
    assert (len(cal), len(validation), len(heldout)) == (12, 4, 2)
    assert len(set((*cal, *validation, *heldout))) == 18
    with pytest.raises(authority.AuthorityVerificationError):
        authority.phase_request_ids("GENERIC")
    with pytest.raises(TypeError):
        authority.phase_request_ids("CAL", (("X", CALIBRATION_CENTERS[0], CHORD_RADIUS),))  # type: ignore[call-arg]


def test_session_reviewed_fields_are_read_only_and_stale_plan_is_refused() -> None:
    plan = geometry_plan()
    session = ProtocolSession(plan)
    with pytest.raises(AttributeError):
        session.state = ProtocolState.H_PASS  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session.plan = replace(plan, plan_sha256="0" * 64)  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session.source_lock = object()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session.fit = object()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session.predictions = object()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session.calibration_responses = ()  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session.degeneracy = "FORGED"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session._ProtocolSession__state = ProtocolState.H_PASS
    with pytest.raises(AttributeError):
        session._authorization = _forged_internal_phase()
    assert not hasattr(session, "_set")
    with pytest.raises(TypeError, match="reviewed geometry plan"):
        ProtocolSession(replace(plan, plan_sha256="0" * 64))


def test_nonauthoritative_transition_model_reaches_synthetic_h_pass_only_in_order() -> None:
    events = (
        "LOCK_VERIFIED",
        "CAL_AUTH_VERIFIED",
        "CAL_ACCESS_STARTED",
        "CAL_EXACT_PASS",
        "PREDICTIONS_PREPARED",
        "PREDICTIONS_DURABLY_COMMITTED",
        "V_AUTH_VERIFIED",
        "V_ACCESS_STARTED",
        "V_ATOMIC_PASS",
        "H_AUTH_VERIFIED",
        "H_ACCESS_STARTED",
        "H_SCALAR_PASS",
    )
    record = nonauthoritative_source_test_trace(events)
    assert record == {
        "authoritative": False,
        "response_accessed": False,
        "state": "H_PASS",
        "events": events,
    }
    with pytest.raises(RuntimeError, match="out of order"):
        nonauthoritative_source_test_trace(("H_AUTH_VERIFIED",))


def test_full_synthetic_h_pass_is_exact_and_explicitly_nonauthoritative() -> None:
    plan = geometry_plan()
    coefficients = (Fraction(2), Fraction(-3), Fraction(5))
    fit = fit_exact(plan, _exact_observations(coefficients))
    predicted = commit_predictions(plan, fit)
    passed = nonauthoritative_source_test_model(
        fit.observed_deltas,
        predicted.confirmation_vectors,
        predicted.heldout_scalar_projection,
    )
    assert passed == {
        "authoritative": False,
        "response_accessed": False,
        "state": "H_PASS",
    }
    failed_v = nonauthoritative_source_test_model(
        fit.observed_deltas,
        (
            (Fraction(0), Fraction(0), Fraction(0)),
            predicted.confirmation_vectors[1],
        ),
        predicted.heldout_scalar_projection,
    )
    assert failed_v["state"] == "V_FAIL"
    failed_h = nonauthoritative_source_test_model(
        fit.observed_deltas,
        predicted.confirmation_vectors,
        predicted.heldout_scalar_projection + 1,
    )
    assert failed_h["state"] == "H_FAIL"


def test_exact_response_sample_schema_and_normalized_pullback() -> None:
    sample = _sample()
    assert (
        _validate_sample(
            sample,
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
        )
        is sample
    )
    assert NORMALIZED_CURVATURE_SCALES == (
        Fraction(1, 300),
        Fraction(1, 300),
        Fraction(1, 2500),
    )


def test_response_sample_rejects_fraction_subclass_bool_order_alias_and_bad_normalization() -> None:
    class FractionSubclass(Fraction):
        pass

    sample = _sample()
    with pytest.raises(TypeError, match="exact Fraction"):
        _validate_sample(
            replace(sample, raw_direct_response_curl=(FractionSubclass(1), Fraction(2), Fraction(3))),
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
        )
    with pytest.raises(TypeError, match="identity refused"):
        _validate_sample(
            replace(sample, orientation=True),
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
        )
    with pytest.raises(TypeError, match="identity refused"):
        _validate_sample(
            replace(sample, component_order=("F_t_b", "F_d_t", "F_b_d")),
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
        )
    with pytest.raises(RuntimeError, match="reused one result object"):
        _validate_sample(
            replace(sample, raw_independent_fcs_curl=sample.raw_direct_response_curl),
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
        )
    bad_normalized = (
        sample.normalized_direct_response_curl[0] + Fraction(1),
        *sample.normalized_direct_response_curl[1:],
    )
    with pytest.raises(RuntimeError, match="pullback differs"):
        _validate_sample(
            replace(sample, normalized_direct_response_curl=bad_normalized),
            label="A1",
            center=CALIBRATION_CENTERS[0],
            radius=CHORD_RADIUS,
        )


def test_exact_direct_and_fcs_record_schemas_are_closed_distinct_and_ordered() -> None:
    direct = _direct_record()
    fcs = _fcs_record()
    observed = _validate_producer_records(direct, fcs, orientation=1)
    assert observed[0] == observed[1]
    assert observed[2] == observed[3]
    assert direct is not fcs
    assert direct["direct_response_curl"] is not fcs["fcs_normal_connection_curl"]


@pytest.mark.parametrize(
    "attack",
    [
        "missing",
        "extra",
        "fcs_order",
        "shared_matrix",
        "shared_one_form",
        "shared_curl",
        "direct_matrix_curl_mismatch",
        "fcs_matrix_curl_mismatch",
        "fraction_subclass",
        "shared_record",
    ],
)
def test_producer_record_schema_alias_and_fcs_order_attacks_fail(attack: str) -> None:
    direct = _direct_record()
    fcs = _fcs_record()
    if attack == "missing":
        fcs.pop("fcs_normal_connection_curl_order")
    elif attack == "extra":
        direct["FORGED"] = True
    elif attack == "fcs_order":
        fcs["fcs_normal_connection_curl_order"] = ("F_t_b", "F_d_t", "F_b_d")
    elif attack == "shared_matrix":
        fcs["fcs_normal_connection_derivative_matrix"] = direct["direct_response_derivative_matrix"]
    elif attack == "shared_one_form":
        fcs["fcs_minus_partial_q_connection_one_form"] = direct["direct_response_one_form"]
    elif attack == "shared_curl":
        fcs["fcs_normal_connection_curl"] = direct["direct_response_curl"]
    elif attack == "direct_matrix_curl_mismatch":
        direct["direct_response_derivative_matrix"][2][1] += Fraction(1)
    elif attack == "fcs_matrix_curl_mismatch":
        fcs["fcs_normal_connection_derivative_matrix"][1][2] += Fraction(1)
    elif attack == "fraction_subclass":

        class FractionSubclass(Fraction):
            pass

        fcs["fcs_normal_connection_curl"] = (
            FractionSubclass(1),
            Fraction(-2),
            Fraction(3),
        )
    else:
        shared = {**direct, **fcs}
        direct = shared
        fcs = shared
    with pytest.raises((TypeError, RuntimeError)):
        _validate_producer_records(direct, fcs, orientation=1)


def test_preloaded_fake_producer_module_and_callable_are_refused(monkeypatch) -> None:
    expected = PRODUCER_CALLABLES["build_branch_bundle"]
    module_name = expected["module"]
    fake_module = ModuleType(module_name)

    def forged_callable(*, center=None, radius=None):
        del center, radius
        return None

    forged_callable.__module__ = module_name
    forged_callable.__qualname__ = expected["qualname"]
    with monkeypatch.context() as context:
        context.setitem(sys.modules, module_name, fake_module)
        with pytest.raises(RuntimeError, match="module origin refused"):
            anchors.authenticate_runtime_callable(forged_callable, expected)
    assert _producer_modules() == ()


def test_runtime_callable_authentication_binds_identity_globals_metadata_and_helpers(
    monkeypatch, tmp_path: Path
) -> None:
    module_name = "synthetic_runtime_callable_authority"
    source = (
        "from __future__ import annotations\n"
        "def helper(value: int = 1) -> int:\n"
        "    return value + 1\n"
        "def reviewed(value: int = 1, *, scale: int = 2) -> int:\n"
        "    return helper(value) * scale\n"
    )
    source_path = tmp_path / f"{module_name}.py"
    source_path.write_text(source, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location(module_name, source_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    expected = {
        "module": module_name,
        "qualname": "reviewed",
        "blob_oid": "0" * 40,
        "sha256_raw": hashlib.sha256(source.encode("utf-8")).hexdigest(),
        **anchors._callable_source_record(source, "reviewed"),
    }
    monkeypatch.setattr(anchors, "SIM_ROOT", tmp_path)
    anchors._RUNTIME_MODULE_SNAPSHOTS.pop(module_name, None)
    try:
        reviewed = module.reviewed
        helper = module.helper
        anchors.authenticate_runtime_callable(reviewed, expected)

        forged_globals = {"helper": helper, "__builtins__": module.__dict__["__builtins__"]}
        cloned = FunctionType(
            reviewed.__code__,
            forged_globals,
            reviewed.__name__,
            reviewed.__defaults__,
            reviewed.__closure__,
        )
        cloned.__module__ = module_name
        cloned.__qualname__ = reviewed.__qualname__
        cloned.__kwdefaults__ = dict(reviewed.__kwdefaults__ or {})
        cloned.__annotations__ = dict(reviewed.__annotations__)
        with pytest.raises(RuntimeError, match="callable identity refused"):
            anchors.authenticate_runtime_callable(cloned, expected)

        module.reviewed = cloned
        with pytest.raises(RuntimeError, match="(?:callable identity|module dictionary drift) refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
        module.reviewed = reviewed

        reviewed.__defaults__ = (2,)
        with pytest.raises(RuntimeError, match="callable metadata refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
        reviewed.__defaults__ = (1,)

        reviewed.__kwdefaults__ = {"scale": 3}
        with pytest.raises(RuntimeError, match="callable metadata refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
        reviewed.__kwdefaults__ = {"scale": 2}

        reviewed.__annotations__ = {"value": "FORGED", "return": "int"}
        with pytest.raises(RuntimeError, match="callable metadata refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
        reviewed.__annotations__ = {"value": "int", "scale": "int", "return": "int"}

        def closure_factory(offset: int):
            def forged(value: int = 1, *, scale: int = 2) -> int:
                return (value + offset) * scale

            return forged

        closure = closure_factory(1)
        closure.__module__ = module_name
        closure.__qualname__ = "reviewed"
        module.reviewed = closure
        with pytest.raises(RuntimeError, match="refused"):
            anchors.authenticate_runtime_callable(closure, expected)
        module.reviewed = reviewed

        helper_clone = FunctionType(
            helper.__code__,
            module.__dict__,
            helper.__name__,
            helper.__defaults__,
            helper.__closure__,
        )
        helper_clone.__module__ = module_name
        helper_clone.__qualname__ = "helper"
        helper_clone.__annotations__ = dict(helper.__annotations__)
        module.helper = helper_clone
        with pytest.raises(RuntimeError, match="module dictionary drift refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
        module.helper = helper

        def forged_helper(value: int = 1) -> int:
            return value + 99

        original_helper_code = helper.__code__
        helper.__code__ = forged_helper.__code__
        with pytest.raises(RuntimeError, match="callable metadata refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
        helper.__code__ = original_helper_code

        helper.__defaults__ = (2,)
        with pytest.raises(RuntimeError, match="callable metadata refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
        helper.__defaults__ = (1,)

        module.UNREVIEWED_GLOBAL = object()
        with pytest.raises(RuntimeError, match="module dictionary drift refused"):
            anchors.authenticate_runtime_callable(reviewed, expected)
    finally:
        anchors._RUNTIME_MODULE_SNAPSHOTS.pop(module_name, None)
        sys.modules.pop(module_name, None)
    assert _producer_modules() == ()


def test_imported_transitive_helper_code_and_defaults_are_revalidated(monkeypatch, tmp_path: Path) -> None:
    helper_name = "experiments.loop_flux_counting_curvature_proof.synthetic_helper"
    root_name = "synthetic_runtime_root"
    helper_source = (
        "from __future__ import annotations\n" "def helper(value: int = 1) -> int:\n" "    return value + 1\n"
    )
    root_source = (
        "from __future__ import annotations\n"
        "def reviewed(value: int = 1) -> int:\n"
        "    return helper(value)\n"
    )
    helper_path = tmp_path / (helper_name.replace(".", "/") + ".py")
    helper_path.parent.mkdir(parents=True)
    helper_path.write_text(helper_source, encoding="utf-8", newline="\n")
    root_path = tmp_path / f"{root_name}.py"
    root_path.write_text(root_source, encoding="utf-8", newline="\n")

    def load(name: str, path: Path) -> ModuleType:
        spec = importlib.util.spec_from_file_location(name, path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        return module

    helper_module = load(helper_name, helper_path)
    root_module = load(root_name, root_path)
    root_module.helper = helper_module.helper
    expected = {
        "module": root_name,
        "qualname": "reviewed",
        "blob_oid": "0" * 40,
        "sha256_raw": hashlib.sha256(root_source.encode("utf-8")).hexdigest(),
        **anchors._callable_source_record(root_source, "reviewed"),
    }
    monkeypatch.setattr(anchors, "SIM_ROOT", tmp_path)
    monkeypatch.setattr(anchors, "_require_producer_module_lock", lambda _name, _raw: None)
    anchors._RUNTIME_MODULE_SNAPSHOTS.pop(root_name, None)
    anchors._RUNTIME_MODULE_SNAPSHOTS.pop(helper_name, None)
    try:
        anchors.authenticate_runtime_callable(root_module.reviewed, expected)
        helper = helper_module.helper

        def forged(value: int = 1) -> int:
            return value + 99

        original_code = helper.__code__
        helper.__code__ = forged.__code__
        with pytest.raises(RuntimeError, match="callable metadata refused"):
            anchors.authenticate_runtime_callable(root_module.reviewed, expected)
        helper.__code__ = original_code

        helper.__defaults__ = (2,)
        with pytest.raises(RuntimeError, match="callable metadata refused"):
            anchors.authenticate_runtime_callable(root_module.reviewed, expected)
        helper.__defaults__ = (1,)
    finally:
        anchors._RUNTIME_MODULE_SNAPSHOTS.pop(root_name, None)
        anchors._RUNTIME_MODULE_SNAPSHOTS.pop(helper_name, None)
        sys.modules.pop(root_name, None)
        sys.modules.pop(helper_name, None)
    assert _producer_modules() == ()


def test_full_fit_is_independently_recomputed_and_all_forged_fields_fail() -> None:
    plan = geometry_plan()
    coefficients = (Fraction(2, 3), Fraction(-5, 7), Fraction(11, 13))
    fit = fit_exact(plan, _exact_observations(coefficients))
    assert fit_passes(plan, fit)
    assert fit_record(plan, fit)["fit_sha256"] == fit.fit_sha256
    assert fit.coefficients == coefficients
    assert fit.exact_rank == 3 and fit.gram_determinant != 0
    assert len(fit.design_matrix) == 18 and len(fit.target_vector) == 18
    identity = matrix_multiply(fit.gram_matrix, fit.gram_inverse)
    assert identity == tuple(
        tuple(Fraction(1) if row == column else Fraction(0) for column in range(3)) for row in range(3)
    )
    attacks = (
        replace(fit, plan_sha256="0" * 64),
        replace(fit, target_vector=(fit.target_vector[0] + 1, *fit.target_vector[1:])),
        replace(fit, coefficients=(fit.coefficients[0] + 1, *fit.coefficients[1:])),
        replace(fit, gram_inverse=tuple(reversed(fit.gram_inverse))),
        replace(fit, normal_rhs=(fit.normal_rhs[0] + 1, *fit.normal_rhs[1:])),
        replace(fit, residuals=(Fraction(0),) * 17 + (Fraction(1),)),
        replace(fit, fit_sha256="0" * 64),
    )
    assert all(not fit_passes(plan, attack) for attack in attacks)
    with pytest.raises(TypeError, match="exact geometry-plan"):
        fit_exact(replace(plan, plan_sha256="0" * 64), _exact_observations(coefficients))
    shared = (Fraction(1), Fraction(2), Fraction(3))
    with pytest.raises(RuntimeError, match="vectors alias"):
        fit_exact(plan, (shared,) * 6)


def test_prediction_commit_is_exact_and_module_level_refuses_both_degeneracies() -> None:
    plan = geometry_plan()
    fit = fit_exact(plan, _exact_observations((Fraction(3), Fraction(-2), Fraction(5))))
    committed = commit_predictions(plan, fit)
    assert prediction_record(committed)["confirmation_vectors"] == committed.confirmation_vectors
    assert len(committed.prediction_sha256) == 64
    zero_fit = fit_exact(plan, _exact_observations((Fraction(0), Fraction(0), Fraction(0))))
    with pytest.raises(RuntimeError, match="degenerate"):
        commit_predictions(plan, zero_fit)
    first, second, _third = plan.heldout_projection_row
    zero_h = (second, -first, Fraction(0))
    assert zero_h != (Fraction(0), Fraction(0), Fraction(0))
    h_fit = fit_exact(plan, _exact_observations(zero_h))
    with pytest.raises(RuntimeError, match="degenerate"):
        commit_predictions(plan, h_fit)


def test_prediction_record_digest_and_payload_mutations_fail() -> None:
    plan = geometry_plan()
    fit = fit_exact(plan, _exact_observations((Fraction(1), Fraction(2), Fraction(3))))
    committed = commit_predictions(plan, fit)
    with pytest.raises(RuntimeError, match="digest refused"):
        prediction_record(replace(committed, prediction_sha256="0" * 64))

    class StringSubclass(str):
        pass

    with pytest.raises(TypeError, match="schema refused"):
        prediction_record(replace(committed, prediction_sha256=StringSubclass(committed.prediction_sha256)))
    canonical_payload = json.loads(canonical_json_bytes(prediction_record(committed)))
    assert validate_canonical_prediction_payload(canonical_payload, committed.prediction_sha256)
    canonical_payload["fit_record"]["exact_rank"] = True
    assert not validate_canonical_prediction_payload(canonical_payload, committed.prediction_sha256)
    with pytest.raises(RuntimeError, match="values differ|digest refused"):
        prediction_record(
            replace(
                committed,
                confirmation_vectors=(
                    (Fraction(0), Fraction(0), Fraction(0)),
                    committed.confirmation_vectors[1],
                ),
            )
        )
    with pytest.raises(TypeError, match="schema refused"):
        prediction_record(replace(committed, fit_sha256="G" * 64))
    with pytest.raises(TypeError, match="schema refused"):
        prediction_record(replace(committed, fit=replace(committed.fit, fit_sha256="0" * 64)))
    with pytest.raises(TypeError, match="schema refused"):
        prediction_record(
            replace(
                committed,
                confirmation_vectors=(
                    committed.confirmation_vectors[0],
                    committed.confirmation_vectors[0],
                ),
            )
        )


def test_committed_phase_results_bind_exact_fit_confirmation_and_heldout_values() -> None:
    plan = geometry_plan()
    fit = fit_exact(plan, _exact_observations((Fraction(1), Fraction(2), Fraction(3))))
    committed = commit_predictions(plan, fit)
    prediction = json.loads(canonical_json_bytes(prediction_record(committed)))
    phase_raw = b"exact phase authority\n"

    def phase_payload(phase: str, sequence: int) -> dict[str, object]:
        return {
            "phase": phase,
            "sequence": sequence,
            "session_id": "1" * 64,
            "request_ids": list(authority.phase_request_ids(phase)),
        }

    def result_payload(
        phase: str,
        sequence: int,
        vectors: tuple[tuple[Fraction, Fraction, Fraction], ...],
        scalar: Fraction | None,
    ) -> dict[str, object]:
        return json.loads(
            authority.canonical_json_bytes(
                {
                    "schema": "generator_tensor_response_phase_result_v1",
                    "phase": phase,
                    "sequence": sequence,
                    "session_id": "1" * 64,
                    "authority_commit_oid": "2" * 40,
                    "authority_record_sha256": hashlib.sha256(phase_raw).hexdigest(),
                    "request_ids": authority.phase_request_ids(phase),
                    "sample_call_count": {"CAL": 12, "V": 4, "H": 2}[phase],
                    "normalized_excess_vectors": vectors,
                    "heldout_scalar_projection": scalar,
                    "direct_fcs_crosscheck_complete": True,
                }
            )
        )

    cases = (
        ("CAL", 1, fit.observed_deltas, None),
        ("V", 2, committed.confirmation_vectors, None),
        ("H", 3, (), committed.heldout_scalar_projection),
    )
    for phase, sequence, vectors, scalar in cases:
        payload = result_payload(phase, sequence, vectors, scalar)
        assert authority._validate_phase_result_payload(
            payload,
            phase_commit_oid="2" * 40,
            phase_payload=phase_payload(phase, sequence),
            phase_raw=phase_raw,
            prediction_payload=prediction,
        )
        forged = copy.deepcopy(payload)
        forged["direct_fcs_crosscheck_complete"] = 1
        assert not authority._validate_phase_result_payload(
            forged,
            phase_commit_oid="2" * 40,
            phase_payload=phase_payload(phase, sequence),
            phase_raw=phase_raw,
            prediction_payload=prediction,
        )
        forged = copy.deepcopy(payload)
        if phase == "H":
            forged["heldout_scalar_projection"] = {
                "denominator_hex": "1",
                "numerator_hex": "0",
            }
        else:
            forged["normalized_excess_vectors"][0][0] = {
                "denominator_hex": "1",
                "numerator_hex": "0",
            }
        assert not authority._validate_phase_result_payload(
            forged,
            phase_commit_oid="2" * 40,
            phase_payload=phase_payload(phase, sequence),
            phase_raw=phase_raw,
            prediction_payload=prediction,
        )


def test_external_outcome_commit_delta_is_exactly_result_plus_outcome(monkeypatch) -> None:
    phase = "CAL"
    expected_paths = (
        authority.PHASE_OUTCOME_RELATIVE[phase],
        authority.PHASE_RESULT_RELATIVE[phase],
    )
    encoded = b"".join(b"A\0" + path.encode("utf-8") + b"\0" for path in sorted(expected_paths))
    monkeypatch.setattr(authority, "_git", lambda _arguments: encoded)
    authority._require_exact_commit_delta("1" * 40, "2" * 40, expected_paths)
    monkeypatch.setattr(
        authority,
        "_git",
        lambda _arguments: encoded + b"A\0cwt-sim/experiments/forged.json\0",
    )
    with pytest.raises(authority.AuthorityVerificationError, match="delta refused"):
        authority._require_exact_commit_delta("1" * 40, "2" * 40, expected_paths)
    monkeypatch.setattr(
        authority,
        "_git",
        lambda _arguments: b"M\0" + encoded[2:],
    )
    with pytest.raises(authority.AuthorityVerificationError, match="delta refused"):
        authority._require_exact_commit_delta("1" * 40, "2" * 40, expected_paths)


def test_durable_ledger_records_are_exclusive_and_nonretryable(monkeypatch, tmp_path: Path) -> None:
    checkout = tmp_path / "detached-checkout"
    checkout.mkdir()
    target = tmp_path / "durable-access"
    target.mkdir()
    monkeypatch.setattr(authority, "REPO_ROOT", checkout)
    monkeypatch.setenv(authority.DURABLE_LEDGER_ROOT_ENV, str(target.resolve(strict=True)))
    payload = {"schema": "test", "phase": "CAL"}
    authority._create_immutable_ledger_record("session.1.CAL.started.json", payload)
    with (target / "session.1.CAL.started.json").open("rb") as stream:
        raw = stream.read()
    assert raw == authority.canonical_json_bytes(payload)
    with pytest.raises(authority.AuthorityVerificationError, match="already consumed"):
        authority._create_immutable_ledger_record("session.1.CAL.started.json", payload)


def test_durable_ledger_requires_explicit_disjoint_outer_binding(monkeypatch, tmp_path: Path) -> None:
    checkout = tmp_path / "detached-checkout"
    checkout.mkdir()
    monkeypatch.setattr(authority, "REPO_ROOT", checkout)
    monkeypatch.delenv(authority.DURABLE_LEDGER_ROOT_ENV, raising=False)
    with pytest.raises(authority.AuthorityVerificationError, match="binding is required"):
        authority._ordinary_ledger_directory()
    monkeypatch.setenv(authority.DURABLE_LEDGER_ROOT_ENV, "relative-ledger")
    with pytest.raises(authority.AuthorityVerificationError, match="path refused"):
        authority._ordinary_ledger_directory()
    nested = checkout / "ledger"
    nested.mkdir()
    monkeypatch.setenv(authority.DURABLE_LEDGER_ROOT_ENV, str(nested.resolve(strict=True)))
    with pytest.raises(authority.AuthorityVerificationError, match="outside detached worktree"):
        authority._ordinary_ledger_directory()
    monkeypatch.setenv(authority.DURABLE_LEDGER_ROOT_ENV, str(tmp_path.resolve(strict=True)))
    with pytest.raises(authority.AuthorityVerificationError, match="outside detached worktree"):
        authority._ordinary_ledger_directory()


def test_precreated_local_pass_is_audit_only_and_never_phase_authority(monkeypatch, tmp_path: Path) -> None:
    checkout = tmp_path / "detached-checkout"
    checkout.mkdir()
    target = tmp_path / "durable-access"
    target.mkdir()
    monkeypatch.setattr(authority, "REPO_ROOT", checkout)
    monkeypatch.setenv(authority.DURABLE_LEDGER_ROOT_ENV, str(target.resolve(strict=True)))
    phase_raw = b"canonical CAL authority record\n"
    phase_payload = {"phase": "CAL", "sequence": 1, "session_id": "1" * 64}
    outcome = {
        "schema": "generator_tensor_response_access_outcome_v1",
        "phase": "CAL",
        "sequence": 1,
        "session_id": "1" * 64,
        "authority_record_sha256": hashlib.sha256(phase_raw).hexdigest(),
        "outcome": "CAL_PASS",
    }
    authority._create_immutable_ledger_record(
        f"1.CAL.{'1' * 64}.{'2' * 40}.outcome.json",
        outcome,
    )
    authority._verify_local_phase_outcome_audit(
        phase_payload,
        phase_raw,
        phase_commit_oid="2" * 40,
        expected_outcome="CAL_PASS",
    )
    with pytest.raises(authority.AuthorityVerificationError, match="binding refused"):
        authority._verify_local_phase_outcome_audit(
            phase_payload,
            phase_raw,
            phase_commit_oid="2" * 40,
            expected_outcome="CAL_FAIL",
        )
    source_lock = _forged_internal_phase()
    forged_binding = authority._VerifiedAdapterSourceLock(
        authority_commit_oid=source_lock.adapter_source_lock_commit_oid,
        source_commit_oid=source_lock.adapter_source_commit_oid,
        source_tree_oid=source_lock.adapter_source_tree_oid,
        raw_sha256=source_lock.adapter_source_lock_sha256,
        plan_sha256=source_lock.plan_sha256,
        seal=authority._VERIFIED_SEAL,
    )
    with pytest.raises(authority.AuthorityVerificationError):
        authority._validated_phase_record("2" * 40, phase="V", source_lock=forged_binding)
    assert "_verify_local_phase_outcome_audit" not in inspect.getsource(authority._validated_phase_record)


def test_two_detached_checkouts_share_one_durable_single_use_store(monkeypatch, tmp_path: Path) -> None:
    first_checkout = tmp_path / "checkout-one"
    second_checkout = tmp_path / "checkout-two"
    durable = tmp_path / "outer-durable-ledger"
    for path in (first_checkout, second_checkout, durable):
        path.mkdir()
    authorization = _forged_internal_phase()
    monkeypatch.setattr(authority, "reverify_phase_authorization", lambda observed: observed)
    monkeypatch.setenv(authority.DURABLE_LEDGER_ROOT_ENV, str(durable.resolve(strict=True)))

    monkeypatch.setattr(authority, "REPO_ROOT", first_checkout)
    authority.consume_phase_authorization(authorization)
    marker = durable / authority._ledger_record_name(authorization, "started")
    assert marker.is_file()

    monkeypatch.setattr(authority, "REPO_ROOT", second_checkout)
    with pytest.raises(authority.AuthorityVerificationError, match="already consumed"):
        authority.consume_phase_authorization(authorization)
    assert _producer_modules() == ()


def test_synthetic_git_requires_durable_committed_v_state_and_reaches_h(
    monkeypatch,
    tmp_path: Path,
) -> None:
    original_repo = authority.REPO_ROOT.resolve(strict=True)
    repo = tmp_path / "synthetic-authority"
    repo.mkdir()
    _synthetic_git(repo, "init", "-q")
    _synthetic_git(repo, "commit", "--allow-empty", "-m", "reviewed parent")
    source_parent_oid = _synthetic_git(repo, "rev-parse", "HEAD").decode("ascii").strip()

    source_raw: dict[str, bytes] = {}
    for relative in authority.REVIEWED_SOURCE_PATHS:
        raw = original_repo.joinpath(*relative.split("/")).read_bytes()
        destination = repo.joinpath(*relative.split("/"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        source_raw[relative] = raw
    _synthetic_git(repo, "add", "--", *authority.REVIEWED_SOURCE_PATHS)
    _synthetic_git(repo, "commit", "-m", "reviewed adapter source")
    source_oid = _synthetic_git(repo, "rev-parse", "HEAD").decode("ascii").strip()
    source_tree = _synthetic_git(repo, "rev-parse", f"{source_oid}^{{tree}}").decode("ascii").strip()

    entries: list[dict[str, object]] = []
    for relative in authority.REVIEWED_SOURCE_PATHS:
        record = _synthetic_git(repo, "ls-tree", source_oid, "--", relative).decode("utf-8").strip()
        metadata, found = record.split("\t", 1)
        mode, kind, blob_oid = metadata.split(" ")
        assert (mode, kind, found) == ("100644", "blob", relative)
        raw = source_raw[relative]
        assert _synthetic_git(repo, "cat-file", "blob", blob_oid) == raw
        entries.append(
            {
                "path": relative,
                "mode": mode,
                "blob_oid": blob_oid,
                "size": len(raw),
                "sha256_raw": hashlib.sha256(raw).hexdigest(),
            }
        )
    lock_payload: dict[str, object] = {
        "schema": authority.SOURCE_LOCK_SCHEMA,
        "source_commit_oid": source_oid,
        "source_tree_oid": source_tree,
        "source_parent_oid": source_parent_oid,
        "git_object_format": "sha1",
        "entries": entries,
        "path_set_sha256": canonical_sha256(authority.REVIEWED_SOURCE_PATHS),
        "entries_sha256": canonical_sha256(tuple(entries)),
        "source_bundle_sha256": "",
    }
    lock_payload["source_bundle_sha256"] = authority._source_bundle_sha256(lock_payload)
    lock_raw = canonical_json_bytes(lock_payload)
    lock_path = repo.joinpath(*authority.ADAPTER_SOURCE_LOCK_RELATIVE.split("/"))
    lock_path.write_bytes(lock_raw)
    _synthetic_git(repo, "add", "--", authority.ADAPTER_SOURCE_LOCK_RELATIVE)
    _synthetic_git(repo, "commit", "-m", "bind reviewed adapter source")
    lock_oid = _synthetic_git(repo, "rev-parse", "HEAD").decode("ascii").strip()

    git_executable = shutil.which("git")
    assert git_executable is not None
    monkeypatch.setattr(authority, "REPO_ROOT", repo)
    monkeypatch.setattr(authority, "SIM_ROOT", repo / "cwt-sim")
    monkeypatch.setattr(authority, "ADAPTER_SOURCE_LOCK_PATH", lock_path)
    monkeypatch.setenv(authority.GIT_DIR_ENV, str((repo / ".git").resolve(strict=True)))
    monkeypatch.setenv(authority.GIT_INDEX_ENV, str((repo / ".git/index").resolve(strict=True)))
    monkeypatch.setenv(authority.GIT_WORK_TREE_ENV, str(repo.resolve(strict=True)))
    monkeypatch.setenv(
        authority.GIT_EXECUTABLE_ENV,
        str(Path(git_executable).resolve(strict=True)),
    )
    source_lock = authority.verify_adapter_source_lock(
        lock_oid,
        plan_sha256=geometry_plan().plan_sha256,
    )

    plan = geometry_plan()
    fit = fit_exact(plan, _exact_observations((Fraction(1), Fraction(2), Fraction(3))))
    predictions = commit_predictions(plan, fit)
    prediction = json.loads(canonical_json_bytes(prediction_record(predictions)))
    prediction_sha256 = predictions.prediction_sha256
    session_id = "1" * 64

    def phase_record(
        phase: str,
        parent_oid: str,
        prior_record_sha256: str,
        prior_state: str,
    ) -> bytes:
        return canonical_json_bytes(
            {
                "schema": authority.PHASE_RECORD_SCHEMA,
                "phase": phase,
                "sequence": {"CAL": 1, "V": 2, "H": 3}[phase],
                "decision": "ALLOW_EXACT_ONE_SHOT",
                "session_id": session_id,
                "adapter_source_lock_commit_oid": lock_oid,
                "adapter_source_lock_sha256": hashlib.sha256(lock_raw).hexdigest(),
                "adapter_source_commit_oid": source_oid,
                "adapter_source_tree_oid": source_tree,
                "plan_sha256": plan.plan_sha256,
                "contract_sha256": contract_module.CONTRACT_SHA256,
                "prior_authority_commit_oid": parent_oid,
                "prior_record_sha256": prior_record_sha256,
                "prior_state": prior_state,
                "prediction_sha256": None if phase == "CAL" else prediction_sha256,
                "prediction_record": None if phase == "CAL" else prediction,
                "request_ids": authority.phase_request_ids(phase),
            }
        )

    def result_record(phase: str, authority_oid: str, phase_raw: bytes) -> bytes:
        return canonical_json_bytes(
            {
                "schema": "generator_tensor_response_phase_result_v1",
                "phase": phase,
                "sequence": {"CAL": 1, "V": 2, "H": 3}[phase],
                "session_id": session_id,
                "authority_commit_oid": authority_oid,
                "authority_record_sha256": hashlib.sha256(phase_raw).hexdigest(),
                "request_ids": authority.phase_request_ids(phase),
                "sample_call_count": {"CAL": 12, "V": 4, "H": 2}[phase],
                "normalized_excess_vectors": {
                    "CAL": fit.observed_deltas,
                    "V": predictions.confirmation_vectors,
                    "H": (),
                }[phase],
                "heldout_scalar_projection": (
                    predictions.heldout_scalar_projection if phase == "H" else None
                ),
                "direct_fcs_crosscheck_complete": True,
            }
        )

    def outcome_record(
        phase: str,
        authority_oid: str,
        phase_raw: bytes,
        result_raw: bytes,
    ) -> bytes:
        return canonical_json_bytes(
            {
                "schema": "generator_tensor_response_external_outcome_v1",
                "phase": phase,
                "sequence": {"CAL": 1, "V": 2, "H": 3}[phase],
                "session_id": session_id,
                "phase_authority_commit_oid": authority_oid,
                "phase_authority_record_sha256": hashlib.sha256(phase_raw).hexdigest(),
                "response_result_sha256": hashlib.sha256(result_raw).hexdigest(),
                "outcome": f"{phase}_PASS",
                "prediction_sha256": prediction_sha256,
                "prediction_record": prediction,
            }
        )

    cal_raw = phase_record("CAL", lock_oid, source_lock.raw_sha256, "ADAPTER_SOURCE_LOCKED")
    cal_oid = _synthetic_commit(
        repo,
        lock_oid,
        {authority.PHASE_RECORD_RELATIVE["CAL"]: cal_raw},
        label="cal-authority",
    )
    assert authority.verify_phase_authority_commit(cal_oid).prior_state == "ADAPTER_SOURCE_LOCKED"
    cal_result = result_record("CAL", cal_oid, cal_raw)
    cal_outcome = outcome_record("CAL", cal_oid, cal_raw, cal_result)
    cal_outcome_oid = _synthetic_commit(
        repo,
        cal_oid,
        {
            authority.PHASE_RESULT_RELATIVE["CAL"]: cal_result,
            authority.PHASE_OUTCOME_RELATIVE["CAL"]: cal_outcome,
        },
        label="cal-outcome",
    )

    prepared_v_raw = phase_record(
        "V",
        cal_outcome_oid,
        hashlib.sha256(cal_outcome).hexdigest(),
        "PREDICTIONS_PREPARED",
    )
    prepared_v_oid = _synthetic_commit(
        repo,
        cal_outcome_oid,
        {authority.PHASE_RECORD_RELATIVE["V"]: prepared_v_raw},
        label="prepared-v-authority",
    )
    with pytest.raises(authority.AuthorityVerificationError, match="lineage payload refused"):
        authority.verify_phase_authority_commit(prepared_v_oid)

    v_raw = phase_record(
        "V",
        cal_outcome_oid,
        hashlib.sha256(cal_outcome).hexdigest(),
        "PREDICTIONS_COMMITTED",
    )
    v_oid = _synthetic_commit(
        repo,
        cal_outcome_oid,
        {authority.PHASE_RECORD_RELATIVE["V"]: v_raw},
        label="v-authority",
    )
    verified_v = authority.verify_phase_authority_commit(v_oid)
    assert verified_v.phase == "V"
    assert verified_v.prior_state == "PREDICTIONS_COMMITTED"
    v_result = result_record("V", v_oid, v_raw)
    v_outcome = outcome_record("V", v_oid, v_raw, v_result)
    v_outcome_oid = _synthetic_commit(
        repo,
        v_oid,
        {
            authority.PHASE_RESULT_RELATIVE["V"]: v_result,
            authority.PHASE_OUTCOME_RELATIVE["V"]: v_outcome,
        },
        label="v-outcome",
    )

    h_raw = phase_record(
        "H",
        v_outcome_oid,
        hashlib.sha256(v_outcome).hexdigest(),
        "V_PASS",
    )
    h_oid = _synthetic_commit(
        repo,
        v_outcome_oid,
        {authority.PHASE_RECORD_RELATIVE["H"]: h_raw},
        label="h-authority",
    )
    verified_h = authority.verify_phase_authority_commit(h_oid)
    assert verified_h.phase == "H"
    assert verified_h.prior_state == "V_PASS"
    h_result = result_record("H", h_oid, h_raw)
    h_outcome = outcome_record("H", h_oid, h_raw, h_result)
    h_outcome_oid = _synthetic_commit(
        repo,
        h_oid,
        {
            authority.PHASE_RESULT_RELATIVE["H"]: h_result,
            authority.PHASE_OUTCOME_RELATIVE["H"]: h_outcome,
        },
        label="h-outcome",
    )
    _phase, _phase_raw, outcome, _outcome_raw = authority._validated_external_outcome_commit(
        h_outcome_oid,
        phase="H",
        source_lock=source_lock,
    )
    assert outcome["outcome"] == "H_PASS"
    assert _producer_modules() == ()


def test_provider_injection_and_provider_exception_leakage_are_impossible() -> None:
    class LeakingProvider:
        calls = 0

        def __call__(self, **_kwargs):
            self.calls += 1
            raise RuntimeError("SECRET_PROVIDER_OUTPUT")

    provider = LeakingProvider()
    with pytest.raises(TypeError) as caught:
        OneShotResponseBroker(producer=provider, plan_sha256=geometry_plan().plan_sha256)  # type: ignore[call-arg]
    assert "SECRET_PROVIDER_OUTPUT" not in str(caught.value)
    assert provider.calls == 0
    assert _producer_modules() == ()


@pytest.mark.parametrize(
    ("role", "source", "fragment"),
    [
        (
            "geometry",
            "from experiments.loop_flux_counting_curvature_proof.counting_lane import fcs_record",
            "producer_import_outside_lazy_broker",
        ),
        (
            "geometry",
            "from experiments import loop_flux_counting_curvature_proof as response",
            "producer_import_outside_lazy_broker",
        ),
        (
            "broker",
            "from experiments.generator_tensor_prediction_protocol."
            "connection_eligibility import connection_basis",
            "predictor_import_outside_geometry",
        ),
        (
            "broker",
            "from experiments.generator_tensor_response_protocol.geometry_plan import geometry_plan",
            "broker_imported_geometry_lane",
        ),
        ("fit", "import importlib", "forbidden_capability_import"),
        ("protocol", "value = __import__('x')", "dynamic_capability_reference"),
        (
            "geometry",
            "from pathlib import Path\nPath('response').read_bytes()",
            "path_or_io_capability",
        ),
        (
            "focused_test",
            "from experiments.loop_flux_counting_curvature_proof import counting_lane",
            "producer_import_outside_lazy_broker",
        ),
        (
            "broker",
            "class LockedProducerCallable:\n"
            " def _call_authorized(self):\n"
            "  from experiments.loop_flux_counting_curvature_proof.generator "
            "import build_branch_bundle\n",
            "producer_import_outside_lazy_broker",
        ),
    ],
)
def test_lane_firewall_rejects_cross_capabilities(role: str, source: str, fragment: str) -> None:
    assert any(fragment in issue for issue in analyze_source_text(source, role=role, relative="attack.py"))


@pytest.mark.parametrize(
    ("role", "relative", "source"),
    [
        ("geometry", "geometry_plan.py", "from pathlib import Path\nPath('x').open('rb').read()"),
        ("fit", "fit.py", "from pathlib import Path\ntuple(Path('x').iterdir())"),
        ("protocol", "protocol.py", "from pathlib import Path\nPath('x').glob('*')"),
        (
            "focused_test",
            "tests/experiments/test_generator_tensor_response_protocol.py",
            "from pathlib import Path\nPath('x').rglob('*')",
        ),
        (
            "authority",
            "authority.py",
            "from pathlib import Path, PurePosixPath\nPath('x').stat()",
        ),
        ("authority", "authority.py", "from pathlib import Path as P\nP('x').lstat()"),
        (
            "authority",
            "authority.py",
            "from pathlib import Path, PurePosixPath\ncap = Path.open",
        ),
        (
            "authority",
            "authority.py",
            "from pathlib import Path, PurePosixPath\nclass Q(Path): pass\nQ('x').walk()",
        ),
        (
            "anchor",
            "anchors.py",
            "from experiments.generator_tensor_response_protocol.firewall import Path\n"
            "Path('x').resolve()",
        ),
        ("geometry", "geometry_plan.py", "import io\nio.open('x', 'rb').read()"),
    ],
)
def test_closed_path_and_io_firewall_refuses_alias_higher_order_and_reexports(
    role: str, relative: str, source: str
) -> None:
    issues = analyze_source_text(source, role=role, relative=relative)
    assert any(
        fragment in issue
        for issue in issues
        for fragment in (
            "path_or_io_capability",
            "path_constructor_capability",
            "path_constructor_reexport",
            "unreviewed_pathlib_import",
            "forbidden_capability_import",
        )
    )


@pytest.mark.parametrize(
    ("role", "relative", "source"),
    [
        ("authority", "authority.py", "import os\nos.system('forged')"),
        ("authority", "authority.py", "import subprocess\nsubprocess.run(('forged',))"),
        ("authority", "authority.py", "import os as harmless\nharmless.getcwd()"),
        ("composition", "run.py", "import sys\npayload=sys.path"),
        ("anchor", "anchors.py", "import builtins\ncapability=builtins.open"),
        ("anchor", "anchors.py", "import inspect\ncapability=inspect.getmembers"),
    ],
)
def test_controlled_modules_require_exact_import_and_statement_identity(
    role: str,
    relative: str,
    source: str,
) -> None:
    issues = analyze_source_text(source, role=role, relative=relative)
    assert any(
        issue.startswith("forbidden_capability_import:") or issue.startswith("controlled_module_capability:")
        for issue in issues
    )


@pytest.mark.parametrize(
    ("role", "relative", "source"),
    [
        ("authority", "authority.py", "import shutil\nshutil.copyfile('a', 'b')"),
        ("fit", "fit.py", "import sqlite3\nsqlite3.connect('response.db').execute('select 1')"),
        ("fit", "fit.py", "import numpy\nvalue=numpy.load('response.npy')"),
        ("fit", "fit.py", "import pandas\nvalue=pandas.read_csv('response.csv')"),
        ("protocol", "protocol.py", "import requests\nvalue=requests.get('https://x').content"),
        (
            "protocol",
            "protocol.py",
            "from zipfile import ZipFile\nZipFile('response.zip').extractall('out')",
        ),
        ("protocol", "protocol.py", "import pty\npty.spawn('response-reader')"),
        (
            "fit",
            "fit.py",
            "loader=__builtins__['__im'+'port__']\n"
            "mod=loader('experiments.loop_flux_'+'counting_curvature_proof.counting_lane',"
            "fromlist=('*',))\npayload=mod.counted_q_jet",
        ),
    ],
)
def test_closed_structural_inventory_rejects_unknown_modules_calls_and_attributes(
    role: str,
    relative: str,
    source: str,
) -> None:
    assert f"unreviewed_source_structure:{relative}" in analyze_source_text(
        source,
        role=role,
        relative=relative,
    )


@pytest.mark.parametrize(
    "expression",
    [
        "Path('x').open('rb')",
        "Path('x').iterdir()",
        "Path('x').glob('*')",
        "Path('x').rglob('*')",
        "Path('x').stat()",
        "Path('x').lstat()",
        "Path('x').scandir()",
        "Path('x').walk()",
        "Path('x').resolve()",
        "Path.home()",
        "Path.cwd()",
        "Path('x').parser.os.listdir('.')",
        "Path('x').rename('y')",
    ],
)
def test_authority_path_receiver_surface_is_closed(expression: str) -> None:
    source = f"from pathlib import Path, PurePosixPath\nvalue = {expression}"
    issues = analyze_source_text(source, role="authority", relative="authority.py")
    assert any("path_or_io_capability" in issue for issue in issues)


def test_live_firewall_material_inventory_and_no_output_paths() -> None:
    record = source_firewall_record()
    assert record["expected_package_files"] == EXPECTED_PACKAGE_FILES
    assert record["unexpected_package_entries"] == ()
    assert record["missing_package_entries"] == ()
    assert record["protected_role_firewalls_clean"] is True
    assert record["source_structure_authority"].startswith("defense_in_depth_only")
    assert len([item for item in record["file_records"] if item["source_structure_sha256"] is not None]) == 13
    assert len(record["file_records"]) == len(authority.REVIEWED_SOURCE_PATHS)
    package = authority.SIM_ROOT / "experiments/generator_tensor_response_protocol"
    assert not (package / "SOURCE_LOCK.json").exists()
    assert not authority.ADAPTER_SOURCE_LOCK_PATH.exists()
    assert not (package / "artifacts").exists()
    assert not authority.ACCESS_LEDGER_DIR.exists()
    for relative in (
        *authority.PHASE_RECORD_RELATIVE.values(),
        *authority.PHASE_OUTCOME_RELATIVE.values(),
        *authority.PHASE_RESULT_RELATIVE.values(),
    ):
        assert not authority.REPO_ROOT.joinpath(*relative.split("/")).exists()


def test_closed_structure_inventory_is_python_minor_neutral() -> None:
    python313 = Path(r"C:\Python313\python.exe")
    if not python313.is_file():
        pytest.skip("Python 3.13 runtime unavailable")
    script = (
        "import json,sys;"
        f"sys.path.insert(0,{str(authority.SIM_ROOT.resolve(strict=True))!r});"
        "from experiments.generator_tensor_response_protocol.firewall import source_firewall_record;"
        "r=source_firewall_record();"
        "print(json.dumps({'clean':r['protected_role_firewalls_clean'],"
        "'aggregate':r['source_structure_aggregate_sha256']},sort_keys=True))"
    )
    environment = dict(os.environ)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        [str(python313), "-I", "-B", "-c", script],
        cwd=authority.REPO_ROOT,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    observed = json.loads(result.stdout)
    local = source_firewall_record()
    assert observed == {
        "aggregate": local["source_structure_aggregate_sha256"],
        "clean": True,
    }


def test_theorem_is_preaccess_only_and_all_gates_pass() -> None:
    assert _producer_modules() == ()
    summary, records = execute_program()
    assert summary["disposition"] == "PASS_INTERNAL_ANALYTIC"
    assert summary["passed_gate_count"] == len(ORDERED_GATES)
    assert summary["failed_gates"] == ()
    assert summary["response_accessed"] is False
    assert summary["adapter_source_lock_present"] is False
    assert summary["artifacts_present"] is False
    assert summary["access_ledger_present"] is False
    assert summary["protocol_state"] == "PREDICTOR_LOCKED"
    assert summary["authoritative_response_entrypoint"] == (
        "outer_trusted_detached_launcher_to_fresh_isolated_whole_phase_child_only"
    )
    assert summary["local_ledger_grants_phase_authority"] is False
    assert summary["next_phase_requires_committed_external_outcome"] is True
    assert records["preaccess_state"]["response_stream"] == ()
    assert records["preaccess_state"]["output_stream"] == ()
    assert records["preaccess_state"]["inprocess_response_api_authoritative"] is False
    assert records["preaccess_state"]["outer_trusted_orchestrator_is_sole_access_authority"] is True
    assert records["preaccess_state"]["child_argv_and_globals_are_defense_in_depth"] is True
    assert records["preaccess_state"]["external_outcome_delta_path_count"] == 2
    assert _producer_modules() == ()


def test_cli_source_commands_pass_and_access_commands_refuse_without_import() -> None:
    runner = CliRunner()
    source = runner.invoke(app, ["verify-source"])
    assert source.exit_code == 0
    assert "PASS 12/12 response_accessed=false adapter_source_lock_present=false" in source.stdout
    for command in ("calibrate", "confirm", "heldout"):
        result = runner.invoke(app, [command])
        assert result.exit_code == 1
        assert ACCESS_REFUSAL in result.stderr
    assert _producer_modules() == ()


def test_cli_whole_phase_child_refuses_outside_fresh_isolated_authority() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["phase-child", "1" * 40])
    assert result.exit_code == 1
    assert "REFUSED: authoritative whole-phase execution failed closed" in result.stderr
    assert not authority.ACCESS_LEDGER_DIR.exists()
    assert _producer_modules() == ()


@pytest.mark.parametrize(
    ("contaminate_pythonpath", "omit_git_binding"),
    [(False, False), (True, False), (False, True)],
)
def test_external_fresh_child_refuses_prelock_contamination_and_unbound_checkout(
    tmp_path: Path,
    contaminate_pythonpath: bool,
    omit_git_binding: bool,
) -> None:
    result = _fresh_detached_child(
        tmp_path,
        contaminate_pythonpath=contaminate_pythonpath,
        omit_git_binding=omit_git_binding,
    )
    assert result.returncode == 1
    assert "REFUSED: authoritative whole-phase execution failed closed" in result.stderr
    assert "Traceback" not in result.stderr
    assert _producer_modules() == ()


def test_external_fresh_child_refuses_stale_same_size_mtime_pyc_before_access(tmp_path: Path) -> None:
    result = _fresh_detached_child(tmp_path, stale_pyc=True)
    assert result.returncode == 1
    assert "REFUSED: authoritative whole-phase execution failed closed" in result.stderr
    assert not authority.ACCESS_LEDGER_DIR.exists()
    assert _producer_modules() == ()


def test_digest_and_schema_mutations_are_type_sensitive() -> None:
    assert canonical_sha256((True,)) != canonical_sha256((1,))
    assert canonical_sha256((Fraction(1),)) != canonical_sha256((1,))
    assert not contract_issues()

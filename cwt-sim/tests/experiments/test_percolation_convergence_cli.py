"""Serial frozen study execution, child confinement, and retained failures."""

import hashlib
import json
from itertools import product

import pytest
from typer.testing import CliRunner

from experiments.percolation_finite_size import convergence_run, run
from experiments.percolation_finite_size.model import stable_seed, wilson95


@pytest.fixture
def invoke(tmp_path, monkeypatch):
    monkeypatch.setattr(convergence_run, "ARTIFACT_ROOT", tmp_path / "artifacts")
    return lambda name: CliRunner().invoke(convergence_run.app, ["--run-name", name])


def child_records(parameters):
    trials = parameters["samples"]
    records = []
    for d in map(int, parameters["dimensions"].split(",")):
        for radius in map(int, parameters["radii"].split(",")):
            for p in map(float, parameters[f"probabilities_{d}d"].split(",")):
                records.append(
                    dict(
                        dimension=d,
                        radius=radius,
                        p=p,
                        trials=trials,
                        boundary_hits=1,
                        rate=1 / trials,
                        ci95=list(wilson95(1, trials)),
                        histogram=[trials - 1] + [0] * (radius - 1) + [1],
                        measurement_seed=stable_seed(parameters["seed"], d, radius, p, "measurement"),
                        geometry=[
                            dict(
                                batch=b,
                                seed=stable_seed(parameters["seed"], d, radius, p, "geometry", b),
                                requested_trials=parameters["geometry_samples"],
                                trials=parameters["geometry_samples"],
                                excluded_reason=None,
                                g_uu=1.0,
                                g_uv=0.0,
                                g_vv=1.0,
                            )
                            for b in range(parameters["batches"])
                        ],
                    )
                )
    return records


def save_child(parameters):
    output = run.ARTIFACT_ROOT / parameters["run_name"]
    output.mkdir(parents=True)
    (output / "records.json").write_text(json.dumps(child_records(parameters)))
    (output / "STATUS.json").write_text('{"state":"complete"}')


def test_frozen_protocol_precedes_four_explicit_calls_and_deduplicated_results(invoke, monkeypatch):
    original_root = run.ARTIFACT_ROOT
    profile_source = convergence_run.PROFILE_PATH.read_bytes()
    profile = json.loads(profile_source)
    calls = []

    def child(**parameters):
        output = convergence_run.ARTIFACT_ROOT / "frozen"
        assert (output / "profile.json").read_bytes() == profile_source
        for stem in ["profile", "protocol"]:
            assert (output / f"{stem}.sha256").read_text().strip() == hashlib.sha256(
                (output / f"{stem}.json").read_bytes()
            ).hexdigest()
        assert run.ARTIFACT_ROOT == output / "children"
        calls.append(parameters)
        save_child(parameters)

    monkeypatch.setattr(run, "main", child)
    result = invoke("frozen")

    assert result.exit_code == 0, result.exception
    assert run.ARTIFACT_ROOT == original_root
    assert [(p["geometry_samples"], p["step"]) for p in calls] == list(product([512, 2048], [0.01, 0.02]))
    for parameters in calls:
        assert parameters["samples"] == 2048 and parameters["batches"] == 5
        assert parameters["seed"] == 20261002 and parameters["min_overlap"] == 0.9
        assert parameters["dimensions"] == "2,3" and parameters["radii"] == "2,4,6,8"
        for d in [2, 3]:
            assert (
                list(map(float, parameters[f"probabilities_{d}d"].split(",")))
                == profile[f"probabilities_{d}d"]
            )
    output = convergence_run.ARTIFACT_ROOT / "frozen"
    summaries = json.loads((output / "aggregate.json").read_text())
    assert len(summaries) == 24 and all(row["measurement_duplicates_verified"] == 4 for row in summaries)
    assert all(row["measurement"]["trials"] == 2048 for row in summaries)
    assert json.loads((output / "STATUS.json").read_text())["state"] == "complete"
    assert "never pool" in (output / "REPORT.md").read_text()
    before = {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}
    assert invoke("frozen").exit_code != 0
    assert before == {p.name: p.read_bytes() for p in output.iterdir() if p.is_file()}


@pytest.mark.parametrize("failure", ["child", "aggregate"])
def test_failed_child_or_aggregation_retains_partial_records_and_status(invoke, monkeypatch, failure):
    calls = []
    original_root = run.ARTIFACT_ROOT

    def child(**parameters):
        save_child(parameters)
        calls.append(parameters)
        output = run.ARTIFACT_ROOT / parameters["run_name"]
        if failure == "child" and len(calls) == 2:
            (output / "STATUS.json").write_text('{"state":"incomplete"}')
            raise RuntimeError("injected child failure")
        if failure == "aggregate":
            records = child_records(parameters)
            records[0].pop("ci95")
            (output / "records.json").write_text(json.dumps(records))

    monkeypatch.setattr(run, "main", child)
    result = invoke("failed")

    assert result.exit_code != 0 and run.ARTIFACT_ROOT == original_root
    output = convergence_run.ARTIFACT_ROOT / "failed"
    status = json.loads((output / "STATUS.json").read_text())
    assert status["state"] == "incomplete" and status["error"]
    assert len(list((output / "children").glob("*/records.json"))) == (2 if failure == "child" else 4)
    assert "incomplete" in (output / "REPORT.md").read_text()
    assert not (output / "aggregate.json").exists()


@pytest.mark.parametrize("name", ["../escape", "/tmp/escape", "a/b", "."])
def test_invalid_names_do_not_create_artifacts(invoke, name):
    assert invoke(name).exit_code != 0
    assert not convergence_run.ARTIFACT_ROOT.exists()


def test_symlink_root_and_profile_hash_mismatch_are_refused(invoke, tmp_path, monkeypatch):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    convergence_run.ARTIFACT_ROOT.symlink_to(elsewhere, target_is_directory=True)
    assert invoke("escape").exit_code != 0 and list(elsewhere.iterdir()) == []
    convergence_run.ARTIFACT_ROOT.unlink()
    monkeypatch.setattr(convergence_run, "FROZEN_SHA256", "0" * 64)
    assert invoke("mismatch").exit_code != 0 and not convergence_run.ARTIFACT_ROOT.exists()


def test_tiny_fixture_profile_runs_real_children(invoke, tmp_path, monkeypatch):
    profile = json.loads(convergence_run.PROFILE_PATH.read_text())
    profile.update(
        dimensions=[2],
        radii=[1],
        probabilities_2d=[0.4],
        measurement_trials=4,
        geometry_trials=[2, 4],
        geometry_batches=2,
        required_joint_batches=2,
    )
    source = json.dumps(profile).encode()
    path = tmp_path / "test-only-profile.json"
    path.write_bytes(source)
    monkeypatch.setattr(convergence_run, "PROFILE_PATH", path)
    monkeypatch.setattr(convergence_run, "FROZEN_SHA256", hashlib.sha256(source).hexdigest())

    result = invoke("tiny")

    assert result.exit_code == 0, result.exception
    output = convergence_run.ARTIFACT_ROOT / "tiny"
    summary = json.loads((output / "aggregate.json").read_text())[0]
    assert summary["measurement"]["trials"] == 4 and len(summary["levels"]) == 4
    assert len(list((output / "children").glob("*/REPORT.md"))) == 4


def test_cli_help_has_only_study_name_control():
    result = CliRunner().invoke(convergence_run.app, ["--help"])
    assert result.exit_code == 0 and "--run-name" in result.output
    assert "--samples" not in result.output and "--profile" not in result.output

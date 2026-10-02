"""CLI reproducibility, frozen protocol, failure records, and output confinement."""

import hashlib
import json

import pytest
from typer.testing import CliRunner

from experiments.percolation_finite_size import run


@pytest.fixture
def invoke(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ARTIFACT_ROOT", tmp_path / "artifacts")
    return lambda *args: CliRunner().invoke(run.app, list(args))


def test_help_exposes_sampling_and_geometry_parameters(invoke):
    result = invoke("--help")

    assert result.exit_code == 0
    assert "--geometry-samples" in result.output and "--probabilities-3d" in result.output


@pytest.mark.parametrize(
    "options",
    [
        ["--run-name", "../escape"],
        ["--run-name", "/tmp/x"],
        ["--run-name", "valid", "--dimensions", "4"],
        ["--run-name", "valid", "--radii", "0"],
        ["--run-name", "valid", "--samples", "0"],
        ["--run-name", "valid", "--probabilities-2d", "nan"],
    ],
)
def test_invalid_parameters_create_no_artifacts(invoke, options):
    result = invoke(*options)

    assert result.exit_code != 0
    assert not run.ARTIFACT_ROOT.exists()


def test_small_run_freezes_protocol_retains_batches_and_replays_order(invoke):
    common = (
        "--radii 1 --samples 8 --geometry-samples 8 --batches 2 "
        "--probabilities-2d 0.4 --probabilities-3d 0.2"
    ).split()

    first = invoke("--run-name", "first", "--dimensions", "3,2,2", *common)
    second = invoke("--run-name", "second", "--dimensions", "2,3", *common)

    assert first.exit_code == second.exit_code == 0, first.output
    out = run.ARTIFACT_ROOT / "first"
    protocol = (out / "protocol.json").read_bytes()
    assert (out / "protocol.sha256").read_text().strip() == hashlib.sha256(protocol).hexdigest()
    records = json.loads((out / "records.json").read_text())
    assert records == json.loads((run.ARTIFACT_ROOT / "second" / "records.json").read_text())
    assert len(records) == 2 and records[0]["trials"] == 8
    assert len(records[0]["geometry"]) == 2 and sum(records[0]["histogram"]) == 8
    assert records[0]["measurement_seed"] != records[0]["geometry"][0]["seed"]
    for path in out.glob("*.json"):
        json.loads(path.read_text(), parse_constant=lambda value: pytest.fail(f"Nonfinite JSON: {value}"))
    assert "Finite reference diagnostic" in (out / "REPORT.md").read_text()
    assert json.loads((out / "STATUS.json").read_text())["state"] == "complete"
    assert invoke("--run-name", "first", *common).exit_code != 0


def test_symlink_artifact_root_is_refused(invoke, tmp_path):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    run.ARTIFACT_ROOT.symlink_to(elsewhere, target_is_directory=True)

    result = invoke("--run-name", "escape")

    assert result.exit_code != 0 and list(elsewhere.iterdir()) == []


def test_sampling_failure_preserves_frozen_incomplete_run(invoke, monkeypatch):
    def fail(*args, **kwargs):
        assert (run.ARTIFACT_ROOT / "failed" / "protocol.sha256").exists()
        raise RuntimeError("synthetic sampling failure")

    monkeypatch.setattr(run.model, "sample_shells", fail)

    result = invoke("--run-name", "failed", "--dimensions", "2", "--radii", "1", "--samples", "1")

    assert result.exit_code != 0
    status = json.loads((run.ARTIFACT_ROOT / "failed" / "STATUS.json").read_text())
    assert status["state"] == "incomplete" and "synthetic sampling failure" in status["error"]

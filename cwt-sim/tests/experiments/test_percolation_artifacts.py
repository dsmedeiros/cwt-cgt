"""Report, provenance, uncertainty figure, and failure-status artifact checks."""

import hashlib
import json
import struct

import pytest
from typer.testing import CliRunner

from experiments.percolation_finite_size import run


@pytest.fixture
def invoke(tmp_path, monkeypatch):
    monkeypatch.setattr(run, "ARTIFACT_ROOT", tmp_path / "artifacts")
    options = (
        "--radii 1 --samples 8 --geometry-samples 8 --batches 2 --probabilities-2d .4 --probabilities-3d .2"
    )
    return lambda name, *args: CliRunner().invoke(run.app, ["--run-name", name, *options.split(), *args])


def test_completed_artifacts_have_source_provenance_and_status_linked_hashes(invoke):
    result = invoke("complete")
    output = run.ARTIFACT_ROOT / "complete"

    assert result.exit_code == 0, result.output
    assert (output / "provenance.json").is_file(), "Source/runtime provenance must be archived"
    provenance = json.loads((output / "provenance.json").read_text())
    assert len(provenance["git_commit"]) == 40 and isinstance(provenance["git_dirty"], bool)
    assert json.loads((output / "protocol.json").read_text())["references"]["3D_p_c"] == 0.2488
    assert {"numpy", "typer", "matplotlib"} <= provenance["packages"].keys()
    for source, digest in provenance["source_sha256"].items():
        assert hashlib.sha256((run.artifacts.REPO_ROOT / source).read_bytes()).hexdigest() == digest
    manifest = json.loads((output / "CHECKSUMS.json").read_text())
    assert manifest["state"] == "complete"
    actual = {str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()}
    assert set(manifest["files"]) == actual - {"CHECKSUMS.json"}
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest


def test_report_discloses_scope_uncertainty_controls_and_renders_two_panel_png(invoke):
    assert invoke("report").exit_code == 0
    output = run.ARTIFACT_ROOT / "report"
    report = (output / "REPORT.md").read_text()

    for text in [
        "θ(p_c)=0",
        "3–10",
        "pointwise",
        "zero_bin",
        "P(R=r)",
        "16 configurations",
        "independent human review",
        "provenance.json",
        "connectivity.png",
        "Accepted batches",
    ]:
        assert text in report
    png = (output / "connectivity.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    width, height = struct.unpack(">II", png[16:24])
    assert width > 1.5 * height and height >= 400


def test_real_cli_endpoint_rates_plot_with_exact_containing_intervals(invoke):
    result = invoke(
        "endpoints",
        "--dimensions",
        "2",
        "--probabilities-2d",
        "0,1",
        "--samples",
        "3",
        "--geometry-samples",
        "1",
        "--batches",
        "1",
    )
    output = run.ARTIFACT_ROOT / "endpoints"

    assert result.exit_code == 0, str(result.exception)
    records = json.loads((output / "records.json").read_text())
    assert [row["rate"] for row in records] == [0.0, 1.0]
    for row in records:
        assert row["ci95"][0] <= row["rate"] <= row["ci95"][1]
    assert (output / "connectivity.png").is_file()
    assert json.loads((output / "CHECKSUMS.json").read_text())["state"] == "complete"


@pytest.mark.parametrize("operation", ["plot_connectivity", "write_report"])
def test_plot_or_full_report_failure_preserves_raw_records_and_incomplete_manifest(
    invoke, monkeypatch, operation
):
    def fail(*args, **kwargs):
        raise RuntimeError(f"synthetic {operation} failure")

    monkeypatch.setattr(run.artifacts, operation, fail)

    result = invoke("failed")
    output = run.ARTIFACT_ROOT / "failed"

    assert result.exit_code != 0
    assert len(json.loads((output / "records.json").read_text())) == 2
    assert json.loads((output / "STATUS.json").read_text())["state"] == "incomplete"
    assert json.loads((output / "CHECKSUMS.json").read_text())["state"] == "incomplete"
    assert "Run status: incomplete" in (output / "REPORT.md").read_text()

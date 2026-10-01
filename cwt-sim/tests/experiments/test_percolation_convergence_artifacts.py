"""Complete study disclosure, descriptive figure, timing, hashes, and retained failures."""

import hashlib
import json
import struct
from itertools import product

import pytest
from typer.testing import CliRunner

from experiments.percolation_finite_size import convergence_artifacts as study_artifacts, convergence_run
from experiments.percolation_finite_size.model import wilson95


@pytest.fixture
def tiny(tmp_path, monkeypatch):
    profile = json.loads(convergence_run.PROFILE_PATH.read_text())
    profile.update(
        dimensions=[2, 3],
        radii=[1],
        probabilities_2d=[0.4],
        probabilities_3d=[0.2],
        measurement_trials=4,
        geometry_trials=[2, 4],
        geometry_batches=2,
        required_joint_batches=2,
    )
    source = json.dumps(profile).encode()
    path = tmp_path / "fixture-profile.json"
    path.write_bytes(source)
    monkeypatch.setattr(convergence_run, "PROFILE_PATH", path)
    monkeypatch.setattr(convergence_run, "FROZEN_SHA256", hashlib.sha256(source).hexdigest())
    monkeypatch.setattr(convergence_run, "ARTIFACT_ROOT", tmp_path / "artifacts")
    return lambda name: CliRunner().invoke(convergence_run.app, ["--run-name", name])


def test_actual_tiny_artifacts_archive_prechild_provenance_times_and_recursive_hashes(tiny, monkeypatch):
    original = convergence_run._child

    def child(output, plan, profile):
        assert (output / "provenance.json").is_file()
        provenance = json.loads((output / "provenance.json").read_text())
        assert provenance["profile_sha256"] == (output / "profile.sha256").read_text().strip()
        assert provenance["protocol_sha256"] == (output / "protocol.sha256").read_text().strip()
        original(output, plan, profile)

    monkeypatch.setattr(convergence_run, "_child", child)
    result = tiny("complete")
    output = convergence_run.ARTIFACT_ROOT / "complete"

    assert result.exit_code == 0, result.exception
    provenance = json.loads((output / "provenance.json").read_text())
    assert len(provenance["git_commit"]) == 40 and "numpy" in provenance["packages"]
    assert any(name.endswith("convergence-profile.json") for name in provenance["source_sha256"])
    for name, digest in provenance["source_sha256"].items():
        assert hashlib.sha256((study_artifacts.artifacts.REPO_ROOT / name).read_bytes()).hexdigest() == digest
    status = json.loads((output / "STATUS.json").read_text())
    assert status["elapsed_seconds"] >= sum(child["elapsed_seconds"] for child in status["children"]) > 0
    manifest = json.loads((output / "CHECKSUMS.json").read_text())
    actual = {str(path.relative_to(output)) for path in output.rglob("*") if path.is_file()}
    assert set(manifest["files"]) == actual - {"CHECKSUMS.json"}
    assert len([name for name in manifest["files"] if name.endswith("/CHECKSUMS.json")]) == 4
    for name, digest in manifest["files"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
    png = (output / "tensor_variation.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and min(struct.unpack(">II", png[16:24])) >= 800
    report = (output / "REPORT.md").read_text()
    for text in [
        "different finite observables",
        "Ω=0",
        "undamaged",
        "≈0.2488",
        "no CWT validation",
        "pointwise",
        "operational",
        "profile.json",
        "STATUS.json",
        "source dirty",
        "uniform array",
    ]:
        assert text in report


def test_all_24_cases_and_partial_support_are_reported_and_plotted(tmp_path, monkeypatch):
    profile = json.loads(convergence_run.PROFILE_PATH.read_text())
    rows = []
    for d, radius in product([2, 3], profile["radii"]):
        for p in profile[f"probabilities_{d}d"]:
            values = [0.1, 0.2, 0.3, None, None]
            rows.append(
                dict(
                    dimension=d,
                    radius=radius,
                    p=p,
                    fine_accepted=3,
                    status="indeterminate",
                    measurement=dict(boundary_hits=512, trials=2048, rate=0.25, ci95=wilson95(512, 2048)),
                    comparisons={
                        name: dict(changes=values, defined_pairs=3, joint_accepted=3, median=0.2, maximum=0.3)
                        for name in ["N_at_fine_h", "h_at_fine_N"]
                    },
                    levels=[
                        dict(
                            geometry_trials=n,
                            step=h,
                            exclusion_counts={"zero_bin": 2},
                            geometry=[dict(excluded_reason="zero_bin")] * 2
                            + [dict(excluded_reason=None, omega=0)] * 3,
                        )
                        for n, h in product([512, 2048], [0.01, 0.02])
                    ],
                )
            )
    rows[0]["comparisons"]["N_at_fine_h"].update(
        changes=[None] * 5, defined_pairs=0, joint_accepted=0, median=None, maximum=None
    )
    status = dict(state="complete", error=None, children=[], elapsed_seconds=1)
    (tmp_path / "profile.sha256").write_text(convergence_run.FROZEN_SHA256)
    (tmp_path / "protocol.sha256").write_text("fixture")
    study_artifacts.write_report(tmp_path, profile, rows, status, study_artifacts.capture_provenance())
    report = (tmp_path / "REPORT.md").read_text()
    assert "24/24" in report and report.count("| indeterminate |") == 24
    assert "227 MB" in report
    assert "3/5" in report and "zero_bin" in report and "0.1–0.3" in report
    from matplotlib.figure import Figure

    original = Figure.savefig
    figures = []

    def save(figure, *args, **kwargs):
        figures.append(figure)
        original(figure, *args, **kwargs)

    monkeypatch.setattr(Figure, "savefig", save)
    study_artifacts.plot_variation(tmp_path, rows, profile)
    assert len(figures[0].axes) == 4
    assert all(any(text.get_text() == "3/5" for text in axis.texts) for axis in figures[0].axes)
    assert any(text.get_text() == "0/5" for text in figures[0].axes[0].texts)


@pytest.mark.parametrize("operation", ["plot_variation", "write_report", "write_checksums"])
def test_artifact_failures_preserve_raw_children_incomplete_status_and_minimal_report(
    tiny, monkeypatch, operation
):
    def fail(*args, **kwargs):
        if operation == "write_checksums":
            (args[0] / "CHECKSUMS.json").write_text('{"state":"complete"}')
        raise RuntimeError(f"injected {operation} failure")

    monkeypatch.setattr(study_artifacts, operation, fail)
    result = tiny("failed")
    output = convergence_run.ARTIFACT_ROOT / "failed"

    assert result.exit_code != 0
    status = json.loads((output / "STATUS.json").read_text())
    assert status["state"] == "incomplete" and operation in status["error"]
    assert len(list((output / "children").glob("*/records.json"))) == 4
    assert (output / "aggregate.json").is_file()
    assert "Run status: incomplete" in (output / "REPORT.md").read_text()
    if operation == "write_checksums":
        assert not (output / "CHECKSUMS.json").exists()
        assert (output / "CHECKSUMS.partial.json").is_file()
        assert (output / "CHECKSUMS_FAILURE.json").is_file()
    else:
        assert json.loads((output / "CHECKSUMS.json").read_text())["state"] == "incomplete"

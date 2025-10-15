import json

import pytest

from experiments.adiabatic_boundary import run


def _write_summary(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_load_substrate_artifact_accepts_generic_summary(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    summary_path = artifacts_dir / "summary.json"
    _write_summary(summary_path, {"graph": "ring3_hetero"})

    substrate = run._load_substrate_artifact(artifacts_dir)

    assert hasattr(substrate, "N")
    assert substrate.N > 0


def test_load_substrate_artifact_falls_back_when_summary_invalid(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    summary_path = artifacts_dir / "summary.json"
    _write_summary(summary_path, {"graph": {}})

    edges_path = artifacts_dir / "edges.csv"
    edges_path.write_text("source,target\n0,1\n", encoding="utf-8")

    substrate = run._load_substrate_artifact(artifacts_dir)

    assert hasattr(substrate, "N")
    assert substrate.N == 2


def test_load_substrate_artifact_reports_last_summary_error(tmp_path):
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir()

    summary_path = artifacts_dir / "summary.json"
    _write_summary(summary_path, {"graph": {"identifier": ""}})

    with pytest.raises(ValueError) as excinfo:
        run._load_substrate_artifact(artifacts_dir)

    assert "last error" in str(excinfo.value)
    assert "identifier" in str(excinfo.value)

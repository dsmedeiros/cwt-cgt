"""Integration tests for CLI utilities and configuration loading."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError
from typer.testing import CliRunner

from cwt.io.config import AppConfig, load_config
from scripts import eval_report, run_loop, sweep_grid

CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs"
RUNNER = CliRunner()


def test_load_config_round_trip() -> None:
    config_path = CONFIG_DIR / "small_ring.yaml"
    config = load_config(config_path)

    assert isinstance(config, AppConfig)
    assert config.graph.kind == "ring6"
    assert config.params.steps == 6

    round_trip = AppConfig.model_validate(config.model_dump())
    assert round_trip.model_dump() == config.model_dump()


def test_load_config_rejects_unknown_fields(tmp_path: Path) -> None:
    config_path = CONFIG_DIR / "small_ring.yaml"
    config = load_config(config_path)

    payload = config.model_dump()
    payload["graph"]["unexpected"] = "value"

    invalid_path = tmp_path / "invalid.yaml"
    with invalid_path.open("w", encoding="utf8") as handle:
        yaml.safe_dump(payload, handle)

    with pytest.raises(ValidationError) as excinfo:
        load_config(invalid_path)
    assert "unexpected" in str(excinfo.value)


def test_run_loop_cli_persists_run(tmp_path: Path) -> None:
    config_path = CONFIG_DIR / "small_ring.yaml"
    out_dir = tmp_path / "single"

    result = RUNNER.invoke(
        run_loop.app,
        ["--config", str(config_path), "--out", str(out_dir)],
    )
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout.strip())
    run_dir = Path(payload["out_dir"])
    assert run_dir.exists()

    meta_path = run_dir / "meta.json"
    assert meta_path.exists()
    meta = json.loads(meta_path.read_text())
    assert meta["meta"]["label"] == "small_ring"
    assert meta["run_id"] == run_dir.name


def test_sweep_grid_cli_and_report(tmp_path: Path) -> None:
    config_path = CONFIG_DIR / "grid_scan.yaml"
    out_dir = tmp_path / "sweep"

    result = RUNNER.invoke(
        sweep_grid.app,
        ["--config", str(config_path), "--out", str(out_dir), "--limit", "2"],
    )
    assert result.exit_code == 0, result.stdout

    payload = json.loads(result.stdout.strip())
    assert payload["count"] == 2

    run_dirs = sorted(out_dir.iterdir())
    assert len(run_dirs) == 2
    labels = set()
    for run_dir in run_dirs:
        meta = json.loads((run_dir / "meta.json").read_text())
        labels.add(meta["meta"]["label"])
        assert meta["run_id"] == run_dir.name

    assert labels == {"grid_scan_0", "grid_scan_1"}

    report = RUNNER.invoke(eval_report.app, [str(out_dir)])
    assert report.exit_code == 0, report.stdout

    summary = json.loads(report.stdout.strip())
    assert summary["count"] == 2
    reported_labels = {item["label"] for item in summary["runs"]}
    assert reported_labels == labels

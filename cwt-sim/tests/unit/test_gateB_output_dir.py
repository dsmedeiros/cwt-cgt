from __future__ import annotations

from experiments.gateB_ridge_finder import run


def test_resolve_output_dir_prefers_cli(tmp_path, monkeypatch):
    env_path = tmp_path / "env"
    monkeypatch.setenv("CWT_OUTPUT_DIR", str(env_path))

    cli_path = tmp_path / "cli"
    resolved = run.resolve_output_dir(cli_path)

    assert resolved == cli_path


def test_resolve_output_dir_falls_back_to_env(tmp_path, monkeypatch):
    env_path = tmp_path / "env"
    monkeypatch.setenv("CWT_OUTPUT_DIR", str(env_path))

    resolved = run.resolve_output_dir(None)

    assert resolved == env_path


def test_resolve_output_dir_defaults_to_module_artifacts(monkeypatch):
    monkeypatch.delenv("CWT_OUTPUT_DIR", raising=False)

    resolved = run.resolve_output_dir(None)

    assert resolved == run.DEFAULT_ARTIFACTS_DIR

from __future__ import annotations

from typing import Type

from pydantic import BaseModel

from cwt.io.config import APP_CONFIG_RUN_CONFIG_COVERAGE, AppConfig, to_run_config


def _leaf_field_paths(model_type: Type[BaseModel], prefix: str = "") -> set[str]:
    leaves: set[str] = set()
    for name, field in model_type.model_fields.items():
        path = f"{prefix}.{name}" if prefix else name
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            leaves.update(_leaf_field_paths(annotation, path))
        else:
            leaves.add(path)
    return leaves


def test_app_config_coverage_table_tracks_all_declared_leaf_fields() -> None:
    declared = _leaf_field_paths(AppConfig)
    covered = set(APP_CONFIG_RUN_CONFIG_COVERAGE)
    assert declared == covered

    for path, note in APP_CONFIG_RUN_CONFIG_COVERAGE.items():
        assert note.startswith(("mapped:", "ignored:")), f"{path} missing explicit coverage intent"


def test_to_run_config_translates_scheduler_section_keys() -> None:
    app = AppConfig.model_validate(
        {
            "graph": {"kind": "ring3", "weights": 1.2, "delays": 2.0},
            "params": {"knobs": ["rho", "tau"], "steps": 7},
            "geometry": {
                "delta_frac": {"tau": 0.015, "zeta": 0.01},
                "s_min": 0.55,
                "smooth_window": 7,
                "compute_metric": False,
                "compute_curvature": True,
                "adapt_levels": 3,
                "ci_tol": 0.02,
                "sample_mode": "direct",
                "neighbor_steps": 2,
                "neighbor_settle_steps": 17,
            },
            "dynamics": {"eta_q": 0.11, "zeta": 0.4, "omega_scale": 1.3},
            "geometric_coupling": {
                "alpha": 0.5,
                "beta": 0.8,
                "xi_kind": {"type": "dynamic"},
                "corner_area_mode": False,
            },
            "readout": {
                "type": "stochastic",
                "T": 0.7,
                "memory_form": "uniform_charge",
                "params": {"mode": "one_hot", "target": 1},
            },
            "noise": {"phase_std": 0.12, "amp_noise": 0.03, "delay_std": 0.09},
            "seed": 99,
            "out_dir": "runs/test",
        }
    )

    cfg = to_run_config(app)

    assert cfg.geometry["sample_mode"] == "direct"
    assert cfg.geometry["neighbor_steps"] == 2
    assert cfg.geometry["neighbor_settle_steps"] == 17
    assert cfg.delta_frac == {"tau": 0.015, "zeta": 0.01}
    assert cfg.readout["kind"] == "stochastic"
    assert cfg.readout["temperature"] == 0.7
    assert cfg.readout["memory_form"] == "uniform_charge"
    assert "type" not in cfg.readout
    assert "T" not in cfg.readout
    assert cfg.noise["theta_std"] == 0.12
    assert cfg.noise["prob_std"] == 0.03
    assert cfg.noise["delay_std"] == 0.09
    assert "phase_std" not in cfg.noise
    assert "amp_noise" not in cfg.noise


def test_run_config_from_sections_preserves_readout_passthrough_and_normalizes_aliases() -> None:
    from cwt.io.config import run_config_from_sections

    cfg = run_config_from_sections(
        dynamics={"eta_q": 0.2},
        geometry={"delta_frac": {"tau": 0.01}},
        geometric_coupling={},
        readout={"final": True, "interval": 2, "type": "stochastic", "T": 0.9},
        noise={"theta_sigma": 0.4, "prob_sigma": 0.3, "delay_sigma": 0.2},
    )

    assert cfg.readout["final"] is True
    assert cfg.readout["interval"] == 2
    assert cfg.readout["kind"] == "stochastic"
    assert cfg.readout["temperature"] == 0.9
    assert "type" not in cfg.readout
    assert "T" not in cfg.readout
    assert cfg.noise["theta_std"] == 0.4
    assert cfg.noise["prob_std"] == 0.3
    assert cfg.noise["delay_std"] == 0.2
    assert "theta_sigma" not in cfg.noise
    assert "prob_sigma" not in cfg.noise
    assert "delay_sigma" not in cfg.noise
    assert cfg.alpha == 1.0

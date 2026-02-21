"""Pydantic-backed configuration loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field

from cwt.orchestrator.scheduler import RunConfig


class GraphConfig(BaseModel):
    """Configuration for the substrate graph."""

    model_config = ConfigDict(extra="forbid")

    kind: str = "ring3"
    weights: float = 1.0
    delays: float | list[float] = 1.0


class ParamsConfig(BaseModel):
    """Parameter sweep definition."""

    model_config = ConfigDict(extra="allow")

    knobs: list[str] = Field(default_factory=lambda: ["rho", "tau"])
    rho_center: float = 0.0
    rho_extent: float = 0.0
    tau_center: float = 0.0
    tau_extent: float = 0.0
    zeta_phase_center: float = 0.0
    zeta_phase_extent: float = 0.0
    steps: int = 200


class GeometryConfig(BaseModel):
    """Geometry estimation settings."""

    model_config = ConfigDict(extra="forbid")

    delta_frac: dict[str, float]
    s_min: float = 0.6
    smooth_window: int = 5
    compute_metric: bool = True
    compute_curvature: bool = True
    adapt_levels: int = 2
    ci_tol: float = 0.05
    sample_mode: str = "direct"
    neighbor_steps: int = 1
    neighbor_settle_steps: int = 20


class DynamicsConfig(BaseModel):
    """Layer dynamics parameters."""

    model_config = ConfigDict(extra="forbid")

    eta_q: float = 0.3
    zeta: float = 0.2
    omega_scale: float = 1.0


class GeomCouplingConfig(BaseModel):
    """Geometric coupling configuration.

    ``corner_area_mode`` controls rectangle area allocation in ``ParameterPath``:
    distributed per-step area by default, or legacy corner impulses when enabled.
    """

    model_config = ConfigDict(extra="forbid")

    alpha: float = 0.2
    beta: float = 1.0
    xi_kind: dict[str, Any] = Field(default_factory=dict)
    corner_area_mode: bool = False


class ReadoutConfig(BaseModel):
    """Readout configuration."""

    model_config = ConfigDict(extra="forbid")

    type: str = "stochastic"
    T: float = 1.0
    memory_form: str = "current_coupled"
    params: dict[str, Any] = Field(default_factory=dict)


class NoiseConfig(BaseModel):
    """Noise process configuration."""

    model_config = ConfigDict(extra="forbid")

    phase_std: float = 0.0
    amp_noise: float = 0.0
    delay_std: float = 0.0


class AppConfig(BaseModel):
    """Top-level application configuration bundle."""

    model_config = ConfigDict(extra="forbid")

    graph: GraphConfig
    params: ParamsConfig
    geometry: GeometryConfig
    dynamics: DynamicsConfig
    geometric_coupling: GeomCouplingConfig
    readout: ReadoutConfig
    noise: NoiseConfig
    seed: int = 1234
    out_dir: str = "runs/"


# Leaf-level `AppConfig` fields are either translated into `RunConfig` or
# intentionally ignored by the run-config converter.
APP_CONFIG_RUN_CONFIG_COVERAGE: dict[str, str] = {
    "graph.kind": "ignored: used by substrate construction, not the scheduler",
    "graph.weights": "ignored: used by substrate construction, not the scheduler",
    "graph.delays": "ignored: used by substrate construction, not the scheduler",
    "params.knobs": "ignored: consumed by ParameterPath construction",
    "params.rho_center": "ignored: consumed by ParameterPath construction",
    "params.rho_extent": "ignored: consumed by ParameterPath construction",
    "params.tau_center": "ignored: consumed by ParameterPath construction",
    "params.tau_extent": "ignored: consumed by ParameterPath construction",
    "params.zeta_phase_center": "ignored: consumed by ParameterPath construction",
    "params.zeta_phase_extent": "ignored: consumed by ParameterPath construction",
    "params.steps": "ignored: consumed by ParameterPath construction",
    "geometry.delta_frac": "mapped: RunConfig.delta_frac",
    "geometry.s_min": "mapped: RunConfig.s_min",
    "geometry.smooth_window": "mapped: RunConfig.smooth_window",
    "geometry.compute_metric": "mapped: RunConfig.compute_metric",
    "geometry.compute_curvature": "mapped: RunConfig.compute_curvature",
    "geometry.adapt_levels": "mapped: RunConfig.adapt_levels",
    "geometry.ci_tol": "mapped: RunConfig.ci_tol",
    "geometry.sample_mode": "mapped: RunConfig.geometry['sample_mode']",
    "geometry.neighbor_steps": "mapped: RunConfig.geometry['neighbor_steps']",
    "geometry.neighbor_settle_steps": "mapped: RunConfig.neighbor_settle_steps + geometry section",
    "dynamics.eta_q": "mapped: RunConfig.eta_q",
    "dynamics.zeta": "mapped: RunConfig.zeta",
    "dynamics.omega_scale": "mapped: RunConfig.omega_scale",
    "geometric_coupling.alpha": "mapped: RunConfig.alpha",
    "geometric_coupling.beta": "mapped: RunConfig.beta",
    "geometric_coupling.xi_kind": "mapped: RunConfig.xi_kind",
    "geometric_coupling.corner_area_mode": "ignored: consumed by ParameterPath construction",
    "readout.type": "mapped: RunConfig.readout['kind']",
    "readout.T": "mapped: RunConfig.readout['temperature']",
    "readout.memory_form": "mapped: RunConfig.readout['memory_form']",
    "readout.params": "mapped: RunConfig.readout['params']",
    "noise.phase_std": "mapped: RunConfig.noise['theta_std']",
    "noise.amp_noise": "mapped: RunConfig.noise['prob_std']",
    "noise.delay_std": "mapped: RunConfig.noise['delay_std']",
    "seed": "ignored: passed directly to run_parameter_loop",
    "out_dir": "ignored: used by IO layer",
}


def _translate_geometry_settings(geometry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "sample_mode": geometry.get("sample_mode", "direct"),
        "neighbor_steps": int(geometry.get("neighbor_steps", 1)),
        "neighbor_settle_steps": int(geometry.get("neighbor_settle_steps", 20)),
    }


def _translate_readout_settings(readout: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(readout)
    if "kind" not in payload:
        payload["kind"] = str(readout.get("type", "stochastic"))
    if "temperature" not in payload:
        payload["temperature"] = float(readout.get("T", 1.0))
    payload["memory_form"] = str(payload.get("memory_form", "current_coupled"))
    payload["params"] = dict(payload.get("params", {}))
    for stale in ("type", "T"):
        payload.pop(stale, None)
    return payload


def _translate_noise_settings(noise: Mapping[str, Any]) -> dict[str, float]:
    payload = {key: float(val) for key, val in dict(noise).items()}
    phase_std = payload.get("theta_std", payload.get("theta_sigma", payload.get("phase_std", 0.0)))
    amp_std = payload.get(
        "prob_std",
        payload.get("prob_sigma", payload.get("amp_noise", payload.get("amp_std", 0.0))),
    )
    delay_std = payload.get("delay_std", payload.get("delay_sigma", payload.get("tau_sigma", 0.0)))
    payload["theta_std"] = float(phase_std)
    payload["prob_std"] = float(amp_std)
    payload["delay_std"] = float(delay_std)
    for stale in (
        "theta_sigma",
        "phase_std",
        "prob_sigma",
        "amp_noise",
        "amp_std",
        "delay_sigma",
        "tau_sigma",
    ):
        payload.pop(stale, None)
    return payload


def run_config_from_sections(
    *,
    dynamics: Mapping[str, Any],
    geometry: Mapping[str, Any],
    geometric_coupling: Mapping[str, Any],
    readout: Mapping[str, Any] | None = None,
    noise: Mapping[str, Any] | None = None,
    fs_step_guard: Mapping[str, Any] | None = None,
) -> RunConfig:
    """Build a :class:`RunConfig` from config sections using canonical translations."""

    translated_geometry = _translate_geometry_settings(geometry)
    translated_readout = _translate_readout_settings(readout or {})
    translated_noise = _translate_noise_settings(noise or {})

    defaults = RunConfig()

    return RunConfig(
        eta_q=float(dynamics.get("eta_q", defaults.eta_q)),
        zeta=float(dynamics.get("zeta", defaults.zeta)),
        omega_scale=float(dynamics.get("omega_scale", defaults.omega_scale)),
        s_min=float(geometry.get("s_min", defaults.s_min)),
        smooth_window=int(geometry.get("smooth_window", defaults.smooth_window)),
        compute_metric=bool(geometry.get("compute_metric", defaults.compute_metric)),
        compute_curvature=bool(geometry.get("compute_curvature", defaults.compute_curvature)),
        adapt_levels=int(geometry.get("adapt_levels", defaults.adapt_levels)),
        ci_tol=float(geometry.get("ci_tol", defaults.ci_tol)),
        alpha=float(geometric_coupling.get("alpha", defaults.alpha)),
        beta=float(geometric_coupling.get("beta", defaults.beta)),
        neighbor_settle_steps=int(translated_geometry["neighbor_settle_steps"]),
        geometry=translated_geometry,
        delta_frac={k: float(v) for k, v in dict(geometry.get("delta_frac", {})).items()},
        xi_kind=dict(geometric_coupling.get("xi_kind", {})),
        readout=translated_readout,
        noise=translated_noise,
        fs_step_guard=dict(fs_step_guard or {}),
    )


def to_run_config(app: AppConfig) -> RunConfig:
    """Translate :class:`AppConfig` into :class:`RunConfig`."""

    return run_config_from_sections(
        dynamics=app.dynamics.model_dump(),
        geometry=app.geometry.model_dump(),
        geometric_coupling=app.geometric_coupling.model_dump(),
        readout=app.readout.model_dump(),
        noise=app.noise.model_dump(),
    )


def load_config(path: str | Path) -> AppConfig:
    """Load an :class:`AppConfig` from a YAML file."""

    config_path = Path(path)
    if not config_path.exists():  # pragma: no cover - defensive guard
        raise FileNotFoundError(f"Configuration file '{config_path}' does not exist.")

    with config_path.open("r", encoding="utf8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise TypeError("Configuration payload must be a mapping.")

    return AppConfig.model_validate(payload)


__all__ = [
    "AppConfig",
    "DynamicsConfig",
    "GeomCouplingConfig",
    "GeometryConfig",
    "GraphConfig",
    "NoiseConfig",
    "ParamsConfig",
    "ReadoutConfig",
    "APP_CONFIG_RUN_CONFIG_COVERAGE",
    "load_config",
    "run_config_from_sections",
    "to_run_config",
]

"""Pydantic-backed configuration loading utilities."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field


class GraphConfig(BaseModel):
    """Configuration for the substrate graph."""

    model_config = ConfigDict(extra="forbid")

    kind: str = "ring3"
    weights: float = 1.0
    delays: float = 1.0


class ParamsConfig(BaseModel):
    """Parameter sweep definition."""

    model_config = ConfigDict(extra="forbid")

    knobs: list[str] = Field(default_factory=lambda: ["rho", "tau"])
    rho_center: float
    rho_extent: float
    tau_center: float
    tau_extent: float
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


class DynamicsConfig(BaseModel):
    """Layer dynamics parameters."""

    model_config = ConfigDict(extra="forbid")

    eta_q: float = 0.3
    zeta: float = 0.2
    omega_scale: float = 1.0


class GeomCouplingConfig(BaseModel):
    """Geometric coupling configuration."""

    model_config = ConfigDict(extra="forbid")

    alpha: float = 0.2
    beta: float = 1.0
    xi_kind: dict[str, Any] = Field(default_factory=dict)
    corner_area_mode: bool = True


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
    "load_config",
]

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np
import pytest

from cwt.geometry.adapt_mesh import curvature_anytime
from cwt.graph.factories import ring3
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import (
    RunConfig,
    _direct_neighbor_state_factory,
    _psi_at,
    _psi_sampler_factory_direct,
    run_parameter_loop,
)

NOMINAL_CENTER = {"tau": 0.8, "zeta": 0.0}


def _clone_run_config(config: RunConfig) -> RunConfig:
    cloned = replace(config)
    cloned.geometry = dict(config.geometry)
    cloned.delta_frac = dict(config.delta_frac)
    cloned.xi_kind = dict(config.xi_kind)
    cloned.readout = dict(config.readout)
    cloned.noise = dict(config.noise)
    cloned.fs_step_guard = dict(config.fs_step_guard)
    return cloned


def _make_run_config() -> RunConfig:
    return RunConfig(
        eta_q=0.3,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=3,
        compute_metric=False,
        compute_curvature=True,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=0.3,
        beta=1.0,
        neighbor_settle_steps=40,
        geometry={"sample_mode": "direct", "neighbor_steps": 1},
        delta_frac={"tau": 0.01, "zeta": 0.01},
        xi_kind={"type": "static"},
        readout={},
        noise={},
    )


def _pick_uniform_center(
    config: RunConfig,
    *,
    lam0: dict[str, float] | None = None,
    span: float = 0.03,
    delta: float = 0.01,
    grid: int = 5,
) -> dict[str, float]:
    lam_nominal = NOMINAL_CENTER.copy()
    if lam0:
        lam_nominal.update({str(k): float(v) for k, v in lam0.items()})

    if grid < 3:
        grid = 3

    substrate = ring3(weight=1.0, delays=[1.0, 1.5, 2.2])
    base_prob = np.full(substrate.N, 1.0 / substrate.N, dtype=float)
    base_theta = np.zeros(substrate.N, dtype=float)

    settle_steps = max(int(getattr(config, "neighbor_settle_steps", 20)), 1)

    tau_vals = np.linspace(lam_nominal["tau"] - span, lam_nominal["tau"] + span, grid)
    zeta_vals = np.linspace(lam_nominal["zeta"] - span, lam_nominal["zeta"] + span, grid)
    omegas = np.full((grid, grid), np.nan, dtype=float)

    cloned_cfg = _clone_run_config(config)

    for i, tau_val in enumerate(tau_vals):
        for j, zeta_val in enumerate(zeta_vals):
            lam = {"tau": float(tau_val), "zeta": float(zeta_val)}
            try:
                psi0 = _psi_at(substrate, lam, base_prob, base_theta, cloned_cfg, steps=settle_steps)
            except Exception:  # pragma: no cover - defensive guard
                continue

            prob = np.square(np.abs(psi0))
            theta = np.angle(psi0)

            try:
                neighbor_factory = _direct_neighbor_state_factory(
                    substrate,
                    lam,
                    prob,
                    theta,
                    cloned_cfg,
                    neighbor_steps=1,
                    settle_steps=settle_steps,
                )
                sampler = _psi_sampler_factory_direct(psi0, "tau", "zeta", neighbor_factory)
                plaquette = curvature_anytime(
                    sampler,
                    delta,
                    delta,
                    s_min=float(cloned_cfg.s_min),
                    ci_tol=float(cloned_cfg.ci_tol),
                    max_levels=max(int(cloned_cfg.adapt_levels), 1),
                )
            except Exception:  # pragma: no cover - defensive guard
                continue

            omega = float(plaquette.omega_mean)
            if math.isfinite(omega):
                omegas[i, j] = omega

    if not np.isfinite(omegas).any():
        return lam_nominal

    best_score = -math.inf
    best_center: dict[str, float] | None = None
    for i in range(1, grid - 1):
        for j in range(1, grid - 1):
            omega = omegas[i, j]
            if not math.isfinite(omega):
                continue

            neighbors = [
                omegas[i - 1, j],
                omegas[i + 1, j],
                omegas[i, j - 1],
                omegas[i, j + 1],
            ]
            if any(not math.isfinite(val) for val in neighbors):
                continue
            if any(omega * val < 0.0 for val in neighbors if val != 0.0):
                continue

            local_grad = max(abs(omega - val) for val in neighbors)
            score = abs(omega) / (1.0 + local_grad)
            if score > best_score:
                best_score = score
                best_center = {"tau": float(tau_vals[i]), "zeta": float(zeta_vals[j])}

    return best_center or lam_nominal


def _run_loop(
    extent: float,
    orientation: str,
    *,
    center: dict[str, float],
    config: RunConfig,
) -> tuple[float, float]:
    run_config = _clone_run_config(config)
    substrate = ring3(weight=1.0, delays=[1.0, 1.5, 2.2])
    base_prob = np.full(substrate.N, 1.0 / substrate.N, dtype=float)
    base_theta = np.zeros(substrate.N, dtype=float)

    path_center = {
        "tau": float(center.get("tau", NOMINAL_CENTER["tau"])),
        "zeta": float(center.get("zeta", NOMINAL_CENTER["zeta"])),
    }
    base_steps = 2048
    step_scale = max(1, int(round(extent / 0.02)))
    path = ParameterPath(
        kind="rectangle",
        center=path_center,
        extents={"tau": extent, "zeta": extent},
        steps=base_steps * step_scale,
        orientation=orientation,
        axes=("tau", "zeta"),
    )

    try:
        psi_center = _psi_at(
            substrate,
            path_center,
            base_prob,
            base_theta,
            run_config,
            steps=max(int(run_config.neighbor_settle_steps), 1),
        )
    except Exception:  # pragma: no cover - defensive guard
        psi_center = _psi_at(substrate, path_center, base_prob, base_theta, run_config, steps=1)

    init_state = LayersState(
        pQ=np.square(np.abs(psi_center)).astype(float, copy=False),
        theta=np.angle(psi_center).astype(float, copy=False),
    )

    record = run_parameter_loop(substrate, init_state, path, run_config, seed=13)
    total_area = float(sum(record.delta_area))
    omega_flux = 0.0
    corner_flux: float | None = None
    for area_contrib, tile in zip(record.delta_area, record.omega_tiles):
        area_val = float(area_contrib)
        omega_val = float(tile.get("omega", 0.0))
        if not (math.isfinite(area_val) and math.isfinite(omega_val)):
            continue
        if area_val == 0.0:
            continue
        corner_flux = omega_val * total_area
        break

    if corner_flux is not None:
        omega_flux = corner_flux
    else:
        omega_weighted_sum = 0.0
        weight_sum = 0.0
        for tile in record.omega_tiles:
            omega_val = float(tile.get("omega", 0.0))
            tile_area = float(tile.get("tile_area", 0.0))
            if not (math.isfinite(omega_val) and math.isfinite(tile_area)):
                continue
            if tile_area <= 0.0:
                continue
            omega_weighted_sum += omega_val * tile_area
            weight_sum += tile_area
        if weight_sum > 0.0:
            omega_flux = (omega_weighted_sum / weight_sum) * total_area
    return total_area, omega_flux


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_tau_zeta_loop_orientation_and_scaling() -> None:
    config = _make_run_config()
    center = _pick_uniform_center(config)

    area_small_ccw, flux_small_ccw = _run_loop(0.02, "CCW", center=center, config=config)
    area_small_cw, flux_small_cw = _run_loop(0.02, "CW", center=center, config=config)
    assert area_small_ccw != 0.0
    assert area_small_cw != 0.0
    sign_flip_error = abs(area_small_cw + area_small_ccw) / max(abs(area_small_ccw), 1e-9)
    assert sign_flip_error <= 0.05
    flux_flip_error = abs(flux_small_cw + flux_small_ccw) / max(abs(flux_small_ccw), 1e-9)
    assert flux_flip_error <= 0.05

    kappa_small = flux_small_ccw / area_small_ccw

    area_large, flux_large_ccw = _run_loop(0.04, "CCW", center=center, config=config)
    assert area_large != 0.0
    kappa_large = flux_large_ccw / area_large

    scale_error = abs(kappa_small - kappa_large) / max(abs(kappa_small), 1e-9)
    assert scale_error <= 0.20

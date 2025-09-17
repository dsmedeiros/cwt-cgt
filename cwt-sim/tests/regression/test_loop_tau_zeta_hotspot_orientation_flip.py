from __future__ import annotations

import math

import numpy as np
import pytest

from cwt.graph.factories import ring3
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, run_parameter_loop


def _run_loop(extent: float, orientation: str) -> tuple[float, float]:
    substrate = ring3(weight=1.0, delays=[1.0, 1.5, 2.2])
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N, dtype=float),
        theta=np.zeros(substrate.N, dtype=float),
    )

    path = ParameterPath(
        kind="rectangle",
        center={"tau": 0.8, "zeta": 0.0},
        extents={"tau": extent, "zeta": extent},
        steps=64,
        orientation=orientation,
        axes=("tau", "zeta"),
    )

    config = RunConfig(
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
        neighbor_settle_steps=20,
        geometry={"sample_mode": "direct", "neighbor_steps": 1},
        delta_frac={"tau": extent, "zeta": extent},
        xi_kind={"type": "static"},
        readout={},
        noise={},
    )

    record = run_parameter_loop(substrate, init_state, path, config, seed=13)
    total_area = float(sum(record.delta_area))
    omega_flux = 0.0
    for tile in record.omega_tiles:
        omega_val = float(tile.get("omega", 0.0))
        tile_area = float(tile.get("tile_area", 0.0))
        if math.isfinite(omega_val) and math.isfinite(tile_area):
            omega_flux += omega_val * tile_area
    return total_area, omega_flux


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_tau_zeta_loop_orientation_and_scaling() -> None:
    area_small_ccw, flux_small_ccw = _run_loop(0.02, "CCW")
    area_small_cw, flux_small_cw = _run_loop(0.02, "CW")
    assert area_small_ccw != 0.0
    assert area_small_cw != 0.0
    sign_flip_error = abs(area_small_cw + area_small_ccw) / max(abs(area_small_ccw), 1e-9)
    assert sign_flip_error <= 0.05

    kappa_small = flux_small_ccw / area_small_ccw

    area_large, flux_large_ccw = _run_loop(0.04, "CCW")
    assert area_large != 0.0
    kappa_large = flux_large_ccw / area_large

    scale_error = abs(kappa_small - kappa_large) / max(abs(kappa_small), 1e-9)
    assert scale_error <= 0.20

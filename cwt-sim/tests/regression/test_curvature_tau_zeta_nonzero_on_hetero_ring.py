from __future__ import annotations

import math

import numpy as np
import pytest

from cwt.graph.factories import ring3
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, run_parameter_loop


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_curvature_tau_zeta_nonzero_on_hetero_ring() -> None:
    substrate = ring3(weight=1.0, delays=[1.0, 1.5, 2.2])
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N, dtype=float),
        theta=np.zeros(substrate.N, dtype=float),
    )

    path = ParameterPath(
        kind="rectangle",
        center={"tau": 0.8, "zeta": 0.0},
        extents={"tau": 0.02, "zeta": 0.02},
        steps=48,
        orientation="CCW",
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
        delta_frac={"tau": 0.02, "zeta": 0.02},
        xi_kind={"type": "static"},
        readout={},
        noise={},
    )

    record = run_parameter_loop(substrate, init_state, path, config, seed=11)
    assert record.omega_tiles

    magnitudes = [abs(tile["omega"]) for tile in record.omega_tiles if math.isfinite(tile["omega"])]
    assert magnitudes, "expected finite curvature estimates"
    assert max(magnitudes) > 1e-4

from __future__ import annotations

import numpy as np
import pytest

from cwt.graph.factories import ring3
from cwt.layers.state import LayersState
from cwt.orchestrator import scheduler
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, run_parameter_loop


def test_theta_frustration_and_direct_sampler_settle(monkeypatch: pytest.MonkeyPatch) -> None:
    substrate = ring3(weight=1.0, delays=[1.0, 1.5, 2.2])
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N, dtype=float),
        theta=np.zeros(substrate.N, dtype=float),
    )

    settle_steps = 18
    recorded_settle: list[int] = []
    original_psi_at = scheduler._psi_at

    def _recording_psi_at(*args, **kwargs):
        steps = kwargs.get("steps")
        if steps is None and len(args) >= 5:
            steps = args[4]
        if steps is None:
            raise AssertionError("_psi_at should receive an explicit settle step count")
        recorded_settle.append(int(steps))
        return original_psi_at(*args, **kwargs)

    monkeypatch.setattr(scheduler, "_psi_at", _recording_psi_at)

    path = ParameterPath(
        kind="rectangle",
        center={"tau": 0.8, "zeta_phase": 0.0},
        extents={"tau": 0.02, "zeta_phase": 0.03},
        steps=48,
        orientation="CCW",
        axes=("tau", "zeta_phase"),
    )

    config = RunConfig(
        eta_q=0.3,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=3,
        compute_metric=False,
        compute_curvature=False,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=0.3,
        beta=1.0,
        neighbor_settle_steps=settle_steps,
        geometry={"sample_mode": "direct", "neighbor_steps": 2},
        delta_frac={"tau": 0.02, "zeta_phase": 0.03},
        xi_kind={"type": "static"},
        readout={},
        noise={},
        fs_step_guard={"action": "none"},
    )

    record = run_parameter_loop(substrate, init_state, path, config, seed=7)
    theta_variances = [float(np.var(theta)) for theta in record.theta_traj[1:]]

    assert any(var > 1e-6 for var in theta_variances), "zeta_phase should frustrate immediate phase lock"
    leading_window = theta_variances[: min(len(theta_variances), 8)]
    assert sum(1 for var in leading_window if var > 1e-6) >= max(1, len(leading_window) // 2)

    assert recorded_settle, "direct sampler should invoke _psi_at with settle steps"
    for value in recorded_settle:
        assert value >= settle_steps

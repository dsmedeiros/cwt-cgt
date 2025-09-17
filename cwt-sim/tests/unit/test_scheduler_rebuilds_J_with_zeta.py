from __future__ import annotations

import math

import networkx as nx
import numpy as np
import pytest

from cwt.graph.substrate import build_substrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, run_parameter_loop


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_scheduler_rebuilds_J_with_zeta(monkeypatch: pytest.MonkeyPatch) -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 2, weight=1.0, delay=1.5)
    G.add_edge(2, 0, weight=1.0, delay=2.0)

    substrate = build_substrate(G)
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N, dtype=float),
        theta=np.zeros(substrate.N, dtype=float),
    )

    zeta_calls: list[float] = []

    def _fake_build_J(S, *, zeta: float) -> np.ndarray:  # type: ignore[override]
        zeta_calls.append(float(zeta))
        return np.eye(S.N, dtype=float)

    monkeypatch.setattr("cwt.orchestrator.scheduler.build_J_from_W", _fake_build_J)

    path = ParameterPath(
        kind="rectangle",
        center={"tau": 0.9, "zeta": 0.0},
        extents={"tau": 0.05, "zeta": 0.15},
        steps=12,
        orientation="CCW",
        axes=("tau", "zeta"),
    )

    config = RunConfig(
        eta_q=0.4,
        zeta=0.0,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=1,
        compute_metric=False,
        compute_curvature=False,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=0.0,
        beta=0.0,
        delta_frac={"tau": 0.01, "zeta": 0.02},
        xi_kind={"type": "static"},
        readout={},
        noise={},
    )

    run_parameter_loop(substrate, init_state, path, config, seed=3)

    recorded = [float(val) for val in zeta_calls]
    expected = [path.step(step_index)[0]["zeta"] for step_index in range(path.steps)]
    assert len({round(val, 6) for val in expected}) >= 2
    for value in expected:
        assert any(math.isclose(value, call, rel_tol=1e-6, abs_tol=1e-6) for call in recorded)

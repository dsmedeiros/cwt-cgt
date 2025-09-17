from __future__ import annotations

import math
from collections import defaultdict

import networkx as nx
import numpy as np
import pytest

from cwt.graph.substrate import build_substrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator import scheduler
from cwt.orchestrator.scheduler import RunConfig, run_parameter_loop


@pytest.mark.filterwarnings("ignore::RuntimeWarning")
def test_scheduler_rebuilds_J_from_path_zeta(monkeypatch: pytest.MonkeyPatch) -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 2, weight=1.0, delay=1.5)
    G.add_edge(2, 0, weight=1.0, delay=2.0)

    substrate = build_substrate(G)
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N, dtype=float),
        theta=np.zeros(substrate.N, dtype=float),
    )

    recorded: dict[float, list[np.ndarray]] = defaultdict(list)
    original_build_J = scheduler.build_J_from_W

    def _recording_build_J(S, *, zeta: float) -> np.ndarray:  # type: ignore[override]
        J = original_build_J(S, zeta=zeta)
        recorded[round(float(zeta), 9)].append(J)
        return J

    monkeypatch.setattr(scheduler, "build_J_from_W", _recording_build_J)

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

    expected = [path.step(step_index)[0]["zeta"] for step_index in range(path.steps)]
    distinct_expected = {round(val, 9) for val in expected}
    assert len(distinct_expected) >= 2

    for key in distinct_expected:
        assert key in recorded, f"missing zeta={key} in recorded J rebuilds"

    matrices = [values[0] for values in recorded.values() if values]
    assert len(matrices) >= 2
    for i in range(len(matrices)):
        for j in range(i + 1, len(matrices)):
            assert not math.isclose(float(np.max(np.abs(matrices[i] - matrices[j]))), 0.0, abs_tol=1e-9)

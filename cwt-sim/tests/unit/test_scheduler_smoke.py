import networkx as nx
import numpy as np

from cwt.graph.substrate import build_substrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, run_parameter_loop


def test_run_parameter_loop_smoke() -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 2, weight=1.0, delay=1.0)
    G.add_edge(2, 0, weight=1.0, delay=1.0)

    substrate = build_substrate(G)
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N),
        theta=np.zeros(substrate.N),
    )

    path = ParameterPath(
        kind="line",
        center={"rho": 0.5, "tau": 1.0},
        extents={"rho": 0.1},
        steps=6,
    )

    config = RunConfig(
        eta_q=0.5,
        zeta=0.2,
        omega_scale=1.0,
        s_min=0.6,
        smooth_window=1,
        compute_metric=False,
        compute_curvature=False,
        adapt_levels=1,
        ci_tol=0.05,
        alpha=1.0,
        beta=1.0,
        delta_frac={"rho": 0.05, "tau": 0.05},
        xi_kind={"type": "static"},
        readout={
            "interval": 3,
            "final": True,
            "memory_form": "uniform_charge",
            "params": {"mode": "psi_amp"},
        },
        noise={"theta_sigma": 0.0, "prob_sigma": 0.0},
    )

    record = run_parameter_loop(substrate, init_state, path, config, seed=42)

    assert len(record.lambda_path) == path.steps
    assert len(record.pQ_traj) == path.steps + 1
    assert len(record.theta_traj) == path.steps + 1
    assert len(record.psi_traj) == path.steps + 1
    assert len(record.fs_steps) == path.steps
    assert len(record.clip_counts) == path.steps

    for vec in record.pQ_traj:
        assert vec.shape == (substrate.N,)
        assert np.isclose(vec.sum(), 1.0)

    for angles in record.theta_traj:
        assert angles.shape == (substrate.N,)
        assert np.all(np.isfinite(angles))

    assert record.meta["seed"] == 42
    assert record.meta["steps"] == path.steps
    assert record.meta["substrate_size"] == substrate.N
    guard_meta = record.meta.get("fs_step_guard")
    assert isinstance(guard_meta, dict)
    assert "threshold" in guard_meta
    assert "overall_fraction" in guard_meta
    assert record.readouts  # interval + final
    final_readout = record.readouts[-1]
    if final_readout.get("step") == path.steps:
        assert "phi_flux" in final_readout
        assert "memory" in final_readout
        assert len(final_readout["memory"]) == substrate.N

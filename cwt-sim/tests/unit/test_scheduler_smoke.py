import networkx as nx
import numpy as np
import pytest

from cwt.graph.substrate import build_substrate
from cwt.layers.state import LayersState
from cwt.orchestrator import scheduler
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


def test_readouts_include_normalization_diagnostics() -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 0, weight=1.0, delay=1.0)

    substrate = build_substrate(G)
    init_state = LayersState(
        pQ=np.array([1.2, -0.2]),
        theta=np.zeros(substrate.N),
    )
    path = ParameterPath(kind="line", center={"rho": 0.3}, extents={"rho": 0.0}, steps=1, axes=("rho", "rho"))
    config = RunConfig(
        xi_kind={"type": "dynamic"},
        readout={"interval": 1, "final": True},
        noise={"prob_sigma": 0.0, "theta_sigma": 0.0},
    )

    record = run_parameter_loop(substrate, init_state, path, config, seed=0)

    assert record.readouts
    final_readout = record.readouts[-1]
    normalization = final_readout.get("normalization")
    assert isinstance(normalization, dict)
    assert {
        "xi_neg_clamped_count",
        "xi_neg_clamped_mass",
        "xi_uniform_fallback",
        "q_step_neg_clamped_count",
        "q_step_neg_clamped_mass",
        "q_step_uniform_fallback",
        "noise_neg_clamped_count",
        "noise_neg_clamped_mass",
        "noise_uniform_fallback",
    }.issubset(normalization)
    assert normalization["noise_uniform_fallback"] is False
    assert normalization["xi_uniform_fallback"] is False


def _make_static_path(center: dict[str, float]) -> ParameterPath:
    keys = list(center)
    if not keys:
        raise ValueError("center must contain at least one knob")
    if len(keys) == 1:
        axes = (keys[0], keys[0])
    else:
        axes = (keys[0], keys[1])
    extents = {key: 0.0 for key in center}
    return ParameterPath(kind="line", center=center, extents=extents, steps=1, axes=axes)


def test_run_parameter_loop_respects_tau_knobs(monkeypatch: pytest.MonkeyPatch) -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    substrate = build_substrate(G)
    init_state = LayersState(pQ=np.array([1.0, 0.0]), theta=np.zeros(2))

    config = RunConfig(
        eta_q=0.5,
        zeta=0.0,
        omega_scale=1.0,
        smooth_window=1,
        compute_curvature=False,
        readout={},
        noise={},
        fs_step_guard={},
    )

    kernel_calls: list[float] = []
    omega_calls: list[float] = []

    real_kernel = scheduler.build_transport_kernel
    real_omega = scheduler.omega_from_delays

    def capture_kernel(S, rho, tau_scale, kappa):
        kernel_calls.append(float(tau_scale))
        return real_kernel(S, rho, tau_scale, kappa)

    def capture_omega(S, rho, tau_scale, omega_scale):
        omega_calls.append(float(tau_scale))
        return real_omega(S, rho, tau_scale, omega_scale)

    monkeypatch.setattr(scheduler, "build_transport_kernel", capture_kernel)
    monkeypatch.setattr(scheduler, "omega_from_delays", capture_omega)

    def run_with(center: dict[str, float]) -> float:
        kernel_calls.clear()
        omega_calls.clear()
        path = _make_static_path(center)
        run_parameter_loop(substrate, init_state, path, config, seed=0)
        assert kernel_calls, "transport kernel was not invoked"
        assert omega_calls, "omega update was not invoked"
        assert pytest.approx(kernel_calls[0]) == omega_calls[0]
        return kernel_calls[0]

    assert run_with({"tau": 1.7}) == pytest.approx(1.7)
    assert run_with({"tau_scale": 2.5}) == pytest.approx(2.5)
    assert run_with({"tau": 1.2, "tau_scale": 1.5}) == pytest.approx(1.2 * 1.5)


def test_snapshot_interval_one_preserves_dense_vector_trajectories() -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 2, weight=1.0, delay=1.0)
    G.add_edge(2, 0, weight=1.0, delay=1.0)

    substrate = build_substrate(G)
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N),
        theta=np.zeros(substrate.N),
    )
    path = ParameterPath(kind="line", center={"rho": 0.5}, extents={"rho": 0.1}, steps=6, axes=("rho", "rho"))
    config = RunConfig(snapshot_interval=1, readout={})

    record = run_parameter_loop(substrate, init_state, path, config, seed=0)

    assert len(record.pQ_traj) == path.steps + 1
    assert len(record.theta_traj) == path.steps + 1
    assert len(record.psi_traj) == path.steps + 1
    assert len(record.phase_kicks) == path.steps
    assert len(record.curvature_biases) == path.steps
    assert len(record.fs_steps) == path.steps
    assert record.meta["snapshot_cadence"]["interval"] == 1
    assert record.meta["snapshot_cadence"]["kept_steps"] == list(range(path.steps + 1))


def test_snapshot_interval_reduces_vector_snapshots_predictably() -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 2, weight=1.0, delay=1.0)
    G.add_edge(2, 0, weight=1.0, delay=1.0)

    substrate = build_substrate(G)
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N),
        theta=np.zeros(substrate.N),
    )
    path = ParameterPath(kind="line", center={"rho": 0.5}, extents={"rho": 0.1}, steps=5, axes=("rho", "rho"))
    config = RunConfig(snapshot_interval=2, readout={})

    record = run_parameter_loop(substrate, init_state, path, config, seed=1)

    expected_kept_steps = [0, 2, 4, 5]
    expected_vector_steps = [2, 4, 5]

    assert len(record.pQ_traj) == len(expected_kept_steps)
    assert len(record.theta_traj) == len(expected_kept_steps)
    assert len(record.psi_traj) == len(expected_kept_steps)
    assert len(record.phase_kicks) == len(expected_vector_steps)
    assert len(record.curvature_biases) == len(expected_vector_steps)
    assert len(record.fs_steps) == path.steps
    assert len(record.overlaps_min) == path.steps
    assert len(record.clip_counts) == path.steps
    assert record.meta["snapshot_cadence"]["interval"] == 2
    assert record.meta["snapshot_cadence"]["kept_steps"] == expected_kept_steps


def test_snapshot_interval_keeps_final_snapshot_after_early_abort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    G = nx.DiGraph()
    G.add_edge(0, 1, weight=1.0, delay=1.0)
    G.add_edge(1, 2, weight=1.0, delay=1.0)
    G.add_edge(2, 0, weight=1.0, delay=1.0)

    substrate = build_substrate(G)
    init_state = LayersState(
        pQ=np.full(substrate.N, 1.0 / substrate.N),
        theta=np.zeros(substrate.N),
    )
    path = ParameterPath(kind="line", center={"rho": 0.5}, extents={"rho": 0.1}, steps=8, axes=("rho", "rho"))
    config = RunConfig(
        snapshot_interval=3,
        readout={},
        fs_step_guard={"enforce_p95": True, "boundary": 1e-12},
    )

    monkeypatch.setattr(scheduler, "_should_abort_fs", lambda *args, **kwargs: True)

    record = run_parameter_loop(substrate, init_state, path, config, seed=7)

    completed = int(record.meta["path"]["completed"])
    kept_steps = record.meta["snapshot_cadence"]["kept_steps"]

    assert completed < path.steps
    assert kept_steps[0] == 0
    assert kept_steps[-1] == completed
    assert len(record.pQ_traj) == len(kept_steps)
    assert len(record.theta_traj) == len(kept_steps)
    assert len(record.psi_traj) == len(kept_steps)

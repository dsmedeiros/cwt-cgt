"""Inverse design of curvature-guided loops targeting enhanced readout R."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np

from cwt.graph import factories
from cwt.graph.substrate import GraphSubstrate
from cwt.layers.state import LayersState
from cwt.orchestrator.param_path import ParameterPath
from cwt.orchestrator.scheduler import RunConfig, _psi_at, run_parameter_loop


@dataclass
class PathEvaluation:
    """Metrics collected for a candidate control polygon."""

    control_points: tuple[tuple[float, float], ...]
    phi_flux: float
    guard_fraction: float
    path_length: float
    objective: float

    @property
    def R_value(self) -> float:
        return float(self.phi_flux)


def _build_substrate() -> GraphSubstrate:
    return factories.ring3_hetero()


def _initial_state(
    substrate: GraphSubstrate,
    center: Mapping[str, float],
    config: RunConfig,
    settle_steps: int,
) -> LayersState:
    N = substrate.N
    if N <= 0:
        return LayersState(pQ=np.zeros(0, dtype=float), theta=np.zeros(0, dtype=float))

    base_prob = np.full(N, 1.0 / N, dtype=float)
    base_theta = np.zeros(N, dtype=float)
    psi_center = _psi_at(substrate, center, base_prob, base_theta, config, steps=settle_steps)
    prob = np.square(np.abs(psi_center)).astype(float, copy=False)
    theta = np.angle(psi_center).astype(float, copy=False)
    return LayersState(pQ=prob, theta=theta)


def _run_config(max_fs: float, target_index: int) -> RunConfig:
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
        readout={
            "final": True,
            "memory_form": "uniform_charge",
            "params": {
                "mode": "one_hot",
                "target": int(target_index),
                "pQ_source": "probability",
            },
        },
        noise={},
        fs_step_guard={"threshold": float(max_fs), "fraction": 0.25, "window": 32, "action": "warn"},
    )


def _rectangle_path(
    center: Mapping[str, float],
    extents: Mapping[str, float],
    axes: tuple[str, str],
    steps: int,
) -> ParameterPath:
    return ParameterPath(
        kind="rectangle",
        center={axis: float(center[axis]) for axis in axes},
        extents={axis: float(extents[axis]) for axis in axes},
        steps=max(int(steps), 4),
        orientation="CCW",
        axes=axes,
    )


def _control_polygon_path(
    center: Mapping[str, float],
    axes: tuple[str, str],
    steps: int,
    control_points: Sequence[Sequence[float]],
    orientation: str,
) -> ParameterPath:
    if len(axes) != 2:
        raise ValueError("control polygon requires exactly two axes")
    axis_i, axis_j = axes
    steps = max(int(steps), 4)
    if steps < len(control_points):
        raise ValueError("step budget too small for number of control points")

    orientation_key = orientation.upper()
    if orientation_key not in {"CW", "CCW"}:
        raise ValueError("orientation must be either CW or CCW")

    # Instantiate a dummy path to leverage bookkeeping from ParameterPath.
    dummy = ParameterPath(
        kind="line",
        center={axis_i: float(center[axis_i]), axis_j: float(center[axis_j])},
        extents={axis_i: 0.0, axis_j: 0.0},
        steps=steps,
        orientation=orientation_key,
        axes=axes,
    )

    center_vec = np.array([float(center[axis_i]), float(center[axis_j])], dtype=float)
    points = [np.array(point, dtype=float) for point in control_points]
    if len(points) < 3:
        raise ValueError("control polygon must contain at least three vertices")

    if orientation_key == "CW":
        points = list(reversed(points))

    points_cycle = points + [points[0]]
    segment_steps = ParameterPath._split_steps(steps, len(points))

    positions: list[np.ndarray] = []
    for idx, count in enumerate(segment_steps):
        start = center_vec + points_cycle[idx]
        end = center_vec + points_cycle[idx + 1]
        for step in range(count):
            t = 0.0 if count == 0 else step / count
            pos = (1.0 - t) * start + t * end
            positions.append(pos)
    if len(positions) != steps:
        raise RuntimeError("failed to tile positions across steps")

    lambda_steps: list[dict[str, float]] = []
    delta_steps: list[dict[str, float]] = []
    area_steps: list[float] = []

    for step in range(steps):
        pos = positions[step]
        nxt = positions[(step + 1) % steps]
        lambda_steps.append({axis_i: float(pos[0]), axis_j: float(pos[1])})
        delta_steps.append({axis_i: float(nxt[0] - pos[0]), axis_j: float(nxt[1] - pos[1])})
        area_steps.append(0.5 * float(pos[0] * nxt[1] - nxt[0] * pos[1]))

    dummy._lambdas = lambda_steps  # type: ignore[attr-defined]
    dummy._deltas = delta_steps  # type: ignore[attr-defined]
    dummy._areas = area_steps  # type: ignore[attr-defined]
    return dummy


def _path_length(deltas: Iterable[Mapping[str, float]], axes: tuple[str, str]) -> float:
    axis_i, axis_j = axes
    total = 0.0
    for delta in deltas:
        dx = float(delta.get(axis_i, 0.0))
        dy = float(delta.get(axis_j, 0.0))
        total += math.hypot(dx, dy)
    return total


def _phi_flux(record_steps: int, readouts: Sequence[Mapping[str, float]]) -> float:
    for entry in readouts:
        if not isinstance(entry, Mapping):
            continue
        if int(entry.get("step", -1)) != record_steps:
            continue
        try:
            return float(entry.get("phi_flux", 0.0))
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _evaluate_path(
    substrate: GraphSubstrate,
    base_state: LayersState,
    config: RunConfig,
    path: ParameterPath,
    *,
    lambda_penalty: float,
    mu_penalty: float,
    baseline_length: float,
    control_points: Sequence[Sequence[float]] | None = None,
) -> PathEvaluation:
    record = run_parameter_loop(
        substrate,
        LayersState(pQ=base_state.pQ.copy(), theta=base_state.theta.copy()),
        path,
        config,
        seed=0,
    )
    phi_flux = _phi_flux(path.steps, record.readouts)
    guard_meta = record.meta.get("fs_step_guard", {}) if isinstance(record.meta, Mapping) else {}
    guard_fraction = float(guard_meta.get("overall_fraction", 0.0)) if guard_meta else 0.0
    length = _path_length(record.delta_lambda, path.axes)
    if baseline_length <= 0.0:
        length_overrun = 0.0
    else:
        length_overrun = max(0.0, (length / baseline_length) - 1.0)
    objective = -abs(phi_flux) + lambda_penalty * guard_fraction + mu_penalty * length_overrun
    if control_points is None:
        points = tuple(
            (
                float(path._lambdas[idx][path.axes[0]] - path._center[path.axes[0]]),  # type: ignore[attr-defined]
                float(path._lambdas[idx][path.axes[1]] - path._center[path.axes[1]]),  # type: ignore[attr-defined]
            )
            for idx in range(min(len(path._lambdas), 4))  # type: ignore[attr-defined]
        )
    else:
        points = tuple((float(pt[0]), float(pt[1])) for pt in control_points)

    return PathEvaluation(
        control_points=points,
        phi_flux=float(phi_flux),
        guard_fraction=guard_fraction,
        path_length=length,
        objective=float(objective),
    )


def _optimise_control_points(
    substrate: GraphSubstrate,
    base_state: LayersState,
    config: RunConfig,
    axes: tuple[str, str],
    center: Mapping[str, float],
    steps: int,
    initial_points: Sequence[Sequence[float]],
    bounds: Sequence[tuple[float, float]],
    *,
    lambda_penalty: float,
    mu_penalty: float,
    baseline_length: float,
    max_rounds: int = 5,
    tol: float = 1e-4,
) -> PathEvaluation:
    cache: dict[tuple[tuple[float, float], ...], PathEvaluation] = {}

    def evaluate(points: Sequence[Sequence[float]]) -> PathEvaluation:
        key = tuple((float(pt[0]), float(pt[1])) for pt in points)
        if key in cache:
            return cache[key]
        path = _control_polygon_path(center, axes, steps, points, "CCW")
        result = _evaluate_path(
            substrate,
            base_state,
            config,
            path,
            lambda_penalty=lambda_penalty,
            mu_penalty=mu_penalty,
            baseline_length=baseline_length,
            control_points=points,
        )
        cache[key] = result
        return result

    best = evaluate(initial_points)
    step_sizes = [0.2 * (upper - lower) for lower, upper in bounds]

    for _ in range(max_rounds):
        improved = False
        for idx in range(len(initial_points)):
            for axis_idx in range(2):
                for direction in (-1.0, 1.0):
                    current = [list(pt) for pt in initial_points]
                    current[idx][axis_idx] += direction * step_sizes[axis_idx]
                    lower, upper = bounds[axis_idx]
                    current[idx][axis_idx] = float(np.clip(current[idx][axis_idx], lower, upper))
                    result = evaluate(current)
                    if result.objective + tol < best.objective:
                        best = result
                        improved = True
                        initial_points = current
        if not improved:
            step_sizes = [size * 0.5 for size in step_sizes]
            if all(size < 1e-3 * (upper - lower) for size, (lower, upper) in zip(step_sizes, bounds)):
                break
    return best


def main() -> None:
    parser = argparse.ArgumentParser(description="Inverse design for enhanced R readout.")
    parser.add_argument("--axes", nargs=2, default=("tau", "zeta"), metavar=("AXIS_I", "AXIS_J"))
    parser.add_argument("--budget-steps", type=int, default=200, help="Step budget shared across all paths")
    parser.add_argument("--max-fs", type=float, default=0.1, help="Maximum FS step before penalty")
    parser.add_argument("--center", nargs=2, type=float, default=(0.24, 0.0), metavar=("TAU", "ZETA"))
    parser.add_argument("--extent", nargs=2, type=float, default=(0.05, 0.04), metavar=("TAU", "ZETA"))
    parser.add_argument("--target-index", type=int, default=0, help="One-hot memory target index")
    args = parser.parse_args()

    axes = (str(args.axes[0]), str(args.axes[1]))
    center = {axes[0]: float(args.center[0]), axes[1]: float(args.center[1])}
    extents = {axes[0]: float(abs(args.extent[0])), axes[1]: float(abs(args.extent[1]))}
    steps = max(int(args.budget_steps), 4)

    substrate = _build_substrate()
    config = _run_config(args.max_fs, args.target_index)
    base_state = _initial_state(substrate, center, config, settle_steps=60)

    rectangle_path = _rectangle_path(center, extents, axes, steps)
    rectangle_result = _evaluate_path(
        substrate,
        base_state,
        config,
        rectangle_path,
        lambda_penalty=10.0,
        mu_penalty=5.0,
        baseline_length=1.0,
    )
    baseline_length = rectangle_result.path_length

    print("Baseline rectangle:")
    print(
        "  |R|={:.6f}  guard_fraction={:.3f}  length={:.4f}".format(
            abs(rectangle_result.R_value), rectangle_result.guard_fraction, rectangle_result.path_length
        )
    )

    initial_points = [
        (-extents[axes[0]], -extents[axes[1]]),
        (extents[axes[0]], -extents[axes[1]]),
        (extents[axes[0]], extents[axes[1]]),
        (-extents[axes[0]], extents[axes[1]]),
    ]
    bounds = [(-extents[axes[0]], extents[axes[0]]), (-extents[axes[1]], extents[axes[1]])]

    best_result = _optimise_control_points(
        substrate,
        base_state,
        config,
        axes,
        center,
        steps,
        initial_points,
        bounds,
        lambda_penalty=10.0,
        mu_penalty=5.0,
        baseline_length=baseline_length,
    )

    improvement = (
        abs(best_result.R_value) / max(abs(rectangle_result.R_value), 1e-12)
        if rectangle_result.R_value
        else float("inf")
    )

    print("Optimised control polygon:")
    print("  control points:")
    for idx, point in enumerate(best_result.control_points):
        print(f"    v{idx + 1}: Δ{axes[0]}={point[0]:+.5f}, Δ{axes[1]}={point[1]:+.5f}")
    print(
        "  |R|={:.6f}  guard_fraction={:.3f}  length={:.4f}  improvement={:.3f}x".format(
            abs(best_result.R_value), best_result.guard_fraction, best_result.path_length, improvement
        )
    )

    if improvement >= 1.15 and best_result.guard_fraction <= rectangle_result.guard_fraction + 1e-6:
        print("Acceptance criterion met: |R| improved by ≥15% without worsening FS guard.")
    else:
        print("Warning: acceptance criterion not satisfied; consider adjusting bounds or budget.")


if __name__ == "__main__":
    main()

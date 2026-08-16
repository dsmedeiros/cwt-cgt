"""Loop conventions, centered response sums, and convergence diagnostics."""

from __future__ import annotations

import numpy as np

from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.open_system import apply_local_open_step, fixed_point_density, observable_operator

from .adapter import (
    affine_population_components,
    core_config,
    mean_position_operator,
    theorem_d0_state,
)
from .contract import MODEL_CONTRACT
from .fixed_branch import fixed_branch_bundle, response_one_form


def square_loop(center: tuple[float, float], side: float, steps_per_edge: int) -> np.ndarray:
    """Store one CCW square with a duplicated close and no duplicated joins."""

    if steps_per_edge < 1:
        raise ValueError("steps_per_edge must be positive")
    center_array = np.asarray(center, dtype=float)
    half = 0.5 * side
    corners = (
        center_array + (-half, -half),
        center_array + (half, -half),
        center_array + (half, half),
        center_array + (-half, half),
        center_array + (-half, -half),
    )
    segments = []
    for index, (start, stop) in enumerate(zip(corners[:-1], corners[1:])):
        segment = np.linspace(start, stop, steps_per_edge + 1)
        segments.append(segment if index == 0 else segment[1:])
    path = np.vstack(segments)
    if not np.array_equal(path[0], path[-1]):
        raise AssertionError("stored loop must close exactly")
    return path


def reverse_loop(ccw: np.ndarray) -> np.ndarray:
    """Return the exact stored-sequence reverse, not a regenerated path."""

    reverse = np.asarray(ccw, dtype=float)[::-1].copy()
    if not np.array_equal(reverse, ccw[::-1]):
        raise AssertionError("CW path is not the exact stored reverse")
    return reverse


def d0_path_is_within_contract(path: np.ndarray) -> bool:
    """Return whether every D0 loop point lies in the certified closed box."""

    points = np.asarray(path, dtype=float)
    box = MODEL_CONTRACT.box
    # The side=.04 registered square lands analytically on b=.01 and b=.05;
    # admit only the floating representation error of those exact endpoints.
    tolerance = 32.0 * np.finfo(float).eps
    return bool(
        np.all(points[:, 0] >= float(box.bias_min) - tolerance)
        and np.all(points[:, 0] <= float(box.bias_max) + tolerance)
        and np.all(points[:, 1] >= float(box.diffusion_min) - tolerance)
        and np.all(points[:, 1] <= float(box.diffusion_max) + tolerance)
    )


def require_d0_path_within_contract(path: np.ndarray) -> None:
    """Fail before dynamics if a D0 loop leaves the certified theorem domain."""

    if not d0_path_is_within_contract(path):
        raise ValueError("D0 loop leaves the certified control box")


def _core_readout_vector() -> np.ndarray:
    operator = mean_position_operator()
    return np.diag(operator).real.copy()


def _batched_affine_path(path: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    """Vectorize affine matrices and certified fixed populations along a D0 path."""

    path = np.asarray(path, dtype=float)
    bias = path[:, 0]
    diffusion = path[:, 1]
    k_plus = diffusion + bias
    k_minus = diffusion - bias
    jump = float(MODEL_CONTRACT.jump_probability_scale)
    contraction = float(MODEL_CONTRACT.contraction_factor)
    transitions = np.zeros((len(path), 5, 5), dtype=float)
    transitions[:, 0, 0] = 1.0 - jump * k_plus
    transitions[:, 0, 1] = jump * k_plus
    for node in range(1, 4):
        transitions[:, node, node - 1] = jump * k_minus
        transitions[:, node, node + 1] = jump * k_plus
        transitions[:, node, node] = 1.0 - jump * (k_plus + k_minus)
    transitions[:, 4, 3] = jump * k_minus
    transitions[:, 4, 4] = 1.0 - jump * k_minus
    matrices = contraction * np.transpose(transitions, (0, 2, 1))
    offsets = np.full((len(path), 5, 1), float(MODEL_CONTRACT.depolarizing_floor))
    fixed = np.linalg.solve(np.eye(5)[None, :, :] - matrices, offsets)[..., 0]
    residuals = np.einsum("nij,nj->ni", matrices, fixed) + offsets[..., 0] - fixed
    max_residual_l1 = float(np.max(np.sum(np.abs(residuals), axis=1)))
    return matrices, fixed, max_residual_l1


def cycle_sum_diagnostics(
    path: np.ndarray,
    readout: np.ndarray | None = None,
    *,
    constant_branch: bool = False,
) -> dict[str, float]:
    """Return Q plus the fixed-solver residual used in its centering budget."""

    path = np.asarray(path, dtype=float)
    require_d0_path_within_contract(path)
    if readout is None:
        readout = _core_readout_vector()
    readout = np.asarray(readout, dtype=float)
    if constant_branch:
        matrix, offset = affine_population_components(
            float(MODEL_CONTRACT.center_bias),
            float(MODEL_CONTRACT.center_diffusion),
        )
        fixed_population = fixed_branch_bundle(
            float(MODEL_CONTRACT.center_bias),
            float(MODEL_CONTRACT.center_diffusion),
        ).population
        matrices = np.repeat(matrix[None, :, :], len(path), axis=0)
        fixed = np.repeat(fixed_population[None, :], len(path), axis=0)
        offsets = np.repeat(offset[None, :], len(path), axis=0)
        residual = matrix @ fixed_population + offset - fixed_population
        max_fixed_residual_l1 = float(np.linalg.norm(residual, ord=1))
    else:
        matrices, fixed, max_fixed_residual_l1 = _batched_affine_path(path)
        offsets = np.full_like(fixed, float(MODEL_CONTRACT.depolarizing_floor))
    population = fixed[0].copy()
    total = 0.0
    # The duplicate initial point is not sampled; the closing endpoint is updated/sampled once.
    for index in range(1, len(path)):
        population = matrices[index] @ population + offsets[index]
        total += float(readout @ (population - fixed[index]))
    return {"q": total, "max_fixed_residual_l1": max_fixed_residual_l1}


def cycle_sum(
    path: np.ndarray,
    readout: np.ndarray | None = None,
    *,
    constant_branch: bool = False,
) -> float:
    """Right-endpoint update-then-sample centered cycle sum ``Q``."""

    return cycle_sum_diagnostics(path, readout, constant_branch=constant_branch)["q"]


def orientation_pair(
    side: float,
    steps_per_edge: int,
    readout: np.ndarray | None = None,
    *,
    constant_branch: bool = False,
) -> dict[str, float]:
    """Return CCW, exact-reverse CW, odd half-difference, and even contamination."""

    center = (float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion))
    ccw = square_loop(center, side, steps_per_edge)
    cw = reverse_loop(ccw)
    ccw_result = cycle_sum_diagnostics(ccw, readout, constant_branch=constant_branch)
    cw_result = cycle_sum_diagnostics(cw, readout, constant_branch=constant_branch)
    q_ccw = ccw_result["q"]
    q_cw = cw_result["q"]
    return {
        "q_ccw": q_ccw,
        "q_cw": q_cw,
        "q_anti": 0.5 * (q_ccw - q_cw),
        "q_even": 0.5 * (q_ccw + q_cw),
        "updates_per_cycle": float(4 * steps_per_edge),
        "max_fixed_residual_l1": max(
            ccw_result["max_fixed_residual_l1"],
            cw_result["max_fixed_residual_l1"],
        ),
    }


def core_cycle_sum(path: np.ndarray) -> float:
    """Run the identical centered cycle through ``apply_local_open_step`` itself."""

    config = core_config()
    require_d0_path_within_contract(path)
    readout = _core_readout_vector()
    fixed = [fixed_branch_bundle(float(point[0]), float(point[1])).population for point in path]
    rho = np.diag(fixed[0]).astype(complex)
    total = 0.0
    for index in range(1, len(path)):
        state = theorem_d0_state(float(path[index, 0]), float(path[index, 1]))
        rho = apply_local_open_step(rho, state, config, float(MODEL_CONTRACT.dephasing))
        total += float(np.real(np.trace(np.diag(readout) @ (rho - np.diag(fixed[index])))))
    return total


def line_integral_square(side: float, quadrature_order: int = 96) -> float:
    """High-order Gauss-Legendre integral of ``B`` around the square."""

    center = np.asarray(
        (float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion)),
        dtype=float,
    )
    half = 0.5 * side
    corners = (
        center + (-half, -half),
        center + (half, -half),
        center + (half, half),
        center + (-half, half),
        center + (-half, -half),
    )
    nodes, weights = np.polynomial.legendre.leggauss(quadrature_order)
    total = 0.0
    for start, stop in zip(corners[:-1], corners[1:]):
        midpoint = 0.5 * (start + stop)
        tangent = 0.5 * (stop - start)
        for node, weight in zip(nodes, weights):
            point = midpoint + node * tangent
            total += float(weight * (response_one_form(float(point[0]), float(point[1])) @ tangent))
    return total


def fixed_loop_refinement() -> dict[str, object]:
    """Demonstrate the generic fixed-loop ``O(1/N)`` endpoint transient."""

    side = 0.04
    steps_per_edge = (1024, 2048, 4096, 8192, 16384)
    target = line_integral_square(side)
    rows = []
    for steps in steps_per_edge:
        pair = orientation_pair(side, steps)
        updates = 4 * steps
        error = pair["q_anti"] - target
        rows.append(
            {
                "steps_per_edge": steps,
                "updates": updates,
                **pair,
                "line_integral_target": target,
                "signed_error": error,
                "absolute_error": abs(error),
                "updates_times_signed_error": updates * error,
            }
        )
    logs_n = np.log([row["updates"] for row in rows[-4:]])
    logs_error = np.log([row["absolute_error"] for row in rows[-4:]])
    slope = float(np.polyfit(logs_n, logs_error, 1)[0])
    tail_scaled = np.abs([row["updates_times_signed_error"] for row in rows[-3:]])
    return {
        "side": side,
        "line_integral_target": target,
        "rows": rows,
        "tail_log_slope": slope,
        "tail_scaled_error_ratio": float(np.max(tail_scaled) / np.min(tail_scaled)),
    }


def shrinking_loop_refinement() -> dict[str, object]:
    """Demonstrate ``Q_anti/s^2 -> F_bd`` while ``N*s`` grows."""

    ladder = ((0.04, 2048), (0.02, 8192), (0.01, 32768), (0.005, 131072))
    from .exact_oracle import exact_response_oracle

    curvature = float(exact_response_oracle().response_curvature_bd)
    rows = []
    for side, steps in ladder:
        pair = orientation_pair(side, steps)
        density = pair["q_anti"] / side**2
        error = abs(density - curvature)
        fixed_error_bound = pair["max_fixed_residual_l1"] / (1.0 - float(MODEL_CONTRACT.contraction_factor))
        centering_density_budget = (
            2.0
            * float(np.max(np.abs(_core_readout_vector())))
            * pair["updates_per_cycle"]
            * fixed_error_bound
            / side**2
        )
        rows.append(
            {
                "side": side,
                "steps_per_edge": steps,
                "updates": 4 * steps,
                "updates_times_side": 4 * steps * side,
                **pair,
                "response_density": density,
                "curvature_target": curvature,
                "absolute_density_error": error,
                "relative_density_error": error / abs(curvature),
                "fixed_branch_error_bound_l1": fixed_error_bound,
                "centering_density_error_budget": centering_density_budget,
                "centering_budget_to_observed_density_error": centering_density_budget / error,
            }
        )
    error_ratios = [
        rows[index + 1]["absolute_density_error"] / rows[index]["absolute_density_error"]
        for index in range(len(rows) - 1)
    ]
    return {
        "required_limit": "updates_times_side_to_infinity",
        "rows": rows,
        "successive_error_ratios": error_ratios,
        "finest_relative_density_error": rows[-1]["relative_density_error"],
        "max_centering_budget_to_observed_density_error": max(
            row["centering_budget_to_observed_density_error"] for row in rows
        ),
        "centering_budget_formula": "2*||H||_infinity*N*e_fixed/s^2",
        "numerical_tolerances_selected_during_harness_development": True,
    }


def core_cycle_equivalence() -> dict[str, float]:
    """Cross-check a complete oriented trace against the actual core step."""

    path = square_loop(
        (float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion)),
        0.02,
        16,
    )
    affine = cycle_sum(path)
    core = core_cycle_sum(path)
    return {"affine_q": affine, "core_q": core, "absolute_error": abs(affine - core)}


def loop_domain_diagnostics() -> dict[str, object]:
    """Prove every registered D0 loop is contained in the certified box."""

    center = (float(MODEL_CONTRACT.center_bias), float(MODEL_CONTRACT.center_diffusion))
    specifications = (
        ("fixed_loop", 0.04, 16384),
        ("core_equivalence", 0.02, 16),
        ("null_controls", 0.04, 64),
        ("shrinking_1", 0.04, 2048),
        ("shrinking_2", 0.02, 8192),
        ("shrinking_3", 0.01, 32768),
        ("shrinking_4", 0.005, 131072),
    )
    rows = []
    for name, side, steps in specifications:
        path = square_loop(center, side, steps)
        rows.append(
            {
                "name": name,
                "side": side,
                "steps_per_edge": steps,
                "minimum_bias": float(np.min(path[:, 0])),
                "maximum_bias": float(np.max(path[:, 0])),
                "minimum_diffusion": float(np.min(path[:, 1])),
                "maximum_diffusion": float(np.max(path[:, 1])),
                "contained": d0_path_is_within_contract(path),
            }
        )
    return {"all_registered_loops_contained": all(row["contained"] for row in rows), "rows": rows}


def null_control_diagnostics() -> dict[str, object]:
    """Compute identity-readout, constant-branch, and Benchmark C true-fixed nulls."""

    identity_pair = orientation_pair(0.04, 64, np.ones(5))
    constant_pair = orientation_pair(0.04, 64, constant_branch=True)

    benchmark_c = get_benchmark("benchmark_c")
    config = core_config()
    path_c = square_loop((0.0, 0.0), 0.10, 16)
    fixed_c = np.eye(3, dtype=complex) / 3.0
    primary_c = None
    max_kernel_column_error = 0.0
    max_fixed_error = 0.0
    q_c = 0.0
    rho_c = fixed_c.copy()
    for index, point in enumerate(path_c):
        candidate = benchmark_c.resolve_candidate_by_id(float(point[0]), float(point[1]), "C0")
        if candidate is None:
            raise AssertionError("Benchmark C C0 disappeared on the null-control patch")
        state = candidate.state
        max_kernel_column_error = max(
            max_kernel_column_error,
            float(np.max(np.abs(np.sum(state.kernel, axis=0) - 1.0))),
        )
        if primary_c is None:
            primary_c = observable_operator(benchmark_c, state, benchmark_c.primary_observable)
        true_fixed = fixed_point_density(state, config, float(MODEL_CONTRACT.dephasing))
        max_fixed_error = max(max_fixed_error, float(np.linalg.norm(true_fixed - fixed_c, ord="fro")))
        if index == 0:
            continue
        rho_c = apply_local_open_step(rho_c, state, config, float(MODEL_CONTRACT.dephasing))
        q_c += float(np.real(np.trace(primary_c @ (rho_c - fixed_c))))
    return {
        "identity_readout": identity_pair,
        "constant_branch": constant_pair,
        "benchmark_c": {
            "branch_id": "C0",
            "max_kernel_column_error": max_kernel_column_error,
            "max_true_fixed_to_identity_over_three_fro": max_fixed_error,
            "centered_primary_cycle_sum": q_c,
        },
    }

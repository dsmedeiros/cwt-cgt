"""Deterministic analytic/executable theorem harness for benchmark C."""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Any

import numpy as np

from cwt.cgt._geom_compat import berry_loop_flux, polygon_signed_area, psi_from_state
from cwt.cgt.benchmarks import get_benchmark
from cwt.cgt.continuation import continue_path_with_branch_ids
from cwt.cgt.loop_protocols import build_loop_path
from cwt.cgt.models import LoopConfig
from experiments.independent_response_theorem.response import (
    ResponseTrace,
    calculate_response_trace,
    circulation_phase_gradient,
)

BENCHMARK_ID = "benchmark_c"
CANONICAL_BRANCH_ID = "C0"
CURRENT_TICK_DT = 1.0


@dataclass(frozen=True)
class ExperimentConfig:
    """Locked deterministic configuration for the discovery/analytic fixture."""

    phase_relaxation: float = 0.35
    current_phase_gain: float = 0.45
    refinement_center: tuple[float, float] = (0.18, 0.0)
    refinement_side: float = 0.08
    refinement_steps: tuple[int, ...] = (48, 96, 192, 384)
    derivative_center: tuple[float, float] = (0.0, 0.0)
    derivative_steps: tuple[float, ...] = (0.004, 0.002, 0.001, 0.0005)
    area_center: tuple[float, float] = (0.0, 0.0)
    area_sides: tuple[float, ...] = (0.16, 0.08, 0.04, 0.02)
    area_step_scale: float = 0.96
    quotient_centers: tuple[tuple[float, float], ...] = (
        (0.0, 0.0),
        (0.18, 0.0),
        (0.0, 0.18),
        (-0.18, 0.10),
    )
    quotient_side: float = 0.02
    quotient_steps_per_segment: int = 2400
    cyclic_center: tuple[float, float] = (0.18, 0.0)
    cyclic_side: float = 0.08
    cyclic_steps: tuple[int, ...] = (96, 192, 384, 768)
    cyclic_start_fractions: tuple[float, ...] = (0.0, 0.25, 0.5, 0.75)
    null_center: tuple[float, float] = (0.0, 0.0)
    null_side: float = 0.08
    null_steps_per_segment: int = 96

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


@dataclass(frozen=True)
class LoopEvaluation:
    """Response and separately computed predictors for one oriented loop."""

    center: tuple[float, float]
    side: float
    steps_per_segment: int
    orientation: str
    start_fraction: float
    response: ResponseTrace
    signed_area: float
    signed_flux: float
    tangent_line_integral: float
    switch_count: int
    ambiguous_step_count: int
    unique_branch_ids: tuple[str, ...]
    endpoint_duplicated: bool


@dataclass(frozen=True)
class OrientationPair:
    """CCW/CW half-differences for one geometric loop."""

    ccw: LoopEvaluation
    cw: LoopEvaluation

    @property
    def discrete_cycle_sum_surrogate_anti(self) -> float:
        return 0.5 * (
            self.ccw.response.discrete_cycle_sum_surrogate - self.cw.response.discrete_cycle_sum_surrogate
        )

    @property
    def discrete_cycle_sum_surrogate_even(self) -> float:
        return 0.5 * (
            self.ccw.response.discrete_cycle_sum_surrogate + self.cw.response.discrete_cycle_sum_surrogate
        )

    @property
    def legacy_mean_response_anti(self) -> float:
        return 0.5 * (self.ccw.response.legacy_mean_response - self.cw.response.legacy_mean_response)

    @property
    def signed_area_anti(self) -> float:
        return 0.5 * (self.ccw.signed_area - self.cw.signed_area)

    @property
    def signed_flux_anti(self) -> float:
        return 0.5 * (self.ccw.signed_flux - self.cw.signed_flux)

    @property
    def tangent_line_integral_anti(self) -> float:
        return 0.5 * (self.ccw.tangent_line_integral - self.cw.tangent_line_integral)


DEFAULT_CONFIG = ExperimentConfig()


def _benchmark_c_state(u: float, v: float):
    benchmark = get_benchmark(BENCHMARK_ID)
    candidate = benchmark.resolve_candidate_by_id(float(u), float(v), CANONICAL_BRANCH_ID)
    if candidate is None:
        raise RuntimeError(f"{CANONICAL_BRANCH_ID} is unavailable at ({u}, {v})")
    return candidate.state


def benchmark_c_phase_tangent(u: float, v: float) -> np.ndarray:
    """Return exact columns (partial_u theta, partial_v theta) for branch C0."""

    dphi_du = 0.15 + 0.45 * float(v)
    dphi_dv = 0.70 + 0.45 * float(u)
    return np.asarray(
        [
            [dphi_du, dphi_dv],
            [0.0, 0.0],
            [-dphi_du, -dphi_dv],
        ],
        dtype=float,
    )


def tangent_one_form(
    u: float,
    v: float,
    phase_relaxation: float,
    current_phase_gain: float,
) -> np.ndarray:
    """Evaluate B_i=-(1-alpha)/alpha grad_theta(C) dot partial_i(theta)."""

    alpha = float(phase_relaxation)
    if not 0.0 < alpha <= 1.0:
        raise ValueError("phase_relaxation must lie in (0, 1]")
    state = _benchmark_c_state(u, v)
    gradient = circulation_phase_gradient(
        state.p,
        state.theta,
        state.kernel,
        current_phase_gain,
    )
    phase_tangent = benchmark_c_phase_tangent(u, v)
    return -(1.0 - alpha) / alpha * (gradient @ phase_tangent)


def response_curvature(
    center: tuple[float, float],
    derivative_step: float,
    phase_relaxation: float,
    current_phase_gain: float,
) -> float:
    """Compute F_R=partial_u B_v-partial_v B_u by central differences."""

    u, v = center
    h = float(derivative_step)
    if h <= 0.0:
        raise ValueError("derivative_step must be positive")
    d_bv_du = (
        tangent_one_form(u + h, v, phase_relaxation, current_phase_gain)[1]
        - tangent_one_form(u - h, v, phase_relaxation, current_phase_gain)[1]
    ) / (2.0 * h)
    d_bu_dv = (
        tangent_one_form(u, v + h, phase_relaxation, current_phase_gain)[0]
        - tangent_one_form(u, v - h, phase_relaxation, current_phase_gain)[0]
    ) / (2.0 * h)
    return float(d_bv_du - d_bu_dv)


def projective_curvature(center: tuple[float, float], derivative_step: float) -> float:
    """Compute Omega=2 Im<C_u|C_v> from independent projective derivatives."""

    u, v = center
    h = float(derivative_step)
    if h <= 0.0:
        raise ValueError("derivative_step must be positive")
    psi0 = psi_from_state(_benchmark_c_state(u, v))
    dpsi_u = (psi_from_state(_benchmark_c_state(u + h, v)) - psi_from_state(_benchmark_c_state(u - h, v))) / (
        2.0 * h
    )
    dpsi_v = (psi_from_state(_benchmark_c_state(u, v + h)) - psi_from_state(_benchmark_c_state(u, v - h))) / (
        2.0 * h
    )
    projective_u = dpsi_u - psi0 * np.vdot(psi0, dpsi_u)
    projective_v = dpsi_v - psi0 * np.vdot(psi0, dpsi_v)
    return float(2.0 * np.imag(np.vdot(projective_u, projective_v)))


def _rotate_closed_path(path: list[tuple[float, float]], start_fraction: float) -> list[tuple[float, float]]:
    if len(path) < 2 or path[0] != path[-1]:
        raise ValueError("path must be explicitly closed before cyclic rotation")
    open_path = path[:-1]
    offset = int(round(float(start_fraction) * len(open_path))) % len(open_path)
    rotated = open_path[offset:] + open_path[:offset]
    return rotated + [rotated[0]]


def _loop_fixture(
    center: tuple[float, float],
    side: float,
    steps_per_segment: int,
    orientation: str,
    phase_relaxation: float,
    current_phase_gain: float,
    start_fraction: float,
) -> tuple[list[tuple[float, float]], list[Any], dict[str, Any]]:
    path = build_loop_path(
        center=center,
        side=float(side),
        orientation=orientation,
        shape="square",
        steps_per_segment=int(steps_per_segment),
    )
    if start_fraction:
        path = _rotate_closed_path(path, start_fraction)
    config = LoopConfig(
        shape="square",
        steps_per_segment=int(steps_per_segment),
        phase_relaxation=float(phase_relaxation),
        current_phase_gain=float(current_phase_gain),
    )
    continuation = continue_path_with_branch_ids(
        benchmark=get_benchmark(BENCHMARK_ID),
        path=path,
        config=config,
    )
    return path, continuation["states"], continuation


def tangent_line_integral(
    path: list[tuple[float, float]],
    phase_relaxation: float,
    current_phase_gain: float,
) -> float:
    """Trapezoid-evaluate the response one-form along an explicitly closed path."""

    total = 0.0
    for start, stop in zip(path[:-1], path[1:]):
        b_start = tangent_one_form(*start, phase_relaxation, current_phase_gain)
        b_stop = tangent_one_form(*stop, phase_relaxation, current_phase_gain)
        delta = np.asarray(stop, dtype=float) - np.asarray(start, dtype=float)
        total += float(0.5 * (b_start + b_stop) @ delta)
    return total


def evaluate_loop(
    center: tuple[float, float],
    side: float,
    steps_per_segment: int,
    orientation: str,
    phase_relaxation: float,
    current_phase_gain: float,
    start_fraction: float = 0.0,
) -> LoopEvaluation:
    """Evaluate response first, then compute geometric predictors separately."""

    path, states, continuation = _loop_fixture(
        center=center,
        side=side,
        steps_per_segment=steps_per_segment,
        orientation=orientation,
        phase_relaxation=phase_relaxation,
        current_phase_gain=current_phase_gain,
        start_fraction=start_fraction,
    )

    response = calculate_response_trace(
        branch_states=states,
        path=path,
        phase_relaxation=phase_relaxation,
        current_phase_gain=current_phase_gain,
    )

    # Predictor/geometry calculations are intentionally downstream of response.
    signed_area = polygon_signed_area(path)
    signed_flux = berry_loop_flux(states)
    line_integral = tangent_line_integral(path, phase_relaxation, current_phase_gain)
    endpoint_duplicated = bool(np.array_equal(np.asarray(path[0]), np.asarray(path[-1])))
    return LoopEvaluation(
        center=center,
        side=float(side),
        steps_per_segment=int(steps_per_segment),
        orientation=orientation,
        start_fraction=float(start_fraction),
        response=response,
        signed_area=float(signed_area),
        signed_flux=float(signed_flux),
        tangent_line_integral=float(line_integral),
        switch_count=int(continuation["switch_count"]),
        ambiguous_step_count=int(continuation["ambiguous_step_count"]),
        unique_branch_ids=tuple(continuation["unique_branch_ids"]),
        endpoint_duplicated=endpoint_duplicated,
    )


def evaluate_pair(
    center: tuple[float, float],
    side: float,
    steps_per_segment: int,
    phase_relaxation: float,
    current_phase_gain: float,
    start_fraction: float = 0.0,
) -> OrientationPair:
    """Evaluate the two orientations without passing their labels to response code."""

    kwargs = {
        "center": center,
        "side": side,
        "steps_per_segment": steps_per_segment,
        "phase_relaxation": phase_relaxation,
        "current_phase_gain": current_phase_gain,
        "start_fraction": start_fraction,
    }
    return OrientationPair(
        ccw=evaluate_loop(orientation="ccw", **kwargs),
        cw=evaluate_loop(orientation="cw", **kwargs),
    )


def _log_slope(x_values: list[float], y_values: list[float]) -> float:
    x_arr = np.asarray(x_values, dtype=float)
    y_arr = np.asarray(y_values, dtype=float)
    mask = np.isfinite(x_arr) & np.isfinite(y_arr) & (x_arr > 0.0) & (y_arr > 0.0)
    if int(np.sum(mask)) < 2:
        return math.nan
    return float(np.polyfit(np.log(x_arr[mask]), np.log(y_arr[mask]), 1)[0])


def _relative_error(observed: float, expected: float) -> float:
    if not math.isfinite(observed) or not math.isfinite(expected) or abs(expected) <= 1e-15:
        return math.nan
    return float(abs(observed - expected) / abs(expected))


def _pair_record(record_type: str, pair: OrientationPair, **extra: Any) -> dict[str, Any]:
    q_anti = pair.discrete_cycle_sum_surrogate_anti
    area_anti = pair.signed_area_anti
    flux_anti = pair.signed_flux_anti
    return {
        "record_type": record_type,
        "center": list(pair.ccw.center),
        "side": pair.ccw.side,
        "steps_per_segment": pair.ccw.steps_per_segment,
        "path_length": pair.ccw.response.path_length,
        "start_fraction": pair.ccw.start_fraction,
        "ccw": {
            "discrete_cycle_sum_surrogate": pair.ccw.response.discrete_cycle_sum_surrogate,
            "legacy_mean_response": pair.ccw.response.legacy_mean_response,
            "signed_area": pair.ccw.signed_area,
            "signed_flux": pair.ccw.signed_flux,
            "tangent_line_integral": pair.ccw.tangent_line_integral,
        },
        "cw": {
            "discrete_cycle_sum_surrogate": pair.cw.response.discrete_cycle_sum_surrogate,
            "legacy_mean_response": pair.cw.response.legacy_mean_response,
            "signed_area": pair.cw.signed_area,
            "signed_flux": pair.cw.signed_flux,
            "tangent_line_integral": pair.cw.tangent_line_integral,
        },
        "discrete_cycle_sum_surrogate_anti": q_anti,
        "discrete_cycle_sum_surrogate_even": pair.discrete_cycle_sum_surrogate_even,
        "legacy_mean_response_anti": pair.legacy_mean_response_anti,
        "signed_area_anti": area_anti,
        "signed_flux_anti": flux_anti,
        "tangent_line_integral_anti": pair.tangent_line_integral_anti,
        "response_density": q_anti / area_anti,
        "flux_density": flux_anti / area_anti,
        "observed_response_per_flux": q_anti / flux_anti,
        "max_lag_recurrence_residual": max(
            pair.ccw.response.max_lag_recurrence_residual,
            pair.cw.response.max_lag_recurrence_residual,
        ),
        "max_abs_phase_increment": max(
            pair.ccw.response.max_abs_phase_increment,
            pair.cw.response.max_abs_phase_increment,
        ),
        "max_abs_lag_error": max(
            pair.ccw.response.max_abs_lag_error,
            pair.cw.response.max_abs_lag_error,
        ),
        "switch_count": pair.ccw.switch_count + pair.cw.switch_count,
        "ambiguous_step_count": (pair.ccw.ambiguous_step_count + pair.cw.ambiguous_step_count),
        "endpoint_duplicated": pair.ccw.endpoint_duplicated and pair.cw.endpoint_duplicated,
        **extra,
    }


def _gate(
    name: str,
    passed: bool | None,
    observed: Any,
    requirement: str,
) -> dict[str, Any]:
    status = "indeterminate" if passed is None else ("pass" if passed else "fail")
    return {
        "name": name,
        "status": status,
        "observed": observed,
        "requirement": requirement,
    }


def execute_protocol(
    config: ExperimentConfig = DEFAULT_CONFIG,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Run the locked deterministic checks and return summary plus raw records."""

    records: list[dict[str, Any]] = []
    all_pairs: list[OrientationPair] = []

    response_curvatures: list[float] = []
    projective_curvatures: list[float] = []
    for step in config.derivative_steps:
        f_response = response_curvature(
            config.derivative_center,
            step,
            config.phase_relaxation,
            config.current_phase_gain,
        )
        omega = projective_curvature(config.derivative_center, step)
        response_curvatures.append(f_response)
        projective_curvatures.append(omega)
        records.append(
            {
                "record_type": "central_derivative",
                "center": list(config.derivative_center),
                "derivative_step": step,
                "response_curvature": f_response,
                "projective_curvature": omega,
                "local_two_form_quotient": f_response / omega,
            }
        )

    refinement_records: list[dict[str, Any]] = []
    refinement_pairs: list[OrientationPair] = []
    for steps in config.refinement_steps:
        pair = evaluate_pair(
            center=config.refinement_center,
            side=config.refinement_side,
            steps_per_segment=steps,
            phase_relaxation=config.phase_relaxation,
            current_phase_gain=config.current_phase_gain,
        )
        refinement_pairs.append(pair)
        all_pairs.append(pair)
        record = _pair_record(
            "fixed_side_tick_refinement",
            pair,
            absolute_tangent_remainder=abs(
                pair.discrete_cycle_sum_surrogate_anti - pair.tangent_line_integral_anti
            ),
        )
        refinement_records.append(record)
        records.append(record)

    area_records: list[dict[str, Any]] = []
    area_pairs: list[OrientationPair] = []
    f_center = response_curvatures[-1]
    omega_center = projective_curvatures[-1]
    local_quotient_center = f_center / omega_center
    for side in config.area_sides:
        steps = int(round(config.area_step_scale / (side * side)))
        pair = evaluate_pair(
            center=config.area_center,
            side=side,
            steps_per_segment=steps,
            phase_relaxation=config.phase_relaxation,
            current_phase_gain=config.current_phase_gain,
        )
        area_pairs.append(pair)
        all_pairs.append(pair)
        line_flux_quotient_error = _relative_error(
            pair.tangent_line_integral_anti,
            local_quotient_center * pair.signed_flux_anti,
        )
        record = _pair_record(
            "coupled_area_tick_refinement",
            pair,
            response_curvature_at_center=f_center,
            projective_curvature_at_center=omega_center,
            local_two_form_quotient=local_quotient_center,
            response_density_relative_error=_relative_error(
                pair.discrete_cycle_sum_surrogate_anti / pair.signed_area_anti,
                f_center,
            ),
            flux_density_relative_error=_relative_error(
                pair.signed_flux_anti / pair.signed_area_anti,
                omega_center,
            ),
            tangent_line_vs_local_quotient_flux_relative_error=line_flux_quotient_error,
        )
        area_records.append(record)
        records.append(record)

    local_two_form_quotients: list[float] = []
    quotient_consistency_errors: list[float] = []
    for center in config.quotient_centers:
        f_local = response_curvature(
            center,
            config.derivative_steps[-1],
            config.phase_relaxation,
            config.current_phase_gain,
        )
        omega_local = projective_curvature(center, config.derivative_steps[-1])
        local_two_form_quotient = f_local / omega_local
        pair = evaluate_pair(
            center=center,
            side=config.quotient_side,
            steps_per_segment=config.quotient_steps_per_segment,
            phase_relaxation=config.phase_relaxation,
            current_phase_gain=config.current_phase_gain,
        )
        all_pairs.append(pair)
        finite_loop_quotient = pair.discrete_cycle_sum_surrogate_anti / pair.signed_flux_anti
        relative_error = _relative_error(finite_loop_quotient, local_two_form_quotient)
        local_two_form_quotients.append(local_two_form_quotient)
        quotient_consistency_errors.append(relative_error)
        record = _pair_record(
            "local_two_form_quotient_consistency",
            pair,
            response_curvature_at_center=f_local,
            projective_curvature_at_center=omega_local,
            local_two_form_quotient=local_two_form_quotient,
            local_quotient_consistency_relative_error=relative_error,
            quotient_has_independent_predictive_content=False,
        )
        records.append(record)

    null_records: list[dict[str, Any]] = []
    for null_name, alpha, gain in (
        ("current_phase_gain_zero", config.phase_relaxation, 0.0),
        ("phase_relaxation_one", 1.0, config.current_phase_gain),
    ):
        pair = evaluate_pair(
            center=config.null_center,
            side=config.null_side,
            steps_per_segment=config.null_steps_per_segment,
            phase_relaxation=alpha,
            current_phase_gain=gain,
        )
        all_pairs.append(pair)
        max_abs_sample = max(
            float(np.max(np.abs(pair.ccw.response.q_samples))),
            float(np.max(np.abs(pair.cw.response.q_samples))),
        )
        record = _pair_record(
            "same_observable_exact_null",
            pair,
            null_name=null_name,
            phase_relaxation=alpha,
            current_phase_gain=gain,
            max_abs_q_sample=max_abs_sample,
        )
        null_records.append(record)
        records.append(record)

    cyclic_spreads: list[float] = []
    cyclic_relative_spreads: list[float] = []
    for steps in config.cyclic_steps:
        values: list[float] = []
        for start_fraction in config.cyclic_start_fractions:
            pair = evaluate_pair(
                center=config.cyclic_center,
                side=config.cyclic_side,
                steps_per_segment=steps,
                phase_relaxation=config.phase_relaxation,
                current_phase_gain=config.current_phase_gain,
                start_fraction=start_fraction,
            )
            all_pairs.append(pair)
            values.append(pair.discrete_cycle_sum_surrogate_anti)
            records.append(_pair_record("cyclic_start_refinement", pair))
        spread = float(max(values) - min(values))
        mean_abs = abs(float(np.mean(values)))
        cyclic_spreads.append(spread)
        cyclic_relative_spreads.append(spread / mean_abs)

    response_derivative_stability = _relative_error(response_curvatures[-1], response_curvatures[-2])
    projective_derivative_stability = _relative_error(projective_curvatures[-1], projective_curvatures[-2])
    mean_decay_slope = _log_slope(
        [float(value) for value in config.refinement_steps],
        [abs(record["legacy_mean_response_anti"]) for record in refinement_records],
    )
    tangent_remainder_slope = _log_slope(
        [float(value) for value in config.refinement_steps],
        [record["absolute_tangent_remainder"] for record in refinement_records],
    )
    finest_refinement = refinement_records[-1]
    finest_q_tangent_error = _relative_error(
        finest_refinement["discrete_cycle_sum_surrogate_anti"],
        finest_refinement["tangent_line_integral_anti"],
    )
    response_area_errors = [record["response_density_relative_error"] for record in area_records]
    flux_area_errors = [record["flux_density_relative_error"] for record in area_records]
    line_flux_errors = [
        record["tangent_line_vs_local_quotient_flux_relative_error"] for record in area_records
    ]
    line_flux_relative_slope = _log_slope(
        [record["side"] for record in area_records],
        line_flux_errors,
    )
    max_null_sample = max(record["max_abs_q_sample"] for record in null_records)
    finest_area = area_records[-1]
    orientation_even_fraction = abs(finest_area["discrete_cycle_sum_surrogate_even"]) / abs(
        finest_area["discrete_cycle_sum_surrogate_anti"]
    )
    cyclic_spread_slope = _log_slope(
        [float(value) for value in config.cyclic_steps],
        cyclic_spreads,
    )
    max_recurrence_residual = max(
        max(
            pair.ccw.response.max_lag_recurrence_residual,
            pair.cw.response.max_lag_recurrence_residual,
        )
        for pair in all_pairs
    )
    max_phase_increment = max(
        max(
            pair.ccw.response.max_abs_phase_increment,
            pair.cw.response.max_abs_phase_increment,
        )
        for pair in all_pairs
    )
    max_lag_error = max(
        max(pair.ccw.response.max_abs_lag_error, pair.cw.response.max_abs_lag_error) for pair in all_pairs
    )
    fixed_branch = all(
        pair.ccw.switch_count == 0
        and pair.cw.switch_count == 0
        and pair.ccw.ambiguous_step_count == 0
        and pair.cw.ambiguous_step_count == 0
        and pair.ccw.unique_branch_ids == (CANONICAL_BRANCH_ID,)
        and pair.cw.unique_branch_ids == (CANONICAL_BRANCH_ID,)
        for pair in all_pairs
    )
    endpoints_duplicated = all(
        pair.ccw.endpoint_duplicated and pair.cw.endpoint_duplicated for pair in all_pairs
    )
    orientation_signs = all(
        pair.ccw.signed_area > 0.0
        and pair.cw.signed_area < 0.0
        and pair.signed_flux_anti > 0.0
        and pair.discrete_cycle_sum_surrogate_anti < 0.0
        for pair in area_pairs
    )

    finite_quotient_consistency = all(math.isfinite(value) for value in quotient_consistency_errors)
    finite_derivatives = all(math.isfinite(value) for value in response_curvatures + projective_curvatures)
    derivative_gate = (
        None
        if not finite_derivatives
        or not math.isfinite(response_derivative_stability)
        or not math.isfinite(projective_derivative_stability)
        else response_derivative_stability <= 1e-4 and projective_derivative_stability <= 1e-4
    )
    mean_decay_gate = None if not math.isfinite(mean_decay_slope) else -1.1 <= mean_decay_slope <= -0.9
    tangent_remainder_gate = (
        None if not math.isfinite(tangent_remainder_slope) else -1.15 <= tangent_remainder_slope <= -0.8
    )
    q_tangent_gate = None if not math.isfinite(finest_q_tangent_error) else finest_q_tangent_error <= 0.005
    response_area_gate = (
        None
        if not all(math.isfinite(value) for value in response_area_errors)
        else all(
            later < earlier for earlier, later in zip(response_area_errors[:-1], response_area_errors[1:])
        )
        and response_area_errors[-1] <= 5e-4
    )
    flux_area_gate = (
        None
        if not all(math.isfinite(value) for value in flux_area_errors)
        else all(later < earlier for earlier, later in zip(flux_area_errors[:-1], flux_area_errors[1:]))
        and flux_area_errors[-1] <= 2e-5
    )
    local_quotient_consistency_gate = (
        None if not finite_quotient_consistency else max(quotient_consistency_errors) <= 0.005
    )
    local_quotient_variation_gate = (
        None
        if not all(math.isfinite(value) for value in local_two_form_quotients)
        else max(local_two_form_quotients) - min(local_two_form_quotients) >= 0.15
    )
    cyclic_gate = (
        None
        if not math.isfinite(cyclic_spread_slope)
        or not all(math.isfinite(value) for value in cyclic_relative_spreads)
        else -1.1 <= cyclic_spread_slope <= -0.9 and cyclic_relative_spreads[-1] <= 0.007
    )
    spatial_quotient_consistency_gate = (
        None
        if not math.isfinite(line_flux_relative_slope)
        or not all(math.isfinite(value) for value in line_flux_errors)
        else 1.7 <= line_flux_relative_slope <= 2.3 and line_flux_errors[-1] <= 2e-4
    )
    gates = [
        _gate(
            "exact_lag_recurrence",
            max_recurrence_residual <= 5e-13,
            max_recurrence_residual,
            "max wrapped recurrence residual <= 5e-13",
        ),
        _gate(
            "fixed_branch_no_wrap_domain",
            fixed_branch and max_phase_increment < 0.1 and max_lag_error < 0.1,
            {
                "fixed_branch": fixed_branch,
                "max_abs_phase_increment": max_phase_increment,
                "max_abs_lag_error": max_lag_error,
            },
            "C0 only, no ambiguous steps, and phase increments/lags < 0.1 rad",
        ),
        _gate(
            "endpoint_duplication",
            endpoints_duplicated,
            endpoints_duplicated,
            "every loop includes the legacy duplicated endpoint",
        ),
        _gate(
            "tangent_derivative_stability",
            derivative_gate,
            {
                "response_relative_change": response_derivative_stability,
                "projective_relative_change": projective_derivative_stability,
            },
            "last-two central-difference relative changes <= 1e-4",
        ),
        _gate(
            "legacy_mean_vanishes_with_ticks",
            mean_decay_gate,
            mean_decay_slope,
            "log slope versus steps lies in [-1.1, -0.9]",
        ),
        _gate(
            "summed_remainder_is_inverse_tick",
            tangent_remainder_gate,
            tangent_remainder_slope,
            "|Q_anti-line integral| log slope lies in [-1.15, -0.8]",
        ),
        _gate(
            "discrete_cycle_sum_converges_to_tangent_line",
            q_tangent_gate,
            finest_q_tangent_error,
            "finest fixed-side relative error <= 0.005",
        ),
        _gate(
            "coupled_area_tick_response_limit",
            response_area_gate,
            response_area_errors,
            "m scales as 0.96/side^2; errors decrease and final error <= 5e-4",
        ),
        _gate(
            "wilson_flux_density_limit",
            flux_area_gate,
            flux_area_errors,
            "Wilson Phi_anti/area errors decrease and final error <= 2e-5",
        ),
        _gate(
            "two_dimensional_quotient_consistency",
            local_quotient_consistency_gate,
            quotient_consistency_errors,
            (
                "finite-loop Q_anti/Phi_anti approaches pointwise F_R/Omega within 0.5%; "
                "this is an algebraic 2D quotient consistency check, not predictive evidence"
            ),
        ),
        _gate(
            "local_two_form_quotient_is_not_common",
            local_quotient_variation_gate,
            {
                "local_two_form_quotients": local_two_form_quotients,
                "spread": max(local_two_form_quotients) - min(local_two_form_quotients),
            },
            "pointwise F_R/Omega quotient spread >= 0.15; no common coefficient is inferred",
        ),
        _gate(
            "same_observable_exact_nulls",
            max_null_sample <= 1e-14,
            max_null_sample,
            "gain=0 and phase_relaxation=1 each give max |q_t| <= 1e-14",
        ),
        _gate(
            "orientation_even_contamination",
            orientation_even_fraction <= 0.005,
            orientation_even_fraction,
            "|Q_even/Q_anti| <= 0.005 on the finest coupled refinement",
        ),
        _gate(
            "cyclic_start_remainder",
            cyclic_gate,
            {
                "spread_log_slope": cyclic_spread_slope,
                "relative_spreads": cyclic_relative_spreads,
            },
            "start-point spread scales as 1/m and final relative spread <= 0.007",
        ),
        _gate(
            "orientation_and_area_signs",
            orientation_signs,
            orientation_signs,
            "CCW/CW areas reverse, Phi_anti > 0, and Q_anti < 0",
        ),
        _gate(
            "two_dimensional_quotient_spatial_convergence",
            spatial_quotient_consistency_gate,
            {
                "relative_error_log_slope": line_flux_relative_slope,
                "relative_errors": line_flux_errors,
            },
            (
                "line-vs-local-(F_R/Omega)*Phi consistency error is second order and final "
                "<= 2e-4; this has no independent predictive content"
            ),
        ),
    ]

    failed = [gate["name"] for gate in gates if gate["status"] == "fail"]
    indeterminate = [gate["name"] for gate in gates if gate["status"] == "indeterminate"]
    status = "fail" if failed else ("indeterminate" if indeterminate else "pass")
    summary = {
        "schema_version": 1,
        "experiment_id": "independent_response_theorem",
        "status": status,
        "evidence_tier": "internal_synthetic_analytic_fixture",
        "claim_scope": "explicit benchmark-C fixed-tick geometry-blind-response theorem",
        "central_empirical_external_claim_status": "proof_incomplete",
        "estimand": "discrete_cycle_sum_surrogate",
        "estimand_units": "circulation-current-ticks with dt=1",
        "legacy_mean_response_preserved": True,
        "estimand_and_thresholds_selected_after_exploratory_probe": True,
        "two_dimensional_pointwise_proportionality_is_algebraic": True,
        "quotient_consistency_is_not_predictive_evidence": True,
        "not_preregistered": True,
        "not_untouched_holdout": True,
        "not_external_evidence": True,
        "config": config.as_dict(),
        "metrics": {
            "response_curvature_center": response_curvatures[-1],
            "projective_curvature_center": projective_curvatures[-1],
            "local_two_form_quotient_center": local_quotient_center,
            "response_derivative_stability": response_derivative_stability,
            "projective_derivative_stability": projective_derivative_stability,
            "legacy_mean_log_slope": mean_decay_slope,
            "summed_tangent_remainder_log_slope": tangent_remainder_slope,
            "finest_q_to_tangent_relative_error": finest_q_tangent_error,
            "finest_response_density_relative_error": response_area_errors[-1],
            "finest_flux_density_relative_error": flux_area_errors[-1],
            "max_local_quotient_consistency_relative_error": max(quotient_consistency_errors),
            "local_two_form_quotient_spread": (max(local_two_form_quotients) - min(local_two_form_quotients)),
            "max_exact_null_q_sample": max_null_sample,
            "orientation_even_fraction": orientation_even_fraction,
            "cyclic_start_spread_log_slope": cyclic_spread_slope,
            "finest_cyclic_start_relative_spread": cyclic_relative_spreads[-1],
            "max_lag_recurrence_residual": max_recurrence_residual,
        },
        "gates": gates,
        "failed_gates": failed,
        "indeterminate_gates": indeterminate,
    }
    return summary, records

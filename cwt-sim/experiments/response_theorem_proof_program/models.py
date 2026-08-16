"""Exact contracting-map and stable-ODE fixtures for the proof program."""

from __future__ import annotations

import math
from collections.abc import Callable

import numpy as np

from .contracts import Array, OneForm, OrientationPair, ResponseCycle
from .forms import exact_reverse


def _validate_rho(rho: float) -> float:
    value = float(rho)
    if not math.isfinite(value) or not 0.0 < value < 1.0:
        raise ValueError("rho must lie strictly between zero and one")
    return value


def unique_periodic_initial_state(path: Array, rho: float) -> Array:
    """Solve the unique driven-periodic initial condition for the linear map."""

    path_arr = np.asarray(path, dtype=float)
    contraction = _validate_rho(rho)
    if path_arr.ndim != 2 or path_arr.shape[0] < 2 or not np.array_equal(path_arr[0], path_arr[-1]):
        raise ValueError("path must be an explicitly closed sample array")
    steps = path_arr.shape[0] - 1
    powers = contraction ** np.arange(steps - 1, -1, -1, dtype=float)
    forcing = (1.0 - contraction) * np.sum(powers[:, None] * path_arr[1:], axis=0)
    return forcing / (1.0 - contraction**steps)


def realizability_cycle(
    beta: OneForm,
    path: Array,
    rho: float,
    *,
    initialization: str = "equilibrium",
) -> ResponseCycle:
    """Execute the exact no-go construction with update-then-sample timing.

    F(x,lambda)=rho*x+(1-rho)*lambda and
    r=-(1-rho)/rho beta(lambda).(x-lambda) realize B=beta.
    """

    path_arr = np.asarray(path, dtype=float)
    contraction = _validate_rho(rho)
    if path_arr.ndim != 2 or path_arr.shape[0] < 2 or not np.array_equal(path_arr[0], path_arr[-1]):
        raise ValueError("path must be explicitly closed")
    if initialization == "equilibrium":
        state = path_arr[0].copy()
    elif initialization == "periodic":
        state = unique_periodic_initial_state(path_arr, contraction)
    else:
        raise ValueError("initialization must be 'equilibrium' or 'periodic'")

    states = [state.copy()]
    samples: list[float] = []
    response_scale = -(1.0 - contraction) / contraction
    for parameter in path_arr[1:]:
        state = contraction * state + (1.0 - contraction) * parameter
        centered = state - parameter
        samples.append(float(response_scale * np.asarray(beta(parameter), dtype=float) @ centered))
        states.append(state.copy())
    return ResponseCycle(
        path=path_arr,
        states=np.asarray(states, dtype=float),
        samples=np.asarray(samples, dtype=float),
        total_response=float(np.sum(samples)),
        initialization=initialization,
        rho=contraction,
    )


def realizability_pair(
    beta: OneForm,
    positive_path: Array,
    rho: float,
    *,
    initialization: str = "equilibrium",
) -> OrientationPair:
    """Execute an exact path and its exact reversal."""

    return OrientationPair(
        positive=realizability_cycle(beta, positive_path, rho, initialization=initialization),
        reverse=realizability_cycle(beta, exact_reverse(positive_path), rho, initialization=initialization),
    )


def realized_tangent_one_form(beta: OneForm, point: Array, rho: float) -> Array:
    """Evaluate -H(I-M)^-1 M X for the exact no-go construction."""

    contraction = _validate_rho(rho)
    beta_value = np.asarray(beta(np.asarray(point, dtype=float)), dtype=float)
    dimension = beta_value.size
    hessian_row = -(1.0 - contraction) / contraction * beta_value
    resolvent = np.eye(dimension, dtype=float) / (1.0 - contraction)
    tangent = np.eye(dimension, dtype=float)
    return -hessian_row @ resolvent @ (contraction * np.eye(dimension)) @ tangent


def interaction_pair(
    beta_on: OneForm,
    beta_zero: OneForm,
    path: Array,
    rho: float,
    *,
    initialization: str = "equilibrium",
) -> dict[str, float]:
    """Return Qanti,on, Qanti,0, D, and the ordinary factor-two DID."""

    on_pair = realizability_pair(beta_on, path, rho, initialization=initialization)
    zero_pair = realizability_pair(beta_zero, path, rho, initialization=initialization)
    interaction = on_pair.anti - zero_pair.anti
    return {
        "qanti_on": on_pair.anti,
        "qanti_zero": zero_pair.anti,
        "interaction_D": interaction,
        "ordinary_difference_in_differences": 2.0 * interaction,
        "orientation_even_on": on_pair.even,
        "orientation_even_zero": zero_pair.even,
    }


def alpha_from_dt(dt: float, tau: float) -> float:
    """Exact held-input relaxation map alpha(dt)=1-exp(-dt/tau)."""

    dt_value = float(dt)
    tau_value = float(tau)
    if not math.isfinite(dt_value) or not math.isfinite(tau_value) or dt_value <= 0.0 or tau_value <= 0.0:
        raise ValueError("dt and tau must be positive and finite")
    return float(1.0 - math.exp(-dt_value / tau_value))


def continuous_harmonic_cycle(
    beta: OneForm,
    center: Array,
    scale: float,
    tau: float,
    period: float,
    *,
    initialization: str,
    samples: int = 32768,
) -> dict[str, float]:
    """Integrate an exact stable-ODE harmonic solution and centered readout.

    The ODE is dx/dt=(lambda(t)-x)/tau and the readout is
    r=-(1/tau) beta(lambda).(x-lambda), for which B=beta.
    """

    center_arr = np.asarray(center, dtype=float)
    if center_arr.shape != (2,):
        raise ValueError("continuous harmonic fixture requires a 2D center")
    if scale <= 0.0 or tau <= 0.0 or period <= 0.0 or samples < 64:
        raise ValueError("scale, tau, period, and samples must be positive")
    times = np.linspace(0.0, float(period), int(samples) + 1)
    omega = 2.0 * np.pi / float(period)
    phase = omega * times
    parameters = center_arr[None, :] + float(scale) * np.column_stack((np.cos(phase), np.sin(phase)))
    lag_ratio = omega * float(tau)
    periodic_offsets = (
        float(scale)
        / (1.0 + lag_ratio**2)
        * np.column_stack(
            (np.cos(phase) + lag_ratio * np.sin(phase), np.sin(phase) - lag_ratio * np.cos(phase))
        )
    )
    periodic_state = center_arr[None, :] + periodic_offsets
    if initialization == "periodic":
        states = periodic_state
    elif initialization == "equilibrium":
        initial_state = parameters[0]
        transient = np.exp(-times / float(tau))[:, None] * (initial_state - periodic_state[0])[None, :]
        states = periodic_state + transient
    else:
        raise ValueError("initialization must be 'equilibrium' or 'periodic'")
    response = np.asarray(
        [
            -(np.asarray(beta(parameter), dtype=float) @ (state - parameter)) / float(tau)
            for parameter, state in zip(parameters, states)
        ],
        dtype=float,
    )
    total = float(np.trapezoid(response, times))
    return {
        "total_response": total,
        "max_centered_state": float(np.max(np.linalg.norm(states - parameters, axis=1))),
        "tau_over_period": float(tau / period),
        "alpha_at_sample_dt": alpha_from_dt(period / samples, tau),
    }


def centered_readout(
    beta: OneForm,
    rho: float,
) -> Callable[[Array, Array], float]:
    """Return the realizability theorem's centered readout function."""

    contraction = _validate_rho(rho)
    scale = -(1.0 - contraction) / contraction

    def readout(state: Array, parameter: Array) -> float:
        parameter_arr = np.asarray(parameter, dtype=float)
        return float(
            scale * np.asarray(beta(parameter_arr), dtype=float) @ (np.asarray(state) - parameter_arr)
        )

    return readout

"""Pure finite-dimensional path, one-form, and projective-geometry helpers."""

from __future__ import annotations

import math

import numpy as np

from .contracts import Array, OneForm, StateMap


def closed_circle_path(
    center: Array,
    scale: float,
    steps: int,
    *,
    reverse: bool = False,
) -> Array:
    """Return an exact-reverse pairable circle with both endpoints present."""

    center_arr = np.asarray(center, dtype=float)
    if center_arr.shape != (2,):
        raise ValueError("the circle fixture requires a two-dimensional center")
    if not math.isfinite(scale) or scale <= 0.0:
        raise ValueError("scale must be positive and finite")
    if steps < 8:
        raise ValueError("steps must be at least eight")
    angles = np.linspace(0.0, 2.0 * np.pi, int(steps) + 1)
    offsets = np.column_stack((np.cos(angles), np.sin(angles)))
    path = center_arr[None, :] + float(scale) * offsets
    path[-1] = path[0]
    return path[::-1].copy() if reverse else path


def exact_reverse(path: Array) -> Array:
    """Reverse an explicitly closed sampled path exactly."""

    path_arr = np.asarray(path, dtype=float)
    if path_arr.ndim != 2 or path_arr.shape[0] < 2:
        raise ValueError("path must be a two-dimensional sample array")
    if not np.array_equal(path_arr[0], path_arr[-1]):
        raise ValueError("path must be exactly closed")
    return path_arr[::-1].copy()


def rotational_one_form(kappa: float) -> OneForm:
    """Return beta=(-kappa*y/2, kappa*x/2), so d beta=kappa dx^dy."""

    coefficient = float(kappa)

    def beta(point: Array) -> Array:
        x, y = np.asarray(point, dtype=float)
        return np.asarray((-0.5 * coefficient * y, 0.5 * coefficient * x), dtype=float)

    return beta


def line_integral(one_form: OneForm, path: Array) -> float:
    """Trapezoid-evaluate a one-form on an explicitly closed polygonal path."""

    path_arr = np.asarray(path, dtype=float)
    if path_arr.ndim != 2 or path_arr.shape[0] < 2:
        raise ValueError("path must be a two-dimensional sample array")
    if not np.array_equal(path_arr[0], path_arr[-1]):
        raise ValueError("path must be exactly closed")
    total = 0.0
    for start, stop in zip(path_arr[:-1], path_arr[1:]):
        total += float(0.5 * (one_form(start) + one_form(stop)) @ (stop - start))
    return total


def area_bivector(path: Array) -> Array:
    """Return A^{ij}=1/2 integral(x^i dx^j-x^j dx^i)."""

    path_arr = np.asarray(path, dtype=float)
    if path_arr.ndim != 2 or path_arr.shape[0] < 2:
        raise ValueError("path must be a two-dimensional sample array")
    if not np.array_equal(path_arr[0], path_arr[-1]):
        raise ValueError("path must be exactly closed")
    dimension = path_arr.shape[1]
    area = np.zeros((dimension, dimension), dtype=float)
    for start, stop in zip(path_arr[:-1], path_arr[1:]):
        area += 0.5 * (np.outer(start, stop) - np.outer(stop, start))
    return area


def exterior_derivative(one_form: OneForm, point: Array, step: float = 1e-5) -> Array:
    """Centered finite-difference exterior derivative dB."""

    point_arr = np.asarray(point, dtype=float)
    if point_arr.ndim != 1:
        raise ValueError("point must be one-dimensional")
    if not math.isfinite(step) or step <= 0.0:
        raise ValueError("step must be positive and finite")
    dimension = point_arr.size
    jacobian = np.zeros((dimension, dimension), dtype=float)
    for coordinate in range(dimension):
        delta = np.zeros(dimension, dtype=float)
        delta[coordinate] = step
        forward = np.asarray(one_form(point_arr + delta), dtype=float)
        backward = np.asarray(one_form(point_arr - delta), dtype=float)
        if forward.shape != (dimension,) or backward.shape != (dimension,):
            raise ValueError("one-form dimension does not match its parameter point")
        jacobian[:, coordinate] = (forward - backward) / (2.0 * step)
    # jacobian[j, i] is partial_i B_j, hence
    # (dB)_{ij}=partial_i B_j-partial_j B_i.
    return jacobian.T - jacobian


def normalized_state(state_map: StateMap, point: Array) -> Array:
    """Evaluate and normalize a nonzero complex state."""

    state = np.asarray(state_map(np.asarray(point, dtype=float)), dtype=complex)
    if state.ndim != 1:
        raise ValueError("state map must return a vector")
    norm = float(np.linalg.norm(state))
    if not math.isfinite(norm) or norm <= 0.0:
        raise ValueError("state map must return a finite nonzero vector")
    return state / norm


def projective_curvature_tensor(state_map: StateMap, point: Array, step: float = 1e-5) -> Array:
    """Return Omega_ij=+2 Im <D_i psi|D_j psi> in the repository convention."""

    point_arr = np.asarray(point, dtype=float)
    psi = normalized_state(state_map, point_arr)
    derivatives: list[Array] = []
    for coordinate in range(point_arr.size):
        delta = np.zeros(point_arr.size, dtype=float)
        delta[coordinate] = step
        derivative = (
            normalized_state(state_map, point_arr + delta) - normalized_state(state_map, point_arr - delta)
        ) / (2.0 * step)
        derivatives.append(derivative - psi * np.vdot(psi, derivative))
    curvature = np.zeros((point_arr.size, point_arr.size), dtype=float)
    for i in range(point_arr.size):
        for j in range(point_arr.size):
            curvature[i, j] = float(2.0 * np.imag(np.vdot(derivatives[i], derivatives[j])))
    return curvature


def bloch_state(point: Array) -> Array:
    """Three-control CP1 state used by the internal positive-control fixture."""

    x, y, z = np.asarray(point, dtype=float)
    polar = x + z
    azimuth = y + 2.0 * z
    return np.asarray(
        [np.cos(0.5 * polar), np.exp(1j * azimuth) * np.sin(0.5 * polar)],
        dtype=complex,
    )


def bloch_connection(point: Array) -> Array:
    """A=-i<psi|d psi> for ``bloch_state`` in its smooth local gauge."""

    x, _y, z = np.asarray(point, dtype=float)
    polar = x + z
    weight = float(np.sin(0.5 * polar) ** 2)
    return weight * np.asarray((0.0, 1.0, 2.0), dtype=float)


def two_form_vector(two_form: Array) -> Array:
    """Map a three-dimensional two-form to (F23,F31,F12)."""

    form = np.asarray(two_form, dtype=float)
    if form.shape != (3, 3):
        raise ValueError("two-form vectorization requires a 3x3 matrix")
    return np.asarray((form[1, 2], form[2, 0], form[0, 1]), dtype=float)


def normalized_area_condition(vectors: Array) -> float:
    """Frobenius condition number of row-normalized three-dimensional areas."""

    values = np.asarray(vectors, dtype=float)
    if values.ndim != 2 or values.shape[1] != 3:
        raise ValueError("area vectors must have shape (n, 3)")
    norms = np.linalg.norm(values, axis=1)
    if np.any(norms <= 0.0):
        raise ValueError("area vectors must be nonzero")
    normalized = values / norms[:, None]
    return float(
        np.linalg.norm(normalized, ord="fro") * np.linalg.norm(np.linalg.pinv(normalized), ord="fro")
    )


def pullback_two_form(two_form: Array, jacobian: Array) -> Array:
    """Pull a covariant two-form back through lambda=J mu."""

    form = np.asarray(two_form, dtype=float)
    transform = np.asarray(jacobian, dtype=float)
    return transform.T @ form @ transform


def conditional_alignment_bound(
    surface_mass: float,
    sup_error: float,
    dynamic_remainder: float,
    *,
    kappa_lipschitz: float = 0.0,
    omega_comass_sup: float = 0.0,
    surface_diameter: float = 0.0,
) -> float:
    """Bound a center-kappa predictor using surface mass and the two-form comass."""

    values = (
        float(surface_mass),
        float(sup_error),
        float(dynamic_remainder),
        float(kappa_lipschitz),
        float(omega_comass_sup),
        float(surface_diameter),
    )
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("bound inputs must be finite and nonnegative")
    mass, error, remainder, lipschitz, omega_sup, diameter = values
    return mass * (error + lipschitz * omega_sup * diameter) + remainder


def log_slope(xs: list[float], ys: list[float]) -> float:
    """Return a finite log-log slope for positive samples."""

    x_values = np.asarray(xs, dtype=float)
    y_values = np.asarray(ys, dtype=float)
    mask = np.isfinite(x_values) & np.isfinite(y_values) & (x_values > 0.0) & (y_values > 0.0)
    if int(np.sum(mask)) < 2:
        raise ValueError("at least two positive finite samples are required")
    return float(np.polyfit(np.log(x_values[mask]), np.log(y_values[mask]), 1)[0])

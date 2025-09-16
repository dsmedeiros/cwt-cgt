"""Parameter path utilities for orchestrating simulations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal


@dataclass
class ParameterPath:
    """Discretized parameter-space paths used by the orchestrator.

    The path generates a sequence of points :math:`\\lambda_s`, step increments
    ``Δλ_s`` and (optionally) oriented area elements ``Δσ_s``.  These are used to
    drive control loops and apply curvature-dependent bias corrections.
    """

    kind: Literal["rectangle", "line", "lissajous", "torus_loop"]
    center: dict[str, float]
    extents: dict[str, float]
    steps: int
    orientation: Literal["CW", "CCW"] = "CCW"
    periodic: dict[str, bool] | None = None
    corner_area_mode: bool = True

    def __post_init__(self) -> None:
        if self.steps <= 0:
            raise ValueError("steps must be positive")

        if self.orientation not in {"CW", "CCW"}:
            raise ValueError(f"invalid orientation: {self.orientation}")

        self._orientation_sign = 1 if self.orientation == "CCW" else -1

        knob_keys = set(self.center) | set(self.extents)
        if not knob_keys:
            raise ValueError("center/extents must specify at least one knob")

        self._knobs = sorted(knob_keys)
        self._center = {k: float(self.center.get(k, 0.0)) for k in self._knobs}
        self._extents = {k: float(self.extents.get(k, 0.0)) for k in self._knobs}
        if self.periodic:
            self._periodic = {k: bool(self.periodic.get(k, False)) for k in self._knobs}
        else:
            self._periodic = {k: False for k in self._knobs}

        self._varying = [k for k in self._knobs if abs(self._extents[k]) > 0.0]

        builders = {
            "rectangle": self._build_rectangle_path,
            "line": self._build_line_path,
            "lissajous": self._build_lissajous_path,
            "torus_loop": self._build_torus_loop_path,
        }
        try:
            builder = builders[self.kind]
        except KeyError as exc:  # pragma: no cover - Literal prevents this in practice
            raise ValueError(f"unknown path kind: {self.kind}") from exc

        self._lambdas, self._deltas, self._areas = builder()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def step(self, s: int) -> tuple[dict[str, float], dict[str, float], float]:
        """Return the state, increment and area contribution for step ``s``.

        Parameters
        ----------
        s:
            Zero-based step index.  The method wraps around so ``s`` may be any
            integer.
        """

        idx = s % self.steps
        lambda_state = dict(self._lambdas[idx])
        delta_state = dict(self._deltas[idx])
        area = self._areas[idx]
        return lambda_state, delta_state, area

    # ------------------------------------------------------------------
    # Path construction helpers
    # ------------------------------------------------------------------
    def _build_rectangle_path(self) -> tuple[list[dict[str, float]], list[dict[str, float]], list[float]]:
        if len(self._varying) < 2:
            raise ValueError("rectangle path requires at least two varying knobs")
        if self.steps < 4:
            raise ValueError("rectangle path requires at least four steps")

        axes = self._varying[:2]
        steps_per_edge = self._split_steps(self.steps, 4)
        if min(steps_per_edge) <= 0:
            raise ValueError("insufficient steps to cover rectangle edges")

        corners = [
            (-1.0, -1.0),  # bottom-left
            (1.0, -1.0),  # bottom-right
            (1.0, 1.0),  # top-right
            (-1.0, 1.0),  # top-left
        ]
        if self._orientation_sign > 0:
            order = [0, 1, 2, 3]
        else:
            order = [0, 3, 2, 1]

        lambda_steps: list[dict[str, float]] = []
        delta_steps: list[dict[str, float]] = []
        area_steps: list[float] = []
        corner_area = abs(self._extents[axes[0]]) * abs(self._extents[axes[1]])

        for edge_idx in range(4):
            count = steps_per_edge[edge_idx]
            start_corner = corners[order[edge_idx]]
            end_corner = corners[order[(edge_idx + 1) % 4]]
            delta_norm = [(end_corner[i] - start_corner[i]) / count for i in range(2)]
            current_norm = [start_corner[0], start_corner[1]]

            for step_in_edge in range(count):
                lambda_state = self._center.copy()
                delta_state = {k: 0.0 for k in self._knobs}
                for axis_i, axis_name in enumerate(axes):
                    extent = self._extents[axis_name]
                    lambda_state[axis_name] = self._center[axis_name] + extent * current_norm[axis_i]
                    delta_state[axis_name] = extent * delta_norm[axis_i]

                if self.corner_area_mode and step_in_edge == 0:
                    area_steps.append(self._orientation_sign * corner_area)
                else:
                    area_steps.append(delta_state[axes[0]] * delta_state[axes[1]])

                lambda_steps.append(lambda_state)
                delta_steps.append(delta_state)

                current_norm[0] += delta_norm[0]
                current_norm[1] += delta_norm[1]

        return lambda_steps, delta_steps, area_steps

    def _build_line_path(self) -> tuple[list[dict[str, float]], list[dict[str, float]], list[float]]:
        axes = self._varying[:1] if self._varying else []
        if not axes:
            axes = [self._knobs[0]]

        axis = axes[0]
        lambda_steps: list[dict[str, float]] = []
        for step_index in range(self.steps):
            u = ((self._orientation_sign * step_index) / self.steps) % 1.0
            norm = self._triangular_wave(u)
            lambda_state = self._center.copy()
            lambda_state[axis] = self._center[axis] + self._extents[axis] * norm
            lambda_steps.append(lambda_state)

        delta_steps = self._make_deltas(lambda_steps)
        area_steps = [0.0 for _ in range(self.steps)]
        return lambda_steps, delta_steps, area_steps

    def _build_lissajous_path(self) -> tuple[list[dict[str, float]], list[dict[str, float]], list[float]]:
        if not self._varying:
            raise ValueError("lissajous path requires at least one varying knob")

        lambda_steps: list[dict[str, float]] = []
        for step_index in range(self.steps):
            u = ((self._orientation_sign * step_index) / self.steps) % 1.0
            t = 2.0 * math.pi * u
            lambda_state = self._center.copy()
            for axis_index, axis_name in enumerate(self._varying):
                amplitude = self._extents[axis_name]
                if amplitude == 0.0:
                    continue
                omega = axis_index + 1
                phase = axis_index * (math.pi / 2.0)
                lambda_state[axis_name] = self._center[axis_name] + amplitude * math.sin(omega * t + phase)
            lambda_steps.append(lambda_state)

        delta_steps = self._make_deltas(lambda_steps)
        area_steps = self._compute_area_from_deltas(delta_steps, self._varying)
        return lambda_steps, delta_steps, area_steps

    def _build_torus_loop_path(self) -> tuple[list[dict[str, float]], list[dict[str, float]], list[float]]:
        if not self._varying:
            raise ValueError("torus loop requires at least one varying knob")

        raw_steps: list[dict[str, float]] = []
        wrapped_steps: list[dict[str, float]] = []
        for step_index in range(self.steps):
            u = ((self._orientation_sign * step_index) / self.steps) % 1.0
            t = 2.0 * math.pi * u
            raw_state = self._center.copy()
            for axis_index, axis_name in enumerate(self._varying):
                amplitude = self._extents[axis_name]
                if amplitude == 0.0:
                    continue
                omega = axis_index + 1
                phase = axis_index * (math.pi / 2.0)
                raw_state[axis_name] = self._center[axis_name] + amplitude * math.sin(omega * t + phase)
            raw_steps.append(raw_state)

            wrapped_state = raw_state.copy()
            for knob in self._knobs:
                if self._periodic.get(knob, False):
                    wrapped_value = wrapped_state[knob] % 1.0
                    if math.isclose(wrapped_value, 1.0, rel_tol=0.0, abs_tol=1e-9):
                        wrapped_value = 0.0
                    wrapped_state[knob] = wrapped_value
            wrapped_steps.append(wrapped_state)

        delta_steps = self._make_deltas(raw_steps, apply_periodic=True)
        area_steps = self._compute_area_from_deltas(delta_steps, self._varying)
        return wrapped_steps, delta_steps, area_steps

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------
    def _make_deltas(
        self,
        positions: list[dict[str, float]],
        *,
        apply_periodic: bool = False,
    ) -> list[dict[str, float]]:
        delta_steps: list[dict[str, float]] = []
        for step_index in range(self.steps):
            current = positions[step_index]
            nxt = positions[(step_index + 1) % self.steps]
            delta_state: dict[str, float] = {}
            for knob in self._knobs:
                current_val = current.get(knob, self._center[knob])
                next_val = nxt.get(knob, self._center[knob])
                diff = next_val - current_val
                if apply_periodic and self._periodic.get(knob, False):
                    diff -= round(diff)
                delta_state[knob] = diff
            delta_steps.append(delta_state)
        return delta_steps

    @staticmethod
    def _compute_area_from_deltas(
        deltas: list[dict[str, float]],
        axes: list[str],
    ) -> list[float]:
        if len(axes) < 2:
            return [0.0 for _ in deltas]
        axis_i, axis_j = axes[0], axes[1]
        return [delta.get(axis_i, 0.0) * delta.get(axis_j, 0.0) for delta in deltas]

    @staticmethod
    def _split_steps(total_steps: int, segments: int) -> list[int]:
        base = total_steps // segments
        remainder = total_steps % segments
        allocation = [base for _ in range(segments)]
        for i in range(remainder):
            allocation[i] += 1
        return allocation

    @staticmethod
    def _triangular_wave(u: float) -> float:
        frac = u % 1.0
        cycle = (frac * 2.0) % 2.0
        value = 1.0 - abs(cycle - 1.0)
        return 2.0 * value - 1.0


def placeholder_param_path() -> list[float]:
    """Return a trivial parameter path."""

    return [0.0]
